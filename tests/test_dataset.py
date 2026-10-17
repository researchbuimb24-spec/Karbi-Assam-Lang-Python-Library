"""
Automated Unit Tests for Batch Dataset Validation (`karbi.core.dataset`)
========================================================================

Uses temporary directories and fictional test datasets to verify:
- Cross-file duplicate ID detection (entries, sources, examples, reviews).
- Referential integrity for sources and cross-references.
- Batch error aggregation (all errors surfaced in one run).
- Enforcement of strict verification and test-fixture rejection rules.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src is on sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from karbi.core.dataset import DatasetValidator, validate_dataset_files
from karbi.core.models import (
    ReviewerRegistration,
    ReviewerRole,
    SourceType,
    Status,
)


def make_fictional_source_dict(source_id: str = "SRC-PUB-00001", title: str = "Mock Source") -> dict:
    """Helper creating a fictional source dictionary for testing."""
    return {
        "source_id": source_id,
        "source_type": SourceType.PRINT_PUBLICATION.value,
        "title": title,
        "creators": [{"name_or_organization": "Synthetic Test Author", "role": "author"}],
        "rights_and_permissions": {"status": "synthetic_test_data", "details": "Testing only"},
        "publication_details": {"publisher": "Test Press", "year": 2026},
    }


def make_fictional_entry_dict(
    entry_id: str = "KB-TEST-0000001",
    lemma: str = "mock_word",
    source_id: str = "SRC-PUB-00001",
    example_id: str = "EX-000001",
    status: str = Status.DRAFT.value,
    is_test_fixture: bool = True,
    target_xref_id: str = None,
) -> dict:
    """Helper creating a fictional entry dictionary for testing."""
    xrefs = []
    if target_xref_id:
        xrefs.append({"target_entry_id": target_xref_id, "relation_type": "see_also"})

    return {
        "id": entry_id,
        "is_test_fixture": is_test_fixture,
        "headword": {
            "lemma": lemma,
            "script": "latin",
            "orthography_standard": {
                "system_name": "fictional_system",
                "authority_status": "provisional",
            },
        },
        "dialect": {"primary_variety": "fictional_variety", "status": "provisional"},
        "cross_references": xrefs,
        "senses": [
            {
                "sense_id": "S1",
                "part_of_speech": "noun",
                "definitions": {"en": ["mock definition"]},
                "status": status,
                "examples": [
                    {
                        "example_id": example_id,
                        "text_karbi": "Mock sentence.",
                        "translations": {"en": "Mock translation."},
                        "source_id": source_id,
                        "locator": "p. 1",
                    }
                ],
            }
        ],
        "status": status,
        "provenance": {
            "evidence_records": [
                {
                    "source_id": source_id,
                    "locator": "p. 1",
                    "evidence_type": "published_print_citation",
                }
            ],
            "contributors": [],
            "reviews": [],
        },
    }


class TestBatchDatasetValidation(unittest.TestCase):
    """Test suite covering multi-file dataset validation and integrity audits."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_dataset_passes(self):
        """A dataset with valid sources and consistent entries passes validation."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        lex_file = self.dir_path / "lexicon.jsonl"
        lex_file.write_text(
            json.dumps(make_fictional_entry_dict("KB-TEST-0000001", source_id="SRC-PUB-00001", example_id="EX-01")) + "\n"
            + json.dumps(make_fictional_entry_dict("KB-TEST-0000002", source_id="SRC-PUB-00001", example_id="EX-02")) + "\n",
            encoding="utf-8",
        )

        result = validate_dataset_files([lex_file], [src_file])
        self.assertTrue(result.is_valid, f"Expected dataset to be valid, got errors: {[str(e) for e in result.errors]}")
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.lexicon_entries_count, 2)
        self.assertEqual(result.sources_count, 1)

    def test_duplicate_entry_id_across_files(self):
        """Duplicate entry IDs across different files are detected with exact locations."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        file1 = self.dir_path / "file1.jsonl"
        file1.write_text(json.dumps(make_fictional_entry_dict("KB-TEST-0000001", example_id="EX-01")) + "\n", encoding="utf-8")

        file2 = self.dir_path / "file2.jsonl"
        # Duplicate entry ID KB-TEST-0000001!
        file2.write_text(json.dumps(make_fictional_entry_dict("KB-TEST-0000001", example_id="EX-02")) + "\n", encoding="utf-8")

        result = validate_dataset_files([file1, file2], [src_file])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Duplicate entry ID 'KB-TEST-0000001'" in str(e) for e in result.errors))
        self.assertTrue(any("file1.jsonl:1" in str(e) for e in result.errors))

    def test_duplicate_source_id_across_files(self):
        """Duplicate source IDs across source files are detected and reported."""
        src_file1 = self.dir_path / "sources1.jsonl"
        src_file1.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        src_file2 = self.dir_path / "sources2.jsonl"
        # Duplicate source ID!
        src_file2.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        result = validate_dataset_files([], [src_file1, src_file2])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Duplicate source_id 'SRC-PUB-00001'" in str(e) for e in result.errors))

    def test_duplicate_example_id_across_files(self):
        """Duplicate example IDs across different entries and files are detected."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        lex_file1 = self.dir_path / "lex1.jsonl"
        lex_file1.write_text(
            json.dumps(make_fictional_entry_dict("KB-TEST-0000001", example_id="EX-SHARED-01")) + "\n",
            encoding="utf-8",
        )

        lex_file2 = self.dir_path / "lex2.jsonl"
        # Duplicate example ID EX-SHARED-01!
        lex_file2.write_text(
            json.dumps(make_fictional_entry_dict("KB-TEST-0000002", example_id="EX-SHARED-01")) + "\n",
            encoding="utf-8",
        )

        result = validate_dataset_files([lex_file1, lex_file2], [src_file])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Duplicate example_id 'EX-SHARED-01'" in str(e) for e in result.errors))

    def test_missing_source_reference(self):
        """An entry referencing an unregistered source ID is flagged with line and record ID."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        lex_file = self.dir_path / "lexicon.jsonl"
        # References unknown source SRC-PUB-MISSING-999
        lex_file.write_text(
            json.dumps(make_fictional_entry_dict("KB-TEST-0000001", source_id="SRC-PUB-MISSING-999")) + "\n",
            encoding="utf-8",
        )

        result = validate_dataset_files([lex_file], [src_file])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("SRC-PUB-MISSING-999" in str(e) for e in result.errors))

    def test_missing_cross_reference(self):
        """An entry cross-referencing a non-existent entry ID is caught."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        lex_file = self.dir_path / "lexicon.jsonl"
        # Cross-reference targets non-existent KB-TEST-NONEXISTENT
        lex_file.write_text(
            json.dumps(make_fictional_entry_dict("KB-TEST-0000001", target_xref_id="KB-TEST-NONEXISTENT")) + "\n",
            encoding="utf-8",
        )

        result = validate_dataset_files([lex_file], [src_file])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Cross-reference target 'KB-TEST-NONEXISTENT' does not exist" in str(e) for e in result.errors))

    def test_multiple_errors_reported_together(self):
        """Batch validation reports multiple diverse errors together without stopping at the first."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        lex_file = self.dir_path / "lex_multi_err.jsonl"
        # Line 1: Missing lemma
        bad_entry1 = make_fictional_entry_dict("KB-TEST-0000001", lemma="", example_id="EX-01")
        # Line 2: Syntax error
        # Line 3: Unknown source
        bad_entry2 = make_fictional_entry_dict("KB-TEST-0000002", source_id="SRC-PUB-UNKNOWN", example_id="EX-02")

        lex_file.write_text(
            json.dumps(bad_entry1) + "\n"
            + '{"broken_json": [missing_bracket\n'
            + json.dumps(bad_entry2) + "\n",
            encoding="utf-8",
        )

        result = validate_dataset_files([lex_file], [src_file])
        self.assertFalse(result.is_valid)

        # All 3 errors must be surfaced together
        error_texts = [str(e) for e in result.errors]
        has_lemma_error = any("headword.lemma cannot be empty" in t for t in error_texts)
        has_syntax_error = any("Invalid JSON syntax" in t for t in error_texts)
        has_source_error = any("SRC-PUB-UNKNOWN" in t for t in error_texts)

        self.assertTrue(has_lemma_error, "Missing lemma error not reported")
        self.assertTrue(has_syntax_error, "Syntax error on line 2 not reported")
        self.assertTrue(has_source_error, "Unknown source reference not reported")
        self.assertGreaterEqual(len(result.errors), 3)

    def test_test_fixture_cannot_be_verified_in_dataset(self):
        """Test fixtures with status VERIFIED are rejected by dataset validation."""
        src_file = self.dir_path / "sources.jsonl"
        src_file.write_text(json.dumps(make_fictional_source_dict("SRC-PUB-00001")) + "\n", encoding="utf-8")

        lex_file = self.dir_path / "lexicon.jsonl"
        # status: VERIFIED on a test fixture!
        entry = make_fictional_entry_dict("KB-TEST-0000001", status=Status.VERIFIED.value, is_test_fixture=True)
        lex_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")

        result = validate_dataset_files([lex_file], [src_file])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Test fixtures and synthetic entries are strictly prohibited" in str(e) for e in result.errors))


if __name__ == "__main__":
    unittest.main()
