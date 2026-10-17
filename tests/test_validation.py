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


if __name__ == "__main__":
    unittest.main()
