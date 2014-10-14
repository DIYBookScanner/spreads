# -*- coding: utf-8 -*-

import os
import sys

import mock
MOCK_MODULES = ['usb', 'stevedore.extension', 'stevedore.named',
                'requests', 'isbnlib', 'PIL', 'tornado', 'tornado.web',
                'tornado.ioloop', 'tornado.websocket', 'tornado.wsgi',
                'wand', 'wand.image']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = mock.Mock()

import spreads.util as util

sys.path.append(os.path.abspath('_themes'))
sys.path.insert(0, os.path.abspath(os.path.join('..')))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage',
              'sphinx.ext.intersphinx', 'sphinxcontrib.fulltoc',
              'sphinxcontrib.autohttp.flask', 'sphinx.ext.viewcode' ]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'spreads'
copyright = u'2013, Johannes Baiter (jbaiter)'
version = util.get_version()
release = version
exclude_patterns = ['_build']
add_function_parentheses = True
pygments_style = 'sphinx'

intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7', None),
    'flask': ('http://flask.pocoo.org/docs/0.10/', None),
    'tornado': ('http://tornado.readthedocs.org/en/branch4.0/', None),
    'pillow': ('http://pillow.readthedocs.org/', None),
    'wand': ('http://docs.wand-py.org/en/0.3.8/', None),
    'pathlib': ('http://pathlib.readthedocs.org/en/pep428/', None),
    'confit': ('http://confit.readthedocs.org/en/latest/', None),
    'futures': ('http://pythonhosted.org//futures/', None)
}

http_index_shortname = 'api'
http_index_localname = 'Spreads HTTP API'
http_index_ignore_prefixes = ['/api']


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
