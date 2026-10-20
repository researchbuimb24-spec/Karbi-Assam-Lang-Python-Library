"""
Karbi Dictionary Lookup & Search Engine (`karbi.dictionary`)
============================================================

Provides direct Karbi headword lookup, spelling variant resolution,
and comprehensive search across definitions and phonetic notations.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

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
    source_citations: List[str] = field(default_factory=list)

    def get_meanings(self, lang: str = "en", verified_only: bool = False) -> List[str]:
        """
        Returns list of definition strings for a given language code ('en', 'hi', 'as', 'bn').
        If verified_only=True, excludes definitions marked as unverified.
        """
        results: List[str] = []
        for sense in self.senses:
            defs = sense.get("definitions", {}).get(lang, [])
            gloss_prov = str((sense.get("gloss_provenance") or {}).get(lang, "")).lower()
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
                    is_ver = gloss_prov in ("source_attested", "verified", "peer_reviewed")
                    if verified_only and not is_ver:
                        continue
                    if txt and txt not in results:
                        results.append(txt)
        return results

    def get_spelling_variants(self) -> List[str]:
        """Returns list of alternative spellings and contemporary orthographic variants."""
        variants: List[str] = []
        for v in self.spelling_variants:
            if isinstance(v, dict):
                t = v.get("text", "").strip()
                if t and t not in variants:
                    variants.append(t)
            elif isinstance(v, str):
                t = v.strip()
                if t and t not in variants:
                    variants.append(t)
        return variants

    def as_dict(self) -> Dict[str, Any]:
        """Serializes the dictionary entry into a clean Python dictionary."""
        return {
            "entry_id": self.entry_id,
            "lemma": self.lemma,
            "script": self.script,
            "dialect": self.dialect,
            "status": self.status,
            "phonetics_ipa": self.phonetics_ipa,
            "senses": self.senses,
            "spelling_variants": self.spelling_variants,
            "cross_references": self.cross_references,
            "provenance": self.provenance,
            "source_citation": self.source_citation,
            "source_citations": self.source_citations,
        }


def lookup(
    karbi_word: str,
    db_path: Optional[Union[str, Path]] = None,
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

    target_db = ensure_database_ready(db_path)
    conn = get_db_connection(target_db)
    cur = conn.cursor()

    cur.execute("SELECT raw_json FROM lexicon_entries WHERE lemma = ? COLLATE NOCASE", (word,))
    row = cur.fetchone()

    # If not found directly, check FTS5 for lemma variants
    if not row:
        safe_word = word.replace('"', '""')
        cur.execute(
            """
            SELECT e.raw_json 
            FROM fts_lexicon f 
            JOIN lexicon_entries e ON f.entry_id = e.entry_id 
            WHERE f.lemma MATCH ? 
            LIMIT 1
            """,
            (f'"{safe_word}"',),
        )
        row = cur.fetchone()

    # If not found directly or via FTS, check spelling variants in lexicon entries
    if not row:
        cur.execute("SELECT raw_json FROM lexicon_entries")
        for candidate_row in cur.fetchall():
            c_raw = json.loads(candidate_row["raw_json"])
            variants = c_raw.get("spelling_variants", [])
            if any(
                isinstance(v, dict) and v.get("text", "").strip().lower() == word.lower()
                for v in variants
            ):
                row = candidate_row
                break

    if not row:
        conn.close()
        return None

    raw = json.loads(row["raw_json"])

    # Extract citations from all recorded evidence records
    citations: List[str] = []
    evs = raw.get("provenance", {}).get("evidence_records", [])
    for ev in evs:
        if not isinstance(ev, dict):
            continue
        sid = ev.get("source_id")
        locator = ev.get("locator", "")
        if sid:
            cur.execute("SELECT title FROM sources WHERE source_id = ?", (sid,))
            s_row = cur.fetchone()
            if s_row and s_row["title"]:
                title = s_row["title"]
                c_str = f"{title} ({locator})" if locator else title
            else:
                c_str = f"{sid} ({locator})" if locator else sid
            if c_str not in citations:
                citations.append(c_str)

    citation = "; ".join(citations) if citations else None

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
        source_citation=citation,
        source_citations=citations,
    )


def batch_lookup(
    karbi_words: Sequence[str],
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Optional[DictionaryEntry]]:
    """
    Performs batch lookup for multiple Karbi headwords or spelling variants.

    Args:
        karbi_words: Iterable of Karbi words to look up.
        db_path: Optional custom path to compiled SQLite database.

    Returns:
        Dictionary mapping each input word to its DictionaryEntry, or None if not found.
    """
    return {word: lookup(word, db_path=db_path) for word in karbi_words}

