# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'cryodecoder'
copyright = '2026, CHIL (Cryospheric and Hydrological Instrumentation Laboratory), Cardiff University'
author = 'J. D. Hawkins, L. Craw, M. R. Prior-Jones, P. Biggs'
release = '0.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'
html_theme_options = {
    "navigation_depth" : 3,
    "collapse_navigation" : False
}

html_static_path = ['_static']

html_logo = "_static/logo.png"

# Refer to here for autosummary templates
# > https://www.aahilm.com/blog/documenting-large-projects-with-sphinx