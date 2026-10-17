"""
Automated Unit Tests for JSONL Loader (`karbi.core.loader`)
===========================================================

Uses temporary directories and fictional test data to verify robust UTF-8
JSONL reading, line tracking, syntax error detection, and type enforcement.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure src is on sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from karbi.core.loader import JSONLLoadError, load_jsonl_file


class TestJSONLLoader(unittest.TestCase):
    """Test suite covering line-by-line JSONL loading and error handling."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_valid_jsonl(self):
        """Valid JSONL file is read into LoadedRecord objects with exact line numbers."""
        test_file = self.dir_path / "valid.jsonl"
        test_file.write_text(
            '{"id": "KB-TEST-01", "name": "first"}\n'
            '{"id": "KB-TEST-02", "name": "second"}\n',
            encoding="utf-8",
        )

        records, errors = load_jsonl_file(test_file)
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 2)

        self.assertEqual(records[0].line_number, 1)
        self.assertEqual(records[0].data["id"], "KB-TEST-01")
        self.assertEqual(records[0].file_path, str(test_file))

        self.assertEqual(records[1].line_number, 2)
        self.assertEqual(records[1].data["id"], "KB-TEST-02")

    def test_empty_file_and_blank_lines(self):
        """Empty files and blank lines between records are skipped cleanly."""
        # 1. Completely empty file
        empty_file = self.dir_path / "empty.jsonl"
        empty_file.write_text("", encoding="utf-8")
        records, errors = load_jsonl_file(empty_file)
        self.assertEqual(records, [])
        self.assertEqual(errors, [])

        # 2. File with blank lines
        blank_file = self.dir_path / "blanks.jsonl"
        blank_file.write_text(
            '\n\n'
            '{"id": "KB-TEST-03"}\n'
            '   \n'
            '{"id": "KB-TEST-04"}\n'
            '\n',
            encoding="utf-8",
        )
        records, errors = load_jsonl_file(blank_file)
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].line_number, 3)
        self.assertEqual(records[1].line_number, 5)

    def test_malformed_json_reports_filename_and_line(self):
        """Syntax errors in JSON report exact file name and line number."""
        broken_file = self.dir_path / "syntax_error.jsonl"
        broken_file.write_text(
            '{"id": "KB-TEST-05", "valid": true}\n'
            '{"id": "KB-TEST-06", broken_json_here\n'
            '{"id": "KB-TEST-07", "valid": true}\n',
            encoding="utf-8",
        )

        records, errors = load_jsonl_file(broken_file)
        self.assertEqual(len(records), 2)  # Lines 1 and 3 parsed
        self.assertEqual(len(errors), 1)

        err = errors[0]
        self.assertIn("syntax_error.jsonl:2", err)
        self.assertIn("Invalid JSON syntax", err)

        # Also test raise_on_error=True
        with self.assertRaises(JSONLLoadError) as ctx:
            load_jsonl_file(broken_file, raise_on_error=True)
        self.assertEqual(ctx.exception.line_number, 2)
        self.assertIn("syntax_error.jsonl", ctx.exception.file_path)

    def test_non_object_json_rejected(self):
        """JSON records that are arrays or primitives instead of objects are rejected."""
        non_object_file = self.dir_path / "non_object.jsonl"
        non_object_file.write_text(
            '["array", "not", "dict"]\n'
            '"simple string"\n'
            '12345\n',
            encoding="utf-8",
        )

        records, errors = load_jsonl_file(non_object_file)
        self.assertEqual(records, [])
        self.assertEqual(len(errors), 3)

        self.assertIn("non_object.jsonl:1", errors[0])
        self.assertIn("Record must be a JSON object (dict)", errors[0])
        self.assertIn("list", errors[0])

        self.assertIn("non_object.jsonl:2", errors[1])
        self.assertIn("str", errors[1])

        self.assertIn("non_object.jsonl:3", errors[2])
        self.assertIn("int", errors[2])

    def test_missing_file_handled(self):
        """Missing files return a clear error message or raise JSONLLoadError."""
        missing = self.dir_path / "does_not_exist.jsonl"
        records, errors = load_jsonl_file(missing, raise_on_error=False)
        self.assertEqual(records, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("File not found", errors[0])

        with self.assertRaises(JSONLLoadError):
            load_jsonl_file(missing, raise_on_error=True)

    def test_unreadable_file_handled(self):
        """Unreadable files (e.g. PermissionError) are captured and reported cleanly."""
        target = self.dir_path / "unreadable.jsonl"
        target.write_text('{"id": "KB-TEST-08"}\n', encoding="utf-8")

        with patch("builtins.open", side_effect=PermissionError("Simulated permission denied")):
            records, errors = load_jsonl_file(target, raise_on_error=False)
            self.assertEqual(records, [])
            self.assertEqual(len(errors), 1)
            self.assertIn("Cannot read file", errors[0])
            self.assertIn("Simulated permission denied", errors[0])

            with self.assertRaises(JSONLLoadError):
                load_jsonl_file(target, raise_on_error=True)


if __name__ == "__main__":
    unittest.main()
