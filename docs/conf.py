import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from packaging.version import InvalidVersion, Version


sys.path.insert(0, os.path.abspath("../src"))

ROOT = Path(__file__).resolve().parent.parent


def _get_release() -> str:
    release = os.getenv("SPHINX_MULTIVERSION_RELEASE")
    if release:
        return release

    env_version = os.getenv("ODDSLIB_DOC_VERSION")
    if env_version:
        return env_version

    try:
        from importlib import metadata as importlib_metadata

        return importlib_metadata.version("oddslib")
    except Exception:
        try:
            import setuptools_scm

            return setuptools_scm.get_version(root=str(ROOT), fallback_version="0.0.0")
        except Exception:
            return "0.0.0"


release = _get_release()
short_release = release.lstrip("v")
version = ".".join(short_release.split(".")[:2]) or short_release

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
smv_remote_whitelist = None
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


def _safe_version(tag_name: str) -> Version:
    normalized = tag_name.lstrip("v")
    try:
        return Version(normalized)
    except InvalidVersion:
        return Version("0")


def _inject_alias_versions(app, config) -> None:  # type: ignore[override]
    metadata = getattr(config, "smv_metadata", {})
    if not metadata:
        return

    alias_map = getattr(config, "smv_alias_map", {})

    tags = {name: data for name, data in metadata.items() if data.get("source") == "tags"}
    stable_name = None
    if tags:
        stable_name = max(tags, key=_safe_version)

    main_name = None
    for candidate in ("main", "origin/main"):
        if candidate in metadata:
            main_name = candidate
            break

    new_entries: dict[str, dict[str, object]] = {}

    if stable_name and "stable" not in metadata:
        stable_meta = metadata[stable_name]
        stable_dir = Path(stable_meta["outputdir"]).parent / "stable"
        alias_meta = {**stable_meta}
        alias_meta.update(
            {
                "name": "stable",
                "version": "stable",
                "release": stable_name,
                "outputdir": str(stable_dir),
                "source": "alias",
                "is_released": True,
            }
        )
        new_entries["stable"] = alias_meta
        alias_map["stable"] = {
            "source_name": stable_name,
            "outputdir": stable_dir,
        }

    if main_name and "latest" not in metadata:
        main_meta = metadata[main_name]
        latest_dir = Path(main_meta["outputdir"]).parent / "latest"
        alias_meta = {**main_meta}
        alias_meta.update(
            {
                "name": "latest",
                "version": "latest",
                "release": main_name,
                "outputdir": str(latest_dir),
                "source": "alias",
                "is_released": False,
            }
        )
        new_entries["latest"] = alias_meta
        alias_map["latest"] = {
            "source_name": main_name,
            "outputdir": latest_dir,
        }

    if not new_entries:
        return

    ordered_metadata = {**new_entries, **metadata}
    config.smv_metadata = ordered_metadata  # type: ignore[attr-defined]
    config.smv_alias_map = alias_map  # type: ignore[attr-defined]


def _copy_alias_builds(app, exception) -> None:  # type: ignore[override]
    if exception is not None:
        return

    alias_map = getattr(app.config, "smv_alias_map", {})
    current_name = os.getenv("SPHINX_MULTIVERSION_NAME")
    metadata = getattr(app.config, "smv_metadata", {})

    for alias, data in alias_map.items():
        source_name = data.get("source_name")
        alias_outputdir = Path(data.get("outputdir"))
        source_meta = metadata.get(source_name)
        if current_name != source_name or not source_meta:
            continue

        source_dir = Path(source_meta["outputdir"]).resolve()
        target_dir = alias_outputdir.resolve()

        if source_dir == target_dir:
            continue

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir)

        shutil.copytree(source_dir, target_dir)


def setup(app):  # type: ignore[override]
    app.connect("config-inited", _inject_alias_versions, priority=900)
    app.connect("build-finished", _copy_alias_builds, priority=900)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
