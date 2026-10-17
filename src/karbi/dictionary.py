"""
Karbi Dictionary Lookup & Search Engine (`karbi.dictionary`)
============================================================

Provides direct Karbi headword lookup, spelling variant resolution,
and comprehensive search across definitions and phonetic notations.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from karbi.core.db import DEFAULT_DB_PATH, get_db_connection
from karbi.translator import ensure_database_ready


@dataclass
class DictionaryEntry:
    """A fully hydrated Karbi dictionary entry."""
    entry_id: str
    lemma: str
    script: str
    dialect: str
    status: str
    phonetics_ipa: Optional[str]
    senses: List[Dict[str, Any]]
    spelling_variants: List[Dict[str, Any]]
    cross_references: List[Dict[str, Any]]
    provenance: Dict[str, Any]
    source_citation: Optional[str] = None


def lookup(
    karbi_word: str,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> Optional[DictionaryEntry]:
    """
    Looks up a Karbi headword or spelling variant.

    Args:
        karbi_word: The Karbi word to search for (e.g. 'arlèng', 'hem', 'làng').
        db_path: Optional custom path to compiled SQLite database.

    Returns:
        DictionaryEntry object if found, or None.
    """
    word = karbi_word.strip()
    if not word:
        return None

    ensure_database_ready(db_path)
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT raw_json FROM lexicon_entries WHERE lemma = ? COLLATE NOCASE", (word,))
    row = cur.fetchone()

    # If not found directly, check FTS5 for lemma variants
    if not row:
        cur.execute(
            """
            SELECT e.raw_json 
            FROM fts_lexicon f 
            JOIN lexicon_entries e ON f.entry_id = e.entry_id 
            WHERE f.lemma MATCH ? 
            LIMIT 1
            """,
            (f'"{word}"',),
        )
        row = cur.fetchone()

    if not row:
        conn.close()
        return None

    raw = json.loads(row["raw_json"])
    conn.close()

    return DictionaryEntry(
        entry_id=raw.get("id", ""),
        lemma=raw.get("headword", {}).get("lemma", ""),
        script=raw.get("headword", {}).get("script", "latin"),
        dialect=raw.get("dialect", {}).get("primary_variety", "rongkhang"),
        status=raw.get("status", "DRAFT"),
        phonetics_ipa=raw.get("phonetics", {}).get("ipa"),
        senses=raw.get("senses", []),
        spelling_variants=raw.get("spelling_variants", []),
        cross_references=raw.get("cross_references", []),
        provenance=raw.get("provenance", {}),
    )
