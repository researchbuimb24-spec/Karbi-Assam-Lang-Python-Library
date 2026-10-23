"""
Automated Unit Tests for Karbi Alphabet, Grammar, and Culture
=============================================================

Tests:
- Alphabet, vowels, consonants, aspirates.
- Numerical classifier composition.
- Cardinal numbers and personal pronouns.
- Cultural record citations and sensitivity markers.
"""

import sys
import unittest
from pathlib import Path

# Add src to sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import karbi


class TestAlphabetAndGrammar(unittest.TestCase):
    """Test suite covering phonetics, grammar rules, and cultural records."""

    def test_vowels_and_consonants(self):
        """Phonological inventory returns authentic documented characters."""
        vowels = karbi.get_vowels()
        self.assertIn("a", vowels)
        self.assertIn("à", vowels)
        self.assertIn("è", vowels)

        consonants = karbi.get_consonants()
        self.assertIn("b", consonants)
        self.assertIn("ng", consonants)
        self.assertNotIn("f", consonants)  # Traditionally absent

        aspirates = karbi.get_aspirates()
        self.assertIn("kh", aspirates)
        self.assertIn("ph", aspirates)
        self.assertIn("th", aspirates)

    def test_numerical_classifiers(self):
        """Classifier expressions correctly follow documented linguistic rules for all 7 documented forms."""
        classifiers = karbi.get_classifiers()
        expected_classifiers = {"bang": "bàng", "jon": "jòn", "rong": "ròng", "hum": "hum", "pak": "pàk", "pum": "pum", "hong": "hòng"}
        for key, expected_form in expected_classifiers.items():
            self.assertIn(key, classifiers)
            self.assertEqual(classifiers[key]["classifier"], expected_form)

        # 4 buffaloes -> jòn-phili
        self.assertEqual(karbi.count_with_classifier(4, "animals"), "jòn-phili")

        # 6 trees -> ròng-theròk
        self.assertEqual(karbi.count_with_classifier(6, "trees"), "ròng-theròk")

        # 10 houses -> hum-kèp
        self.assertEqual(karbi.count_with_classifier(10, "houses"), "hum-kèp")

        # 1 person -> inut (special rule)
        self.assertEqual(karbi.count_with_classifier(1, "persons"), "inut")

        # 1 tree -> e-ròng
        self.assertEqual(karbi.count_with_classifier(1, "trees"), "e-ròng")

        # 2 eggs -> pum-ni (round objects)
        self.assertEqual(karbi.count_with_classifier(2, "round"), "pum-ni")

        # 1 book/flat item -> e-pàk
        self.assertEqual(karbi.count_with_classifier(1, "flat"), "e-pàk")

        # 2 bracelets/limbs -> hòng-ni
        self.assertEqual(karbi.count_with_classifier(2, "ornaments"), "hòng-ni")

        # None and out of range edge cases
        self.assertIsNone(karbi.count_with_classifier(None, "animals"))
        self.assertIsNone(karbi.count_with_classifier(1, None))
        self.assertIsNone(karbi.count_with_classifier(0, "animals"))
        self.assertIsNone(karbi.count_with_classifier(11, "animals"))
        self.assertIsNone(karbi.count_with_classifier(1, "unknown_category_xyz"))

    def test_cardinals_and_pronouns(self):
        """Cardinals and pronouns match historical documentation, preserving inclusive/exclusive distinction."""
        cardinals = karbi.get_cardinals()
        self.assertEqual(cardinals[1], "isi")
        self.assertEqual(cardinals[2], "hini")
        self.assertEqual(cardinals[7], "theròk-si")  # 6 + 1
        self.assertEqual(cardinals[8], "nerkèp")      # 10 - 2
        self.assertEqual(cardinals[10], "kèp")

        pronouns = karbi.get_pronouns()
        self.assertEqual(pronouns["first_person_singular"]["karbi"], "ne")
        self.assertEqual(pronouns["second_person_singular"]["karbi"], "nàng")
        self.assertEqual(pronouns["third_person_singular"]["karbi"], "la")

        # Preserved inclusive vs exclusive grammatical distinction
        self.assertEqual(pronouns["first_person_plural_exclusive"]["karbi"], "ne-tum")
        self.assertEqual(pronouns["first_person_plural_inclusive"]["karbi"], "i-tum")
        self.assertEqual(pronouns["second_person_plural"]["karbi"], "nàng-tum")
        self.assertEqual(pronouns["third_person_plural"]["karbi"], "la-tum")

    def test_cultural_records(self):
        """Cultural records contain exact citations, sensitivity markers, and caution on unverified sources."""
        rituals = karbi.get_rituals()
        self.assertGreaterEqual(len(rituals), 2)
        rongker = next(r for r in rituals if r["name"] == "Rongker")
        self.assertIn("The Mikirs", rongker["source_citation"])

        chomangkan = next(r for r in rituals if "Chomangkan" in r["name"])
        self.assertEqual(chomangkan["sensitivity"], "culturally_sensitive_sacred_mortuary")

        deities = karbi.get_deities()
        self.assertGreaterEqual(len(deities), 3)
        deity_names = {d["name"] for d in deities}
        self.assertIn("Hemphu", deity_names)
        self.assertIn("Mukrang", deity_names)
        self.assertIn("Rasinja", deity_names)

        hemphu = next(d for d in deities if d["name"] == "Hemphu")
        self.assertEqual(hemphu["title"], "Household and Clan Guardian Deity")

        mukrang = next(d for d in deities if d["name"] == "Mukrang")
        self.assertEqual(mukrang["title"], "Guardian Deity")

        # Rasinja is preserved with explicit caution pending authoritative elder/ethnographic review
        rasinja = next(d for d in deities if d["name"] == "Rasinja")
        self.assertEqual(rasinja["title"], "Female Guardian Deity")
        self.assertIn("Awaiting formal citation", rasinja["source_citation"])

    def test_alphabet_type_hints(self):
        """Type annotations in alphabet module evaluate without NameError."""
        import typing
        hints = typing.get_type_hints(karbi.alphabet.get_phonology_summary)
        self.assertIn("return", hints)


if __name__ == "__main__":
    unittest.main()
