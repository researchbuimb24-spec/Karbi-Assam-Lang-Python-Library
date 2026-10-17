"""
Batch Dataset Validation for Karbi Language Library (`karbi.core.dataset`)
==========================================================================

Coordinates batch loading and comprehensive validation of lexicon entries
and source records across multiple JSONL files.

Features:
- Global duplicate ID detection (entries, sources, examples, reviews).
- Referential integrity auditing (sources, cross-references).
- Complete error aggregation (discovers all issues in one run without early exit).
- Strict verification and test-fixture rejection enforcement.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from karbi.core.loader import LoadedRecord, load_jsonl_file
from karbi.core.models import ReviewerRegistration, SourceRecord
from karbi.core.validator import LexiconValidator


@dataclass
class DatasetError:
    """Structured error representing a data or schema violation within a dataset."""
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    record_id: Optional[str] = None

    def __str__(self) -> str:
        loc_parts = []
        if self.file_path:
            loc_parts.append(self.file_path)
            if self.line_number is not None:
                loc_parts.append(str(self.line_number))
        loc_str = ":".join(loc_parts)

        prefix = f"[{loc_str}]" if loc_str else "[Dataset]"
        id_str = f" (Record: {self.record_id})" if self.record_id else ""
        return f"{prefix}{id_str} {self.message}"


@dataclass
class DatasetValidationResult:
    """The outcome of a batch dataset validation run."""
    is_valid: bool
    errors: List[DatasetError] = field(default_factory=list)
    lexicon_entries_count: int = 0
    sources_count: int = 0
    files_scanned: List[str] = field(default_factory=list)

    def summary(self) -> str:
        status_text = "PASSED" if self.is_valid else "FAILED"
        return (
            f"Dataset Validation {status_text}: "
            f"{self.lexicon_entries_count} entries, {self.sources_count} sources "
            f"across {len(self.files_scanned)} files. Errors: {len(self.errors)}."
        )


class DatasetValidator:
    """
    Validates collections of JSONL source and lexicon files.
    Gathers all syntax, structural, referential, and verification errors.
    """

    def __init__(
        self,
        reviewer_registry: Optional[Dict[str, ReviewerRegistration]] = None,
    ):
        # Reviewer registry: if None or empty, verification fails closed
        self.reviewer_registry = reviewer_registry

    def validate(
        self,
        lexicon_paths: List[Union[str, Path]],
        source_paths: List[Union[str, Path]],
    ) -> DatasetValidationResult:
        """
        Executes a full batch validation across all specified source and lexicon files.

        All errors are aggregated into the returned result without halting early.
        """
        errors: List[DatasetError] = []
        files_scanned: List[str] = []

        sources_registry: Dict[str, SourceRecord] = {}
        source_id_locations: Dict[str, Tuple[str, int]] = {}

        entry_id_locations: Dict[str, Tuple[str, int]] = {}
        example_id_locations: Dict[str, Tuple[str, int, str]] = {}
        review_id_locations: Dict[str, Tuple[str, int, str]] = {}

        lexicon_records: List[LoadedRecord] = []
        all_entry_ids: Set[str] = set()

        # ---------------------------------------------------------
        # Phase 1: Load and Validate Source Files
        # ---------------------------------------------------------
        for src_path in source_paths:
            path_str = str(src_path)
            files_scanned.append(path_str)

            loaded_src_records, load_errors = load_jsonl_file(src_path, raise_on_error=False)
            for le in load_errors:
                errors.append(DatasetError(message=le, file_path=path_str))

            for rec in loaded_src_records:
                src_data = rec.data
                source_id = src_data.get("source_id")

                # Check duplicate source IDs across files
                if source_id:
                    if source_id in source_id_locations:
                        prev_file, prev_line = source_id_locations[source_id]
                        errors.append(
                            DatasetError(
                                message=(
                                    f"Duplicate source_id '{source_id}' detected. "
                                    f"First defined at {prev_file}:{prev_line}."
                                ),
                                file_path=rec.file_path,
                                line_number=rec.line_number,
                                record_id=source_id,
                            )
                        )
                    else:
                        source_id_locations[source_id] = (rec.file_path, rec.line_number)

                # Validate source record structure
                temp_validator = LexiconValidator()
                src_val_errors = temp_validator.validate_source_record(src_data)
                for sve in src_val_errors:
                    errors.append(
                        DatasetError(
                            message=sve,
                            file_path=rec.file_path,
                            line_number=rec.line_number,
                            record_id=source_id,
                        )
                    )

                if not src_val_errors and source_id:
                    coerced_src = temp_validator._coerce_source(src_data)
                    sources_registry[source_id] = coerced_src

        # ---------------------------------------------------------
        # Phase 2: Load Lexicon Files and Index Entry IDs
        # ---------------------------------------------------------
        for lex_path in lexicon_paths:
            path_str = str(lex_path)
            files_scanned.append(path_str)

            loaded_lex_records, load_errors = load_jsonl_file(lex_path, raise_on_error=False)
            for le in load_errors:
                errors.append(DatasetError(message=le, file_path=path_str))

            for rec in loaded_lex_records:
                lexicon_records.append(rec)
                entry_id = rec.data.get("id")

                if entry_id:
                    if entry_id in entry_id_locations:
                        prev_file, prev_line = entry_id_locations[entry_id]
                        errors.append(
                            DatasetError(
                                message=(
                                    f"Duplicate entry ID '{entry_id}' detected across files. "
                                    f"First defined at {prev_file}:{prev_line}."
                                ),
                                file_path=rec.file_path,
                                line_number=rec.line_number,
                                record_id=entry_id,
                            )
                        )
                    else:
                        entry_id_locations[entry_id] = (rec.file_path, rec.line_number)
                        all_entry_ids.add(entry_id)

        # ---------------------------------------------------------
        # Phase 3: Validate Entries, Examples, Reviews & Evidence
        # ---------------------------------------------------------
        # Instantiate validator with gathered sources and reviewer registry
        validator = LexiconValidator(
            sources_registry=sources_registry,
            reviewer_registry=self.reviewer_registry,
        )

        for rec in lexicon_records:
            entry_data = rec.data
            entry_id = entry_data.get("id")

            # Check example ID uniqueness across files
            for s_idx, sense in enumerate(entry_data.get("senses", []), start=1):
                if isinstance(sense, dict):
                    for ex in sense.get("examples", []):
                        if isinstance(ex, dict) and ex.get("example_id"):
                            ex_id = ex["example_id"]
                            if ex_id in example_id_locations:
                                prev_file, prev_line, prev_entry = example_id_locations[ex_id]
                                errors.append(
                                    DatasetError(
                                        message=(
                                            f"Duplicate example_id '{ex_id}' detected. "
                                            f"First defined at {prev_file}:{prev_line} in entry '{prev_entry}'."
                                        ),
                                        file_path=rec.file_path,
                                        line_number=rec.line_number,
                                        record_id=entry_id,
                                    )
                                )
                            else:
                                example_id_locations[ex_id] = (rec.file_path, rec.line_number, entry_id or "")

            # Check review ID uniqueness across files
            prov = entry_data.get("provenance", {})
            if isinstance(prov, dict):
                for rev in prov.get("reviews", []):
                    if isinstance(rev, dict) and rev.get("review_id"):
                        rev_id = rev["review_id"]
                        if rev_id in review_id_locations:
                            prev_file, prev_line, prev_entry = review_id_locations[rev_id]
                            errors.append(
                                DatasetError(
                                    message=(
                                        f"Duplicate review_id '{rev_id}' detected. "
                                        f"First defined at {prev_file}:{prev_line} in entry '{prev_entry}'."
                                    ),
                                    file_path=rec.file_path,
                                    line_number=rec.line_number,
                                    record_id=entry_id,
                                )
                            )
                        else:
                            review_id_locations[rev_id] = (rec.file_path, rec.line_number, entry_id or "")

            # Validate entry structure, schema, enums, verification, fixture rejection
            entry_errors = validator.validate_entry(entry_data, check_cross_refs=False)
            for ee in entry_errors:
                # Avoid re-adding duplicate entry_id error since Phase 2 already reported it with location
                if "Duplicate entry ID detected across dataset" in ee:
                    continue
                errors.append(
                    DatasetError(
                        message=ee,
                        file_path=rec.file_path,
                        line_number=rec.line_number,
                        record_id=entry_id,
                    )
                )

        # ---------------------------------------------------------
        # Phase 4: Referential Integrity for Cross-References
        # ---------------------------------------------------------
        for rec in lexicon_records:
            entry_data = rec.data
            entry_id = entry_data.get("id")
            for xref in entry_data.get("cross_references", []):
                if isinstance(xref, dict):
                    target_id = xref.get("target_entry_id")
                    if target_id and target_id not in all_entry_ids:
                        errors.append(
                            DatasetError(
                                message=(
                                    f"Cross-reference target '{target_id}' does not exist "
                                    f"anywhere in the dataset."
                                ),
                                file_path=rec.file_path,
                                line_number=rec.line_number,
                                record_id=entry_id,
                            )
                        )

        is_valid = len(errors) == 0
        return DatasetValidationResult(
            is_valid=is_valid,
            errors=errors,
            lexicon_entries_count=len(lexicon_records),
            sources_count=len(sources_registry),
            files_scanned=files_scanned,
        )


def validate_dataset_files(
    lexicon_paths: List[Union[str, Path]],
    source_paths: List[Union[str, Path]],
    reviewer_registry: Optional[Dict[str, ReviewerRegistration]] = None,
) -> DatasetValidationResult:
    """Convenience functional interface to validate dataset files."""
    validator = DatasetValidator(reviewer_registry=reviewer_registry)
    return validator.validate(lexicon_paths=lexicon_paths, source_paths=source_paths)
