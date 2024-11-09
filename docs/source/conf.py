# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'COHIWizard_v1.2'
copyright = '2024, Hermann Scharfetter'
author = 'Hermann Scharfetter'
release = '1.2.8'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
]

autodoc_default_options = {
    'member-order': 'groupwise',
    'undoc-members': True,
    'exclude-members': '',
}

# autodoc_default_options = {
#     'members': 'var1, var2',
#     'member-order': 'bysource',
#     'special-members': '__init__',
#     'undoc-members': True,
#     'exclude-members': '__weakref__'
# }
# autodoc_member_order
#     This value selects if automatically documented members are sorted alphabetical (value 'alphabetical'), by member type (value 'groupwise') or by source order (value 'bysource'). The default is alphabetical.
#     Note that for source order, the module must be a Python module with the source code available.
#     Added in version 0.6.
#     Changed in version 1.0: Support for 'bysource'.

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'alabaster'
#import sphinx_rtd_theme
html_theme = 'sphinx_rtd_theme'
#html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

html_static_path = ['_static']

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import fnmatch

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..\\..\\sources'))
sys.path.insert(0, os.path.abspath('..\\..\\sources\\annotator'))
sys.path.insert(0, os.path.abspath('..\\..\\sources\\player'))
sys.path.insert(0, os.path.abspath('..\\..\\sources\\yaml_editor'))
sys.path.insert(0, os.path.abspath('..\\..\\sources\\synthesizer'))
sys.path.insert(0, os.path.abspath('..\\..\\sources\\main'))

def skip_methods(app, what, name, obj, skip, options):
    exclude_patterns = ['get_**', 'set_*', 'Sig*']  # Add your patterns here
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return skip

def setup(app):
    app.connect('autodoc-skip-member', skip_methods)


