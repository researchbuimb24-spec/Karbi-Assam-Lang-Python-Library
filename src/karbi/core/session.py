"""
Reusable Database Session & Context Manager (`karbi.core.session`)
==================================================================

Provides `KarbiSession` and `karbi.session()` for reusing a single SQLite
connection and statement cache across repeated lookups, translations, and
search operations.

Thread Safety:
--------------
`KarbiSession` wraps a single `sqlite3.Connection` handle. It is **NOT** thread-safe
for concurrent use across multiple threads without external synchronization.
In multi-threaded environments, create one `KarbiSession` per thread or use the
default stateless API functions (`karbi.lookup`, `karbi.translate`, `karbi.search`),
which manage individual connections safely.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from karbi.core.db import get_db_connection, get_default_db_path
from karbi.translator import ensure_database_ready, TranslationMatch, translate
from karbi.dictionary import DictionaryEntry, lookup_all, lookup
from karbi.api import SearchResult, search


class KarbiSession:
    """
    Context manager and stateful handle for reusing SQLite database resources
    across repeated dictionary lookups, multilingual translations, and search queries.

    Example:
        >>> import karbi
        >>> with karbi.session() as s:
        ...     entry = s.lookup("arlèng")
        ...     results = s.translate("water", from_lang="en")
        ...     search_res = s.search("house")

    Thread Safety:
        Not thread-safe across concurrent threads. Use one instance per thread.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._closed: bool = False
        self._depth: int = 0

    @property
    def is_closed(self) -> bool:
        """Returns True if the session has been closed."""
        return self._closed

    @property
    def is_active(self) -> bool:
        """Returns True if the session has an active, open connection."""
        return not self._closed and self._conn is not None

    def connection(self) -> sqlite3.Connection:
        """Returns the underlying active sqlite3.Connection."""
        return self._ensure_active()

    def _ensure_active(self) -> sqlite3.Connection:
        """Ensures an open, valid SQLite connection is available."""
        if self._closed:
            raise RuntimeError("Cannot execute operations on a closed KarbiSession.")
        if self._conn is None:
            target_db = ensure_database_ready(self._db_path)
            self._conn = get_db_connection(target_db)
        return self._conn

    def refresh(self) -> None:
        """
        Recompiles the database if resource files have changed, and re-establishes
        the underlying database connection.
        """
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._closed = False
        target_db = ensure_database_ready(self._db_path)
        self._conn = get_db_connection(target_db)

    def close(self) -> None:
        """Closes the underlying SQLite connection and marks the session closed."""
        if self._closed:
            return
        self._closed = True
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self) -> KarbiSession:
        if self._closed:
            raise RuntimeError("Cannot enter a closed KarbiSession.")
        self._depth += 1
        self._ensure_active()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._depth -= 1
        if self._depth <= 0 or exc_type is not None:
            self.close()
        # Return False so that exceptions are propagated

    def lookup(
        self,
        karbi_word: str,
        dialect: Optional[str] = None,
    ) -> Optional[DictionaryEntry]:
        """Looks up a single Karbi headword using the session's shared connection."""
        conn = self._ensure_active()
        return lookup(karbi_word, dialect=dialect, db_path=self._db_path, conn=conn)

    def lookup_all(
        self,
        karbi_word: str,
    ) -> List[DictionaryEntry]:
        """Looks up all matching Karbi headwords and variants using the session's shared connection."""
        conn = self._ensure_active()
        return lookup_all(karbi_word, db_path=self._db_path, conn=conn)

    def translate(
        self,
        text: str,
        from_lang: str = "en",
        verified_only: bool = False,
    ) -> List[TranslationMatch]:
        """Translates a source word into Karbi using the session's shared connection."""
        conn = self._ensure_active()
        return translate(text, from_lang=from_lang, verified_only=verified_only, db_path=self._db_path, conn=conn)

    def search(
        self,
        query: str,
        lang: str = "auto",
        verified_only: bool = False,
    ) -> List[SearchResult]:
        """Searches the dictionary and multilingual indices using the session's shared connection."""
        conn = self._ensure_active()
        return search(query, lang=lang, verified_only=verified_only, db_path=self._db_path, conn=conn)


def session(db_path: Optional[Union[str, Path]] = None) -> KarbiSession:
    """
    Creates and returns a reusable KarbiSession context manager for batch queries.

    Example:
        >>> with karbi.session() as s:
        ...     res = [s.lookup(w) for w in ["arlèng", "làng", "hèm"]]

    Thread Safety:
        The returned KarbiSession is NOT thread-safe across concurrent threads.
        Instantiate one session per thread.
    """
    return KarbiSession(db_path=db_path)
