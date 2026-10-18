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

    def test_lookup_populates_source_citation(self):
        """karbi.lookup() populates source_citation from existing evidence records."""
        entry = karbi.lookup("arlèng")
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry.source_citation)
        self.assertIn("The Mikirs", entry.source_citation)
        self.assertIn("p. 74, 80", entry.source_citation)

    def test_translate_query_with_quotes(self):
        """Queries containing double quotes do not crash FTS5 or SQL search."""
        res1 = karbi.translate('say "hello"', from_lang="en")
        self.assertIsInstance(res1, list)
        res2 = karbi.translate('"house"', from_lang="en")
        self.assertIsInstance(res2, list)
        self.assertGreaterEqual(len(res2), 1)
        self.assertEqual(res2[0].karbi_lemma, "hèm")

    def test_sqlite_foreign_keys_enforced(self):
        """Every connection from get_db_connection() enforces SQLite foreign keys."""
        from karbi.core.db import get_db_connection
        conn = get_db_connection()
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        conn.close()
        self.assertEqual(fk, 1)

    def test_gloss_verification_status_separation(self):
        """Unverified Indic glosses are not presented as verified, and verified_only filters them."""
        # 1. English is source-attested
        en_matches = karbi.translate("house", from_lang="en")
        self.assertGreaterEqual(len(en_matches), 1)
        self.assertTrue(en_matches[0].is_verified)
        self.assertEqual(en_matches[0].status, "source_attested")
        self.assertEqual(en_matches[0].entry_status, "SOURCE_ATTESTED")

        # 2. Hindi gloss is unverified despite parent entry being SOURCE_ATTESTED
        hi_matches = karbi.translate("घर", from_lang="hi")
        self.assertGreaterEqual(len(hi_matches), 1)
        self.assertFalse(hi_matches[0].is_verified)
        self.assertEqual(hi_matches[0].status, "unverified")
        self.assertEqual(hi_matches[0].entry_status, "SOURCE_ATTESTED")

        # 3. Bengali gloss is unverified
        bn_matches = karbi.translate("বাড়ি", from_lang="bn")
        self.assertGreaterEqual(len(bn_matches), 1)
        self.assertFalse(bn_matches[0].is_verified)
        self.assertEqual(bn_matches[0].status, "unverified")

        # 4. verified_only=True excludes unverified Indic glosses
        hi_verified = karbi.translate("घर", from_lang="hi", verified_only=True)
        self.assertEqual(hi_verified, [])

        # 5. verified_only=True retains verified/source-attested English glosses
        en_verified = karbi.translate("house", from_lang="en", verified_only=True)
        self.assertGreaterEqual(len(en_verified), 1)
        self.assertEqual(en_verified[0].karbi_lemma, "hèm")

    def test_multiple_evidence_records_formatting(self):
        """Multiple evidence records are joined without discarding citations or inventing titles."""
        import tempfile
        import json
        from karbi.core.db import get_db_connection, init_db_schema

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_db = Path(tmpdir) / "test_multi_ev.db"
            conn = get_db_connection(temp_db)
            init_db_schema(conn)
            cur = conn.cursor()

            # Insert 2 registered sources
            cur.execute(
                "INSERT INTO sources (source_id, source_type, title, creators_json, rights_status) VALUES (?, ?, ?, ?, ?)",
                ("SRC-01", "print_publication", "Stack & Lyall (1908)", "[]", "public_domain"),
            )
            cur.execute(
                "INSERT INTO sources (source_id, source_type, title, creators_json, rights_status) VALUES (?, ?, ?, ?, ?)",
                ("SRC-02", "print_publication", "Grierson (1903)", "[]", "public_domain"),
            )

            # Insert an entry with 2 evidence records
            raw_entry = {
                "id": "KB-TEST-MULTI-01",
                "headword": {"lemma": "multi_word", "script": "latin"},
                "dialect": {"primary_variety": "rongkhang"},
                "senses": [
                    {
                        "sense_id": "S1",
                        "part_of_speech": "noun",
                        "definitions": {"en": ["multi_concept"]},
                        "gloss_provenance": {"en": "source_attested"},
                    }
                ],
                "status": "SOURCE_ATTESTED",
                "provenance": {
                    "evidence_records": [
                        {"source_id": "SRC-01", "locator": "p. 10", "evidence_type": "citation"},
                        {"source_id": "SRC-02", "locator": "p. 385", "evidence_type": "citation"},
                    ]
                },
            }
            cur.execute(
                "INSERT INTO lexicon_entries (entry_id, lemma, script, dialect, status, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
                ("KB-TEST-MULTI-01", "multi_word", "latin", "rongkhang", "SOURCE_ATTESTED", json.dumps(raw_entry)),
            )
            cur.execute(
                "INSERT INTO translations_index (from_lang, query_term, entry_id, sense_id, lemma, part_of_speech, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("en", "multi_concept", "KB-TEST-MULTI-01", "S1", "multi_word", "noun", "SOURCE_ATTESTED"),
            )
            conn.commit()
            conn.close()

            # 1. Test lookup() on multi-evidence entry
            entry = karbi.lookup("multi_word", db_path=temp_db)
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.source_citation,
                "Stack & Lyall (1908) (p. 10); Grierson (1903) (p. 385)",
            )
            self.assertEqual(
                entry.source_citations,
                ["Stack & Lyall (1908) (p. 10)", "Grierson (1903) (p. 385)"],
            )

            # 2. Test translate() on multi-evidence entry
            matches = karbi.translate("multi_concept", from_lang="en", db_path=temp_db)
            self.assertGreaterEqual(len(matches), 1)
            self.assertEqual(
                matches[0].source_citation,
                "Stack & Lyall (1908) (p. 10); Grierson (1903) (p. 385)",
            )
            self.assertEqual(
                matches[0].source_citations,
                ["Stack & Lyall (1908) (p. 10)", "Grierson (1903) (p. 385)"],
            )


if __name__ == "__main__":
    unittest.main()
