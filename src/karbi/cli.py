"""
Command-Line Dictionary & Translation Interface for Karbi (`karbi.cli`)
========================================================================

Provides a CLI for:
- Direct Karbi headword and spelling variant lookup.
- Translation search from English, Hindi, Assamese, and Bengali into Karbi.
- Display of pronunciation (IPA) and recorded bibliographic source citations.
- Unambiguous labeling of unverified translations.
- Clean missing-word handling and JSON export mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from karbi.core.dataset import DatasetValidationResult, validate_dataset_files
from karbi.core.db import DEFAULT_DB_PATH
from karbi.core.resources import get_resource_paths
from karbi.dictionary import DictionaryEntry, lookup, lookup_all
from karbi.translator import (
    SUPPORTED_LANGUAGES,
    TranslationMatch,
    get_supported_languages,
    translate,
)


def _ensure_utf8_output() -> None:
    """Configures stdout and stderr to handle UTF-8 text safely on all platforms."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _format_verification_badge(is_verified: bool, status_text: str = "") -> str:
    """Formats a clear, visible badge for translation verification status."""
    st_upper = status_text.upper().replace("_", " ") if status_text else ""
    if is_verified:
        return f"[{st_upper or 'VERIFIED'}]"
    return "[UNVERIFIED]"


def format_dictionary_entry(entry: DictionaryEntry) -> str:
    """
    Formats a Karbi DictionaryEntry into a clear, readable text report.
    Pronunciation, citations, and verification status for each gloss are prominently displayed.
    """
    lines = [
        "=" * 70,
        f"KARBI HEADWORD: {entry.lemma}",
        "=" * 70,
        f"  Script:         {entry.script.title()}",
        f"  Dialect:        {entry.dialect.title()}",
        f"  Status:         {entry.status}",
    ]

    if entry.phonetics_ipa:
        lines.append(f"  Pronunciation:  {entry.phonetics_ipa}")

    if entry.spelling_variants:
        var_strs = []
        for v in entry.spelling_variants:
            if isinstance(v, dict):
                txt = v.get("text", "")
                ctx = v.get("dialect_or_context", "")
                var_strs.append(f"{txt} ({ctx})" if ctx else txt)
            elif isinstance(v, str):
                var_strs.append(v)
        if var_strs:
            lines.append(f"  Variant(s):     {', '.join(var_strs)}")

    if entry.source_citations:
        lines.append("  Source(s):")
        for cit in entry.source_citations:
            lines.append(f"    - {cit}")
    elif entry.source_citation:
        lines.append(f"  Source(s):      {entry.source_citation}")

    lines.append("")
    lines.append("Senses & Meanings:")

    for idx, sense in enumerate(entry.senses, 1):
        pos = sense.get("part_of_speech", "general")
        sid = sense.get("sense_id", f"S{idx}")
        lines.append(f"  [{idx}] Part of Speech: {pos} ({sid})")

        defs = sense.get("definitions", {})
        gloss_prov = sense.get("gloss_provenance") or {}

        lang_labels = [
            ("en", "English"),
            ("hi", "Hindi"),
            ("as", "Assamese"),
            ("bn", "Bengali"),
        ]

        for code, label in lang_labels:
            items = defs.get(code, [])
            if not items:
                continue

            term_pieces = []
            for item in items:
                if isinstance(item, dict):
                    txt = item.get("text", "")
                    ver = item.get("verified", False)
                    badge = "[VERIFIED]" if ver else "[UNVERIFIED]"
                    term_pieces.append(f"{txt} {badge}")
                elif isinstance(item, str):
                    prov = str(gloss_prov.get(code, "")).lower()
                    is_ver = prov in ("source_attested", "verified", "peer_reviewed")
                    badge = _format_verification_badge(is_ver, prov)
                    term_pieces.append(f"{item} {badge}")

            if term_pieces:
                lines.append(f"      • {label:<10}: {', '.join(term_pieces)}")

        cult = sense.get("cultural_metadata", {})
        if cult and cult.get("cultural_notes"):
            lines.append(f"      • Cultural Note: {cult['cultural_notes']}")

        examples = sense.get("examples", [])
        if examples:
            lines.append("      • Examples:")
            for ex in examples:
                k_text = ex.get("text_karbi", "")
                en_trans = ex.get("translations", {}).get("en", "")
                loc = ex.get("locator", "")
                loc_str = f" ({loc})" if loc else ""
                lines.append(f"        - Karbi:   {k_text}")
                if en_trans:
                    lines.append(f"          English: {en_trans}{loc_str}")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_translation_match(match: TranslationMatch, index: Optional[int] = None) -> str:
    """
    Formats a TranslationMatch into a clear, readable text report.
    Explicitly labels unverified translations.
    """
    prefix = f"{index}. " if index is not None else ""
    lines = [
        f"{prefix}Karbi Lemma:   {match.karbi_lemma} ({match.part_of_speech})",
        f"   Matched Term:  {match.matched_meaning} (from {match.source_language.upper()})",
    ]

    # Verification status
    badge = _format_verification_badge(match.is_verified, match.status)
    lines.append(f"   Gloss Status:  {badge} (Entry Status: {match.entry_status})")
    if not match.is_verified:
        lines.append("   [!] CAUTION:   This translation gloss is unverified and has not been confirmed by native speakers.")

    if match.phonetics_ipa:
        lines.append(f"   Pronunciation: {match.phonetics_ipa}")

    if match.dialect:
        lines.append(f"   Dialect:       {match.dialect.title()}")

    if match.source_citations:
        lines.append("   Source(s):")
        for cit in match.source_citations:
            lines.append(f"     - {cit}")
    elif match.source_citation:
        lines.append(f"   Source(s):     {match.source_citation}")

    # Definitions in all languages
    if match.all_definitions:
        lines.append("   Definitions in other languages:")
        lang_names = {"en": "English", "hi": "Hindi", "as": "Assamese", "bn": "Bengali"}
        for code, l_name in lang_names.items():
            defs = match.all_definitions.get(code, [])
            if not defs:
                continue
            rendered = []
            for d in defs:
                if isinstance(d, dict):
                    txt = d.get("text", "")
                    ver = d.get("verified", False)
                    rendered.append(f"{txt} {'[VERIFIED]' if ver else '[UNVERIFIED]'}")
                elif isinstance(d, str):
                    rendered.append(d)
            if rendered:
                lines.append(f"     • {l_name:<10}: {', '.join(rendered)}")

    if match.cultural_notes:
        lines.append(f"   Cultural Note: {match.cultural_notes}")

    if match.examples:
        lines.append("   Examples:")
        for ex in match.examples:
            k_txt = ex.get("text_karbi", "")
            en_txt = ex.get("translations", {}).get("en", "")
            lines.append(f"     - Karbi:   {k_txt}")
            if en_txt:
                lines.append(f"       English: {en_txt}")

    return "\n".join(lines)


def run_lookup(
    karbi_word: str,
    as_json: bool = False,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Performs headword lookup in Karbi dictionary.
    Returns 0 if found, 1 if not found.
    """
    entries = lookup_all(karbi_word, db_path=db_path)
    if not entries:
        if as_json:
            print(json.dumps({"found": False, "query": karbi_word, "results": []}))
        else:
            print(f"No Karbi dictionary entry found for: '{karbi_word}'.", file=sys.stderr)
            print("Suggestions:", file=sys.stderr)
            print("  - Check diacritics (e.g., 'hèm', 'làng', 'arlèng')", file=sys.stderr)
            print(f"  - Search across translations with: karbi search {karbi_word}", file=sys.stderr)
        return 1

    if as_json:
        entry_dicts = [
            {
                "entry_id": e.entry_id,
                "lemma": e.lemma,
                "script": e.script,
                "dialect": e.dialect,
                "status": e.status,
                "phonetics_ipa": e.phonetics_ipa,
                "senses": e.senses,
                "spelling_variants": e.spelling_variants,
                "source_citations": e.source_citations,
            }
            for e in entries
        ]
        data = {
            "found": True,
            "query": karbi_word,
            "entry": entry_dicts[0],
            "entries": entry_dicts,
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for idx, e in enumerate(entries):
            if idx > 0:
                print("\n" + "-" * 70 + "\n")
            print(format_dictionary_entry(e))

    return 0


def run_translate(
    query: str,
    from_lang: str = "en",
    verified_only: bool = False,
    as_json: bool = False,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Translates from a source language into Karbi.
    Returns 0 if matches found, 1 if no matches found.
    """
    matches = translate(
        query,
        from_lang=from_lang,
        verified_only=verified_only,
        db_path=db_path,
    )

    lang_info = SUPPORTED_LANGUAGES.get(from_lang, {"name": from_lang})
    lang_name = lang_info.get("name", from_lang)

    if not matches:
        if as_json:
            print(json.dumps({
                "found": False,
                "query": query,
                "source_language": from_lang,
                "verified_only": verified_only,
                "results": [],
            }))
        else:
            filter_msg = " (verified only)" if verified_only else ""
            print(
                f"No matching Karbi entries found for: '{query}' [Source: {lang_name} ({from_lang})]{filter_msg}.",
                file=sys.stderr,
            )
            print("Suggestions:", file=sys.stderr)
            print("  - Check spelling or search synonyms", file=sys.stderr)
            print("  - List supported languages with: karbi languages", file=sys.stderr)
            print(f"  - Try multi-language search with: karbi search \"{query}\"", file=sys.stderr)
        return 1

    if as_json:
        out_matches = []
        for m in matches:
            out_matches.append({
                "karbi_lemma": m.karbi_lemma,
                "part_of_speech": m.part_of_speech,
                "matched_meaning": m.matched_meaning,
                "source_language": m.source_language,
                "status": m.status,
                "entry_status": m.entry_status,
                "is_verified": m.is_verified,
                "phonetics_ipa": m.phonetics_ipa,
                "source_citations": m.source_citations,
                "all_definitions": m.all_definitions,
                "cultural_notes": m.cultural_notes,
                "examples": m.examples,
            })
        print(json.dumps({
            "found": True,
            "query": query,
            "source_language": from_lang,
            "count": len(out_matches),
            "results": out_matches,
        }, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print(f"TRANSLATION RESULTS: '{query}' ({lang_name} -> Karbi)")
        print("=" * 70)
        print(f"Found {len(matches)} matching entry/entries:\n")
        for idx, match in enumerate(matches, 1):
            print(format_translation_match(match, index=idx))
            if idx < len(matches):
                print("-" * 50)
        print("=" * 70)

    return 0


def run_search(
    query: str,
    lang: str = "auto",
    verified_only: bool = False,
    as_json: bool = False,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Flexible search across Karbi dictionary and translation index.
    If lang='karbi', looks up headwords.
    If lang in ('en', 'hi', 'as', 'bn'), translates from that language.
    If lang='auto', first checks Karbi headwords; if not found or if translation query,
    checks translations across supported languages.
    """
    clean_query = query.strip()
    if not clean_query:
        print("Error: Search query cannot be empty.", file=sys.stderr)
        return 2

    # Explicit Karbi lookup
    if lang == "karbi":
        return run_lookup(clean_query, as_json=as_json, db_path=db_path)

    # Specific source language
    if lang in ("en", "hi", "as", "bn"):
        return run_translate(clean_query, from_lang=lang, verified_only=verified_only, as_json=as_json, db_path=db_path)

    # Auto search:
    # 1. Try Karbi headword lookup first
    if not verified_only:
        entry = lookup(clean_query, db_path=db_path)
        if entry:
            return run_lookup(clean_query, as_json=as_json, db_path=db_path)

    # 2. Try translating from each supported active language
    candidate_langs = ["en", "as", "hi", "bn"]
    for code in candidate_langs:
        matches = translate(clean_query, from_lang=code, verified_only=verified_only, db_path=db_path)
        if matches:
            return run_translate(clean_query, from_lang=code, verified_only=verified_only, as_json=as_json, db_path=db_path)

    # Not found in any language
    if as_json:
        print(json.dumps({
            "found": False,
            "query": clean_query,
            "searched_languages": candidate_langs + ["karbi"],
            "results": [],
        }))
    else:
        print(f"No matching Karbi entries found for '{clean_query}'.", file=sys.stderr)
        print("Searched:", file=sys.stderr)
        print("  - Karbi headwords and contemporary variants", file=sys.stderr)
        print("  - English, Assamese, Hindi, and Bengali translations", file=sys.stderr)
        print("Suggestions:", file=sys.stderr)
        print("  - Specify the source language explicitly: karbi translate <word> --from <en|hi|as|bn>", file=sys.stderr)
        print("  - Check available languages: karbi languages", file=sys.stderr)

    return 1


def run_languages(as_json: bool = False) -> int:
    """Displays registry of supported source languages and their status."""
    langs = get_supported_languages()
    if as_json:
        print(json.dumps(langs, indent=2))
        return 0

    print("=" * 60)
    print("SUPPORTED SOURCE LANGUAGES FOR KARBI TRANSLATION")
    print("=" * 60)
    for code, info in langs.items():
        name = info.get("name", code)
        script = info.get("script", "Unknown")
        status = info.get("status", "unknown").replace("_", " ").title()
        print(f"  • [{code}] {name:<12} (Script: {script:<18}) Status: {status}")
    print("=" * 60)
    return 0


def run_validate(
    lexicon_paths: Optional[Sequence[Union[str, Path]]] = None,
    source_paths: Optional[Sequence[Union[str, Path]]] = None,
    strict: bool = False,
    verbose: bool = False,
    as_json: bool = False,
) -> int:
    """
    Validates JSONL dataset files for syntax, schema, unique IDs, source citations,
    and cross-reference integrity. Audits unverified translations and AI candidates.
    Does NOT modify or rewrite data.
    """
    # If paths not explicitly provided, discover default dataset resources
    if not lexicon_paths or not source_paths:
        def_lex, def_src = get_resource_paths()
        lexicon_paths = lexicon_paths or def_lex
        source_paths = source_paths or def_src

    # Expand any directory paths to *.jsonl files
    final_lex: List[Path] = []
    for lp in lexicon_paths:
        p = Path(lp)
        if p.is_dir():
            final_lex.extend(sorted(p.glob("*.jsonl")))
        elif p.is_file():
            final_lex.append(p)
        else:
            final_lex.append(p)

    final_src: List[Path] = []
    for sp in source_paths:
        p = Path(sp)
        if p.is_dir():
            final_src.extend(sorted(p.glob("*.jsonl")))
        elif p.is_file():
            final_src.append(p)
        else:
            final_src.append(p)

    res = validate_dataset_files(lexicon_paths=final_lex, source_paths=final_src)

    if as_json:
        print(json.dumps(res.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(res.report(verbose=verbose or not res.is_valid))

    if not res.is_valid:
        return 1

    if strict and (res.unverified_glosses_count > 0 or len(res.missing_citation_entries) > 0):
        print(
            f"Error: Strict validation mode active. "
            f"Found {res.unverified_glosses_count} unverified gloss(es) and "
            f"{len(res.missing_citation_entries)} entry/entries missing citations.",
            file=sys.stderr,
        )
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="karbi",
        description="Command-line dictionary and multilingual translation tool for the Karbi language.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # 1. lookup subcommand
    p_lookup = subparsers.add_parser("lookup", help="Look up a Karbi headword or spelling variant.")
    p_lookup.add_argument("word", help="The Karbi word to look up (e.g. 'arlèng', 'hèm', 'làng', 'hem')")
    p_lookup.add_argument("--json", action="store_true", help="Output results in JSON format")

    # 2. translate subcommand
    p_trans = subparsers.add_parser("translate", help="Translate from English, Hindi, Assamese, or Bengali into Karbi.")
    p_trans.add_argument("query", help="Word or concept to translate into Karbi (e.g. 'water', 'घर', 'পানী')")
    p_trans.add_argument(
        "--from", "-l", "--lang", "--from-lang",
        dest="from_lang",
        default="en",
        choices=["en", "hi", "as", "bn"],
        help="Source language code (default: 'en')",
    )
    p_trans.add_argument(
        "--verified-only",
        action="store_true",
        help="Only return entries verified by registered authorities",
    )
    p_trans.add_argument("--json", action="store_true", help="Output results in JSON format")

    # 3. search subcommand
    p_search = subparsers.add_parser("search", help="Search across Karbi headwords and translation glosses.")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument(
        "--lang", "-l",
        default="auto",
        choices=["auto", "karbi", "en", "hi", "as", "bn"],
        help="Language to search in ('auto', 'karbi', 'en', 'hi', 'as', 'bn')",
    )
    p_search.add_argument(
        "--verified-only",
        action="store_true",
        help="Only return verified translations",
    )
    p_search.add_argument("--json", action="store_true", help="Output results in JSON format")

    # 4. languages subcommand
    p_langs = subparsers.add_parser("languages", help="List supported translation source languages.")
    p_langs.add_argument("--json", action="store_true", help="Output results in JSON format")

    # 5. validate subcommand
    p_val = subparsers.add_parser("validate", help="Validate dataset files for schema, unique IDs, citations, and unverified glosses.")
    p_val.add_argument("--lexicon", "-l", nargs="*", help="Path(s) to lexicon JSONL file(s) or directory")
    p_val.add_argument("--sources", "-s", nargs="*", help="Path(s) to sources JSONL file(s) or directory")
    p_val.add_argument("--strict", action="store_true", help="Fail with non-zero exit code if unverified glosses or missing citations exist")
    p_val.add_argument("--verbose", "-V", action="store_true", help="Show detailed breakdown of missing citations and errors")
    p_val.add_argument("--json", action="store_true", help="Output validation report in JSON format")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Main entry point for the Karbi CLI.
    Supports subcommands ('lookup', 'translate', 'search', 'languages', 'validate')
    as well as direct queries ('karbi arlèng', 'karbi water').
    """
    _ensure_utf8_output()
    parser = build_parser()

    if argv is None:
        argv = sys.argv[1:]

    # If invoked with no arguments, display help
    if not argv:
        parser.print_help()
        return 0

    known_subcmds = {"lookup", "translate", "search", "languages", "validate", "-h", "--help", "-v", "--version"}

    # Rewrite direct word queries to 'search' for immediate usability
    if argv and argv[0] not in known_subcmds:
        if argv[0].startswith("-"):
            # Flag passed directly e.g. `karbi --json water`
            argv = ["search"] + list(argv)
        else:
            # Word passed directly e.g. `karbi water` or `karbi arlèng`
            argv = ["search"] + list(argv)

    args = parser.parse_args(argv)

    if args.subcommand == "lookup":
        return run_lookup(args.word, as_json=args.json)
    elif args.subcommand == "translate":
        return run_translate(
            args.query,
            from_lang=args.from_lang,
            verified_only=args.verified_only,
            as_json=args.json,
        )
    elif args.subcommand == "search":
        return run_search(
            args.query,
            lang=args.lang,
            verified_only=args.verified_only,
            as_json=args.json,
        )
    elif args.subcommand == "languages":
        return run_languages(as_json=args.json)
    elif args.subcommand == "validate":
        return run_validate(
            lexicon_paths=args.lexicon,
            source_paths=args.sources,
            strict=args.strict,
            verbose=args.verbose,
            as_json=args.json,
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
