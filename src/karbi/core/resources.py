"""
Package Resource Discovery & Synchronization Engine (`karbi.core.resources`)
=============================================================================

Manages loading of runtime JSONL datasets (core lexicon and sources registry)
using standard Python package resources (`importlib.resources`).

Key guarantees:
1. The authoritative development datasets reside in the repository's `data/` directory.
2. In development (when running from a source repository checkout), authoritative
   `data/` files are automatically synchronized into `karbi.resources` to prevent drift.
3. In standalone installations (when running outside the repository in site-packages),
   datasets are discovered and loaded directly from the installed package resources.
"""

from __future__ import annotations

import importlib.resources as pkg_resources
import os
from pathlib import Path
import shutil
from typing import List, Optional, Tuple


# Repository root (4 levels up from this file when in source tree: src/karbi/core/resources.py -> root)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def get_repo_data_paths() -> Optional[Tuple[Path, Path]]:
    """
    Returns (lexicon_path, sources_path) if running within the source repository tree,
    or None if running outside the repository.
    """
    repo_lex = _REPO_ROOT / "data" / "lexicon" / "core_lexicon.jsonl"
    repo_src = _REPO_ROOT / "data" / "sources" / "sources.jsonl"
    if repo_lex.is_file() and repo_src.is_file():
        return repo_lex, repo_src
    return None


def sync_authoritative_data_to_resources() -> bool:
    """
    Synchronizes authoritative repository data files into `src/karbi/resources/`.
    Returns True if synchronized, False if not running from a source checkout.
    """
    paths = get_repo_data_paths()
    if paths is None:
        return False

    repo_lex, repo_src = paths
    resources_dir = Path(__file__).resolve().parent.parent / "resources"

    lex_target = resources_dir / "lexicon" / "core_lexicon.jsonl"
    src_target = resources_dir / "sources" / "sources.jsonl"

    lex_target.parent.mkdir(parents=True, exist_ok=True)
    src_target.parent.mkdir(parents=True, exist_ok=True)

    # Copy only if target is missing or content differs
    for src, dst in [(repo_lex, lex_target), (repo_src, src_target)]:
        if not dst.exists() or dst.stat().st_size != src.stat().st_size or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)

    return True


def get_packaged_resource_paths() -> Tuple[Path, Path]:
    """
    Resolves the packaged lexicon and source registry files from `karbi.resources`
    using standard `importlib.resources`.
    """
    try:
        root = pkg_resources.files("karbi.resources")
    except Exception:
        root = pkg_resources.files("karbi").joinpath("resources")

    lex_item = root.joinpath("lexicon", "core_lexicon.jsonl")
    src_item = root.joinpath("sources", "sources.jsonl")

    # If the resource is backed by a filesystem path
    lex_path = Path(str(lex_item))
    src_path = Path(str(src_item))

    if lex_path.is_file() and src_path.is_file():
        return lex_path, src_path

    # Fallback using as_file for zip or non-filesystem distributions
    # Note: in standard wheel installations, files are always on the filesystem.
    if hasattr(pkg_resources, "as_file"):
        with pkg_resources.as_file(lex_item) as lp, pkg_resources.as_file(src_item) as sp:
            lex_p = Path(lp)
            src_p = Path(sp)
            if lex_p.is_file() and src_p.is_file():
                return lex_p, src_p

    raise FileNotFoundError(
        "Could not locate packaged Karbi runtime resources (lexicon and sources). "
        "Ensure the package was built and installed with package-data enabled."
    )


def get_resource_paths() -> Tuple[List[Path], List[Path]]:
    """
    Discovers runtime dataset paths for database compilation.

    Returns:
        (lexicon_paths, source_paths)

    Resolution order:
    1. If running within a source tree repository, authoritative repository files
       are synchronized and returned.
    2. Otherwise, packaged resources within `karbi.resources` are returned.
    """
    # 1. Source tree checkout
    repo_paths = get_repo_data_paths()
    if repo_paths is not None:
        sync_authoritative_data_to_resources()
        repo_lex, repo_src = repo_paths
        return [repo_lex], [repo_src]

    # 2. Standalone / installed package
    pkg_lex, pkg_src = get_packaged_resource_paths()
    return [pkg_lex], [pkg_src]
