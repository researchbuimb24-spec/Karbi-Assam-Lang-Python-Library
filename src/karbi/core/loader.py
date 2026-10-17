"""
JSONL Loader for Karbi Language Library (`karbi.core.loader`)
=============================================================

Safely reads UTF-8 JSON Lines (.jsonl) files.
Enforces line-by-line JSON object parsing, tracks source files and line numbers,
and reports all syntax and structural file errors without silent failure.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class JSONLLoadError(Exception):
    """Raised when a JSONL file cannot be read or parsed."""
    def __init__(self, file_path: str, message: str, line_number: Optional[int] = None):
        self.file_path = str(file_path)
        self.line_number = line_number
        self.message = message
        location = f"{self.file_path}:{self.line_number}" if line_number is not None else self.file_path
        super().__init__(f"[{location}] {message}")


@dataclass
class LoadedRecord:
    """A single JSON object record loaded from a JSONL file with location provenance."""
    data: Dict[str, Any]
    file_path: str
    line_number: int


def load_jsonl_file(
    file_path: Union[str, Path],
    raise_on_error: bool = False,
) -> Tuple[List[LoadedRecord], List[str]]:
    """
    Reads a UTF-8 JSONL file and parses each non-empty line as a JSON object.

    Args:
        file_path: Path to the .jsonl file.
        raise_on_error: If True, raises JSONLLoadError on the first error encountered.
                        If False, collects all line errors and returns them in the error list.

    Returns:
        A tuple of (loaded_records, error_messages).
        If errors occurred, loaded_records contains all successfully parsed records,
        and error_messages contains human-readable descriptions of all failed lines.
    """
    path = Path(file_path)
    records: List[LoadedRecord] = []
    errors: List[str] = []

    if not path.exists():
        err_msg = f"[{path}] File not found."
        if raise_on_error:
            raise JSONLLoadError(str(path), "File not found.")
        return [], [err_msg]

    if not path.is_file():
        err_msg = f"[{path}] Path is not a regular file."
        if raise_on_error:
            raise JSONLLoadError(str(path), "Path is not a regular file.")
        return [], [err_msg]

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_number, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                # Skip empty or whitespace-only lines
                if not line:
                    continue

                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as jde:
                    msg = f"[{path}:{line_number}] Invalid JSON syntax: {jde.msg} (col {jde.colno})"
                    errors.append(msg)
                    if raise_on_error:
                        raise JSONLLoadError(str(path), msg, line_number=line_number) from jde
                    continue

                if not isinstance(parsed, dict):
                    msg = (
                        f"[{path}:{line_number}] Record must be a JSON object (dict), "
                        f"found '{type(parsed).__name__}'."
                    )
                    errors.append(msg)
                    if raise_on_error:
                        raise JSONLLoadError(str(path), msg, line_number=line_number)
                    continue

                records.append(
                    LoadedRecord(
                        data=parsed,
                        file_path=str(path),
                        line_number=line_number,
                    )
                )

    except (PermissionError, OSError) as os_err:
        msg = f"[{path}] Cannot read file: {os_err}"
        errors.append(msg)
        if raise_on_error:
            raise JSONLLoadError(str(path), f"Cannot read file: {os_err}") from os_err

    return records, errors
