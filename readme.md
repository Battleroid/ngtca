# NGTCA

**N**ever **G**o **T**o **C**onfluence **A**gain.

This should make adding and editing documentation less of a pain.

It's not without fault and has its own set of limitations. Generally you should use this with the assumption the documentation in Github would be the source of truth, what's in Confluence should be of a _"good enough for me"_ quality. My personal recommendation is to use this along with Jekyll to host a nice, pretty, easy to use site and then push what's required into Confluence if necessary. Then let people who want to use Confluence use that, while not sacrificing your sanity to use your own documentation.

## Usage as a CLI

```
usage: ngtca [-h] [--conf-endpoint CONF_ENDPOINT] [--conf-user CONF_USER]
             [--conf-pass CONF_PASS] [-l [LABELS [LABELS ...]]] [-d]
             [--version]
             path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  --conf-endpoint CONF_ENDPOINT
                        confluence wiki endpoint (default:
                        https://example.atlassian.net/wiki)
  --conf-user CONF_USER
                        confluence user (default: None)
  --conf-pass CONF_PASS
                        confluence pass/token (default: None)
  -l [LABELS [LABELS ...]], --labels [LABELS [LABELS ...]]
                        global labels applied to all pages (default: set())
  -d, --debug           debug messages (default: False)
  --version             show program's version number and exit
```

NGTCA can be used with a token from [id.atlassian.com](https://id.atlassian.com/manage/api-tokens). The following environment variables or CLI options need to be set:

- `--conf-endpoint` or `CONFLUENCE_ENDPOINT`, defaults to `https://example.atlassian.net/wiki`
- `--conf-user` or `CONFLUENCE_USER`, this can be the email address of the token's owner, e.g. `user@example.com`
- `--conf-pass` or `CONFLUENCE_PASS`, this should be set to the token value

## Prepping Documents

### The Basics

Minimal required frontmatter is a title, e.g. `title: My Documentation` is good enough, however this will post under the root of the space, it's preferred if you specify a parent page. Parents can be either a title or the ID number of the parent. AFAICT, the parent title does not need to be case sensitive. For example:

```
---
c_title: My Super Page
c_parent: Sample Team Directory
---
```

### Extras

Optionally, `c_space`, `c_toc` can be specified. Space by default is set to `IN`, the Ops documentation space. Setting `c_toc` to true will insert a Table of Contents macro at the beginning of your document when inserted into Confluence. For example:

```
---
c_title: My Super Page
c_parent: Sample Team Directory
c_toc: true
c_space: SOMETHING
---
```

### Labels

If you need a particular label added to a page (or pages) you can just specify a list of labels in the frontmatter via `c_labels`. Extra spacing and non conforming labels will not be set (must be a-z or -). Upon publishing, any labels not part of the page's labels will be removed. For example:

```
---
c_title: My Super Page
c_labels: some-label, something-else, more_labels, i'm@not-a_good_labeldon"tdothis
---
```

If you want to include a label(s) across all documents for a run just use `--labels`. Labels specified here will be merged with the page labels.

### Ordering

If you require a specific page or set of pages to be made before others (to place documents under another to be made document) you can specify `c_order` in the frontmatter. It operates in an ascending manner, by default all documents receive an order of 0. Setting the order higher will push their publishing further down.
See [sample](sample/) for an example. The Sample page is created as one of the first, with a number of pages under it using it's title as the parent.

### Example Usage

Sample usage on [ngtca-sample](https://git.rsglab.com/ops/ngtca-sample):

```
$ ngtca ../ngtca-sample -l repo-ops-ngtca-sample --debug
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:334  Debug on
[2018-05-01 14:33:51] ngtca.ngtca [INFO    ]   ngtca.py:104  ../ngtca-sample is a directory, searching for markdown files recursively
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:93   Added page <Page path:../ngtca-sample/docs/sample.md, title:NGTCA Examples (parent:Other)>
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:93   Added page <Page path:../ngtca-sample/docs/nope.md, title:I shouldn't exist (parent:9999999999999999999999999999999999999999)>
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:93   Added page <Page path:../ngtca-sample/docs/sample_id.md, title:Sample ID (parent:398360897)>
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:93   Added page <Page path:../ngtca-sample/docs/nested/hello.md, title:Sample Nested (parent:NGTCA Examples)>
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:93   Added page <Page path:../ngtca-sample/docs/other.md, title:Sample ToC (parent:NGTCA Examples)>
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:88   Skipping <Page path:../ngtca-sample/readme.md>, no metadata or title
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:205  Publishing page 1/5: <Page path:../ngtca-sample/docs/sample.md, title:NGTCA Examples (parent:Other)> order: 0
[2018-05-01 14:33:51] ngtca.ngtca [DEBUG   ]   ngtca.py:151  Updating <Page path:../ngtca-sample/docs/sample.md, title:NGTCA Examples (parent:Other)>
[2018-05-01 14:33:52] ngtca.ngtca [DEBUG   ]   ngtca.py:179  Setting labels for <Page path:../ngtca-sample/docs/sample.md, title:NGTCA Examples (parent:Other)> to elasticsearch, ngtca, repo-ops-ngtca-sample
[2018-05-01 14:33:53] ngtca.ngtca [DEBUG   ]   ngtca.py:205  Publishing page 2/5: <Page path:../ngtca-sample/docs/nested/hello.md, title:Sample Nested (parent:NGTCA Examples)> order: 0
[2018-05-01 14:33:53] ngtca.ngtca [DEBUG   ]   ngtca.py:151  Updating <Page path:../ngtca-sample/docs/nested/hello.md, title:Sample Nested (parent:NGTCA Examples)>
[2018-05-01 14:33:54] ngtca.ngtca [DEBUG   ]   ngtca.py:179  Setting labels for <Page path:../ngtca-sample/docs/nested/hello.md, title:Sample Nested (parent:NGTCA Examples)> to repo-ops-ngtca-sample
[2018-05-01 14:33:54] ngtca.ngtca [DEBUG   ]   ngtca.py:205  Publishing page 3/5: <Page path:../ngtca-sample/docs/other.md, title:Sample ToC (parent:NGTCA Examples)> order: 10
[2018-05-01 14:33:54] ngtca.ngtca [DEBUG   ]   ngtca.py:151  Updating <Page path:../ngtca-sample/docs/other.md, title:Sample ToC (parent:NGTCA Examples)>
[2018-05-01 14:33:55] ngtca.ngtca [DEBUG   ]   ngtca.py:179  Setting labels for <Page path:../ngtca-sample/docs/other.md, title:Sample ToC (parent:NGTCA Examples)> to ngtca, repo-ops-ngtca-sample
[2018-05-01 14:33:56] ngtca.ngtca [DEBUG   ]   ngtca.py:205  Publishing page 4/5: <Page path:../ngtca-sample/docs/nope.md, title:I shouldn't exist (parent:9999999999999999999999999999999999999999)> order: 20
[2018-05-01 14:33:56] ngtca.ngtca [ERROR   ]   ngtca.py:213  <Page path:../ngtca-sample/docs/nope.md, title:I shouldn't exist (parent:9999999999999999999999999999999999999999)> 9999999999999999999999999999999999999999 is not a valid parent, skipping
[2018-05-01 14:33:56] ngtca.ngtca [DEBUG   ]   ngtca.py:205  Publishing page 5/5: <Page path:../ngtca-sample/docs/sample_id.md, title:Sample ID (parent:398360897)> order: 20
[2018-05-01 14:33:57] ngtca.ngtca [DEBUG   ]   ngtca.py:151  Updating <Page path:../ngtca-sample/docs/sample_id.md, title:Sample ID (parent:398360897)>
[2018-05-01 14:33:57] ngtca.ngtca [DEBUG   ]   ngtca.py:179  Setting labels for <Page path:../ngtca-sample/docs/sample_id.md, title:Sample ID (parent:398360897)> to repo-ops-ngtca-sample
```

## Caveats & Notes

### Updating Content

Unfortunately, due to the wonkiness and ass-backwards nature of Confluence's API, there's no solid way to compare old with new content. It does not store the raw content, so there's no way to accurately do a diff between the two. So any update, will update all of it.

### Confluence Markup

Wiki markup won't work here, most of standard markdown will work without issue. The only markup that has been changed is the fenced code block. It has been modified to use the code macro for syntax highlighting. If no language is specified then text is used for no highlighting.

Some stuff like embedded image links and links to media (not text, binary) will be converted to the proper [XML markup](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html). It does this just by guessing the mimetype. That's it.

### Removing Content

Unfortunately, at this moment I can't think of a good (and safe) way to cleanup old documentation. I'd rather this be a _push_ only process. Where if you need a document within Confluence removed, you do it yourself as that is a process that is not often done. Creation and editing of pages is however something done frequently.

Basically:

- Create or update page? _Use NGTCA_
- Delete or change parent page? _Go to Confluence_

### Changing Parents

Delete the old page within Confluence, make an update to trigger creating the page where it's desired. However, it might be easier to just reassign it in the frontmatter and within Confluence to keep the versioning.

### Selecting Documents via Title/Parent

Due to how annoying the Confluence API is, NGTCA finds existing documents by using an exact CQL match query.

For example, even if you have "Sample", "Sample A", "Sample B", and you set your doc's title to "Sample" it will _only_ look for and match the "Sample" document. This appears to be case sensitive. So "Sample" will not match "sample", but the two titles cannot conflict (technically a case insensitive exact search is possible, but I'm not sure yet how to do this via the API yet).

### Documents with Matching Titles

If two documents share the same title, they will clobber and one of the two (likely whichever was found last) will be used. Titles are unique and used to identify the pages.

### Relative Links

~At this time, there's not a decent way to approach this. It may come down to it that the lexer/tokenizer that handles links will need to be mangled to call out to Confluence to find the appropriate document.~

~This introduces a complex problem as ordering of documents might affect if pages are even available to reference.~

~Relative links will work within Github pages, Jekyll, etc, but not within Confluence. So it's important to group your documents under a common parent to make things easy to find inside Confluence. At the end of the day however, the idea is to _NGTCA_ so for now I'm leaving it be.~

This should now work (at least within the same space for sure). Between spaces I'm not 100% sure, however, you can just use an absolute link anyway so that point may be moot.
