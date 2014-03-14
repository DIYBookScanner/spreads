# -*- coding: utf-8 -*-

import os
import sys

import mock
MOCK_MODULES = ['usb', 'stevedore.extension', 'stevedore.named']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = mock.Mock()

import spreads

sys.path.append(os.path.abspath('_themes'))
sys.path.insert(0, os.path.abspath(os.path.join('..')))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage',
              'sphinx.ext.intersphinx', 'sphinxcontrib.fulltoc',
              'sphinxcontrib.autohttp.flask']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'content'

project = u'spreads'
copyright = u'2013, Johannes Baiter (jbaiter)'
version = spreads.__version__
release = version
exclude_patterns = ['_build']
add_function_parentheses = True
pygments_style = 'sphinx'


html_theme = 'flask'
html_theme_path = ['_themes']
html_logo = os.path.join('_static', 'monk.png')
html_static_path = ['_static']
html_use_smartypants = True
htmlhelp_basename = 'spreadsdoc'

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '11pt',
    'classoptions': ',oneside',
    'babel': '\\usepackage[english]{babel}',
    'tableofcontents': '\\newpage\\thispagestyle{empty}\\mbox{} '
                       '\\tableofcontents \\newpage\\thispagestyle{empty}'
                       '\\mbox{}',
    'fontpkg': '\\usepackage{palatino}',
}
latex_documents = [
    ('content', 'spreads.tex', u'Documentation',
     u'Johannes Baiter', 'manual', True),
]
latex_logo = '_static/logo.png'
latex_show_urls = 'footnote'

man_pages = [
    ('content', 'spreads', u'spreads Documentation',
     [u'Johannes Baiter'], 1)
]

texinfo_documents = [
    ('index', 'spreads', u'spreads Documentation',
     u'Johannes Baiter', 'spreads', 'One line description of project.',
     'Miscellaneous'),
]


def skip(app, what, name, obj, skip, options):
    if name == "__init__":
        return False
    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip)
