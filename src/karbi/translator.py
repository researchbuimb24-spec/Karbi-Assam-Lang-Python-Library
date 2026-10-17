"""
Multilingual-to-Karbi Translation Engine (`karbi.translator`)
=============================================================

Translates words and phrases from supported source languages INTO KARBI.

Supported source languages:
1. English   (en) -> Karbi
2. Hindi     (hi) -> Karbi
3. Assamese  (as) -> Karbi
4. Bengali   (bn) -> Karbi
5. Extensible for additional source languages.
"""

from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from karbi.core.db import DEFAULT_DB_PATH, compile_database, get_db_connection

# Default paths to source data files
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LEXICON_FILES = [PROJECT_ROOT / "data" / "lexicon" / "core_lexicon.jsonl"]
SOURCE_FILES = [PROJECT_ROOT / "data" / "sources" / "sources.jsonl"]

SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "script": "Latin", "status": "active_data"},
    "hi": {"name": "Hindi", "script": "Devanagari", "status": "active_data"},
    "as": {"name": "Assamese", "script": "Bengali-Assamese", "status": "active_data"},
    "bn": {"name": "Bengali", "script": "Bengali", "status": "active_data"},
    "mr": {"name": "Marathi", "script": "Devanagari", "status": "awaiting_sourced_entries"},
}


@dataclass
class TranslationMatch:
    """A matched Karbi translation for a source language query."""
    source_query: str
    source_language: str
    karbi_lemma: str
    part_of_speech: str
    matched_meaning: str
    all_definitions: Dict[str, List[str]]
    status: str
    phonetics_ipa: Optional[str] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    source_citation: Optional[str] = None
    cultural_notes: Optional[str] = None
    dialect: str = "rongkhang"


def ensure_database_ready(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> Path:
    """Ensures the compiled SQLite database exists, compiling it if necessary."""
    path = Path(db_path)
    if not path.exists():
        existing_lex = [p for p in LEXICON_FILES if p.exists()]
        existing_src = [p for p in SOURCE_FILES if p.exists()]
        compile_database(existing_lex, existing_src, db_path=path)
    return path


def get_supported_languages() -> Dict[str, Dict[str, Any]]:
    """Returns the registry of source languages and their current data availability status."""
    return dict(SUPPORTED_LANGUAGES)


def translate(
    text: str,
    from_lang: str = "en",
    verified_only: bool = False,  # False allows PEER_REVIEWED historical data; set True for elder-confirmed only
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> List[TranslationMatch]:
    """
    Translates a word or concept from a source language INTO KARBI.

    Args:
        text: The source language word or phrase (e.g. 'water', 'घर', 'পানী').
        from_lang: ISO language code ('en', 'hi', 'as', 'bn').
        verified_only: If True, only returns entries verified by registered authorities.
                       If False, returns all authentic sourced entries (including PEER_REVIEWED).
        db_path: Optional custom path to the compiled SQLite database.

    Returns:
        List of TranslationMatch objects with full Karbi linguistic and citation details.
    """
    query = text.strip()
    if not query:
        return []

    lang_code = from_lang.lower().strip()
    ensure_database_ready(db_path)
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    matches: List[TranslationMatch] = []
    seen_entry_ids = set()

    # 1. Exact Match against the Multilingual Translations Index
    status_filter = "AND status = 'VERIFIED'" if verified_only else "AND status != 'AI_CANDIDATE'"
    exact_sql = f"""
        SELECT entry_id, sense_id, lemma, part_of_speech, query_term, status
        FROM translations_index
        WHERE from_lang = ? AND query_term = ? COLLATE NOCASE
        {status_filter}
    """
    cur.execute(exact_sql, (lang_code, query))
    rows = cur.fetchall()

    for row in rows:
        eid = row["entry_id"]
        seen_entry_ids.add(eid)

        # Retrieve full entry details
        entry_cur = conn.cursor()
        entry_cur.execute("SELECT raw_json FROM lexicon_entries WHERE entry_id = ?", (eid,))
        e_row = entry_cur.fetchone()
        if not e_row:
            continue

        raw = json.loads(e_row["raw_json"])
        senses = raw.get("senses", [])
        matched_sense = next((s for s in senses if s.get("sense_id") == row["sense_id"]), senses[0] if senses else {})

        # Extract citation details
        citation = None
        evs = raw.get("provenance", {}).get("evidence_records", [])
        if evs:
            ev = evs[0]
            src_cur = conn.cursor()
            src_cur.execute("SELECT title, creators_json, publication_json FROM sources WHERE source_id = ?", (ev.get("source_id"),))
            src_row = src_cur.fetchone()
            if src_row:
                title = src_row["title"]
                locator = ev.get("locator", "")
                citation = f"{title} ({locator})" if locator else title

        matches.append(
            TranslationMatch(
                source_query=query,
                source_language=lang_code,
                karbi_lemma=raw.get("headword", {}).get("lemma", row["lemma"]),
                part_of_speech=matched_sense.get("part_of_speech", row["part_of_speech"]),
                matched_meaning=row["query_term"],
                all_definitions=matched_sense.get("definitions", {}),
                status=raw.get("status", row["status"]),
                phonetics_ipa=raw.get("phonetics", {}).get("ipa"),
                examples=matched_sense.get("examples", []),
                source_citation=citation,
                cultural_notes=matched_sense.get("cultural_metadata", {}).get("cultural_notes"),
                dialect=raw.get("dialect", {}).get("primary_variety", "rongkhang"),
            )
        )

    # 2. Contextual Full-Text Search Match (if no exact matches or for deeper phrase search)
    if not matches:
        def_col_map = {"en": "def_en", "hi": "def_hi", "as": "def_as", "bn": "def_bn"}
        target_col = def_col_map.get(lang_code, "def_en")

        fts_sql = f"""
            SELECT entry_id, lemma
            FROM fts_lexicon
            WHERE {target_col} MATCH ?
            LIMIT 10
        """
        try:
            # Escape query for FTS5
            safe_query = f'"{query}"'
            cur.execute(fts_sql, (safe_query,))
            fts_rows = cur.fetchall()

            for f_row in fts_rows:
                eid = f_row["entry_id"]
                if eid in seen_entry_ids:
                    continue

                entry_cur = conn.cursor()
                entry_cur.execute("SELECT raw_json, status FROM lexicon_entries WHERE entry_id = ?", (eid,))
                e_row = entry_cur.fetchone()
                if not e_row:
                    continue

                if verified_only and e_row["status"] != "VERIFIED":
                    continue
                if e_row["status"] == "AI_CANDIDATE":
                    continue

                raw = json.loads(e_row["raw_json"])
                senses = raw.get("senses", [])
                sense = senses[0] if senses else {}

                matches.append(
                    TranslationMatch(
                        source_query=query,
                        source_language=lang_code,
                        karbi_lemma=raw.get("headword", {}).get("lemma", f_row["lemma"]),
                        part_of_speech=sense.get("part_of_speech", ""),
                        matched_meaning=f"Full-text match in {lang_code} definitions",
                        all_definitions=sense.get("definitions", {}),
                        status=e_row["status"],
                        phonetics_ipa=raw.get("phonetics", {}).get("ipa"),
                        examples=sense.get("examples", []),
                        dialect=raw.get("dialect", {}).get("primary_variety", "rongkhang"),
                    )
                )
        except sqlite3.OperationalError:
            pass  # FTS query syntax fallback

    conn.close()
    return matches
