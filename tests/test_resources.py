"""
Tests for Resource Loading, Synchronization, and Standalone Database Initialization.
=====================================================================================
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock
import pytest

import karbi
from karbi.core.db import (
    get_db_connection,
    get_default_db_path,
    get_user_data_dir,
)
from karbi.core.resources import (
    get_packaged_resource_paths,
    get_repo_data_paths,
    get_resource_paths,
    sync_authoritative_data_to_resources,
)
from karbi.translator import ensure_database_ready


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_authoritative_data_mirrored_in_resources():
    """Packaged resources match the authoritative repository data files byte-for-byte."""
    repo_paths = get_repo_data_paths()
    assert repo_paths is not None, "Running within source repository"
    repo_lex, repo_src = repo_paths

    pkg_lex, pkg_src = get_packaged_resource_paths()

    assert pkg_lex.is_file(), f"Packaged lexicon missing at {pkg_lex}"
    assert pkg_src.is_file(), f"Packaged sources missing at {pkg_src}"

    # Byte-for-byte identity check ensures no divergence
    assert pkg_lex.read_bytes() == repo_lex.read_bytes()
    assert pkg_src.read_bytes() == repo_src.read_bytes()


def test_sync_authoritative_data():
    """sync_authoritative_data_to_resources returns True and preserves sync state."""
    assert sync_authoritative_data_to_resources() is True


def test_packaged_resource_discovery():
    """get_packaged_resource_paths resolves valid, readable JSONL datasets."""
    lex_path, src_path = get_packaged_resource_paths()
    assert lex_path.name == "core_lexicon.jsonl"
    assert src_path.name == "sources.jsonl"
    assert lex_path.stat().st_size > 0
    assert src_path.stat().st_size > 0


def test_fresh_database_initialization_in_custom_directory():
    """ensure_database_ready initializes and populates a database in a fresh location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fresh_db = Path(tmpdir) / "sub_dir" / "fresh_karbi.db"
        assert not fresh_db.exists()

        initialized_path = ensure_database_ready(fresh_db)
        assert initialized_path == fresh_db
        assert fresh_db.is_file()

        # Verify tables and foreign key enforcement
        conn = get_db_connection(fresh_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lexicon_entries")
        lex_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sources")
        src_count = cur.fetchone()[0]

        fk_on = cur.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()

        assert lex_count > 0, "Database must have populated lexicon entries"
        assert src_count > 0, "Database must have populated source records"
        assert fk_on == 1, "Foreign keys must be enabled"

        # Verify lookup and translation work with the fresh database
        entry = karbi.lookup("arlèng", db_path=fresh_db)
        assert entry is not None
        assert entry.lemma == "arlèng"

        matches = karbi.translate("water", from_lang="en", db_path=fresh_db)
        assert len(matches) >= 1
        assert matches[0].karbi_lemma == "làng"


def test_database_recompiles_corrupted_or_empty_file():
    """ensure_database_ready recompiles if the target database exists but is empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_db = Path(tmpdir) / "empty.db"
        empty_db.touch()
        assert empty_db.stat().st_size == 0

        # Must detect empty file and compile fully
        res_path = ensure_database_ready(empty_db)
        assert res_path == empty_db
        assert empty_db.stat().st_size > 0

        conn = get_db_connection(empty_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lexicon_entries")
        count = cur.fetchone()[0]
        conn.close()
        assert count > 0


def test_user_data_dir_location():
    """get_user_data_dir returns a path outside Python installation / site-packages."""
    user_dir = get_user_data_dir()
    assert isinstance(user_dir, Path)
    dir_str = str(user_dir).lower()
    assert "site-packages" not in dir_str
    assert "dist-packages" not in dir_str


def test_env_var_db_path_override():
    """KARBI_DB_PATH overrides the default database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_override = Path(tmpdir) / "custom_env.db"
        with mock.patch.dict(os.environ, {"KARBI_DB_PATH": str(custom_override)}):
            resolved = get_default_db_path()
            assert resolved == custom_override


def test_missing_resource_raises_error():
    """get_packaged_resource_paths raises FileNotFoundError if resources are missing."""
    with mock.patch("karbi.core.resources.pkg_resources.files") as mock_files:
        mock_root = mock.MagicMock()
        mock_root.joinpath.return_value = Path("/nonexistent/path/never_there.jsonl")
        mock_files.return_value = mock_root

        with pytest.raises(FileNotFoundError) as exc_info:
            get_packaged_resource_paths()
        assert "Could not locate packaged Karbi runtime resources" in str(exc_info.value)
