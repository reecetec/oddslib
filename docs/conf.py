import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import tomllib

sys.path.insert(0, os.path.abspath("../src"))

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "pyproject.toml").open("rb") as f:
    _pyproject = tomllib.load(f)


def _resolve_version() -> str:
    env_version = os.getenv("ODDSLIB_DOC_VERSION")
    if env_version:
        return env_version

    try:
        completed = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        tag = completed.stdout.strip()
        if tag:
            return tag
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return _pyproject["project"].get("version", "0.0.0")


raw_version = _resolve_version().lstrip("v")
release = raw_version
version = ".".join(raw_version.split(".")[:2])

project = "Oddslib"
author = "Reece Colclough"
copyright = f"{datetime.now():%Y}, {author}"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "autoapi.extension",
    "nbsphinx",
    "myst_parser",
    "sphinx_multiversion",
]

autoapi_dirs = ["../src/oddslib"]
autoapi_type = "python"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autoapi_root = "autoapi"
autoapi_add_toctree_entry = True
autoapi_keep_files = False

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

nbsphinx_execute = "never"
nbsphinx_allow_errors = True

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

html_theme = "furo"
html_title = f"{project}"

html_theme_options = {
    "sidebar_hide_name": False,
}

html_css_files = [
    "custom.css",
]

html_static_path = ["_static"]

exclude_patterns = [
    "_build",
    "_build/**",
    "Thumbs.db",
    ".DS_Store",
]

smv_tag_whitelist = r"^v\d+\.\d+\.\d+$"
smv_branch_whitelist = r"^(main)$"
smv_remote_whitelist = r"^(origin)$"
smv_released_pattern = r"^refs/tags/.*$"

templates_path = ["_templates"]
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/scroll-end.html",
    ]
}
