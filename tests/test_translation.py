"""
Automated Unit Tests for Multilingual-to-Karbi Translation
==========================================================

Verifies translation lookups:
- English -> Karbi
- Hindi -> Karbi
- Assamese -> Karbi
- Bengali -> Karbi
- Exact lemma retrieval, citation attachment, and verified status checks.
"""

import sys
import unittest
from pathlib import Path

# Add src to sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import karbi


class TestMultilingualTranslation(unittest.TestCase):
    """Test suite covering the Multilingual-to-Karbi translation engine."""

    def test_english_to_karbi(self):
        """English queries return accurate, cited Karbi translations."""
        # 1. 'house' -> 'hèm'
        results = karbi.translate("house", from_lang="en")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "hèm")
        self.assertEqual(results[0].part_of_speech, "noun")
        self.assertIn("The Mikirs", results[0].source_citation)

        # 2. 'water' -> 'làng'
        results = karbi.translate("water", from_lang="en")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "làng")

        # 3. 'fire' -> 'mē'
        results = karbi.translate("fire", from_lang="en")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "mē")

    def test_hindi_to_karbi(self):
        """Hindi queries return accurate Karbi translations."""
        # 'घर' -> 'hèm'
        results = karbi.translate("घर", from_lang="hi")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "hèm")

        # 'पानी' -> 'làng'
        results = karbi.translate("पानी", from_lang="hi")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "làng")

        # 'आग' -> 'mē'
        results = karbi.translate("आग", from_lang="hi")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "mē")

    def test_assamese_to_karbi(self):
        """Assamese queries return accurate Karbi translations."""
        # 'ঘৰ' -> 'hèm'
        results = karbi.translate("ঘৰ", from_lang="as")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "hèm")

        # 'পানী' -> 'làng'
        results = karbi.translate("পানী", from_lang="as")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "làng")

        # 'জুই' -> 'mē'
        results = karbi.translate("জুই", from_lang="as")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "mē")

    def test_bengali_to_karbi(self):
        """Bengali queries return accurate Karbi translations."""
        # 'বাড়ি' -> 'hèm'
        results = karbi.translate("বাড়ি", from_lang="bn")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "hèm")

        # 'জল' -> 'làng'
        results = karbi.translate("জল", from_lang="bn")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].karbi_lemma, "làng")

    def test_karbi_headword_lookup(self):
        """Direct Karbi headword lookup retrieves entry with definitions and examples."""
        entry = karbi.lookup("arlèng")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.lemma, "arlèng")
        self.assertIn("man", entry.senses[0]["definitions"]["en"])

    def test_unsupported_or_empty_query(self):
        """Empty or non-existent terms return an empty list gracefully."""
        self.assertEqual(karbi.translate("", from_lang="en"), [])
        self.assertEqual(karbi.translate("nonexistent_word_xyz_123", from_lang="en"), [])

    def test_supported_languages_metadata(self):
        """Registry distinguishes active data from pending pairs."""
        langs = karbi.get_supported_languages()
        self.assertIn("en", langs)
        self.assertEqual(langs["en"]["status"], "active_data")
        self.assertIn("mr", langs)
        self.assertEqual(langs["mr"]["status"], "awaiting_sourced_entries")


if __name__ == "__main__":
    unittest.main()
