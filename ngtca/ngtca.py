import argparse
import logging
import json
import sys
import os
import re
import html
import mimetypes
from datetime import datetime
from pathlib import Path

import frontmatter
from mistletoe import Document
from mistletoe.span_token import Image, Link
from mistletoe.html_renderer import HTMLRenderer
from confluence.client import Confluence
from confluence.exceptions.resourcenotfound import ConfluenceResourceNotFound
from confluence.exceptions.generalerror import ConfluenceError
from confluence.models.content import ContentType, ContentStatus
from confluence.models.label import Label, LabelPrefix

from ngtca import __version__ as ngtca_version

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='[%(asctime)s] %(name)8s [%(levelname)-8s] %(filename)10s:%(lineno)-4d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


class NoValidPathException(Exception):
    """
    Path is not valid, cannot be used for parsing pages.
    """

    pass


class CreatePageException(Exception):
    """
    Could not create page, due to some unknown error. Thanks Confluence
    for making everything difficult.
    """

    def __init__(self, message, response):
        self.reason = json.loads(response.content)['message']


class InvalidParentException(Exception):
    """
    Parent title or ID is invalid.
    """

    pass


class ConfluenceRenderer(HTMLRenderer):
    """
    I just need the fenced code blocks changed, that's all.
    """

    def __init__(self, root):
        super().__init__()
        self.root = root

    # TODO: what about for links to images? does that work? do I care at the time? nah, not really

    def render_image(self, token):
        template = '!{src}!'
        inner = self.render_inner(token)
        # Use base filename as attachment if local, otherwise as is is fine
        fpath = self.root.joinpath(Path(token.src)).resolve()
        if fpath.is_file():
            return f'<ac:image><ri:attachment ri:filename="{fpath.name}" /></ac:image>'
            # return template.format(src=fpath.name)
        return template.format(src=token.src)

    def render_link(self, token):
        # If it's a file, we generate a macro link from the c_* attributes
        template = '<ac:link><ri:page {link}{anchor} /><ac:plain-text-link-body><![CDATA[{title}]]></ac:plain-text-link-body></ac:link>'
        fpath = self.root.joinpath(Path(token.target.split('#', 1)[0])).resolve()
        if fpath.is_file():
            # No type == text (non-binary)
            if mimetypes.guess_type(str(fpath))[0] == None:
                fm = frontmatter.load(fpath)
                c_title = fm.get('c_title')
                c_space = fm.get('c_space')
                anchor = ''
                inner = self.render_inner(token)
                # This will sorta kinda estimate what the anchor will look like,
                # however, this won't work pretty much at all if the anchor has
                # punctuation in it of any kind since Confluence keeps the punctuation
                # e.g. Why Not? becomes WhyNot?, in kramdown it becomes why-not
                # ugh
                if '#' in token.target:
                    anchor = token.target.split('#', 1)[1]
                    anchor = anchor.replace('-', ' ')
                    anchor = anchor.title().replace(' ', '')
                    anchor = f'{c_title.replace(" ", "")}-{anchor}'
                    anchor = f' ac:anchor="{anchor}"'
                if c_space:
                    return template.format(
                        link=f'ri:content-title="{html.escape(c_title)}" ri:space-key="{c_space}"',
                        title=inner,
                        anchor=anchor,
                    )
                else:
                    return template.format(
                        link=f'ri:content-title="{html.escape(c_title)}"', title=inner, anchor=anchor
                    )
            else:
                # Link to media, e.g. a PDF
                title = self.render_inner(token)
                template = '<ac:link><ri:attachment ri:filename="{link}" /><ac:plain-text-link-body><![CDATA[{title}]]></ac:plain-text-link-body></ac:link>'
                return template.format(link=fpath.name, title=title)

        # Otherwise do the standard link procedure
        # TODO: should this use the jira notation instead?
        template = '<a href="{target}"{title}>{inner}</a>'
        target = self.escape_url(token.target)
        if token.title:
            title = ' title="{}"'.format(self.escape_html(token.title))
        else:
            title = ''
        inner = self.render_inner(token)
        return template.format(target=target, title=title, inner=inner)

    def render_block_code(self, token):
        """
        Render fenced code blocks for Confluence because apparently it's too
        hard to ask for some form of convenience.
        """
        template = (
            '<ac:structured-macro ac:name="code">\n{attr}\n'
            '<ac:plain-text-body><![CDATA[{inner}]]></ac:plain-text-body>\n'
            '</ac:structured-macro>\n'
        )

        # Include lang parameter, else specify text (no syntax)
        attr = f'<ac:parameter ac:name="language">{token.language or "text"}' '</ac:parameter>'

        # Don't do parsing further down, if you do it will use the html entities
        # which is fine. Except in Confluence this means it is presented as the
        # literal entity (not what it should be) because code blocks are just
        # raw text
        inner = token.children[0].content.rstrip()
        return template.format(attr=attr, inner=inner)


class Book:
    """
    Handles pages, updates, creates them, passes confluence object around,
    stuff like that.
    """

    def __init__(self, conf_endpoint, conf_user, conf_pass, pages=None):
        self._client = Confluence(conf_endpoint, (conf_user, conf_pass))
        self.pages = set(pages or [])
        self.labels = set()

    def add_pages(self, *pages):
        """
        Add page to Book, along with adding appropriate metadata where
        appropriate.
        """
        for page in pages:

            # These won't be synced
            if not page._metadata or not page.title:
                logger.debug(f'Skipping {page}, no metadata or title')
                continue

            page.labels = self.labels | page.labels
            self.pages.add(page)
            logger.debug(f'Added page {page}')

    def add_path(self, path):
        """
        Build and add page(s) from directory or path.
        """
        pages = set()
        path = Path(path)

        # Only directories/files are valid uses
        if path.is_dir():
            logger.info(f'{path} is a directory, searching for markdown files recursively')
            for file in path.glob('**/*.md'):
                try:
                    page = Page.from_file(file)
                    pages.add(page)
                except Exception as e:
                    logger.exception(f'could not render file {file}')
        elif path.is_file():
            logger.info(f'{path} is a file, using file')
            pages.add(Page.from_file(path))
        else:
            logger.error(f'{path} is neither a directory or file')
            raise NoValidPathException(f'{path} is not a valid path')

        self.add_pages(*pages)

    def _create_page(self, page):
        """
        Create new page.
        """
        parent_content_id = None
        if page.parent:
            if page.parent.isdigit():
                parent_content_id = page.parent
            else:
                parent_content_id = list(self._client.get_content(space_key=page.space, title=page.parent))[0].id
                logger.debug(f'Found parent for {page} is {parent_content_id}')

            try:
                self._client.get_content_by_id(parent_content_id)
            except ConfluenceError:
                raise InvalidParentException(f'{page} has no valid parent, skipping')

        try:
            content = self._client.create_content(
                content_type=ContentType.PAGE,
                title=page.title,
                space_key=page.space,
                content=page.html,
                parent_content_id=parent_content_id,
            )
        except ConfluenceError as e:
            raise CreatePageException(f'{page} could not be created', e.response)

        return content

    def _update_page(self, page):
        """
        Update existing page.
        """
        logger.debug(f'Updating {page}')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        old_content = list(self._client.get_content(space_key=page.space, title=page.title, expand=['version']))[0]

        # TODO: set parents etc?

        new_content = self._client.update_content(
            old_content.id,
            old_content.type,
            old_content.version.number + 1,
            page.html,
            old_content.title,
            minor_edit=True,
            edit_message=f'Updated via NGTCA at {now}',
            status=old_content.status,
            new_status=ContentStatus.CURRENT,
        )

        return new_content

    def _set_labels(self, page, content):
        """
        Reuse Confluence content resource to set labels. Gets, deletes and sets
        the labels of a  content body (page).
        """
        logger.debug(f'Setting labels for {page} to {", ".join(page.labels)}')

        current_labels = set([l.name for l in self._client.get_labels(content.id, LabelPrefix.GLOBAL)])
        for label in current_labels:
            if label not in page.labels:
                self._client.delete_label(content.id, label)

        if page.labels:
            self._client.create_labels(content.id, [(LabelPrefix.GLOBAL, l) for l in page.labels])

    def _page_exists(self, page):
        """
        Whether or not a page exists within confluence.
        """
        title_esc = page.title.translate(str.maketrans({"'": "\'"}))
        return bool(list(self._client.search(f"(title=\"{title_esc}\" and space='{page.space}' and type=page)")))

    def publish(self):
        """
        Push pages to Confluence.
        """
        for i, page in enumerate(sorted(self.pages, key=lambda p: p.order), 1):
            logger.debug(f'Publishing page {i}/{len(self.pages)}: {page} order: {page.order}')

            if self._page_exists(page):
                content = self._update_page(page)
            else:
                try:
                    content = self._create_page(page)
                except InvalidParentException as e:
                    logger.error(e)
                    continue
                except CreatePageException as e:
                    logger.error(e)
                    continue

            # Create/update labels
            self._set_labels(page, content)

            # Create/update attachments
            attachments = list(self._client.get_attachments(content.id, expand=['version']))
            for image in page.media:
                if image['name'] in [att.title for att in attachments]:
                    att = [att for att in attachments if att.title == image['name']][0]
                    logger.debug(f'Updating attachment {image["name"]} (exists as {att}) for {page} (ID: {content.id})')
                    self._client.update_attachment(content.id, att.id, att.version.number)
                else:
                    logger.debug(f'Creating attachment {image["name"]} for {page} (ID: {content.id})')
                    self._client.add_attachment(content.id, image['src'], image['name'])


class Page:
    """
    Data class for holding markdown, rendered content and metadata.
    """

    def __init__(self, metadata, content, path):
        self._metadata = metadata
        self.path = path
        self.title = metadata.get('c_title')
        self.parent = metadata.get('c_parent')
        self.space = metadata.get('c_space', 'IN')
        self.toc = metadata.get('c_toc', False)
        self.ngtca_notice = metadata.get('c_notice', True)
        self.markdown = content
        self.media = self._find_media(content)
        self.html = ConfluenceRenderer(path.parent).render(Document(content))
        self.order = int(metadata.get('c_order', 0))

        # Add initial labels
        self._labels = metadata.get('c_labels', '')
        if isinstance(self._labels, str):
            self._labels = set(self._labels.split(','))
        self._labels = set(list(map(str.strip, self._labels)))

        # Let people know this is not the place to make changes
        if self.ngtca_notice:
            self.html = (
                f'{self.html}\n<p><i style="font-size: 80%;">'
                'This page is managed by NGTCA, edits in Confluence will '
                'not persist.</i></p>'
            )

        # Insert ToC macro at the front, where it should always be
        if self.toc:
            self.html = f'<ac:structured-macro ac:name="toc">' f'</ac:structured-macro>\n{self.html}'

        # Set type correctly
        if self.parent:
            self.parent = str(self.parent)

    def _find_media(self, content):
        """
        Find any/all image/link span tokens.
        """
        doc = Document(content)
        if not hasattr(doc, 'children'):
            return []

        # TODO: Need to find link tokens too AND only include them if they are to a local file as media type
        # Get image tokens
        tokens = []
        stack = [*doc.children]
        while stack:
            child = stack.pop()
            if isinstance(child, (Image, Link)):
                tokens.append(child)
            if hasattr(child, 'children'):
                for c in child.children:
                    stack.insert(0, c)

        # Return those that are local
        images = []
        for image in tokens:
            attr = 'target' if isinstance(image, Link) else 'src'
            fpath = self.path.parent.joinpath(Path(getattr(image, attr))).resolve()
            if not fpath.is_file() or not mimetypes.guess_type(str(fpath))[0]:
                continue
            logger.debug(f'Adding {fpath.name} as media for {self}')
            images.append({'src': fpath.resolve().absolute(), 'name': fpath.name})

        return images

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, *labels):
        """
        When adding labels, strip spacing, keep only non empties.
        """
        self._labels = set(*labels)
        self._labels = set(list(map(str.strip, self._labels)))
        self._labels = set([l for l in self._labels if l])
        self._labels = set([l for l in self._labels if re.match('^[\w-]+$', l) is not None])

    @labels.deleter
    def labels(self):
        self._labels = set()

    def __repr__(self):
        repr_str = f'path:{self.path}'
        if self.title:
            repr_str += f', title:{self.title}'
        if self.parent:
            repr_str += f' (parent:{self.parent})'
        return f'<Page {repr_str}>'

    @classmethod
    def from_file(cls, file):
        """
        Create page from markdown file.
        """
        path = Path(file)
        matter = frontmatter.load(path)
        return cls(matter.metadata, matter.content, path)

    def __hash__(self):
        """
        The title is the only thing that really separates documents.
        """
        return hash(self.title)


def scan(args):
    """
    Look in directory for markdown files, parse them, and sync them to
    confluence.
    """
    # Self publish our book of convoluted magic
    book = Book(conf_endpoint=args.conf_endpoint, conf_user=args.conf_user, conf_pass=args.conf_pass)
    book.labels = set(args.labels)

    # If path is invalid, we won't continue
    try:
        book.add_path(args.path)
    except NoValidPathException:
        raise SystemExit()

    # Sync
    book.publish()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('path')
    parser.add_argument(
        '--conf-endpoint',
        default=os.getenv('CONFLUENCE_ENDPOINT', 'https://confluence.example.com'),
        help='confluence wiki endpoint',
    )
    parser.add_argument('--conf-user', default=os.getenv('CONFLUENCE_USER'), help='confluence user')
    parser.add_argument('--conf-pass', default=os.getenv('CONFLUENCE_PASS'), help='confluence pass/token')
    parser.add_argument('-l', '--labels', nargs='*', default=set(), help='global labels applied to all pages')
    parser.add_argument('-d', '--debug', action='store_true', help='debug messages')
    parser.add_argument('--version', action='version', version='ngtca ' + ngtca_version)
    args = parser.parse_args()
    if args.debug:
        logging.getLogger(__package__).setLevel(logging.DEBUG)
        logger.debug('Debug on')
    scan(args)


if __name__ == '__main__':
    main()
