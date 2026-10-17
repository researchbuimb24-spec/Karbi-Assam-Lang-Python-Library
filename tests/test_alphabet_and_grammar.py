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
        """Classifier expressions correctly follow documented linguistic rules."""
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

    def test_cardinals_and_pronouns(self):
        """Cardinals and pronouns match historical documentation."""
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

    def test_cultural_records(self):
        """Cultural records contain exact citations and sensitivity markers."""
        rituals = karbi.get_rituals()
        self.assertGreaterEqual(len(rituals), 2)
        rongker = next(r for r in rituals if r["name"] == "Rongker")
        self.assertIn("The Mikirs", rongker["source_citation"])

        chomangkan = next(r for r in rituals if "Chomangkan" in r["name"])
        self.assertEqual(chomangkan["sensitivity"], "culturally_sensitive_sacred_mortuary")

        deities = karbi.get_deities()
        self.assertGreaterEqual(len(deities), 3)
        hemphu = next(d for d in deities if d["name"] == "Hemphu")
        self.assertEqual(hemphu["title"], "Household and Clan Guardian Deity")


if __name__ == "__main__":
    unittest.main()
