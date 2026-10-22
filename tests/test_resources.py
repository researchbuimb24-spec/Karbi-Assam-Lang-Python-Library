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


def test_database_auto_recompiles_when_stale():
    """ensure_database_ready detects when input resources are newer than the database and recompiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stale_db = Path(tmpdir) / "stale_test.db"

        # Initialize fresh DB
        ensure_database_ready(stale_db)
        assert stale_db.is_file()

        # Artificially set database mtime to before the input data files
        lex_files, src_files = get_resource_paths()
        input_files = [f for f in lex_files + src_files if f.is_file()]
        oldest_input = min(f.stat().st_mtime for f in input_files) if input_files else stale_db.stat().st_mtime
        past_time = oldest_input - 3600
        os.utime(stale_db, (past_time, past_time))
        assert stale_db.stat().st_mtime == past_time or stale_db.stat().st_mtime <= oldest_input

        # ensure_database_ready should detect that data files are newer than past_time and recompile
        res = ensure_database_ready(stale_db)
        assert res == stale_db
        # mtime should have been updated to current time
        assert stale_db.stat().st_mtime > past_time + 100


def test_database_recompiles_when_table_missing():
    """ensure_database_ready recompiles if a required relational table or index is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        incomplete_db = Path(tmpdir) / "incomplete.db"
        ensure_database_ready(incomplete_db)
        assert incomplete_db.is_file()

        # Artificially drop translations_index
        conn = get_db_connection(incomplete_db)
        conn.execute("DROP TABLE translations_index")
        conn.commit()
        conn.close()

        # ensure_database_ready must detect missing table and recompile
        res = ensure_database_ready(incomplete_db)
        assert res == incomplete_db

        conn2 = get_db_connection(incomplete_db)
        cur2 = conn2.cursor()
        cur2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translations_index'")
        assert cur2.fetchone() is not None
        conn2.close()


def test_spelling_variants_indexed_lookup():
    """Looking up spelling variants (e.g. 'arleng', 'hem') utilizes indexed resolution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "variant_test.db"
        ensure_database_ready(test_db)

        # Confirm spelling_variants_index table is populated
        conn = get_db_connection(test_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM spelling_variants_index")
        variant_count = cur.fetchone()[0]
        conn.close()
        assert variant_count > 0

        # Test lookup for spelling variant 'arleng'
        res = karbi.lookup("arleng", db_path=test_db)
        assert res is not None
        assert res.lemma == "arlèng"

        # Test lookup for spelling variant 'hem'
        res_hem = karbi.lookup("hem", db_path=test_db)
        assert res_hem is not None
        assert res_hem.lemma == "hèm"


def test_ensure_database_ready_exported_from_core_db():
    """ensure_database_ready is accessible from karbi.core.db as well as karbi.translator."""
    from karbi.core.db import ensure_database_ready as db_ready
    from karbi.translator import ensure_database_ready as trans_ready

    assert db_ready is trans_ready
