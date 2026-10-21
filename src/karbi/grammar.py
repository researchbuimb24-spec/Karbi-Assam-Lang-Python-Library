"""
Karbi Grammar & Language Structures (`karbi.grammar`)
=====================================================

Grammatical rules, pronouns, postpositions, and the Karbi numerical
classifier system as documented by Stack & Lyall (1908) and Grierson (1903).
"""

from typing import Any, Dict, List, Optional

CLASSIFIERS = {
    "bang": {
        "classifier": "bàng",
        "category": "persons / human beings",
        "example_karbi": "kòrte bàng-theròk",
        "example_en": "six brothers",
        "source": "Stack & Lyall (1908), p. 78",
    },
    "jon": {
        "classifier": "jòn",
        "category": "animals",
        "example_karbi": "chelòng jòn-phili",
        "example_en": "four buffaloes",
        "source": "Stack & Lyall (1908), p. 78",
    },
    "rong": {
        "classifier": "ròng",
        "category": "trees and upright objects",
        "example_karbi": "thèngpi ròng-theròk",
        "example_en": "six trees",
        "source": "Stack & Lyall (1908), p. 78",
    },
    "hum": {
        "classifier": "hum",
        "category": "houses and buildings",
        "example_karbi": "hèm hum-kèp",
        "example_en": "ten houses",
        "source": "Stack & Lyall (1908), p. 78",
    },
    "pak": {
        "classifier": "pàk",
        "category": "flat things (mats, leaves, knives, books)",
        "example_karbi": "puthi e-pàk",
        "example_en": "one book",
        "source": "Stack & Lyall (1908), p. 78",
    },
    "pum": {
        "classifier": "pum",
        "category": "globular / round objects (eggs, gourds, fruits)",
        "example_karbi": "vo-ti pum-ni",
        "example_en": "two eggs",
        "source": "Stack & Lyall (1908), p. 78",
    },
    "hong": {
        "classifier": "hòng",
        "category": "limbs, ornaments, bracelets, body parts",
        "example_karbi": "roi hòng-ni",
        "example_en": "two bracelets",
        "source": "Stack & Lyall (1908), p. 78",
    },
}

PRONOUNS = {
    "first_person_singular": {"karbi": "ne", "en": "I / me", "hi": "मैं / मुझे", "as": "মই / মোক"},
    "first_person_plural_exclusive": {"karbi": "ne-tum", "en": "we (excluding listener)", "hi": "हम (श्रोता रहित)", "as": "আমি (শ্ৰোতাক বাদ দি)"},
    "first_person_plural_inclusive": {"karbi": "i-tum", "en": "we (including listener)", "hi": "हम (श्रोता सहित)", "as": "আমি (শ্ৰোতাসহ)"},
    "second_person_singular": {"karbi": "nàng", "en": "you / thou", "hi": "तू / तुम", "as": "তুমি / তই"},
    "second_person_plural": {"karbi": "nàng-tum", "en": "you all / ye", "hi": "तुम सब", "as": "তোমালোক"},
    "third_person_singular": {"karbi": "la", "en": "he / she / it", "hi": "वह / यह", "as": "সি / তেওঁ"},
    "third_person_plural": {"karbi": "la-tum", "en": "they", "hi": "वे / ये", "as": "তেওঁলোক / সিহঁত"},
}

CARDINAL_NUMBERS = {
    1: "isi",
    2: "hini",
    3: "kethòm",
    4: "phili",
    5: "phòngo",
    6: "theròk",
    7: "theròk-si",   # literally 6 + 1
    8: "nerkèp",       # literally 10 - 2
    9: "sirkèp",       # literally 10 - 1
    10: "kèp",
    11: "kre-isi",
    12: "kre-hini",
    13: "kre-kethòm",
    20: "ingkoi",
    100: "pharo",
}


def get_classifiers() -> Dict[str, Dict[str, str]]:
    """Returns the Karbi generic numeral determinatives (classifiers)."""
    return dict(CLASSIFIERS)


def get_pronouns() -> Dict[str, Dict[str, str]]:
    """Returns the documented Karbi personal pronoun system."""
    return dict(PRONOUNS)


def get_cardinals() -> Dict[int, str]:
    """Returns the traditional Karbi cardinal numbers 1-13, 20, 100."""
    return dict(CARDINAL_NUMBERS)


def count_with_classifier(number: int, category: str) -> Optional[str]:
    """
    Constructs a counted expression with the appropriate Karbi numerical classifier.

    Args:
        number: Integer between 1 and 10.
        category: 'persons', 'animals', 'trees', 'houses', 'flat', 'round', or 'ornaments'.
    """
    if category is None or not isinstance(category, str):
        return None
    if number is None or not isinstance(number, int) or not (1 <= number <= 10):
        return None

    key_map = {
        "persons": "bang",
        "person": "bang",
        "animals": "jon",
        "animal": "jon",
        "trees": "rong",
        "tree": "rong",
        "houses": "hum",
        "house": "hum",
        "flat": "pak",
        "round": "pum",
        "ornaments": "hong",
    }
    ckey = key_map.get(category.strip().lower())
    if not ckey or ckey not in CLASSIFIERS:
        return None

    clf_word = CLASSIFIERS[ckey]["classifier"]

    # Special rule: 1 of anything uses 'e-' prefix or 'inut'
    if number == 1:
        if ckey == "bang":
            return "inut"
        return f"e-{clf_word}"

    # Short forms for 2 (ni) and 3 (thòm) in compounds
    num_roots = {
        2: "ni" if ckey != "bang" else "hini",
        3: "thòm",
        4: "phili",
        5: "phòngo",
        6: "theròk",
        7: "theròk-si",
        8: "nerkèp",
        9: "sirkèp",
        10: "kèp",
    }
    nroot = num_roots.get(number)
    if not nroot:
        return None

    return f"{clf_word}-{nroot}"
