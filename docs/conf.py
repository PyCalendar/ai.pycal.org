"""Sphinx configuration for the documentation of ai.pycal.org."""

import datetime
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))  # ai_pycal.errors for autodoc
sys.path.insert(0, str(ROOT / "docs" / "_ext"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_pycal.settings")
os.environ.setdefault("SECRET_KEY", "documentation")
os.environ.setdefault("DATA_DIR", str(ROOT / "docs" / "_build" / "data"))
import django  # noqa: E402

django.setup()

project = "ai.pycal.org"
copyright = f"{datetime.date.today().year}, ai.pycal.org contributors"  # noqa: A001
author = "ai.pycal.org contributors"

extensions = [
    "github_app_form",
    "notfound.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_issues",
]

html_baseurl = "https://ai-pycal-org.readthedocs.io/en/latest/"
issues_github_path = "PyCalendar/ai.pycal.org"

html_theme = "pydata_sphinx_theme"
html_favicon = "../static/img/favicon.png"
html_logo = "../static/img/favicon.png"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/PyCalendar/ai.pycal.org",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
    "logo": {"text": "ai.pycal.org"},
    "show_toc_level": 2,
    "navigation_with_keys": True,
}
html_context = {
    "github_user": "PyCalendar",
    "github_repo": "ai.pycal.org",
    "github_version": "main",
    "doc_path": "docs",
}
html_static_path = ["_static"]
html_css_files = ["style.css"]
html_js_files = [("github-app-form.js", {"defer": "defer"})]

autodoc_member_order = "bysource"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
exclude_patterns = ["_build", "_includes"]

linkcheck_ignore = [
    r"http://localhost",
    r"https://github\.com/PyCalendar/ai\.pycal\.org/(blob|tree)/",
    r"https://github\.com/settings/.*",
    r"https://ai\.pycal\.org.*",  # the site is not online yet
]
