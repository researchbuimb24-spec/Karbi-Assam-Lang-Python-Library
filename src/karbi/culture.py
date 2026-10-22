"""
Karbi Cultural Heritage & Traditional Knowledge (`karbi.culture`)
==================================================================

Documented cultural traditions, rituals, and deities with exact citations
and explicit sensitivity/permission markers, adhering to ethical standards.
"""

from typing import Any, Dict, List

CULTURAL_RECORDS = {
    "rituals": [
        {
            "id": "CULT-RIT-001",
            "name": "Rongker",
            "category": "village_welfare_ritual",
            "description": (
                "An annual community ritual performed at the beginning of the agricultural season "
                "or year to safeguard the village from sickness, bad fortune, and wild animals, "
                "and to pray for bumper crops."
            ),
            "sensitivity": "public_cultural_heritage",
            "source_citation": "Stack & Lyall (1908), 'The Mikirs', Section IV: Religion, pp. 31-34 (historically recorded as 'Ròngker').",
        },
        {
            "id": "CULT-RIT-002",
            "name": "Chomangkan (Thi-Karhi)",
            "category": "sacred_mortuary_ceremony",
            "description": (
                "The great post-funeral ceremony of the Karbis, performed to give rest to the souls "
                "of the dead and escort them safely to Chom-arong / Jòm-aròng (the ancestral spirit village). "
                "Characterized by traditional laments (Charhe Ke-alun / kacharhe) sung by the female master of mourning (Uchepi)."
            ),
            "sensitivity": "culturally_sensitive_sacred_mortuary",
            "source_citation": (
                "Documented as traditional mortuary rituals in Stack & Lyall (1908), Section IV: Funeral Ceremonies, "
                "pp. 37-43 (recording the journey to Jòm-aròng and chants by the uchepi); contemporary ethnographic "
                "scholarship designates the comprehensive ceremony as Chomangkan / Thi-Karhi."
            ),
        },
    ],
    "deities": [
        {
            "id": "CULT-DEI-001",
            "name": "Hemphu",
            "title": "Household and Clan Guardian Deity",
            "description": (
                "Regarded in traditional Karbi belief as the great ancestral master, owner of human beings, "
                "and foremost household guardian deity (historically recorded as Hèmphu)."
            ),
            "sensitivity": "traditional_pantheon",
            "source_citation": "Stack & Lyall (1908), 'The Mikirs', Section IV: Religion--Divinities, p. 32.",
        },
        {
            "id": "CULT-DEI-002",
            "name": "Mukrang",
            "title": "Guardian Deity",
            "description": (
                "Sibling deity alongside Hemphu, invoked in traditional household and village rites "
                "(historically recorded as Mukràng)."
            ),
            "sensitivity": "traditional_pantheon",
            "source_citation": "Stack & Lyall (1908), 'The Mikirs', Section IV: Religion--Divinities, p. 32.",
        },
        {
            "id": "CULT-DEI-003",
            "name": "Rasinja",
            "title": "Female Guardian Deity",
            "description": "Sister deity associated with Hemphu and Mukrang in the traditional triad of domestic protectors.",
            "sensitivity": "traditional_pantheon",
            "source_citation": (
                "Traditional Karbi belief and ethnographic record; not documented in Stack & Lyall (1908). "
                "Awaiting formal citation to authoritative ethnographic literature or community elder review."
            ),
        },
    ],
}


def get_rituals() -> List[Dict[str, Any]]:
    """Returns documented Karbi rituals and communal festivals."""
    return list(CULTURAL_RECORDS["rituals"])


def get_deities() -> List[Dict[str, Any]]:
    """Returns documented deities of the traditional Karbi pantheon."""
    return list(CULTURAL_RECORDS["deities"])


def get_cultural_ethics_policy() -> Dict[str, str]:
    """Returns the ethical and cultural consent framework governing this project."""
    return {
        "policy": (
            "Sacred or esoteric oral knowledge (such as specific ritual recitations, private clan genealogies, "
            "or restricted mortuary chants) is treated with utmost respect. It is never commercialized or made "
            "searchable without verified Free, Prior, and Informed Consent (FPIC) from community elders."
        ),
        "standards": "Indigenous Data Sovereignty (OCAP principles) and Traditional Knowledge guidelines.",
    }
