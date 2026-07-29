"""Inventory JSON loading and validation.

This module is the only place that touches the on-disk inventory format.
It never opens a socket; it only reads a local file the caller points it at.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = "1.0"

TYPE_NHI = "nhi"
TYPE_HUMAN = "human"
VALID_TYPES = (TYPE_NHI, TYPE_HUMAN)

REQUIRED_RECORD_FIELDS = (
    "id",
    "name",
    "type",
    "subclass",
    "source",
    "created",
    "last_used",
    "classification_reason",
)


class SchemaError(Exception):
    """Base class for all inventory-loading errors.

    Every message is written to be shown directly in the GUI's error
    dialog, not just logged, so it must stay human-readable.
    """


class SchemaVersionError(SchemaError):
    def __init__(self, found: str, expected: str = SUPPORTED_SCHEMA_VERSION):
        self.found = found
        self.expected = expected
        super().__init__(
            f"Inventory file uses schema version '{found}', but this GUI "
            f"supports version '{expected}'. Re-run the collector that "
            f"produced this file with a matching ARGUS version, or open a "
            f"compatible inventory file."
        )


class InventoryValidationError(SchemaError):
    pass


class InventoryFileError(SchemaError):
    pass


@dataclass(frozen=True)
class InventoryRecord:
    id: str
    name: str
    type: str
    subclass: str
    source: str
    created: str
    last_used: str
    classification_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_human(self) -> bool:
        return self.type == TYPE_HUMAN

    @property
    def is_selectable(self) -> bool:
        """Human-classified records are visible but never onboardable."""
        return self.type == TYPE_NHI


@dataclass(frozen=True)
class InventoryFile:
    schema_version: str
    source_path: str
    records: tuple[InventoryRecord, ...]


def _require_str(value: Any, field_name: str, record_index: int) -> str:
    if not isinstance(value, str) or not value:
        raise InventoryValidationError(
            f"Record {record_index}: field '{field_name}' must be a "
            f"non-empty string, got {value!r}."
        )
    return value


def _parse_record(raw: dict[str, Any], index: int) -> InventoryRecord:
    if not isinstance(raw, dict):
        raise InventoryValidationError(
            f"Record {index}: expected an object, got {type(raw).__name__}."
        )

    missing = [f for f in REQUIRED_RECORD_FIELDS if f not in raw]
    if missing:
        raise InventoryValidationError(
            f"Record {index}: missing required field(s): {', '.join(missing)}."
        )

    record_id = _require_str(raw["id"], "id", index)
    name = _require_str(raw["name"], "name", index)
    rtype = _require_str(raw["type"], "type", index)
    if rtype not in VALID_TYPES:
        raise InventoryValidationError(
            f"Record {index} ('{record_id}'): field 'type' must be one of "
            f"{VALID_TYPES}, got {rtype!r}."
        )
    subclass = _require_str(raw["subclass"], "subclass", index)
    source = _require_str(raw["source"], "source", index)
    created = _require_str(raw["created"], "created", index)
    last_used = _require_str(raw["last_used"], "last_used", index)
    classification_reason = _require_str(
        raw["classification_reason"], "classification_reason", index
    )
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise InventoryValidationError(
            f"Record {index} ('{record_id}'): field 'metadata' must be an "
            f"object, got {type(metadata).__name__}."
        )

    return InventoryRecord(
        id=record_id,
        name=name,
        type=rtype,
        subclass=subclass,
        source=source,
        created=created,
        last_used=last_used,
        classification_reason=classification_reason,
        metadata=metadata,
    )


def load_inventory(
    path: str | Path, *, expected_version: str = SUPPORTED_SCHEMA_VERSION
) -> InventoryFile:
    """Load and validate an inventory JSON file from local disk.

    Raises SchemaVersionError on a schema version mismatch and
    InventoryValidationError / InventoryFileError on any other malformed
    input. Never raises a raw exception from json or the filesystem layer -
    every failure is converted into a SchemaError subclass with a message
    fit to show a user.
    """
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InventoryFileError(f"Inventory file not found: {path}") from exc
    except OSError as exc:
        raise InventoryFileError(f"Could not read inventory file '{path}': {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise InventoryFileError(
            f"'{path}' is not valid JSON (line {exc.lineno}, col {exc.colno}): {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise InventoryValidationError(
            f"'{path}' must contain a JSON object at the top level, got "
            f"{type(data).__name__}."
        )

    if "schema_version" not in data:
        raise InventoryValidationError(
            f"'{path}' is missing the required 'schema_version' field."
        )
    schema_version = data["schema_version"]
    if not isinstance(schema_version, str):
        raise InventoryValidationError(
            "'schema_version' must be a string, got "
            f"{type(schema_version).__name__}."
        )
    if schema_version != expected_version:
        raise SchemaVersionError(found=schema_version, expected=expected_version)

    raw_records = data.get("records")
    if not isinstance(raw_records, list):
        raise InventoryValidationError(
            f"'{path}' is missing a 'records' array."
        )

    records = tuple(_parse_record(r, i) for i, r in enumerate(raw_records))

    return InventoryFile(
        schema_version=schema_version,
        source_path=str(path),
        records=records,
    )
