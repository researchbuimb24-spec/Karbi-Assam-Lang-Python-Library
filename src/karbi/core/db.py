"""
SQLite & FTS5 Database Engine for Karbi Language Library (`karbi.core.db`)
==========================================================================

Compiles canonical JSONL files into an optimized, indexed SQLite database
with Full-Text Search (FTS5) and reverse Multilingual-to-Karbi indexing.
"""

from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from karbi.core.loader import load_jsonl_file

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "karbi.db"


@dataclass
class SearchResult:
    """Represents a search or translation match."""
    entry_id: str
    lemma: str
    part_of_speech: str
    definitions: Dict[str, List[str]]
    status: str
    match_source: str                      # e.g., "exact_translation", "fts_definition", "lemma_match"
    source_citation: Optional[str] = None
    examples: List[Dict[str, Any]] = None
    phonetic_ipa: Optional[str] = None


def get_db_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db_schema(conn: sqlite3.Connection) -> None:
    """Initializes normalized relational tables and the FTS5 search index."""
    cur = conn.cursor()

    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON;")

    # 1. Sources Registry
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            title TEXT NOT NULL,
            creators_json TEXT NOT NULL,
            publication_json TEXT,
            archive_location TEXT,
            rights_status TEXT NOT NULL
        );
    """)

    # 2. Lexicon Entries
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lexicon_entries (
            entry_id TEXT PRIMARY KEY,
            lemma TEXT NOT NULL COLLATE NOCASE,
            script TEXT NOT NULL,
            dialect TEXT NOT NULL,
            status TEXT NOT NULL,
            ipa TEXT,
            raw_json TEXT NOT NULL
        );
    """)

    # 3. Senses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS senses (
            sense_id TEXT NOT NULL,
            entry_id TEXT NOT NULL,
            part_of_speech TEXT NOT NULL,
            def_en TEXT,
            def_hi TEXT,
            def_as TEXT,
            def_bn TEXT,
            status TEXT NOT NULL,
            is_sensitive INTEGER NOT NULL DEFAULT 0,
            allow_index INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(entry_id) REFERENCES lexicon_entries(entry_id) ON DELETE CASCADE
        );
    """)

    # 4. Multilingual Translation Index (Reverse lookups: en/hi/as/bn -> Karbi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS translations_index (
            from_lang TEXT NOT NULL,
            query_term TEXT NOT NULL COLLATE NOCASE,
            entry_id TEXT NOT NULL,
            sense_id TEXT NOT NULL,
            lemma TEXT NOT NULL,
            part_of_speech TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES lexicon_entries(entry_id) ON DELETE CASCADE
        );
    """)

    # Create b-tree indexes for fast lookups
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trans_lookup ON translations_index(from_lang, query_term);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lemma_lookup ON lexicon_entries(lemma);")

    # 5. Full-Text Search (FTS5) Virtual Table
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_lexicon USING fts5(
            entry_id UNINDEXED,
            lemma,
            def_en,
            def_hi,
            def_as,
            def_bn,
            text_karbi,
            tokenize = 'unicode61 remove_diacritics 0'
        );
    """)

    conn.commit()


def compile_database(
    lexicon_paths: List[Union[str, Path]],
    source_paths: List[Union[str, Path]],
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> Tuple[int, int]:
    """
    Compiles raw JSONL source files and lexicon files into the SQLite database.

    Returns:
        (entries_inserted_count, sources_inserted_count)
    """
    db_p = Path(db_path)
    if db_p.exists():
        db_p.unlink()

    conn = get_db_connection(db_p)
    init_db_schema(conn)
    cur = conn.cursor()

    sources_count = 0
    entries_count = 0

    # 1. Ingest Sources
    for sp in source_paths:
        records, _ = load_jsonl_file(sp, raise_on_error=False)
        for rec in records:
            s = rec.data
            sid = s.get("source_id")
            if not sid:
                continue
            cur.execute(
                """
                INSERT OR REPLACE INTO sources (
                    source_id, source_type, title, creators_json,
                    publication_json, archive_location, rights_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    s.get("source_type", "print_publication"),
                    s.get("title", ""),
                    json.dumps(s.get("creators", []), ensure_ascii=False),
                    json.dumps(s.get("publication_details", {}), ensure_ascii=False),
                    s.get("archive_location", ""),
                    s.get("rights_and_permissions", {}).get("status", ""),
                ),
            )
            sources_count += 1

    # 2. Ingest Lexicon Entries
    for lp in lexicon_paths:
        records, _ = load_jsonl_file(lp, raise_on_error=False)
        for rec in records:
            e = rec.data
            eid = e.get("id")
            if not eid:
                continue

            lemma = e.get("headword", {}).get("lemma", "")
            script = e.get("headword", {}).get("script", "latin")
            dialect = e.get("dialect", {}).get("primary_variety", "rongkhang")
            status = e.get("status", "DRAFT")
            ipa = e.get("phonetics", {}).get("ipa")
            raw_json = json.dumps(e, ensure_ascii=False)

            cur.execute(
                """
                INSERT OR REPLACE INTO lexicon_entries (
                    entry_id, lemma, script, dialect, status, ipa, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (eid, lemma, script, dialect, status, ipa, raw_json),
            )
            entries_count += 1

            # Ingest Senses and Index Reverse Translations
            senses = e.get("senses", [])
            for s in senses:
                sid = s.get("sense_id", "S1")
                pos = s.get("part_of_speech", "")
                s_status = s.get("status", status)
                cm = s.get("cultural_metadata", {})
                is_sens = 1 if cm.get("is_culturally_sensitive", False) else 0
                allow_idx = 1 if cm.get("allow_search_indexing", True) else 0

                defs = s.get("definitions", {})

                def _gloss_texts(gloss_list):
                    """Extract plain strings from a definition list.

                    Each item may be either a bare string or a dict with a
                    'text' key (and optional 'verified' flag).
                    """
                    out = []
                    for item in gloss_list:
                        if isinstance(item, str):
                            out.append(item)
                        elif isinstance(item, dict):
                            t = item.get("text", "")
                            if t:
                                out.append(t)
                    return out

                def_en_str = " ; ".join(_gloss_texts(defs.get("en", [])))
                def_hi_str = " ; ".join(_gloss_texts(defs.get("hi", [])))
                def_as_str = " ; ".join(_gloss_texts(defs.get("as", [])))
                def_bn_str = " ; ".join(_gloss_texts(defs.get("bn", [])))

                cur.execute(
                    """
                    INSERT INTO senses (
                        sense_id, entry_id, part_of_speech,
                        def_en, def_hi, def_as, def_bn,
                        status, is_sensitive, allow_index
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sid, eid, pos, def_en_str, def_hi_str, def_as_str, def_bn_str, s_status, is_sens, allow_idx),
                )

                # Populate Multilingual Index (Every word/gloss maps to Karbi lemma)
                for lang_code, glosses in defs.items():
                    for gloss in _gloss_texts(glosses):
                        cleaned = gloss.strip()
                        if cleaned:
                            cur.execute(
                                """
                                INSERT INTO translations_index (
                                    from_lang, query_term, entry_id, sense_id, lemma, part_of_speech, status
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (lang_code.lower(), cleaned, eid, sid, lemma, pos, s_status),
                            )

                # Insert into FTS5 Index (only if allowed and not culturally confidential)
                if allow_idx and not is_sens:
                    ex_karbi_text = " ".join([ex.get("text_karbi", "") for ex in s.get("examples", [])])
                    cur.execute(
                        """
                        INSERT INTO fts_lexicon (entry_id, lemma, def_en, def_hi, def_as, def_bn, text_karbi)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (eid, lemma, def_en_str, def_hi_str, def_as_str, def_bn_str, ex_karbi_text),
                    )

    conn.commit()
    conn.close()
    return entries_count, sources_count
