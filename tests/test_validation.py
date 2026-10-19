"""
Automated Unit Tests for Karbi Library Data Models & Validator
==============================================================

Uses ONLY fictional test fixtures. Validates structural rules, referential
integrity, fail-closed reviewer authorizations, and anti-forgery protections.
"""

import sys
import unittest
from pathlib import Path

# Add src to sys.path so tests can import the package without installation
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from karbi.core.models import (
    AccessLevel,
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
    Status,
)
from karbi.core.validator import LexiconValidator


def get_fictional_source_fixture() -> SourceRecord:
    """Returns a fictional source fixture for schema testing only."""
    return SourceRecord(
        source_id="SRC-PUB-00001",
        source_type=SourceType.PRINT_PUBLICATION.value,
        title="Fictional Synthetic Lexicon For Unit Testing Only",
        creators=[{"name_or_organization": "Synthetic Test Author", "role": "author"}],
        rights_and_permissions={"status": "synthetic_test_data", "details": "Testing only"},
        publication_details={"publisher": "Test Publisher", "year": 2026},
    )


def get_fictional_entry_fixture(
    entry_id: str = "KB-TEST-0000001",
    status: str = Status.DRAFT.value,
    is_test_fixture: bool = True,
    sense_status: str = Status.DRAFT.value,
) -> LexiconEntry:
    """Returns a fictional entry fixture for schema testing only."""
    headword = Headword(
        lemma="mock_lemma",
        script="latin",
        orthography_standard=OrthographyMetadata(
            system_name="fictional_test_orthography",
            authority_status="provisional",
        ),
    )
    dialect = DialectMetadata(primary_variety="fictional_test_variety", status="provisional")
    example = Example(
        example_id="EX-2026-LONG-0000001",  # Scalable ID
        text_karbi="Mock example sentence.",
        translations={"en": "Mock translation."},
        source_id="SRC-PUB-00001",
        locator="p. 1",
    )
    sense = Sense(
        sense_id="SENSE-01",
        part_of_speech="noun",
        definitions={"en": ["mock fictional definition for unit tests"]},
        status=sense_status,
        examples=[example],
    )
    provenance = Provenance(
        evidence_records=[
            EvidenceRecord(
                source_id="SRC-PUB-00001",
                locator="p. 1",
                evidence_type="published_print_citation",
            )
        ],
        contributors=[],
        reviews=[],
    )
    return LexiconEntry(
        id=entry_id,
        headword=headword,
        dialect=dialect,
        senses=[sense],
        provenance=provenance,
        is_test_fixture=is_test_fixture,
        status=status,
    )


class TestValidationSystem(unittest.TestCase):
    """Test suite covering data validation, fail-closed authorization, and security rules."""

    def setUp(self):
        self.source_fixture = get_fictional_source_fixture()
        self.validator = LexiconValidator(sources_registry={self.source_fixture.source_id: self.source_fixture})

    def test_valid_draft_fixture_passes(self):
        """A valid fictional draft fixture passes schema validation."""
        entry = get_fictional_entry_fixture(status=Status.DRAFT.value)
        errors = self.validator.validate_entry(entry)
        self.assertEqual(errors, [], f"Expected 0 errors, got: {errors}")

    def test_test_fixture_cannot_be_verified(self):
        """Rule 1: An entry marked as a test fixture is strictly forbidden from VERIFIED status."""
        entry = get_fictional_entry_fixture(status=Status.VERIFIED.value, is_test_fixture=True)
        errors = self.validator.validate_entry(entry)
        self.assertTrue(
            any("Test fixtures and synthetic entries are strictly prohibited" in e for e in errors),
            f"Expected test fixture rejection error, got: {errors}",
        )

    def test_anti_forgery_forged_review_rejected(self):
        """Rule 2 & 7: Forged reviewer and unknown source citations are completely rejected."""
        entry = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000001",  # Real-looking ID format
            status=Status.VERIFIED.value,
            is_test_fixture=False,
            sense_status=Status.VERIFIED.value,
        )
        # Attach forged source and reviewer
        entry.provenance.evidence_records = [
            EvidenceRecord(source_id="SRC-PUB-FORGED-999", locator="p. 99", evidence_type="citation")
        ]
        entry.provenance.reviews = [
            ReviewAuditRecord(
                review_id="REV-FORGED-01",
                reviewer_id="REV-ATTACKER-99",
                reviewer_role=ReviewerRole.LINGUIST.value,
                date_reviewed="2026-10-17T00:00:00Z",
                scope_reviewed=["headword_orthography", "definitions_en", "source_locator_match"],
                verification_finding="confirmed_accurate",
                audit_notes="Fake review note",
            )
        ]

        # Validator with a valid reviewer registry containing a legitimate reviewer
        legitimate_reviewer = ReviewerRegistration(
            reviewer_id="REV-LING-LEGIT",
            role=ReviewerRole.LINGUIST.value,
            authorized_scopes=["headword_orthography", "definitions_en", "source_locator_match"],
            is_active=True,
        )
        val = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry={"REV-LING-LEGIT": legitimate_reviewer},
        )
        errors = val.validate_entry(entry)
        self.assertTrue(
            any("unregistered source_id 'SRC-PUB-FORGED-999'" in e for e in errors),
            f"Expected unregistered source error, got: {errors}",
        )
        self.assertTrue(
            any("not in the trusted reviewer registry" in e for e in errors),
            f"Expected unregistered reviewer error, got: {errors}",
        )

    def test_missing_reviewer_registry_fails_closed(self):
        """Rule: If reviewer registry is unconfigured or empty, verification always fails closed."""
        entry = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000002",
            status=Status.VERIFIED.value,
            is_test_fixture=False,
            sense_status=Status.VERIFIED.value,
        )
        entry.provenance.reviews = [
            ReviewAuditRecord(
                review_id="REV-2026-0001",
                reviewer_id="REV-LING-001",
                reviewer_role=ReviewerRole.LINGUIST.value,
                date_reviewed="2026-10-17T00:00:00Z",
                scope_reviewed=["headword_orthography", "definitions_en", "source_locator_match"],
                verification_finding="confirmed_accurate",
                audit_notes="Audit note",
            )
        ]
        # Validator has no reviewer registry
        val_no_registry = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry=None,
        )
        errors = val_no_registry.validate_entry(entry)
        self.assertTrue(
            any("verification check FAILED CLOSED" in e for e in errors),
            f"Expected fail-closed error, got: {errors}",
        )

    def test_unauthorized_reviewer_scope_rejected(self):
        """Rule: A reviewer registered only for 'phonetics' cannot verify definitions or orthography."""
        reviewer_reg = ReviewerRegistration(
            reviewer_id="REV-LING-002",
            role=ReviewerRole.LINGUIST.value,
            authorized_scopes=["phonetics_only"],  # Limited scope!
            is_active=True,
        )
        val = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry={"REV-LING-002": reviewer_reg},
        )
        entry = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000003",
            status=Status.VERIFIED.value,
            is_test_fixture=False,
            sense_status=Status.VERIFIED.value,
        )
        entry.provenance.reviews = [
            ReviewAuditRecord(
                review_id="REV-2026-0002",
                reviewer_id="REV-LING-002",
                reviewer_role=ReviewerRole.LINGUIST.value,
                date_reviewed="2026-10-17T00:00:00Z",
                scope_reviewed=["headword_orthography", "definitions_en"],  # Not authorized!
                verification_finding="confirmed_accurate",
                audit_notes="Audit note",
            )
        ]
        errors = val.validate_entry(entry)
        self.assertTrue(
            any("not authorized for review scope" in e for e in errors),
            f"Expected unauthorized scope error, got: {errors}",
        )

    def test_sense_level_review_consistency(self):
        """Rule: If entry is marked VERIFIED, all its senses must also be VERIFIED."""
        reviewer_reg = ReviewerRegistration(
            reviewer_id="REV-LING-001",
            role=ReviewerRole.LINGUIST.value,
            authorized_scopes=["headword_orthography", "definitions_en", "source_locator_match"],
            is_active=True,
        )
        val = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry={"REV-LING-001": reviewer_reg},
        )
        # Entry is VERIFIED, but sense is still DRAFT
        entry = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000004",
            status=Status.VERIFIED.value,
            is_test_fixture=False,
            sense_status=Status.DRAFT.value,
        )
        entry.provenance.reviews = [
            ReviewAuditRecord(
                review_id="REV-2026-0003",
                reviewer_id="REV-LING-001",
                reviewer_role=ReviewerRole.LINGUIST.value,
                date_reviewed="2026-10-17T00:00:00Z",
                scope_reviewed=["headword_orthography", "definitions_en", "source_locator_match"],
                verification_finding="confirmed_accurate",
                audit_notes="Audit note",
            )
        ]
        errors = val.validate_entry(entry)
        self.assertTrue(
            any("unverified status 'DRAFT'" in e for e in errors),
            f"Expected sense-level status mismatch error, got: {errors}",
        )

    def test_duplicate_id_detection(self):
        """Rule: Duplicate entry IDs, example IDs, or review IDs are detected and rejected."""
        entry1 = get_fictional_entry_fixture(entry_id="KB-TEST-0000005")
        entry2 = get_fictional_entry_fixture(entry_id="KB-TEST-0000005")  # Duplicate!

        errors1 = self.validator.validate_entry(entry1)
        self.assertEqual(errors1, [])

        errors2 = self.validator.validate_entry(entry2)
        self.assertTrue(
            any("Duplicate entry ID detected" in e for e in errors2),
            f"Expected duplicate ID error, got: {errors2}",
        )

    def test_scalable_example_id_accepted(self):
        """Rule: Example IDs support scalable alphanumeric/dash formats without 3-digit limits."""
        entry = get_fictional_entry_fixture(entry_id="KB-TEST-0000006")
        entry.senses[0].examples[0].example_id = "EX-2026-SCALABLE-ID-000099418"
        errors = self.validator.validate_entry(entry)
        self.assertEqual(errors, [], f"Expected scalable example ID to be valid, got: {errors}")

    def test_source_referential_integrity(self):
        """Rule: Examples and evidence records referencing unknown source IDs fail validation."""
        entry = get_fictional_entry_fixture(entry_id="KB-TEST-0000007")
        entry.senses[0].examples[0].source_id = "SRC-PUB-UNKNOWN-404"
        errors = self.validator.validate_entry(entry)
        self.assertTrue(
            any("references unknown source_id 'SRC-PUB-UNKNOWN-404'" in e for e in errors),
            f"Expected referential integrity error, got: {errors}",
        )

    def test_required_fields_enforcement(self):
        """Rule: Empty headword, empty dialect, or missing definitions fail validation."""
        entry = get_fictional_entry_fixture(entry_id="KB-TEST-0000008")
        entry.headword.lemma = ""  # Missing lemma!
        entry.senses[0].definitions = {}  # Missing definitions!
        errors = self.validator.validate_entry(entry)
        self.assertTrue(any("headword.lemma cannot be empty" in e for e in errors))
        self.assertTrue(any("definitions cannot be empty" in e for e in errors))

    def test_cross_reference_note_preservation(self):
        """Cross-reference notes survive dictionary coercion and validation."""
        # 1. JSONL format with singular 'note'
        dict_jsonl = {
            "id": "KB-TEST-0000010",
            "headword": {"lemma": "test", "script": "latin"},
            "dialect": {"primary_variety": "rongkhang"},
            "senses": [{"sense_id": "S1", "part_of_speech": "noun", "definitions": {"en": ["test"]}}],
            "cross_references": [
                {"entry_id": "KB-TEST-0000001", "relationship": "component_word", "note": "JSONL singular note"}
            ],
            "status": Status.DRAFT.value,
        }
        coerced_jsonl = self.validator._coerce_entry(dict_jsonl)
        self.assertEqual(len(coerced_jsonl.cross_references), 1)
        self.assertEqual(coerced_jsonl.cross_references[0].notes, "JSONL singular note")
        self.assertEqual(coerced_jsonl.cross_references[0].target_entry_id, "KB-TEST-0000001")
        self.assertEqual(coerced_jsonl.cross_references[0].relation_type, "component_word")

        # 2. Legacy model format with plural 'notes'
        dict_legacy = {
            "id": "KB-TEST-0000011",
            "headword": {"lemma": "test2", "script": "latin"},
            "dialect": {"primary_variety": "rongkhang"},
            "senses": [{"sense_id": "S1", "part_of_speech": "noun", "definitions": {"en": ["test"]}}],
            "cross_references": [
                {"target_entry_id": "KB-TEST-0000001", "relation_type": "see_also", "notes": "Legacy plural notes"}
            ],
            "status": Status.DRAFT.value,
        }
        coerced_legacy = self.validator._coerce_entry(dict_legacy)
        self.assertEqual(coerced_legacy.cross_references[0].notes, "Legacy plural notes")

        # 3. Both present: prefers populated value
        dict_both = {
            "id": "KB-TEST-0000012",
            "headword": {"lemma": "test3", "script": "latin"},
            "dialect": {"primary_variety": "rongkhang"},
            "senses": [{"sense_id": "S1", "part_of_speech": "noun", "definitions": {"en": ["test"]}}],
            "cross_references": [
                {"entry_id": "KB-TEST-0000001", "notes": "Populated notes", "note": "   "}
            ],
            "status": Status.DRAFT.value,
        }
        coerced_both = self.validator._coerce_entry(dict_both)
        self.assertEqual(coerced_both.cross_references[0].notes, "Populated notes")

    def test_unregistered_evidence_source_rejected_for_source_attested_entry(self):
        """Regression test: An unregistered evidence source is rejected for SOURCE_ATTESTED entries."""
        entry = get_fictional_entry_fixture(
            entry_id="KB-TEST-0000020",
            status=Status.SOURCE_ATTESTED.value,
            sense_status=Status.SOURCE_ATTESTED.value,
        )
        # Point evidence record to an unregistered source
        entry.provenance.evidence_records = [
            EvidenceRecord(
                source_id="SRC-PUB-UNREGISTERED-999",
                locator="p. 42",
                evidence_type="published_print_citation",
            )
        ]
        # Ensure example source does not mask the check
        entry.senses[0].examples = []

        errors = self.validator.validate_entry(entry)
        self.assertTrue(
            any("references unregistered source_id 'SRC-PUB-UNREGISTERED-999'" in e for e in errors),
            f"Expected unregistered source error on SOURCE_ATTESTED entry, got: {errors}",
        )

    def test_unregistered_evidence_source_rejected_for_draft_entry(self):
        """Regression test: An unregistered evidence source is rejected for DRAFT entries."""
        entry = get_fictional_entry_fixture(
            entry_id="KB-TEST-0000021",
            status=Status.DRAFT.value,
            sense_status=Status.DRAFT.value,
        )
        entry.provenance.evidence_records = [
            EvidenceRecord(
                source_id="SRC-PUB-UNREGISTERED-888",
                locator="p. 10",
                evidence_type="published_print_citation",
            )
        ]
        entry.senses[0].examples = []

        errors = self.validator.validate_entry(entry)
        self.assertTrue(
            any("references unregistered source_id 'SRC-PUB-UNREGISTERED-888'" in e for e in errors),
            f"Expected unregistered source error on DRAFT entry, got: {errors}",
        )

    def test_registered_evidence_source_valid_for_attested_entry(self):
        """Regression test: A registered evidence source remains valid when the rest of the entry is valid."""
        entry = get_fictional_entry_fixture(
            entry_id="KB-TEST-0000022",
            status=Status.SOURCE_ATTESTED.value,
            sense_status=Status.SOURCE_ATTESTED.value,
        )
        # Uses registered source fixture SRC-PUB-00001
        entry.provenance.evidence_records = [
            EvidenceRecord(
                source_id=self.source_fixture.source_id,
                locator="p. 100",
                evidence_type="published_print_citation",
            )
        ]
        errors = self.validator.validate_entry(entry)
        self.assertEqual(errors, [])

    def test_verified_entry_safeguards_continue_to_enforce_reviewer_and_evidence(self):
        """Regression test: Existing VERIFIED-entry safeguards continue to work."""
        # 1. VERIFIED entry without reviewer registry must fail closed
        entry_fail_closed = get_fictional_entry_fixture(
            entry_id="KB-TEST-0000023",
            status=Status.VERIFIED.value,
            sense_status=Status.VERIFIED.value,
            is_test_fixture=False,
        )
        errors = self.validator.validate_entry(entry_fail_closed)
        self.assertTrue(
            any("verification check FAILED CLOSED" in e for e in errors),
            f"Expected fail-closed error, got: {errors}",
        )

        # 2. VERIFIED entry with reviewer registry but unregistered evidence source
        authorized_reviewer = ReviewerRegistration(
            reviewer_id="REV-LEAD-01",
            role=ReviewerRole.LINGUIST.value,
            authorized_scopes=["headword_orthography", "definitions_en", "source_locator_match"],
            is_active=True,
        )
        validator_with_registry = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry={"REV-LEAD-01": authorized_reviewer},
        )
        entry_with_bad_source = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000024",
            status=Status.VERIFIED.value,
            sense_status=Status.VERIFIED.value,
            is_test_fixture=False,
        )
        entry_with_bad_source.provenance.evidence_records = [
            EvidenceRecord(
                source_id="SRC-PUB-UNREGISTERED-777",
                locator="p. 50",
                evidence_type="published_print_citation",
            )
        ]
        entry_with_bad_source.provenance.reviews = [
            ReviewAuditRecord(
                review_id="REV-2026-0099",
                reviewer_id="REV-LEAD-01",
                reviewer_role=ReviewerRole.LINGUIST.value,
                date_reviewed="2026-10-17T00:00:00Z",
                scope_reviewed=["headword_orthography", "definitions_en", "source_locator_match"],
                verification_finding="confirmed_accurate",
                audit_notes="Audit note",
            )
        ]
        errors_verified = validator_with_registry.validate_entry(entry_with_bad_source)
        self.assertTrue(
            any("references unregistered source_id 'SRC-PUB-UNREGISTERED-777'" in e for e in errors_verified),
            f"Expected unregistered source error, got: {errors_verified}",
        )
        # Ensure no duplicated error strings
        unreg_errors = [e for e in errors_verified if "SRC-PUB-UNREGISTERED-777" in e]
        self.assertEqual(len(unreg_errors), 1)

    def test_whitespace_only_source_id_consistency_and_no_duplicates(self):
        """Rule: Whitespace-only source_id produces consistent missing source error without duplicate or contradictory errors."""
        authorized_reviewer = ReviewerRegistration(
            reviewer_id="REV-LEAD-01",
            role=ReviewerRole.LINGUIST.value,
            authorized_scopes=["headword_orthography", "definitions_en", "source_locator_match"],
            is_active=True,
        )
        validator = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry={"REV-LEAD-01": authorized_reviewer},
        )
        entry = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000025",
            status=Status.VERIFIED.value,
            sense_status=Status.VERIFIED.value,
            is_test_fixture=False,
        )
        entry.provenance.evidence_records = [
            EvidenceRecord(
                source_id="   ",
                locator="p. 50",
                evidence_type="published_print_citation",
            )
        ]
        entry.provenance.reviews = [
            ReviewAuditRecord(
                review_id="REV-2026-0100",
                reviewer_id="REV-LEAD-01",
                reviewer_role=ReviewerRole.LINGUIST.value,
                date_reviewed="2026-10-17T00:00:00Z",
                scope_reviewed=["headword_orthography", "definitions_en", "source_locator_match"],
                verification_finding="confirmed_accurate",
                audit_notes="Audit note",
            )
        ]
        errors = validator.validate_entry(entry)
        self.assertTrue(
            any("evidence record missing 'source_id'" in e for e in errors),
            f"Expected missing source_id error, got: {errors}",
        )
        self.assertFalse(
            any("references unregistered source_id" in e for e in errors),
            f"Unexpected contradictory unregistered source_id error in: {errors}",
        )
        missing_errors = [e for e in errors if "evidence record missing 'source_id'" in e]
        self.assertEqual(len(missing_errors), 1)

        v_errors = validator._validate_verification_evidence(entry)
        self.assertTrue(any("evidence record missing 'source_id'" in e for e in v_errors))
        self.assertFalse(any("references unregistered source_id" in e for e in v_errors))

    def test_verified_entry_missing_provenance_defensive_check(self):
        """Rule: Malformed VERIFIED entry with provenance is None produces validation errors instead of AttributeError."""
        authorized_reviewer = ReviewerRegistration(
            reviewer_id="REV-LEAD-01",
            role=ReviewerRole.LINGUIST.value,
            authorized_scopes=["headword_orthography", "definitions_en", "source_locator_match"],
            is_active=True,
        )
        validator = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry={"REV-LEAD-01": authorized_reviewer},
        )
        entry = get_fictional_entry_fixture(
            entry_id="KB-LEX-0000026",
            status=Status.VERIFIED.value,
            sense_status=Status.VERIFIED.value,
            is_test_fixture=False,
        )
        entry.provenance = None

        errors = validator.validate_entry(entry)
        self.assertTrue(
            any("provenance is missing" in e for e in errors),
            f"Expected provenance missing validation error, got: {errors}",
        )

        v_errors = validator._validate_verification_evidence(entry)
        self.assertTrue(
            any("provenance is missing" in e for e in v_errors),
            f"Expected provenance missing validation error in direct check, got: {v_errors}",
        )

        # Verify fail-closed safeguard is preserved when reviewer registry is absent
        validator_no_registry = LexiconValidator(
            sources_registry={self.source_fixture.source_id: self.source_fixture},
            reviewer_registry=None,
        )
        errors_no_reg = validator_no_registry.validate_entry(entry)
        self.assertTrue(
            any("verification check FAILED CLOSED" in e for e in errors_no_reg),
            f"Expected fail-closed error to be preserved, got: {errors_no_reg}",
        )


if __name__ == "__main__":
    unittest.main()
