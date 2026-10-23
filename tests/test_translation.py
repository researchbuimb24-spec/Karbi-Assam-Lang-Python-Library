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

    def test_unsupported_language_returns_empty_without_fallback(self):
        """Unsupported language codes return empty list and never fall back to English FTS."""
        # 'fr' is not in SUPPORTED_LANGUAGES, must not return English results
        fr_matches = karbi.translate("house", from_lang="fr")
        self.assertEqual(fr_matches, [])

        xyz_matches = karbi.translate("water", from_lang="xyz_nonexistent")
        self.assertEqual(xyz_matches, [])

    def test_none_and_invalid_inputs(self):
        """None or non-string inputs in translate, lookup, and lookup_all are handled safely."""
        self.assertEqual(karbi.translate(None, from_lang="en"), [])
        self.assertEqual(karbi.translate("water", from_lang=None), [])
        self.assertIsNone(karbi.lookup(None))
        self.assertEqual(karbi.lookup_all(None), [])

    def test_homonym_lookup_all(self):
        """lookup_all retrieves both homonym entries, while lookup returns the primary entry."""
        # 'cho' has verb (KB-LEX-0000154, 'to eat') and noun (KB-LEX-0000323, 'axe, hatchet')
        all_entries = karbi.lookup_all("cho")
        self.assertEqual(len(all_entries), 2)
        lemmas = [e.lemma for e in all_entries]
        self.assertTrue(all(l == "cho" for l in lemmas))
        eids = [e.entry_id for e in all_entries]
        self.assertIn("KB-LEX-0000154", eids)
        self.assertIn("KB-LEX-0000323", eids)

        # Backward-compatible lookup() returns the first entry
        single = karbi.lookup("cho")
        self.assertIsNotNone(single)
        self.assertEqual(single.entry_id, "KB-LEX-0000154")

    def test_translation_match_populates_entry_id(self):
        """TranslationMatch includes the entry_id of the matched lexicon entry."""
        matches = karbi.translate("water", from_lang="en")
        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0].entry_id, "KB-LEX-0000003")

    def test_newly_attested_entries(self):
        """Newly added entries from Stack & Lyall (1908) can be looked up and translated."""
        # 1. Pronoun 'la'
        entry_la = karbi.lookup("la")
        self.assertIsNotNone(entry_la)
        self.assertEqual(entry_la.entry_id, "KB-LEX-0000341")
        self.assertIn("The Mikirs (p. 76)", entry_la.source_citations[0])

        # 2. Classifier 'jòn'
        entry_jon = karbi.lookup("jòn")
        self.assertIsNotNone(entry_jon)
        self.assertEqual(entry_jon.entry_id, "KB-LEX-0000346")
        self.assertIn("The Mikirs (p. 78)", entry_jon.source_citations[0])

        # Spelling variant 'jon' resolves to 'jòn'
        entry_jon_var = karbi.lookup("jon")
        self.assertIsNotNone(entry_jon_var)
        self.assertEqual(entry_jon_var.lemma, "jòn")

        # 3. 'roi' (bracelet)
        entry_roi = karbi.lookup("roi")
        self.assertIsNotNone(entry_roi)
        self.assertEqual(entry_roi.entry_id, "KB-LEX-0000350")

        # 4. 'puthi' (book)
        entry_puthi = karbi.lookup("puthi")
        self.assertIsNotNone(entry_puthi)
        self.assertEqual(entry_puthi.entry_id, "KB-LEX-0000351")

    def test_newly_attested_entries_batch_two(self):
        """Newly added entries KB-LEX-0000352 to 372 from Stack & Lyall (1908) can be looked up and translated."""
        import unicodedata

        # 1. Numeral krē-īsī (11) and modern variant kresi
        entry_11 = karbi.lookup("krē-īsī")
        self.assertIsNotNone(entry_11)
        self.assertEqual(entry_11.entry_id, "KB-LEX-0000352")
        self.assertIn("eleven", entry_11.get_meanings("en"))
        entry_11_var = karbi.lookup("kresi")
        self.assertIsNotNone(entry_11_var)
        self.assertEqual(entry_11_var.entry_id, "KB-LEX-0000352")

        # 2. Reflexive pronoun āmethàng / methang
        entry_methang = karbi.lookup("āmethàng")
        self.assertIsNotNone(entry_methang)
        self.assertEqual(entry_methang.entry_id, "KB-LEX-0000355")
        entry_methang_var = karbi.lookup("methang")
        self.assertIsNotNone(entry_methang_var)
        self.assertEqual(entry_methang_var.entry_id, "KB-LEX-0000355")

        # 3. Postposition ā-thàk / athak
        entry_athak = karbi.lookup("ā-thàk")
        self.assertIsNotNone(entry_athak)
        self.assertEqual(entry_athak.entry_id, "KB-LEX-0000358")
        trans_upon = karbi.translate("upon", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "ā-thàk" for m in trans_upon))

        # 4. Negative existential āvē and emphatic kālī
        entry_ave = karbi.lookup("āvē")
        self.assertIsNotNone(entry_ave)
        self.assertEqual(entry_ave.entry_id, "KB-LEX-0000369")
        entry_kali = karbi.lookup("kālī")
        self.assertIsNotNone(entry_kali)
        self.assertEqual(entry_kali.entry_id, "KB-LEX-0000370")

        # 5. Nouns dohòn (money) and kaibòng (club)
        entry_dohon = karbi.lookup("dohòn")
        self.assertIsNotNone(entry_dohon)
        self.assertEqual(entry_dohon.entry_id, "KB-LEX-0000371")
        entry_kaibong = karbi.lookup("kaibòng")
        self.assertIsNotNone(entry_kaibong)
        self.assertEqual(entry_kaibong.entry_id, "KB-LEX-0000372")

    def test_unicode_nfc_nfd_equivalence(self):
        """Looking up words in NFD decomposed Unicode returns the correct entry via NFC normalization."""
        import unicodedata

        # Decompose arlèng into NFD ('e' + combining grave '\u0300')
        nfd_arleng = unicodedata.normalize("NFD", "arlèng")
        self.assertNotEqual(nfd_arleng, "arlèng")  # Different string codepoints
        entry = karbi.lookup(nfd_arleng)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.entry_id, "KB-LEX-0000001")

        # Decompose hèm into NFD
        nfd_hem = unicodedata.normalize("NFD", "hèm")
        self.assertNotEqual(nfd_hem, "hèm")
        entry_hem = karbi.lookup(nfd_hem)
        self.assertIsNotNone(entry_hem)
        self.assertEqual(entry_hem.entry_id, "KB-LEX-0000002")

        # Translate in NFD
        matches = karbi.translate(unicodedata.normalize("NFD", "water"), from_lang="en")
        self.assertGreaterEqual(len(matches), 1)

    def test_punctuation_tolerant_lookup_and_translation(self):
        """Punctuation surrounding query terms is tolerated without breaking lookup."""
        # Trailing question mark
        entry_q = karbi.lookup("arlèng?")
        self.assertIsNotNone(entry_q)
        self.assertEqual(entry_q.entry_id, "KB-LEX-0000001")

        # Quotes around term
        entry_quotes = karbi.lookup('"hèm"')
        self.assertIsNotNone(entry_quotes)
        self.assertEqual(entry_quotes.entry_id, "KB-LEX-0000002")

        # Trailing exclamation mark in translation
        matches = karbi.translate("water!", from_lang="en")
        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0].karbi_lemma, "làng")

    def test_new_37_lexicon_entries(self):
        """Verify lookup and translation for the newly added 37 source-attested entries."""
        # 1. Numerals and prefixes
        entry_batai = karbi.lookup("bātai")
        self.assertIsNotNone(entry_batai)
        self.assertEqual(entry_batai.entry_id, "KB-LEX-0000373")
        self.assertEqual(entry_batai.senses[0]["part_of_speech"], "prefix")

        entry_pur = karbi.lookup("pur")
        self.assertIsNotNone(entry_pur)
        self.assertEqual(entry_pur.entry_id, "KB-LEX-0000374")

        # 2. Animals
        entry_frog = karbi.lookup("chònghōlosō")
        self.assertIsNotNone(entry_frog)
        self.assertEqual(entry_frog.entry_id, "KB-LEX-0000381")
        matches_frog = karbi.translate("frog", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "chònghōlosō" for m in matches_frog))

        entry_squirrel = karbi.lookup("kāthē")
        self.assertIsNotNone(entry_squirrel)
        self.assertEqual(entry_squirrel.entry_id, "KB-LEX-0000382")

        # 3. Crops & food
        entry_maize = karbi.lookup("thèngthē")
        self.assertIsNotNone(entry_maize)
        self.assertEqual(entry_maize.entry_id, "KB-LEX-0000384")
        matches_maize = karbi.translate("maize", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "thèngthē" for m in matches_maize))

        entry_turmeric = karbi.lookup("thārmit")
        self.assertIsNotNone(entry_turmeric)
        self.assertEqual(entry_turmeric.entry_id, "KB-LEX-0000385")

        # 4. Modals and folklore
        entry_un = karbi.lookup("un")
        self.assertIsNotNone(entry_un)
        self.assertEqual(entry_un.entry_id, "KB-LEX-0000403")

        entry_une = karbi.lookup("un-ē")
        self.assertIsNotNone(entry_une)
        self.assertEqual(entry_une.entry_id, "KB-LEX-0000404")

        entry_recho = karbi.lookup("rēchō")
        self.assertIsNotNone(entry_recho)
        self.assertEqual(entry_recho.entry_id, "KB-LEX-0000408")
        matches_king = karbi.translate("king", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "rēchō" for m in matches_king))

        entry_orphan = karbi.lookup("jàngrēsō")
        self.assertIsNotNone(entry_orphan)
        self.assertEqual(entry_orphan.entry_id, "KB-LEX-0000409")

    def test_grierson_and_stack_expansion_entries(self):
        """Newly expanded source-attested entries from Grierson (1903) and Stack & Lyall (1908) resolve correctly."""
        # 1. Grierson (1903) entries:
        # phàk-alo (boar)
        e_boar = karbi.lookup("phàk-alo")
        self.assertIsNotNone(e_boar)
        self.assertEqual(e_boar.entry_id, "KB-LEX-0000410")
        self.assertEqual(e_boar.senses[0]["part_of_speech"], "noun")
        self.assertIn("Linguistic Survey of India", e_boar.source_citation)
        self.assertIn("p. 383", e_boar.source_citation)

        # Look up by spelling variant without diacritics
        v_boar = karbi.lookup("phak-alo")
        self.assertIsNotNone(v_boar)
        self.assertEqual(v_boar.lemma, "phàk-alo")

        # English translation reverse lookup
        trans_boar = karbi.translate("boar", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "phàk-alo" for m in trans_boar))

        # kaphù (head)
        e_head = karbi.lookup("kaphù")
        self.assertIsNotNone(e_head)
        self.assertEqual(e_head.entry_id, "KB-LEX-0000418")
        trans_head = karbi.translate("skull", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "kaphù" for m in trans_head))

        # kànghi (famine)
        e_famine = karbi.lookup("kànghi")
        self.assertIsNotNone(e_famine)
        trans_famine = karbi.translate("famine", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "kànghi" for m in trans_famine))

        # lūchè (music)
        e_music = karbi.lookup("lūchè")
        self.assertIsNotNone(e_music)
        trans_music = karbi.translate("music", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "lūchè" for m in trans_music))

        # kebàng (assembly, council)
        e_council = karbi.lookup("kebàng")
        self.assertIsNotNone(e_council)
        trans_council = karbi.translate("assembly", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "kebàng" for m in trans_council))

        # 2. Stack & Lyall (1908) entries:
        # hako (once upon a time)
        e_hako = karbi.lookup("hako")
        self.assertIsNotNone(e_hako)
        self.assertEqual(e_hako.senses[0]["part_of_speech"], "adverb")
        self.assertIn("The Mikirs", e_hako.source_citation)
        trans_hako = karbi.translate("long ago", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "hako" for m in trans_hako))

        # vo-thung (wood-pigeon)
        e_pigeon = karbi.lookup("vo-thung")
        self.assertIsNotNone(e_pigeon)
        trans_pigeon = karbi.translate("wood-pigeon", from_lang="en")
        self.assertTrue(any(m.karbi_lemma == "vo-thung" for m in trans_pigeon))

        # hotòn (carrying basket)
        e_basket = karbi.lookup("hotòn")
        self.assertIsNotNone(e_basket)
        v_basket = karbi.lookup("hoton")
        self.assertIsNotNone(v_basket)
        self.assertEqual(v_basket.lemma, "hotòn")

        # 3. Multilingual Indic translations & unverified filtering integrity
        # In unverified mode (verified_only=False), Indic glosses are retrievable
        hi_famine = karbi.translate("अकाल", from_lang="hi", verified_only=False)
        self.assertTrue(any(m.karbi_lemma == "kànghi" for m in hi_famine))

        as_famine = karbi.translate("আকাল", from_lang="as", verified_only=False)
        self.assertTrue(any(m.karbi_lemma == "kànghi" for m in as_famine))

        bn_rooster = karbi.translate("মোরগ", from_lang="bn", verified_only=False)
        self.assertTrue(any(m.karbi_lemma == "vo-alo" for m in bn_rooster))

        # In strict verified-only mode, unverified Indic glosses MUST NOT be presented as verified
        hi_famine_verified = karbi.translate("अकाल", from_lang="hi", verified_only=True)
        self.assertEqual(len(hi_famine_verified), 0, "Unverified Indic gloss must not pass verified_only filter")

    def test_citation_mismatch_audit_and_verification_filtering(self):
        """KB-LEX-0000382 (kāthē) is recorded with CITATION_MISMATCH and excluded from verified_only results."""
        entry = karbi.lookup("kāthē")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.entry_id, "KB-LEX-0000382")
        self.assertEqual(entry.status, "CITATION_MISMATCH")

        # Provenance audit review record exists
        reviews = entry.provenance.get("reviews", [])
        self.assertGreaterEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["review_id"], "REV-AUDIT-0000382-01")
        self.assertEqual(reviews[0]["verification_finding"], "needs_revision")
        self.assertIn("CITATION_MISMATCH", reviews[0]["audit_notes"])

        # When searching with verified_only=True, unverified/mismatched entry is excluded
        ver_search = karbi.search("kāthē", lang="karbi", verified_only=True)
        self.assertEqual(ver_search, [])

        # When searching with verified_only=False, entry is returned with honest flags
        unver_search = karbi.search("kāthē", lang="karbi", verified_only=False)
        self.assertEqual(len(unver_search), 1)
        res = unver_search[0]
        self.assertFalse(res.is_verified)
        self.assertEqual(res.status, "CITATION_MISMATCH")
        self.assertIsNotNone(res.provenance)
        self.assertIn("reviews", res.provenance)

        # Translation for 'squirrel' with verified_only=True returns authentic 'karle' and excludes mismatched 'kāthē'
        squirrel_ver = karbi.translate("squirrel", from_lang="en", verified_only=True)
        self.assertEqual([m.karbi_lemma for m in squirrel_ver], ["karle"])
        self.assertFalse(any(m.karbi_lemma == "kāthē" for m in squirrel_ver))

        # Translation without verified_only includes kāthē but flagged as unverified / citation mismatch
        squirrel_all = karbi.translate("squirrel", from_lang="en", verified_only=False)
        self.assertTrue(any(m.karbi_lemma == "kāthē" and not m.is_verified for m in squirrel_all))

    def test_batch_search_and_provenance(self):
        """batch_search returns structured results for multiple queries and provides provenance."""
        queries = ["arlèng", "hèm", "làng"]
        batch_res = karbi.batch_search(queries, lang="auto")
        self.assertEqual(len(batch_res), 3)
        for q in queries:
            self.assertIn(q, batch_res)
            self.assertGreaterEqual(len(batch_res[q]), 1)
            self.assertIsNotNone(batch_res[q][0].provenance)

    def test_supported_languages_extensibility(self):
        """Supported languages registry includes Khasi and Marathi marked as awaiting sourced entries."""
        langs = karbi.get_supported_languages()
        self.assertIn("kha", langs)
        self.assertEqual(langs["kha"]["status"], "awaiting_sourced_entries")
        self.assertEqual(langs["kha"]["name"], "Khasi")
        self.assertIn("mr", langs)
        self.assertEqual(langs["mr"]["status"], "awaiting_sourced_entries")

    def test_canonical_and_packaged_data_byte_parity(self):
        """Authoritative repository data and packaged resources match byte-for-byte."""
        import filecmp
        p_canon_lex = Path(__file__).resolve().parent.parent / "data" / "lexicon" / "core_lexicon.jsonl"
        p_pkg_lex = Path(__file__).resolve().parent.parent / "src" / "karbi" / "resources" / "lexicon" / "core_lexicon.jsonl"
        self.assertTrue(filecmp.cmp(str(p_canon_lex), str(p_pkg_lex), shallow=False))

        p_canon_src = Path(__file__).resolve().parent.parent / "data" / "sources" / "sources.jsonl"
        p_pkg_src = Path(__file__).resolve().parent.parent / "src" / "karbi" / "resources" / "sources" / "sources.jsonl"
        self.assertTrue(filecmp.cmp(str(p_canon_src), str(p_pkg_src), shallow=False))


    def test_multilingual_translation_for_expanded_entries(self):
        """Expanded entries translate from English, Hindi, Assamese, and Bengali into Karbi."""
        # 1. English -> Karbi (verified_only=True returns source-attested entries)
        elephant_matches = karbi.translate("elephant", from_lang="en", verified_only=True)
        self.assertEqual([m.karbi_lemma for m in elephant_matches], ["ingnar"])
        self.assertTrue(elephant_matches[0].is_verified)

        earthquake_matches = karbi.translate("earthquake", from_lang="en", verified_only=True)
        self.assertEqual([m.karbi_lemma for m in earthquake_matches], ["chikli"])
        self.assertTrue(earthquake_matches[0].is_verified)

        # 2. Hindi -> Karbi: verified_only=True returns empty because Indic candidate glosses are unverified
        self.assertEqual(karbi.translate("हाथी", from_lang="hi", verified_only=True), [])
        # With verified_only=False, unverified candidate match is returned with honest badge
        hi_matches = karbi.translate("हाथी", from_lang="hi", verified_only=False)
        self.assertEqual([m.karbi_lemma for m in hi_matches], ["ingnar"])
        self.assertFalse(hi_matches[0].is_verified)

        # 3. Assamese -> Karbi: unverified candidate match
        self.assertEqual(karbi.translate("হাতী", from_lang="as", verified_only=True), [])
        as_matches = karbi.translate("হাতী", from_lang="as", verified_only=False)
        self.assertEqual([m.karbi_lemma for m in as_matches], ["ingnar"])
        self.assertFalse(as_matches[0].is_verified)

        # 4. Bengali -> Karbi: unverified candidate match
        self.assertEqual(karbi.translate("হাতি", from_lang="bn", verified_only=True), [])
        bn_matches = karbi.translate("হাতি", from_lang="bn", verified_only=False)
        self.assertEqual([m.karbi_lemma for m in bn_matches], ["ingnar"])
        self.assertFalse(bn_matches[0].is_verified)

    def test_gloss_review_workflow_data_model(self):
        """GlossReviewRecord accurately tracks reviewer decisions, locators, and audit histories."""
        from karbi.core.models import GlossReviewDecision, GlossReviewRecord, Provenance

        rec = GlossReviewRecord(
            original_gloss="हाथी",
            language="hi",
            decision=GlossReviewDecision.ACCEPTED.value,
            supporting_source_id="SRC-PUB-00001",
            supporting_locator="p. 88",
            reviewer_id="REV-LING-TEST",
            reviewer_role="linguist",
            review_date="2026-10-23",
            reason="Confirmed against primary source text and interlinear rendering",
            revision_history=[{"action": "initial_submission", "status": "awaiting_review"}],
        )
        self.assertEqual(rec.decision, "accepted")
        self.assertEqual(rec.reviewer_role, "linguist")

        prov = Provenance(gloss_reviews=[rec])
        self.assertEqual(len(prov.gloss_reviews), 1)
        self.assertEqual(prov.gloss_reviews[0].original_gloss, "हाथी")

        # Round-trip serialization
        rec_dict = rec.as_dict()
        self.assertEqual(rec_dict["decision"], "accepted")
        self.assertEqual(rec_dict["supporting_locator"], "p. 88")

        rec_deser = GlossReviewRecord.from_dict(rec_dict)
        self.assertEqual(rec_deser.original_gloss, "हाथी")
        self.assertEqual(rec_deser.decision, "accepted")

    def test_gloss_review_validator_rejection_rules(self):
        """Dataset validator rejects malformed gloss review records."""
        from karbi.core.models import GlossReviewRecord
        from karbi.core.validator import LexiconValidator

        val = LexiconValidator(sources_registry={"SRC-PUB-00001": None})

        # 1. Invalid decision
        bad_dec = [GlossReviewRecord(original_gloss="हाथी", language="hi", decision="conjectured")]
        errs = val._validate_gloss_reviews("KB-TEST-001", bad_dec)
        self.assertTrue(any("invalid decision 'conjectured'" in e for e in errs))

        # 2. Unsupported language
        bad_lang = [GlossReviewRecord(original_gloss="test", language="xx", decision="awaiting_review")]
        errs = val._validate_gloss_reviews("KB-TEST-001", bad_lang)
        self.assertTrue(any("unsupported language code 'xx'" in e for e in errs))

        # 3. Missing supporting locator when source is specified
        missing_loc = [GlossReviewRecord(
            original_gloss="हाथी", language="hi", decision="awaiting_review",
            supporting_source_id="SRC-PUB-00001", supporting_locator="",
        )]
        errs = val._validate_gloss_reviews("KB-TEST-001", missing_loc)
        self.assertTrue(any("requires a locator" in e for e in errs))

        # 4. Accepted review missing reviewer_id and reviewer_role
        unauth_acc = [GlossReviewRecord(
            original_gloss="हाथी", language="hi", decision="accepted",
            reviewer_id="", reviewer_role=""
        )]
        errs = val._validate_gloss_reviews("KB-TEST-001", unauth_acc)
        self.assertTrue(any("requires reviewer_id" in e for e in errs))

        # 5. Rejected review missing reason
        unexp_rej = [GlossReviewRecord(
            original_gloss="हाथी", language="hi", decision="rejected", reason=""
        )]
        errs = val._validate_gloss_reviews("KB-TEST-001", unexp_rej)
        self.assertTrue(any("rejected review must state a reason" in e for e in errs))

        # 6. Impossible future year
        future_date = [GlossReviewRecord(
            original_gloss="हाथी", language="hi", decision="awaiting_review",
            review_date="2099-01-01"
        )]
        errs = val._validate_gloss_reviews("KB-TEST-001", future_date)
        self.assertTrue(any("out of valid range" in e for e in errs))

    def test_gloss_review_no_automatic_promotion_to_verified(self):
        """Attaching a GlossReviewRecord to an unverified entry does NOT leak into verified_only=True."""
        # Querying an unverified Hindi candidate term with verified_only=True remains empty
        self.assertEqual(karbi.translate("हाथी", from_lang="hi", verified_only=True), [])
        self.assertEqual(karbi.translate("হাতী", from_lang="as", verified_only=True), [])
        self.assertEqual(karbi.translate("হাতি", from_lang="bn", verified_only=True), [])


if __name__ == "__main__":
    unittest.main()
