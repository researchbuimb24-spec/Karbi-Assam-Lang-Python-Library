"""
Data Models for Karbi Language Library (`karbi.core.models`)
============================================================

Type-annotated data models representing lexicon entries, senses, examples,
sources, reviews, and cultural access metadata.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(str, Enum):
    """Allowed lifecycle statuses for lexicon entries and senses."""
    DRAFT = "DRAFT"
    AI_CANDIDATE = "AI_CANDIDATE"
    COMMUNITY_SUBMITTED = "COMMUNITY_SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    # SOURCE_ATTESTED: backed by an inspected, published/archival source but not yet
    # independently peer-reviewed. English definitions are source-supported; Indic
    # glosses may be unverified unless gloss_provenance specifies otherwise.
    SOURCE_ATTESTED = "SOURCE_ATTESTED"
    PEER_REVIEWED = "PEER_REVIEWED"
    VERIFIED = "VERIFIED"


class AccessLevel(str, Enum):
    """Access clearance levels for cultural and linguistic data."""
    PUBLIC = "public"
    EDUCATIONAL_RESTRICTED = "educational_restricted"
    COMMUNITY_CONFIDENTIAL = "community_confidential"


class ReviewerRole(str, Enum):
    """Authorized reviewer categories."""
    LINGUIST = "linguist"
    NATIVE_SPEAKER_ELDER = "native_speaker_elder"
    PROJECT_SUPERVISOR = "project_supervisor"
    COMMUNITY_ADVISORY_PANEL = "community_advisory_panel"


class SourceType(str, Enum):
    """Categories of bibliographic and archival sources."""
    PRINT_PUBLICATION = "print_publication"
    JOURNAL_ARTICLE = "journal_article"
    ORAL_FIELD_RECORDING = "oral_field_recording"
    ARCHIVAL_MANUSCRIPT = "archival_manuscript"
    OTHER = "other"


@dataclass
class OrthographyMetadata:
    """Metadata describing the writing system and orthographic conventions."""
    system_name: str
    authority_status: str = "provisional"  # "provisional", "community_confirmed", "unconfirmed"
    script: str = "latin"                  # Extensible: "latin", "assamese_bengali", "ipa", etc.
    notes: Optional[str] = None


@dataclass
class DialectMetadata:
    """Metadata describing the dialectal variety and regional distribution."""
    primary_variety: str                   # e.g., "rongkhang", "amri", "chinthong", "nilip"
    status: str = "provisional"            # "provisional", "community_confirmed", "unconfirmed"
    regional_distribution_notes: Optional[str] = None


@dataclass
class CulturalMetadata:
    """Access and sensitivity flags for cultural material."""
    is_culturally_sensitive: bool = False
    access_level: str = AccessLevel.PUBLIC.value
    allow_search_indexing: bool = True
    cultural_notes: Optional[str] = None


@dataclass
class Example:
    """Usage example sentence with scalable ID, translations, and provenance."""
    example_id: str
    text_karbi: str
    translations: Dict[str, str]           # Language code (e.g. 'en', 'hi', 'mr') -> translation
    source_id: Optional[str] = None
    locator: Optional[str] = None
    permission_status: str = "authorized_quotation"


@dataclass
class Sense:
    """A distinct semantic sense of a headword."""
    sense_id: str
    part_of_speech: str                    # e.g., "noun", "verb", "adjective", etc.
    # definitions values may be:
    #   - List[str]: plain gloss strings (all treated as unverified unless gloss_provenance says otherwise)
    #   - List[Dict]: dicts with {"text": str, "verified": bool} for per-gloss provenance
    definitions: Dict[str, Any]
    status: str = Status.DRAFT.value       # Sense-level status
    # gloss_provenance maps language code -> provenance label for that language's glosses:
    #   "source_attested" | "unverified" | "community_reviewed" | "peer_reviewed"
    gloss_provenance: Optional[Dict[str, str]] = None
    grammatical_category: Optional[Dict[str, Any]] = None
    cultural_metadata: CulturalMetadata = field(default_factory=CulturalMetadata)
    examples: List[Example] = field(default_factory=list)


@dataclass
class SpellingVariant:
    """Spelling or dialectal variant of a headword."""
    text: str
    script: str = "latin"
    dialect_or_context: Optional[str] = None
    status: str = "provisional"


@dataclass
class CrossReference:
    """Semantic or lexical relation to another entry."""
    # Supports both naming conventions:
    #   JSONL uses: entry_id + relationship
    #   Legacy dataclass uses: target_entry_id + relation_type
    target_entry_id: str = ""              # Primary field (populated from entry_id if absent)
    relation_type: str = "see_also"        # "synonym", "antonym", "dialectal_counterpart", "see_also", "component_word", "paired_term"
    notes: Optional[str] = None


@dataclass
class EvidenceRecord:
    """Citation linking a claim to a registered source."""
    source_id: str
    locator: str                           # e.g., "p. 42", "01:23:45"
    evidence_type: str                     # "published_print_citation", "oral_field_recording", etc.
    extracted_text_quote: Optional[str] = None


@dataclass
class ContributorRecord:
    """Record of who transcribed or submitted an entry."""
    contributor_id: str                    # Pseudonym or ID (e.g. "CONTRIB-ANON-042")
    role: str                              # "transcriber", "field_recorder", "model_pipeline"
    date: str                              # ISO date (YYYY-MM-DD)
    submission_channel: str                # "manual_entry", "academic_import", "ai_inference"


@dataclass
class ReviewAuditRecord:
    """Audit trail for a verification review."""
    review_id: str
    reviewer_id: str                       # Pseudonym or ID (e.g. "REV-LING-014")
    reviewer_role: str                     # Must match ReviewerRole enum
    date_reviewed: str                     # ISO-8601 timestamp
    scope_reviewed: List[str]              # e.g., ["headword_orthography", "definitions_en", "source_locator_match"]
    verification_finding: str              # "confirmed_accurate", "needs_revision", "rejected"
    audit_notes: str


@dataclass
class Provenance:
    """Comprehensive audit and provenance history of an entry."""
    evidence_records: List[EvidenceRecord] = field(default_factory=list)
    contributors: List[ContributorRecord] = field(default_factory=list)
    reviews: List[ReviewAuditRecord] = field(default_factory=list)


@dataclass
class Headword:
    """Lemma and orthographic specification."""
    lemma: str
    script: str = "latin"
    orthography_standard: OrthographyMetadata = field(
        default_factory=lambda: OrthographyMetadata(system_name="unspecified", authority_status="provisional")
    )


@dataclass
class LexiconEntry:
    """Top-level dictionary entry in the Karbi language library."""
    id: str
    headword: Headword
    dialect: DialectMetadata
    senses: List[Sense]
    provenance: Provenance
    is_test_fixture: bool = False
    phonetics: Optional[Dict[str, Any]] = None
    spelling_variants: List[SpellingVariant] = field(default_factory=list)
    cross_references: List[CrossReference] = field(default_factory=list)
    status: str = Status.DRAFT.value


@dataclass
class SourceRecord:
    """Complete bibliographic or archival source record."""
    source_id: str
    source_type: str                       # Must match SourceType enum
    title: str
    creators: List[Dict[str, str]]
    rights_and_permissions: Dict[str, Any]
    publication_details: Optional[Dict[str, Any]] = None
    fieldwork_metadata: Optional[Dict[str, Any]] = None
    archive_location: Optional[str] = None
    access_date: Optional[str] = None


@dataclass
class ReviewerRegistration:
    """Authorization registration for a vetted reviewer."""
    reviewer_id: str
    role: str                              # Must match ReviewerRole enum
    authorized_scopes: List[str]           # Scopes this reviewer is credentialed to audit
    is_active: bool = True
