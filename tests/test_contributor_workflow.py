"""
Contributor Workflow & Validation Tests for Karbi Language Library
===================================================================

Verifies:
1. Valid contributor source registration and lexical entry validation.
2. Invalid contributions:
   - Malformed JSONL syntax (with line numbers).
   - Missing required fields.
   - Unregistered source citations.
   - Duplicate entry IDs.
   - Broken cross-references.
   - Unauthorized promotion of AI candidates or unverified entries to VERIFIED.
3. Read-only audit guarantee: validation does NOT modify data on disk.
4. Clear reporting of invalid records, missing citations, and unverified glosses.
5. Strict mode rejection of unverified glosses.
6. CLI `karbi validate` and `karbi validate --json` behavior.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure src is in sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import karbi
from karbi.cli import main as cli_main
from karbi.core.dataset import DatasetValidator, validate_dataset_files
from karbi.core.models import SourceType, Status


def _make_valid_source_dict(
    source_id: str = "SRC-PUB-2026-TEST",
    title: str = "Contributor Test Vocabulary",
) -> dict:
    """Creates a valid dictionary representing a registered source."""
    return {
        "source_id": source_id,
        "source_type": SourceType.PRINT_PUBLICATION.value,
        "title": title,
        "creators": [{"name_or_organization": "Test Contributor", "role": "author"}],
        "publication_details": {
            "publisher": "Karbi Cultural Studies Press",
            "place": "Diphu",
            "year": 2026,
        },
        "archive_location": "Diphu District Library",
        "access_date": "2026-10-17",
        "rights_and_permissions": {
            "status": "open_access",
            "details": "Attested field vocabulary with community consent",
            "community_consent_verified": True,
        },
    }


def _make_valid_lexicon_entry_dict(
    entry_id: str = "KB-LEX-0000031",
    lemma: str = "arhe",
    source_id: str = "SRC-PUB-2026-TEST",
    status: str = Status.SOURCE_ATTESTED.value,
    target_xref_id: str = None,
    with_unverified_glosses: bool = True,
) -> dict:
    """Creates a valid dictionary representing a Karbi lexical entry."""
    xrefs = []
    if target_xref_id:
        xrefs.append({
            "target_entry_id": target_xref_id,
            "relationship": "see_also",
            "note": "Related semantic concept",
        })

    definitions = {
        "en": ["price", "cost", "value"],
    }
    gloss_prov = {
        "en": "source_attested",
    }

    if with_unverified_glosses:
        definitions["hi"] = [{"text": "मूल्य, कीमत", "verified": False}]
        definitions["as"] = [{"text": "মূল্য, দাম", "verified": False}]
        gloss_prov["hi"] = "unverified"
        gloss_prov["as"] = "unverified"

    return {
        "id": entry_id,
        "is_test_fixture": False,
        "headword": {
            "lemma": lemma,
            "script": "latin",
            "orthography_standard": {
                "system_name": "contemporary_standard",
                "authority_status": "community_adopted",
            },
        },
        "phonetics": {
            "ipa": "/aɾˈhe/",
            "tone_pattern": None,
            "audio_recording_ref": None,
        },
        "dialect": {
            "primary_variety": "rongkhang",
            "status": "standard",
        },
        "spelling_variants": [],
        "cross_references": xrefs,
        "senses": [
            {
                "sense_id": "S1",
                "part_of_speech": "noun",
                "definitions": definitions,
                "gloss_provenance": gloss_prov,
                "cultural_metadata": {
                    "is_culturally_sensitive": False,
                    "access_level": "public",
                    "allow_search_indexing": True,
                    "cultural_notes": "Commercial / economic concept.",
                },
                "examples": [
                    {
                        "example_id": f"EX-{entry_id}-01",
                        "text_karbi": "Arhe ke-un.",
                        "translations": {"en": "Affordable price."},
                        "source_id": source_id,
                        "locator": "p. 42",
                    }
                ],
            }
        ],
        "status": status,
        "provenance": {
            "evidence_records": [
                {
                    "source_id": source_id,
                    "locator": "p. 42",
                    "evidence_type": "published_print_citation",
                    "extracted_text_quote": "arhe, 'price'",
                }
            ],
            "contributors": [
                {
                    "contributor_id": "CONTRIB-2026-TEST",
                    "role": "field_researcher",
                    "date": "2026-10-17",
                    "submission_channel": "community_submission",
                }
            ],
            "reviews": [],
        },
    }


class TestContributorWorkflow(unittest.TestCase):
    """Test suite for the Karbi contributor workflow and dataset validation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        self.sources_file = self.test_dir / "sources.jsonl"
        self.lexicon_file = self.test_dir / "core_lexicon.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_contributor_entry_and_source(self):
        """A properly formatted entry and registered source validate cleanly."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        lex_data = _make_valid_lexicon_entry_dict("KB-LEX-0000031", source_id="SRC-PUB-2026-TEST")

        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")
        self.lexicon_file.write_text(json.dumps(lex_data) + "\n", encoding="utf-8")

        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertTrue(res.is_valid, f"Expected valid result, got errors: {res.errors}")
        self.assertEqual(len(res.errors), 0)
        self.assertEqual(res.lexicon_entries_count, 1)
        self.assertEqual(res.sources_count, 1)
        self.assertEqual(res.status_counts.get("SOURCE_ATTESTED"), 1)
        self.assertEqual(res.unverified_glosses_count, 2)  # hi and as
        self.assertEqual(res.unverified_glosses_by_lang.get("hi"), 1)
        self.assertEqual(res.unverified_glosses_by_lang.get("as"), 1)

    def test_invalid_unregistered_source_citation(self):
        """Entries citing unregistered sources fail validation."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        # Entry cites a different unregistered source
        lex_data = _make_valid_lexicon_entry_dict(
            "KB-LEX-0000031", source_id="SRC-PUB-UNREGISTERED-001"
        )

        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")
        self.lexicon_file.write_text(json.dumps(lex_data) + "\n", encoding="utf-8")

        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertFalse(res.is_valid)
        error_msgs = [e.message for e in res.errors]
        self.assertTrue(
            any("SRC-PUB-UNREGISTERED-001" in m and ("unknown source_id" in m or "not registered" in m) for m in error_msgs),
            f"Expected unregistered source error, got: {error_msgs}",
        )

    def test_invalid_malformed_jsonl_syntax(self):
        """Malformed JSON lines are caught with line numbers and do not crash validation."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")

        # Lexicon with syntax error on line 2
        line1 = json.dumps(_make_valid_lexicon_entry_dict("KB-LEX-0000031", source_id="SRC-PUB-2026-TEST"))
        line2_broken = '{"id": "KB-LEX-0000032", "headword": {broken_json'
        self.lexicon_file.write_text(f"{line1}\n{line2_broken}\n", encoding="utf-8")

        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertFalse(res.is_valid)
        error_msgs = [e.message for e in res.errors]
        self.assertTrue(
            any("Invalid JSON syntax" in m and ":2" in m for m in error_msgs),
            f"Expected syntax error on line 2, got: {error_msgs}",
        )

    def test_invalid_duplicate_entry_id(self):
        """Duplicate entry IDs are detected and reported."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")

        entry1 = _make_valid_lexicon_entry_dict("KB-LEX-0000031", lemma="arhe", source_id="SRC-PUB-2026-TEST")
        entry2_dup = _make_valid_lexicon_entry_dict("KB-LEX-0000031", lemma="arhe_variant", source_id="SRC-PUB-2026-TEST")

        self.lexicon_file.write_text(f"{json.dumps(entry1)}\n{json.dumps(entry2_dup)}\n", encoding="utf-8")

        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertFalse(res.is_valid)
        error_msgs = [e.message for e in res.errors]
        self.assertTrue(
            any("Duplicate entry ID" in m and "KB-LEX-0000031" in m for m in error_msgs),
            f"Expected duplicate entry ID error, got: {error_msgs}",
        )

    def test_invalid_broken_cross_reference(self):
        """Cross-references targeting nonexistent entry IDs fail validation."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")

        entry = _make_valid_lexicon_entry_dict(
            "KB-LEX-0000031",
            source_id="SRC-PUB-2026-TEST",
            target_xref_id="KB-LEX-9999999",  # Does not exist
        )
        self.lexicon_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")

        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertFalse(res.is_valid)
        error_msgs = [e.message for e in res.errors]
        self.assertTrue(
            any("KB-LEX-9999999" in m and "does not exist" in m for m in error_msgs),
            f"Expected broken cross-reference error, got: {error_msgs}",
        )

    def test_ai_candidate_cannot_claim_verified_status(self):
        """AI-generated entries cannot claim VERIFIED status without approved reviewers."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")

        entry = _make_valid_lexicon_entry_dict(
            "KB-LEX-0000031",
            source_id="SRC-PUB-2026-TEST",
            status=Status.VERIFIED.value,  # Contributor claiming VERIFIED without reviewer
        )
        self.lexicon_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")

        # Without reviewer registry, fail-closed verification must reject this
        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertFalse(res.is_valid)
        error_msgs = [e.message for e in res.errors]
        self.assertTrue(
            any("FAILED CLOSED" in m.upper() or "CANNOT MARK VERIFIED" in m.upper() or "ALL SENSES MUST BE VERIFIED" in m.upper() for m in error_msgs),
            f"Expected fail-closed verification error, got: {error_msgs}",
        )

    def test_validation_does_not_modify_data_files(self):
        """Validation is strictly read-only and never modifies files on disk."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        entry_data = _make_valid_lexicon_entry_dict("KB-LEX-0000031", source_id="SRC-PUB-2026-TEST")

        src_content = json.dumps(src_data) + "\n"
        lex_content = json.dumps(entry_data) + "\n"

        self.sources_file.write_text(src_content, encoding="utf-8")
        self.lexicon_file.write_text(lex_content, encoding="utf-8")

        src_mtime_before = self.sources_file.stat().st_mtime_ns
        lex_mtime_before = self.lexicon_file.stat().st_mtime_ns

        # Run validation
        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertTrue(res.is_valid)

        # Confirm content and stats are unchanged
        self.assertEqual(self.sources_file.read_text(encoding="utf-8"), src_content)
        self.assertEqual(self.lexicon_file.read_text(encoding="utf-8"), lex_content)
        self.assertEqual(self.sources_file.stat().st_mtime_ns, src_mtime_before)
        self.assertEqual(self.lexicon_file.stat().st_mtime_ns, lex_mtime_before)

    def test_unverified_glosses_reporting(self):
        """Unverified glosses are clearly counted and reported without failing validation in standard mode."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        entry_data = _make_valid_lexicon_entry_dict(
            "KB-LEX-0000031",
            source_id="SRC-PUB-2026-TEST",
            with_unverified_glosses=True,
        )

        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")
        self.lexicon_file.write_text(json.dumps(entry_data) + "\n", encoding="utf-8")

        res = validate_dataset_files([self.lexicon_file], [self.sources_file])
        self.assertTrue(res.is_valid)
        self.assertEqual(res.unverified_glosses_count, 2)
        report_text = res.report(verbose=True)
        self.assertIn("Translation Verification Audit:", report_text)
        self.assertIn("Language 'hi':", report_text)
        self.assertIn("Language 'as':", report_text)

    def test_strict_mode_rejects_unverified_glosses(self):
        """Strict mode treats unverified glosses as errors."""
        src_data = _make_valid_source_dict("SRC-PUB-2026-TEST")
        entry_data = _make_valid_lexicon_entry_dict(
            "KB-LEX-0000031",
            source_id="SRC-PUB-2026-TEST",
            with_unverified_glosses=True,
        )

        self.sources_file.write_text(json.dumps(src_data) + "\n", encoding="utf-8")
        self.lexicon_file.write_text(json.dumps(entry_data) + "\n", encoding="utf-8")

        # Validate with strict=True
        res = karbi.validate_dataset(
            lexicon_path=self.lexicon_file,
            sources_path=self.sources_file,
            strict=True,
        )
        self.assertFalse(res.is_valid)
        error_msgs = [e.message for e in res.errors]
        self.assertTrue(any("[STRICT]" in m for m in error_msgs))

    def test_cli_validate_repository_data(self):
        """The CLI validate command runs on authoritative repository data and exits 0."""
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = cli_main(["validate"])
        self.assertEqual(ret, 0)
        output = stdout_buf.getvalue()
        self.assertIn("PASSED [VALID]", output)
        self.assertIn("Lexicon Entries:", output)
        self.assertIn("Sources Registered:", output)

    def test_cli_validate_json_output(self):
        """The CLI validate --json command produces valid JSON."""
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = cli_main(["validate", "--json"])
        self.assertEqual(ret, 0)
        output = stdout_buf.getvalue()
        parsed = json.loads(output)
        self.assertTrue(parsed["is_valid"])
        self.assertGreater(parsed["lexicon_entries_count"], 0)
        self.assertGreater(parsed["sources_count"], 0)
        self.assertIn("status_counts", parsed)
        self.assertIn("unverified_glosses_by_lang", parsed)

    def test_cli_validate_failure_returns_exit_code_1(self):
        """The CLI validate command exits with 1 on invalid files."""
        # Create an invalid file
        broken_file = self.test_dir / "broken.jsonl"
        broken_file.write_text('{"id": "KB-LEX-0000001", broken\n', encoding="utf-8")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            ret = cli_main(["validate", "--lexicon", str(broken_file)])
        self.assertEqual(ret, 1)
        err_out = stderr_buf.getvalue() or stdout_buf.getvalue()
        self.assertIn("FAILED", err_out)

    def test_public_api_validate_dataset(self):
        """karbi.validate_dataset is exposed in the public API."""
        self.assertTrue(callable(karbi.validate_dataset))
        self.assertIn("validate_dataset", karbi.__all__)
        self.assertIn("DatasetValidationResult", karbi.__all__)

        res = karbi.validate_dataset()
        self.assertTrue(res.is_valid)
        self.assertGreater(res.lexicon_entries_count, 0)
        self.assertGreater(res.sources_count, 0)


if __name__ == "__main__":
    unittest.main()
