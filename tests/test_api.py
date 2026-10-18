"""
Tests for High-Level Public Python API (`karbi.api` and `karbi` top-level exports).
==================================================================================
"""

import json
import pytest
import karbi
from karbi import SearchResult, batch_lookup, batch_search, batch_translate, search


class TestPublicPythonAPI:
    """Tests covering searching, multilingual lookups, batch operations, and verification filtering."""

    def test_search_karbi_headword(self):
        """Search Karbi headword returns structured SearchResult with IPA and citations."""
        results = search("arlèng", lang="karbi")
        assert len(results) == 1
        res = results[0]

        assert isinstance(res, SearchResult)
        assert res.query == "arlèng"
        assert res.query_type == "karbi_headword"
        assert res.karbi_lemma == "arlèng"
        assert res.phonetics_ipa == "/aɾˈlɛŋ/"
        assert res.is_verified is True
        assert res.status == "SOURCE_ATTESTED"
        assert len(res.source_citations) > 0
        assert "The Mikirs (p. 74, 80)" in res.source_citations[0]
        assert "man" in res.get_meanings("en")
        assert "person" in res.get_meanings("en")
        assert res.raw_entry is not None

    def test_search_spelling_variant(self):
        """Searching a contemporary spelling variant resolves to canonical headword."""
        results = search("hem", lang="karbi")
        assert len(results) == 1
        res = results[0]

        assert res.karbi_lemma == "hèm"
        assert res.query_type == "spelling_variant"
        assert res.phonetics_ipa == "/hɛm/"
        assert "hem" in res.spelling_variants
        assert "The Mikirs (p. 77, 79)" in res.source_citations[0]
        assert "house" in res.get_meanings("en")

    def test_multilingual_lookup_all_supported_languages(self):
        """Translating from English, Hindi, Assamese, and Bengali returns structured results."""
        # English
        res_en = search("water", lang="en")
        assert len(res_en) >= 1
        assert res_en[0].karbi_lemma == "làng"
        assert res_en[0].phonetics_ipa == "/laŋ/"
        assert res_en[0].matched_language == "en"

        # Hindi
        res_hi = search("पानी", lang="hi")
        assert len(res_hi) >= 1
        assert res_hi[0].karbi_lemma == "làng"
        assert res_hi[0].matched_language == "hi"

        # Assamese
        res_as = search("পানী", lang="as")
        assert len(res_as) >= 1
        assert res_as[0].karbi_lemma == "làng"
        assert res_as[0].matched_language == "as"

        # Bengali
        res_bn = search("জল", lang="bn")
        assert len(res_bn) >= 1
        assert res_bn[0].karbi_lemma == "làng"
        assert res_bn[0].matched_language == "bn"

    def test_auto_detection_search(self):
        """Auto language search finds both Karbi words, variants, and translations."""
        # Karbi headword
        res_k = search("arlèng", lang="auto")
        assert len(res_k) >= 1
        assert res_k[0].karbi_lemma == "arlèng"

        # Karbi variant
        res_v = search("hem", lang="auto")
        assert len(res_v) >= 1
        assert res_v[0].karbi_lemma == "hèm"

        # English translation
        res_e = search("water", lang="auto")
        assert len(res_e) >= 1
        assert res_e[0].karbi_lemma == "làng"

    def test_unverified_translation_filtering(self):
        """Unverified translation glosses are flagged and excluded when verified_only=True."""
        # Unverified Hindi gloss 'पानी'
        res_unfiltered = search("पानी", lang="hi", verified_only=False)
        assert len(res_unfiltered) >= 1
        assert res_unfiltered[0].is_verified is False
        assert res_unfiltered[0].status == "unverified"

        # Filtered
        res_filtered = search("पानी", lang="hi", verified_only=True)
        assert len(res_filtered) == 0

        # DictionaryEntry get_meanings verification filter
        entry = karbi.lookup("arlèng")
        assert entry is not None
        # English is source-attested
        assert len(entry.get_meanings("en", verified_only=True)) > 0
        # Hindi is unverified in core_lexicon
        assert len(entry.get_meanings("hi", verified_only=False)) > 0
        assert len(entry.get_meanings("hi", verified_only=True)) == 0

    def test_missing_word_handling(self):
        """Searching missing or empty words returns empty collections gracefully."""
        assert search("nonexistentword123", lang="karbi") == []
        assert search("nonexistentword123", lang="en") == []
        assert search("nonexistentword123", lang="auto") == []
        assert search("") == []
        assert search("    ") == []

        assert karbi.lookup("nonexistentword123") is None

    def test_batch_lookup(self):
        """batch_lookup retrieves multiple Karbi headwords and variants in a single call."""
        words = ["arlèng", "hem", "làng", "unknown_missing_xyz"]
        results = batch_lookup(words)

        assert isinstance(results, dict)
        assert len(results) == 4
        assert results["arlèng"] is not None
        assert results["arlèng"].lemma == "arlèng"
        assert results["hem"] is not None
        assert results["hem"].lemma == "hèm"
        assert results["làng"] is not None
        assert results["làng"].lemma == "làng"
        assert results["unknown_missing_xyz"] is None

    def test_batch_translate(self):
        """batch_translate translates multiple concepts with language and verification controls."""
        queries = ["water", "house", "missing_concept"]
        results = batch_translate(queries, from_lang="en")

        assert isinstance(results, dict)
        assert len(results) == 3
        assert len(results["water"]) >= 1
        assert results["water"][0].karbi_lemma == "làng"
        assert len(results["house"]) >= 1
        assert results["house"][0].karbi_lemma == "hèm"
        assert results["missing_concept"] == []

    def test_batch_translate_verified_only(self):
        """batch_translate with verified_only=True filters unverified matches across batch."""
        # Hindi queries where glosses are unverified
        results = batch_translate(["पानी", "घर"], from_lang="hi", verified_only=True)
        assert results["पानी"] == []
        assert results["घर"] == []

        # Without verified_only, unverified matches are returned
        results_all = batch_translate(["पानी", "घर"], from_lang="hi", verified_only=False)
        assert len(results_all["पानी"]) >= 1
        assert results_all["पानी"][0].is_verified is False

    def test_batch_search(self):
        """batch_search performs unified multi-word search."""
        queries = ["water", "arlèng", "hem", "missing_word"]
        results = batch_search(queries)

        assert isinstance(results, dict)
        assert len(results) == 4
        assert len(results["water"]) >= 1
        assert results["water"][0].karbi_lemma == "làng"
        assert len(results["arlèng"]) >= 1
        assert results["arlèng"][0].karbi_lemma == "arlèng"
        assert len(results["hem"]) >= 1
        assert results["hem"][0].karbi_lemma == "hèm"
        assert results["missing_word"] == []

    def test_search_result_serialization(self):
        """SearchResult serializes cleanly into dictionary and JSON."""
        res = search("arlèng")[0]
        d = res.as_dict()

        assert d["karbi_lemma"] == "arlèng"
        assert d["is_verified"] is True
        assert d["status"] == "SOURCE_ATTESTED"
        assert d["phonetics_ipa"] == "/aɾˈlɛŋ/"
        assert isinstance(d["meanings"], dict)
        assert isinstance(d["source_citations"], list)

        # Confirm JSON serialization succeeds
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["karbi_lemma"] == "arlèng"
