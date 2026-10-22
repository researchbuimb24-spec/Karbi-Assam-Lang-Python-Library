"""
Data Validator for Karbi Language Library (`karbi.core.validator`)
==================================================================

Enforces structural schema, referential integrity, fail-closed reviewer
authorizations, test-fixture rejection, and sense-level review consistency.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import unicodedata

# Supported translation definition language codes
SUPPORTED_DEFINITION_LANGUAGES = {"en", "hi", "as", "bn"}

from karbi.core.models import (
    AccessLevel,
    CrossReference,
    CulturalMetadata,
    DialectMetadata,
    EvidenceRecord,
    Example,
    Headword,
    LexiconEntry,
    OrthographyMetadata,
    Provenance,
    ReviewAuditRecord,
    ReviewerRegistration,
    ReviewerRole,
    Sense,
    SourceRecord,
    SourceType,
    SpellingVariant,
    Status,
)


class ValidationError(Exception):
    """Raised when one or more entries fail schema or verification validation."""
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or [message]


# ID regular expression patterns
RE_ENTRY_ID_REAL = re.compile(r"^KB-LEX-[0-9]{7,}$")
RE_ENTRY_ID_TEST = re.compile(r"^KB-TEST-[0-9A-Za-z_-]+$")
RE_SOURCE_ID = re.compile(r"^SRC-(PUB|FLD|ARC|OTH)-[0-9A-Za-z_-]+$")
RE_EXAMPLE_ID = re.compile(r"^EX-[0-9A-Za-z_-]+$")
RE_REVIEW_ID = re.compile(r"^REV-[0-9A-Za-z_-]+$")

# Mandatory verification review scopes
MANDATORY_SCOPES_PATHWAY_A = {"headword_orthography", "definitions_en", "source_locator_match"}
MANDATORY_SCOPES_PATHWAY_B = {"oral_evidence", "definitions_en", "community_consent"}


class LexiconValidator:
    """
    Validates lexicon entries and source records against structural,
    referential, and fail-closed verification rules.
    """

    def __init__(
        self,
        sources_registry: Optional[Dict[str, SourceRecord]] = None,
        reviewer_registry: Optional[Dict[str, ReviewerRegistration]] = None,
    ):
        self.sources_registry: Dict[str, SourceRecord] = sources_registry or {}
        # Reviewer registry: if None or empty, verification FAILS CLOSED.
        self.reviewer_registry: Optional[Dict[str, ReviewerRegistration]] = reviewer_registry

        # Tracking sets for uniqueness across a validation session
        self.seen_entry_ids: Set[str] = set()
        self.seen_example_ids: Set[str] = set()
        self.seen_review_ids: Set[str] = set()
        self.seen_source_ids: Set[str] = set()

    def reset_tracking(self) -> None:
        """Reset internal tracking sets for a new validation session."""
        self.seen_entry_ids.clear()
        self.seen_example_ids.clear()
        self.seen_review_ids.clear()
        self.seen_source_ids.clear()

    def register_source(self, source: Union[Dict[str, Any], SourceRecord]) -> List[str]:
        """Validate and register a source record into the local source registry."""
        src_obj = self._coerce_source(source)
        errors = self.validate_source_record(src_obj)
        if not errors:
            self.sources_registry[src_obj.source_id] = src_obj
            self.seen_source_ids.add(src_obj.source_id)
        return errors

    def validate_source_record(self, source: Union[Dict[str, Any], SourceRecord]) -> List[str]:
        """Validate a single source record."""
        errors: List[str] = []
        src = self._coerce_source(source)

        if not src.source_id:
            errors.append("Source missing 'source_id'.")
        elif not RE_SOURCE_ID.match(src.source_id):
            errors.append(f"Invalid source_id format: '{src.source_id}'. Must match pattern SRC-(PUB|FLD|ARC|OTH)-...")

        if src.source_id in self.seen_source_ids and src.source_id not in self.sources_registry:
            errors.append(f"Duplicate source_id detected: '{src.source_id}'.")

        if not src.title or not src.title.strip():
            errors.append(f"Source '{src.source_id}': title cannot be empty.")

        if src.source_type not in [s.value for s in SourceType]:
            errors.append(
                f"Source '{src.source_id}': invalid source_type '{src.source_type}'. "
                f"Allowed: {[s.value for s in SourceType]}"
            )

        if not src.creators or len(src.creators) == 0:
            errors.append(f"Source '{src.source_id}': must have at least one creator/organization.")

        if not isinstance(src.rights_and_permissions, dict) or not src.rights_and_permissions.get("status"):
            errors.append(f"Source '{src.source_id}': rights_and_permissions.status is required.")

        return errors

    def validate_entry(
        self,
        entry: Union[Dict[str, Any], LexiconEntry],
        check_cross_refs: bool = False,
    ) -> List[str]:
        """Validate a single lexicon entry against all structural and verification rules."""
        errors: List[str] = []
        e = self._coerce_entry(entry)

        # 1. ID Validation and Uniqueness
        if not e.id:
            errors.append("Entry missing 'id'.")
            return errors

        is_test_id = bool(RE_ENTRY_ID_TEST.match(e.id))
        is_real_id = bool(RE_ENTRY_ID_REAL.match(e.id))

        if not (is_test_id or is_real_id):
            errors.append(
                f"Entry '{e.id}': invalid ID format. Real entries must match '^KB-LEX-[0-9]{{7,}}$'; "
                f"test fixtures must match '^KB-TEST-[0-9A-Za-z_-]+$'."
            )

        if e.id in self.seen_entry_ids:
            errors.append(f"Duplicate entry ID detected across dataset: '{e.id}'.")
        self.seen_entry_ids.add(e.id)

        # 2. Test Fixture Identification and Anti-Forgery Rejection
        is_marked_test = e.is_test_fixture or is_test_id
        if is_marked_test and e.status == Status.VERIFIED.value:
            errors.append(
                f"Entry '{e.id}': REJECTED. Test fixtures and synthetic entries are strictly prohibited "
                f"from achieving VERIFIED status."
            )

        # 3. Status Validation
        if e.status not in [s.value for s in Status]:
            errors.append(
                f"Entry '{e.id}': invalid status '{e.status}'. Allowed: {[s.value for s in Status]}"
            )

        # 4. Headword Validation
        if not e.headword or not e.headword.lemma or not e.headword.lemma.strip():
            errors.append(f"Entry '{e.id}': headword.lemma cannot be empty.")
        elif e.headword.lemma != unicodedata.normalize("NFC", e.headword.lemma):
            errors.append(
                f"Entry '{e.id}': headword lemma '{e.headword.lemma}' must be in Unicode NFC normalized form."
            )

        # 5. Dialect Validation
        if not e.dialect or not e.dialect.primary_variety or not e.dialect.primary_variety.strip():
            errors.append(f"Entry '{e.id}': dialect.primary_variety cannot be empty.")

        # 6. Senses Validation
        if not e.senses or len(e.senses) == 0:
            errors.append(f"Entry '{e.id}': must contain at least one sense.")
        else:
            for idx, sense in enumerate(e.senses, start=1):
                sense_errors = self._validate_sense(e.id, idx, sense, e.status)
                errors.extend(sense_errors)

        # 7. Cross-References Check (if enabled)
        if check_cross_refs:
            for xref in e.cross_references:
                target = (xref.target_entry_id or "").strip()
                if not target:
                    errors.append(
                        f"Entry '{e.id}': cross-reference target ID cannot be empty or missing."
                    )
                elif target not in self.seen_entry_ids:
                    errors.append(
                        f"Entry '{e.id}': cross-reference target '{target}' does not exist in dataset."
                    )

        # 8. Provenance Evidence Records Validation (across all statuses)
        if e.status == Status.SOURCE_ATTESTED.value:
            if not e.provenance or not e.provenance.evidence_records or len(e.provenance.evidence_records) == 0:
                errors.append(
                    f"Entry '{e.id}': marked as SOURCE_ATTESTED but has 0 evidence records."
                )

        if e.provenance and e.provenance.evidence_records:
            for ev in e.provenance.evidence_records:
                if not ev.source_id or not ev.source_id.strip():
                    errors.append(f"Entry '{e.id}': evidence record missing 'source_id'.")
                elif ev.source_id not in self.sources_registry:
                    errors.append(
                        f"Entry '{e.id}': evidence record references unregistered source_id '{ev.source_id}'."
                    )
                if not ev.locator or not str(ev.locator).strip():
                    errors.append(
                        f"Entry '{e.id}': evidence record for source '{ev.source_id}' must provide a locator (page/reference)."
                    )

        # 9. Strict Verification Requirements (for VERIFIED status)
        if e.status == Status.VERIFIED.value:
            verification_errors = self._validate_verification_evidence(e)
            for ve in verification_errors:
                if ve not in errors:
                    errors.append(ve)

        return errors

    def _validate_sense(self, entry_id: str, index: int, sense: Sense, parent_status: str) -> List[str]:
        """Validate an individual sense within an entry."""
        errors: List[str] = []

        if not sense.sense_id:
            errors.append(f"Entry '{entry_id}', Sense #{index}: missing 'sense_id'.")

        if not sense.part_of_speech or not sense.part_of_speech.strip():
            errors.append(f"Entry '{entry_id}', Sense '{sense.sense_id}': part_of_speech cannot be empty.")

        if not sense.definitions or len(sense.definitions) == 0:
            errors.append(f"Entry '{entry_id}', Sense '{sense.sense_id}': definitions cannot be empty.")
        else:
            # Check supported definition languages
            for lang in sense.definitions:
                if lang not in SUPPORTED_DEFINITION_LANGUAGES:
                    errors.append(
                        f"Entry '{entry_id}', Sense '{sense.sense_id}': unsupported language code '{lang}' in definitions. "
                        f"Allowed: {sorted(list(SUPPORTED_DEFINITION_LANGUAGES))}"
                    )

            # Definitions may be:
            #   - List[str]: plain gloss strings
            #   - List[Dict]: dicts with 'text' key (and optional 'verified' flag)
            has_valid_def = False
            for lang, def_list in sense.definitions.items():
                if not isinstance(def_list, list):
                    continue
                for d in def_list:
                    if isinstance(d, str) and d.strip():
                        has_valid_def = True
                    elif isinstance(d, dict) and d.get("text", "").strip():
                        has_valid_def = True
                        if parent_status in (Status.DRAFT.value, Status.AI_CANDIDATE.value, Status.IN_REVIEW.value) and d.get("verified") is True:
                            errors.append(
                                f"Entry '{entry_id}', Sense '{sense.sense_id}': contradictory verification state. "
                                f"Entry has unvetted status '{parent_status}' but contains a gloss marked verified=True."
                            )
            if not has_valid_def:
                errors.append(
                    f"Entry '{entry_id}', Sense '{sense.sense_id}': definitions must contain at least one "
                    f"non-empty translation gloss."
                )

        # Sense-level status rule: If parent is VERIFIED, every sense must also be VERIFIED
        if parent_status == Status.VERIFIED.value and sense.status != Status.VERIFIED.value:
            errors.append(
                f"Entry '{entry_id}', Sense '{sense.sense_id}': entry is marked VERIFIED, but this sense has "
                f"unverified status '{sense.status}'. All senses must be VERIFIED for the entry to be VERIFIED."
            )

        # Examples Validation
        for ex in sense.examples:
            if not ex.example_id:
                errors.append(f"Entry '{entry_id}', Sense '{sense.sense_id}': example missing 'example_id'.")
            elif not RE_EXAMPLE_ID.match(ex.example_id):
                errors.append(
                    f"Entry '{entry_id}', Example '{ex.example_id}': invalid format. Must match pattern ^EX-[0-9A-Za-z_-]+$"
                )

            if ex.example_id in self.seen_example_ids:
                errors.append(f"Duplicate example_id detected across dataset: '{ex.example_id}'.")
            self.seen_example_ids.add(ex.example_id)

            if not ex.text_karbi or not ex.text_karbi.strip():
                errors.append(f"Entry '{entry_id}', Example '{ex.example_id}': text_karbi cannot be empty.")

            if ex.source_id and ex.source_id not in self.sources_registry:
                errors.append(
                    f"Entry '{entry_id}', Example '{ex.example_id}': references unknown source_id '{ex.source_id}'."
                )

        return errors

    def _validate_verification_evidence(self, entry: LexiconEntry) -> List[str]:
        """
        Enforce strict verification requirements. Fails closed if the reviewer
        registry is missing or if the reviewer lacks authorization for the required scopes.
        """
        errors: List[str] = []

        # Rule A: Reviewer registry must be configured and non-empty (FAIL CLOSED)
        if not self.reviewer_registry or len(self.reviewer_registry) == 0:
            errors.append(
                f"Entry '{entry.id}': verification check FAILED CLOSED. The trusted reviewer registry is "
                f"missing or empty. No entries can be validated as VERIFIED without an authorized registry."
            )
            return errors

        # Defensive check for missing provenance
        if entry.provenance is None:
            errors.append(f"Entry '{entry.id}': marked as VERIFIED but provenance is missing.")
            return errors

        # Rule B: Evidence records must be present
        if not entry.provenance.evidence_records or len(entry.provenance.evidence_records) == 0:
            errors.append(f"Entry '{entry.id}': marked as VERIFIED but has 0 evidence records.")
            return errors

        # Check every evidence record references a valid registered source
        for ev in entry.provenance.evidence_records:
            if not ev.source_id or not ev.source_id.strip():
                errors.append(f"Entry '{entry.id}': evidence record missing 'source_id'.")
            elif ev.source_id not in self.sources_registry:
                errors.append(
                    f"Entry '{entry.id}': evidence record references unregistered source_id '{ev.source_id}'."
                )
            if not ev.locator or not ev.locator.strip():
                errors.append(
                    f"Entry '{entry.id}': evidence record for source '{ev.source_id}' must provide a locator (page/timestamp)."
                )

        # Rule C: Substantive review audit records must be present
        if not entry.provenance.reviews or len(entry.provenance.reviews) == 0:
            errors.append(
                f"Entry '{entry.id}': marked as VERIFIED but has 0 review audit records."
            )
            return errors

        # Check reviews against the trusted reviewer registry
        all_covered_scopes: Set[str] = set()

        for rev in entry.provenance.reviews:
            if not rev.review_id:
                errors.append(f"Entry '{entry.id}': review missing 'review_id'.")
            elif not RE_REVIEW_ID.match(rev.review_id):
                errors.append(
                    f"Entry '{entry.id}', Review '{rev.review_id}': invalid ID format. Must match ^REV-[0-9A-Za-z_-]+$"
                )

            if rev.review_id in self.seen_review_ids:
                errors.append(f"Duplicate review_id detected across dataset: '{rev.review_id}'.")
            self.seen_review_ids.add(rev.review_id)

            # Check reviewer registration
            reviewer_reg = self.reviewer_registry.get(rev.reviewer_id)
            if not reviewer_reg:
                errors.append(
                    f"Entry '{entry.id}': reviewer '{rev.reviewer_id}' is not in the trusted reviewer registry (FAIL CLOSED)."
                )
                continue

            if not reviewer_reg.is_active:
                errors.append(
                    f"Entry '{entry.id}': reviewer '{rev.reviewer_id}' is marked inactive in registry."
                )

            if reviewer_reg.role != rev.reviewer_role:
                errors.append(
                    f"Entry '{entry.id}': review role '{rev.reviewer_role}' does not match registered role '{reviewer_reg.role}'."
                )

            # Check authorized scopes
            for sc in rev.scope_reviewed:
                if sc not in reviewer_reg.authorized_scopes:
                    errors.append(
                        f"Entry '{entry.id}': reviewer '{rev.reviewer_id}' is not authorized for review scope '{sc}'."
                    )
                else:
                    all_covered_scopes.add(sc)

            if rev.verification_finding != "confirmed_accurate":
                errors.append(
                    f"Entry '{entry.id}': review finding '{rev.verification_finding}' does not support VERIFIED status."
                )

        # Rule D: Review scopes must satisfy Pathway A or Pathway B
        satisfies_pathway_a = MANDATORY_SCOPES_PATHWAY_A.issubset(all_covered_scopes)
        satisfies_pathway_b = MANDATORY_SCOPES_PATHWAY_B.issubset(all_covered_scopes)

        if not (satisfies_pathway_a or satisfies_pathway_b):
            errors.append(
                f"Entry '{entry.id}': reviews do not cover mandatory scopes. Must satisfy either "
                f"Pathway A (published: {sorted(list(MANDATORY_SCOPES_PATHWAY_A))}) OR "
                f"Pathway B (oral: {sorted(list(MANDATORY_SCOPES_PATHWAY_B))}). Covered: {sorted(list(all_covered_scopes))}."
            )

        return errors

    # Coercion helpers to support both dicts (from JSON/JSONL) and typed dataclasses
    def _coerce_entry(self, data: Union[Dict[str, Any], LexiconEntry]) -> LexiconEntry:
        if isinstance(data, LexiconEntry):
            return data

        # Unpack dict to dataclass
        headword_data = data.get("headword", {})
        ortho_data = headword_data.get("orthography_standard", {})
        ortho = OrthographyMetadata(
            system_name=ortho_data.get("system_name", "unspecified"),
            authority_status=ortho_data.get("authority_status", "provisional"),
            script=ortho_data.get("script", "latin"),
            notes=ortho_data.get("notes"),
        )
        headword = Headword(
            lemma=headword_data.get("lemma", ""),
            script=headword_data.get("script", "latin"),
            orthography_standard=ortho,
        )

        dialect_data = data.get("dialect", {})
        dialect = DialectMetadata(
            primary_variety=dialect_data.get("primary_variety", ""),
            status=dialect_data.get("status", "provisional"),
            regional_distribution_notes=dialect_data.get("regional_distribution_notes"),
        )

        senses: List[Sense] = []
        for s in data.get("senses", []):
            cm_data = s.get("cultural_metadata", {})
            cm = CulturalMetadata(
                is_culturally_sensitive=cm_data.get("is_culturally_sensitive", False),
                access_level=cm_data.get("access_level", AccessLevel.PUBLIC.value),
                allow_search_indexing=cm_data.get("allow_search_indexing", True),
                cultural_notes=cm_data.get("cultural_notes"),
            )
            examples: List[Example] = []
            for ex in s.get("examples", []):
                examples.append(
                    Example(
                        example_id=ex.get("example_id", ""),
                        text_karbi=ex.get("text_karbi", ""),
                        translations=ex.get("translations", {}),
                        source_id=ex.get("source_id"),
                        locator=ex.get("locator"),
                        permission_status=ex.get("permission_status", "authorized_quotation"),
                    )
                )
            senses.append(
                Sense(
                    sense_id=s.get("sense_id", ""),
                    part_of_speech=s.get("part_of_speech", ""),
                    definitions=s.get("definitions", {}),
                    status=s.get("status", Status.DRAFT.value),
                    gloss_provenance=s.get("gloss_provenance"),
                    grammatical_category=s.get("grammatical_category"),
                    cultural_metadata=cm,
                    examples=examples,
                )
            )

        prov_data = data.get("provenance", {})
        evidence_records = [
            EvidenceRecord(
                source_id=ev.get("source_id", ""),
                locator=ev.get("locator", ""),
                evidence_type=ev.get("evidence_type", ""),
                extracted_text_quote=ev.get("extracted_text_quote"),
            )
            for ev in prov_data.get("evidence_records", [])
        ]
        reviews = [
            ReviewAuditRecord(
                review_id=rev.get("review_id", ""),
                reviewer_id=rev.get("reviewer_id", ""),
                reviewer_role=rev.get("reviewer_role", ""),
                date_reviewed=rev.get("date_reviewed", ""),
                scope_reviewed=rev.get("scope_reviewed", []),
                verification_finding=rev.get("verification_finding", ""),
                audit_notes=rev.get("audit_notes", ""),
            )
            for rev in prov_data.get("reviews", [])
        ]
        provenance = Provenance(
            evidence_records=evidence_records,
            contributors=prov_data.get("contributors", []),
            reviews=reviews,
        )

        variants = [
            SpellingVariant(
                text=v.get("text", ""),
                script=v.get("script", "latin"),
                dialect_or_context=v.get("dialect_or_context"),
                status=v.get("status", "provisional"),
            )
            for v in data.get("spelling_variants", [])
        ]
        xrefs = []
        for xr in data.get("cross_references", []):
            if isinstance(xr, CrossReference):
                xrefs.append(xr)
                continue
            if not isinstance(xr, dict):
                continue
            # Support both notes and note, preferring the populated value
            note_val = None
            if xr.get("notes") is not None and str(xr.get("notes")).strip():
                note_val = str(xr.get("notes"))
            elif xr.get("note") is not None and str(xr.get("note")).strip():
                note_val = str(xr.get("note"))
            elif xr.get("notes") is not None:
                note_val = str(xr.get("notes"))
            elif xr.get("note") is not None:
                note_val = str(xr.get("note"))

            xrefs.append(
                CrossReference(
                    # JSONL may use entry_id/relationship; legacy uses target_entry_id/relation_type
                    target_entry_id=xr.get("target_entry_id") or xr.get("entry_id", ""),
                    relation_type=xr.get("relation_type") or xr.get("relationship", "see_also"),
                    notes=note_val,
                )
            )

        return LexiconEntry(
            id=data.get("id", ""),
            headword=headword,
            dialect=dialect,
            senses=senses,
            provenance=provenance,
            is_test_fixture=data.get("is_test_fixture", False),
            phonetics=data.get("phonetics"),
            spelling_variants=variants,
            cross_references=xrefs,
            status=data.get("status", Status.DRAFT.value),
        )

    def _coerce_source(self, data: Union[Dict[str, Any], SourceRecord]) -> SourceRecord:
        if isinstance(data, SourceRecord):
            return data
        return SourceRecord(
            source_id=data.get("source_id", ""),
            source_type=data.get("source_type", ""),
            title=data.get("title", ""),
            creators=data.get("creators", []),
            rights_and_permissions=data.get("rights_and_permissions", {}),
            publication_details=data.get("publication_details"),
            fieldwork_metadata=data.get("fieldwork_metadata"),
            archive_location=data.get("archive_location"),
            access_date=data.get("access_date"),
        )
