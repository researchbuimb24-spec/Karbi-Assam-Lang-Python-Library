"""
Tests for Package Discovery, Public Imports, CLI Entry Points, and Packaging Metadata.
======================================================================================
"""

import inspect
import sys
from pathlib import Path
import pytest

import karbi
import karbi.api
import karbi.cli
import karbi.__main__


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_package_version():
    """Package defines a valid semantic version string."""
    assert hasattr(karbi, "__version__")
    assert isinstance(karbi.__version__, str)
    assert karbi.__version__ == "0.1.0"


def test_public_imports_and_all():
    """All symbols declared in karbi.__all__ exist and are accessible."""
    assert hasattr(karbi, "__all__")
    assert len(karbi.__all__) > 0

    for name in karbi.__all__:
        assert hasattr(karbi, name), f"Missing public symbol: '{name}' on karbi"
        val = getattr(karbi, name)
        assert val is not None, f"Public symbol '{name}' is None"

    # Specific required core API symbols
    required_api_callables = [
        "search",
        "lookup",
        "translate",
        "batch_search",
        "batch_lookup",
        "batch_translate",
    ]
    for func_name in required_api_callables:
        assert hasattr(karbi, func_name)
        assert callable(getattr(karbi, func_name)), f"'{func_name}' must be callable"

    required_classes = [
        "SearchResult",
        "DictionaryEntry",
        "TranslationMatch",
    ]
    for cls_name in required_classes:
        assert hasattr(karbi, cls_name)
        assert inspect.isclass(getattr(karbi, cls_name)), f"'{cls_name}' must be a class"


def test_api_module_exports():
    """karbi.api exposes high-level unified search and batch interfaces."""
    assert hasattr(karbi.api, "__all__")
    expected_api_symbols = {
        "SearchResult",
        "search",
        "batch_search",
        "batch_lookup",
        "batch_translate",
    }
    assert set(karbi.api.__all__) == expected_api_symbols

    for sym in expected_api_symbols:
        assert hasattr(karbi.api, sym)
        assert getattr(karbi.api, sym) is getattr(karbi, sym)


def test_cli_entry_points():
    """CLI main function is properly exposed and bound."""
    assert hasattr(karbi.cli, "main")
    assert callable(karbi.cli.main)

    # Exported as cli_main in top-level package
    assert hasattr(karbi, "cli_main")
    assert karbi.cli_main is karbi.cli.main

    # karbi.__main__ imports main
    assert hasattr(karbi.__main__, "main")
    assert karbi.__main__.main is karbi.cli.main


def test_pyproject_metadata_and_entry_point():
    """pyproject.toml declares correct name, version, python requirement, and CLI script."""
    pyproject_file = PROJECT_ROOT / "pyproject.toml"
    assert pyproject_file.is_file(), "pyproject.toml must exist in project root"

    content = pyproject_file.read_text(encoding="utf-8")

    # Direct textual checks (guaranteed across all Python environments)
    assert 'name = "karbi"' in content
    assert f'version = "{karbi.__version__}"' in content
    assert 'requires-python = ">=3.9"' in content
    assert 'karbi = "karbi.cli:main"' in content
    assert 'where = ["src"]' in content
    assert 'package-data' in content
    assert 'testpaths = ["tests"]' in content
    assert 'pythonpath = ["src"]' in content

    # Structured TOML check if tomllib/tomli is available
    tomllib = None
    try:
        import tomllib as _tomllib
        tomllib = _tomllib
    except ImportError:
        try:
            import tomli as _tomllib
            tomllib = _tomllib
        except ImportError:
            pass

    if tomllib is not None:
        data = tomllib.loads(content)
        project = data.get("project", {})
        assert project.get("name") == "karbi"
        assert project.get("version") == karbi.__version__
        assert project.get("requires-python") == ">=3.9"
        assert project.get("readme") == "README.md"
        assert project.get("scripts", {}).get("karbi") == "karbi.cli:main"

        setuptools_cfg = data.get("tool", {}).get("setuptools", {})
        find_cfg = setuptools_cfg.get("packages", {}).get("find", {})
        assert find_cfg.get("where") == ["src"]
        assert "package-data" in setuptools_cfg



def test_readme_contains_core_documentation_topics():
    """README.md contains essential documentation for the public API and verification levels."""
    readme_file = PROJECT_ROOT / "README.md"
    assert readme_file.is_file(), "README.md must exist in project root"

    content = readme_file.read_text(encoding="utf-8")

    topics = [
        "search(",
        "lookup(",
        "translate(",
        "batch_search(",
        "batch_lookup(",
        "batch_translate(",
        "verified_only",
        "SOURCE_ATTESTED",
        "spelling",
        "pip install",
        "pytest",
    ]
    for topic in topics:
        assert topic.lower() in content.lower(), f"README.md should mention '{topic}'"
