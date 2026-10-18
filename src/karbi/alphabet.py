"""
Karbi Alphabet, Phonetics & Writing System (`karbi.alphabet`)
=============================================================

Documentation and programmatic utilities for the Karbi writing system
and phonological inventory, based on standardized conventions and
linguistic documentation from Lyall & Stack (1908) and Grierson (1903).
"""

from typing import Any, Dict, List

VOWELS = {
    "a": {"name": "long a", "example": "father", "ipa": "/aː/"},
    "à": {"name": "short abrupt a", "example": "Mann (German)", "ipa": "/a/"},
    "e": {"name": "long e", "example": "scène (French)", "ipa": "/eː/"},
    "è": {"name": "sharp short e", "example": "men", "ipa": "/ɛ/"},
    "i": {"name": "long i", "example": "machine", "ipa": "/iː/"},
    "o": {"name": "long o", "example": "bone", "ipa": "/oː/"},
    "ò": {"name": "abrupt o", "example": "pot", "ipa": "/ɔ/"},
    "u": {"name": "long u", "example": "June", "ipa": "/uː/"},
}

DIPHTHONGS = {
    "ai": {"example": "aisle", "ipa": "/aɪ/"},
    "ei": {"example": "feign", "ipa": "/eɪ/"},
    "oi": {"example": "boil", "ipa": "/ɔɪ/"},
    "ui": {"example": "u + i", "ipa": "/uɪ/"},
}

CONSONANTS = ["b", "ch", "d", "h", "j", "k", "l", "m", "n", "ng", "p", "r", "s", "t", "v"]
ASPIRATES = ["kh", "ph", "th"]
RARE_LOAN_CONSONANTS = ["bh", "dh", "g"]
TRADITIONALLY_ABSENT = ["f", "sh", "w", "y", "z"]


def get_vowels() -> Dict[str, Dict[str, str]]:
    """Returns the documented vowel sounds and phonetic values."""
    return dict(VOWELS)


def get_consonants() -> List[str]:
    """Returns the primary consonant inventory of the Karbi language."""
    return list(CONSONANTS)


def get_aspirates() -> List[str]:
    """Returns the aspirate consonant inventory."""
    return list(ASPIRATES)


def get_diphthongs() -> Dict[str, Dict[str, str]]:
    """Returns the documented diphthongs."""
    return dict(DIPHTHONGS)


def get_phonology_summary() -> Dict[str, Any]:
    """Returns a full summary of the Karbi phonological system and orthography notes."""
    return {
        "vowels": VOWELS,
        "diphthongs": DIPHTHONGS,
        "consonants": CONSONANTS,
        "aspirates": ASPIRATES,
        "loan_consonants": RARE_LOAN_CONSONANTS,
        "absent_consonants": TRADITIONALLY_ABSENT,
        "orthography_note": (
            "Karbi is predominantly written in the Roman script (as standardized by "
            "Karbi Lammet Amei). Historically, early 19th-century publications also employed "
            "the Assamese script."
        ),
        "source_citation": "Stack & Lyall (1908), 'The Mikirs', Section VI: Language (Sounds), pp. 73-74.",
    }
