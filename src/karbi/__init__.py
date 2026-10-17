"""
Karbi Language Python Library (`karbi`)
=======================================

A comprehensive Python library for Multilingual-to-Karbi translation,
lexicography, grammar, phonetics, and documented cultural heritage.

Primary Translation Direction:
    English  (en) -> Karbi
    Hindi    (hi) -> Karbi
    Assamese (as) -> Karbi
    Bengali  (bn) -> Karbi
"""

from karbi.alphabet import (
    get_aspirates,
    get_consonants,
    get_diphthongs,
    get_phonology_summary,
    get_vowels,
)
from karbi.culture import (
    get_cultural_ethics_policy,
    get_deities,
    get_rituals,
)
from karbi.dictionary import DictionaryEntry, lookup
from karbi.grammar import (
    count_with_classifier,
    get_cardinals,
    get_classifiers,
    get_pronouns,
)
from karbi.translator import (
    TranslationMatch,
    get_supported_languages,
    translate,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Multilingual-to-Karbi Translation
    "translate",
    "get_supported_languages",
    "TranslationMatch",
    # Karbi Dictionary
    "lookup",
    "DictionaryEntry",
    # Alphabet and Phonetics
    "get_vowels",
    "get_consonants",
    "get_aspirates",
    "get_diphthongs",
    "get_phonology_summary",
    # Grammar and Classifiers
    "get_classifiers",
    "get_pronouns",
    "get_cardinals",
    "count_with_classifier",
    # Cultural Heritage
    "get_rituals",
    "get_deities",
    "get_cultural_ethics_policy",
]
