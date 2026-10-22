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
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from karbi.core.db import (
    DEFAULT_DB_PATH,
    compile_database,
    ensure_database_ready,
    get_db_connection,
    get_default_db_path,
)
from karbi.core.resources import get_resource_paths

# Discovered dataset paths (authoritative repo copies in dev, package resources in distribution)
def _get_initial_files():
    try:
        return get_resource_paths()
    except Exception:
        return [], []

LEXICON_FILES, SOURCE_FILES = _get_initial_files()

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
    all_definitions: Dict[str, Any]
    status: str                            # Status of matched gloss: 'source_attested', 'verified', 'unverified'
    entry_status: str = "DRAFT"            # Underlying entry-level lifecycle status
    is_verified: bool = False              # Boolean flag: False for unverified glosses
    phonetics_ipa: Optional[str] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    source_citation: Optional[str] = None
    source_citations: List[str] = field(default_factory=list)
    cultural_notes: Optional[str] = None
    dialect: str = "rongkhang"
    entry_id: Optional[str] = None

    def get_definitions(self, lang: str = "en", verified_only: bool = False) -> List[str]:
        """
        Returns list of definition strings for a given language.
        If verified_only=True, excludes unverified definitions.
        """
        defs = self.all_definitions.get(lang, [])
        results: List[str] = []
        for d in defs:
            if isinstance(d, dict):
                txt = d.get("text", "").strip()
                is_ver = d.get("verified", False)
                if verified_only and not is_ver:
                    continue
                if txt and txt not in results:
                    results.append(txt)
            elif isinstance(d, str):
                txt = d.strip()
                if verified_only and not self.is_verified:
                    continue
                if txt and txt not in results:
                    results.append(txt)
        return results


def _determine_gloss_verification(
    sense: Dict[str, Any], lang_code: str, query_term: str, entry_status: str
) -> Tuple[bool, str]:
    """
    Determines whether a matched translation gloss is verified or unverified.

    Checks per-gloss verification flags and sense-level gloss provenance to prevent
    unverified Indic glosses from inheriting parent entry status.
    """
    gloss_prov_map = sense.get("gloss_provenance") or {}
    lang_prov = str(gloss_prov_map.get(lang_code, "")).lower()

    if lang_prov in ("unverified", "draft", "ai_candidate"):
        return False, "unverified"

    defs = sense.get("definitions", {}).get(lang_code, [])
    q_lower = query_term.strip().lower()
    for item in defs:
        if isinstance(item, dict):
            txt = item.get("text", "").strip().lower()
            if txt == q_lower:
                if item.get("verified") is False:
                    return False, "unverified"
                if item.get("verified") is True:
                    return True, "verified"
        elif isinstance(item, str) and item.strip().lower() == q_lower:
            if lang_prov in ("source_attested", "verified", "peer_reviewed"):
                return True, lang_prov

    if lang_prov in ("source_attested", "verified", "peer_reviewed"):
        return True, lang_prov

    if entry_status == "VERIFIED" and lang_prov != "unverified":
        return True, "verified"

    return False, "unverified"



def get_supported_languages() -> Dict[str, Dict[str, Any]]:
    """Returns the registry of source languages and their current data availability status."""
    return dict(SUPPORTED_LANGUAGES)


def translate(
    text: str,
    from_lang: str = "en",
    verified_only: bool = False,  # False allows PEER_REVIEWED historical data; set True for elder-confirmed only
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[TranslationMatch]:
    """
    Translates a word or concept from a source language INTO KARBI.

    Args:
        text: The source language word or phrase (e.g. 'water', 'घर', 'পানী').
        from_lang: ISO language code ('en', 'hi', 'as', 'bn').
        verified_only: If True, only returns entries verified by registered authorities.
                       If False, returns all authentic sourced entries (including PEER_REVIEWED).
        db_path: Optional custom path to the compiled SQLite database.
        conn: Optional active sqlite3.Connection to reuse for batch operations.

    Returns:
        List of TranslationMatch objects with full Karbi linguistic and citation details.
    """
    if text is None or not isinstance(text, str):
        return []
    query = unicodedata.normalize("NFC", text.strip())
    if not query:
        return []

    if from_lang is None or not isinstance(from_lang, str):
        return []
    lang_code = from_lang.lower().strip()
    if lang_code not in SUPPORTED_LANGUAGES:
        return []

    should_close = False
    if conn is None:
        target_db = ensure_database_ready(db_path)
        conn = get_db_connection(target_db)
        should_close = True

    try:
        cur = conn.cursor()

        matches: List[TranslationMatch] = []
        seen_entry_ids = set()

        # 1. Exact Match against the Multilingual Translations Index
        status_filter = "AND status != 'AI_CANDIDATE'"
        exact_sql = f"""
            SELECT entry_id, sense_id, lemma, part_of_speech, query_term, status
            FROM translations_index
            WHERE from_lang = ? AND query_term = ? COLLATE NOCASE
            {status_filter}
        """
        cur.execute(exact_sql, (lang_code, query))
        rows = cur.fetchall()

        if not rows:
            cleaned_query = re.sub(r"^[^\w]+|[^\w]+$", "", query)
            if cleaned_query and cleaned_query != query:
                cur.execute(exact_sql, (lang_code, cleaned_query))
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

            # Determine true gloss verification
            is_verified, gloss_status = _determine_gloss_verification(
                matched_sense, lang_code, row["query_term"], raw.get("status", row["status"])
            )
            if verified_only and not is_verified:
                continue

            # Extract citation details from all recorded evidence records
            citations: List[str] = []
            evs = raw.get("provenance", {}).get("evidence_records", [])
            for ev in evs:
                if not isinstance(ev, dict):
                    continue
                sid = ev.get("source_id")
                locator = ev.get("locator", "")
                if sid:
                    src_cur = conn.cursor()
                    src_cur.execute("SELECT title FROM sources WHERE source_id = ?", (sid,))
                    src_row = src_cur.fetchone()
                    if src_row and src_row["title"]:
                        title = src_row["title"]
                        c_str = f"{title} ({locator})" if locator else title
                    else:
                        c_str = f"{sid} ({locator})" if locator else sid
                    if c_str not in citations:
                        citations.append(c_str)

            citation = "; ".join(citations) if citations else None

            matches.append(
                TranslationMatch(
                    source_query=query,
                    source_language=lang_code,
                    karbi_lemma=raw.get("headword", {}).get("lemma", row["lemma"]),
                    part_of_speech=matched_sense.get("part_of_speech", row["part_of_speech"]),
                    matched_meaning=row["query_term"],
                    all_definitions=matched_sense.get("definitions", {}),
                    status=gloss_status,
                    entry_status=raw.get("status", row["status"]),
                    is_verified=is_verified,
                    phonetics_ipa=raw.get("phonetics", {}).get("ipa"),
                    examples=matched_sense.get("examples", []),
                    source_citation=citation,
                    source_citations=citations,
                    cultural_notes=matched_sense.get("cultural_metadata", {}).get("cultural_notes"),
                    dialect=raw.get("dialect", {}).get("primary_variety", "rongkhang"),
                    entry_id=eid,
                )
            )

        # 2. Contextual Full-Text Search Match (if no exact matches or for deeper phrase search)
        if not matches:
            def_col_map = {"en": "def_en", "hi": "def_hi", "as": "def_as", "bn": "def_bn"}
            target_col = def_col_map.get(lang_code)

            if target_col is not None:
                fts_sql = f"""
                    SELECT entry_id, lemma
                    FROM fts_lexicon
                    WHERE {target_col} MATCH ?
                    LIMIT 10
                """
                try:
                    # Escape query for FTS5 (escape double quotes by doubling them)
                    escaped_query = query.replace('"', '""')
                    safe_query = f'"{escaped_query}"'
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

                        if e_row["status"] == "AI_CANDIDATE":
                            continue

                        raw = json.loads(e_row["raw_json"])
                        senses = raw.get("senses", [])
                        sense = senses[0] if senses else {}

                        is_verified, gloss_status = _determine_gloss_verification(
                            sense, lang_code, query, e_row["status"]
                        )
                        if verified_only and not is_verified:
                            continue

                        # Extract citation details for FTS match
                        fts_citations: List[str] = []
                        for ev in raw.get("provenance", {}).get("evidence_records", []):
                            if not isinstance(ev, dict):
                                continue
                            sid = ev.get("source_id")
                            locator = ev.get("locator", "")
                            if sid:
                                src_cur = conn.cursor()
                                src_cur.execute("SELECT title FROM sources WHERE source_id = ?", (sid,))
                                src_row = src_cur.fetchone()
                                if src_row and src_row["title"]:
                                    title = src_row["title"]
                                    c_str = f"{title} ({locator})" if locator else title
                                else:
                                    c_str = f"{sid} ({locator})" if locator else sid
                                if c_str not in fts_citations:
                                    fts_citations.append(c_str)

                        fts_citation = "; ".join(fts_citations) if fts_citations else None

                        matches.append(
                            TranslationMatch(
                                source_query=query,
                                source_language=lang_code,
                                karbi_lemma=raw.get("headword", {}).get("lemma", f_row["lemma"]),
                                part_of_speech=sense.get("part_of_speech", ""),
                                matched_meaning=f"Full-text match in {lang_code} definitions",
                                all_definitions=sense.get("definitions", {}),
                                status=gloss_status,
                                entry_status=e_row["status"],
                                is_verified=is_verified,
                                phonetics_ipa=raw.get("phonetics", {}).get("ipa"),
                                examples=sense.get("examples", []),
                                source_citation=fts_citation,
                                source_citations=fts_citations,
                                dialect=raw.get("dialect", {}).get("primary_variety", "rongkhang"),
                                entry_id=eid,
                            )
                        )
                except sqlite3.OperationalError:
                    pass  # FTS query syntax fallback

    finally:
        if should_close:
            try:
                conn.close()
            except Exception:
                pass
    return matches


def batch_translate(
    queries: Sequence[str],
    from_lang: str = "en",
    verified_only: bool = False,
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, List[TranslationMatch]]:
    """
    Translates multiple words or concepts into Karbi, reusing a single database connection.

    Args:
        queries: Iterable of words or concepts to translate.
        from_lang: Source language code ('en', 'hi', 'as', 'bn').
        verified_only: If True, only returns verified entries.
        db_path: Optional custom path to SQLite database.
        conn: Optional active sqlite3.Connection to reuse.

    Returns:
        Dictionary mapping each query string to its list of TranslationMatch objects.
    """
    should_close = False
    if conn is None:
        target_db = ensure_database_ready(db_path)
        conn = get_db_connection(target_db)
        should_close = True

    try:
        return {
            q: translate(q, from_lang=from_lang, verified_only=verified_only, db_path=db_path, conn=conn)
            for q in queries
        }
    finally:
        if should_close:
            try:
                conn.close()
            except Exception:
                pass

