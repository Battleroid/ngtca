from ngtca import __version__ as ngtca_version
from setuptools import setup, find_packages


setup(
    name='ngtca',
    version=ngtca_version,
    author='Casey Weed',
    author_email='casey@caseyweed.com',
    description='Never Go To Confluence Again',
    url='https://github.com/battleroid/ngtca',
    packages=find_packages(),
    install_requires=[
        'mistletoe==0.7.2',
        'confluence-rest-library==1.2.2',
        'python-frontmatter==0.5.0'
    ],
    entry_points="""
        [console_scripts]
        ngtca=ngtca.ngtca:main
    """
)
