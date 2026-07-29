"""Raw identity record schema: the classifier's input format.

This is the pre-classification shape a collector (AWS IAM, Entra, AD,
Kubernetes, ...) is expected to emit: identity facts and observed signals,
but no human/nhi verdict yet. The classifier (classifier.py) turns these
into classified records matching the shared inventory schema.

No such raw/pre-classification format exists elsewhere in this repo (the
DiscoveryTool spec in issue #10 has each collector assign its own type
directly), so this module defines it for the classifier's own use. Any
collector that wants to use this engine's classification logic - rather
than its own inline rule, as issue #10's AWS collector does - can produce
this shape.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class RawSchemaError(Exception):
    """Raised for any malformed raw-input file or record."""


@dataclass(frozen=True)
class RawIdentityRecord:
    id: str
    name: str
    source: str
    created: str | None = None
    last_used: str | None = None
    principal_kind: str | None = None
    interactive_login: bool | None = None
    mfa_enabled: bool | None = None
    credential_type: str | None = None
    is_break_glass: bool = False
    is_shared_admin: bool = False
    naming_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _require_str(value: Any, field_name: str, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise RawSchemaError(
            f"Record {index}: field '{field_name}' must be a non-empty "
            f"string, got {value!r}."
        )
    return value


def _optional_str(value: Any, field_name: str, index: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RawSchemaError(
            f"Record {index}: field '{field_name}' must be a string or "
            f"null, got {type(value).__name__}."
        )
    return value


def _optional_bool(value: Any, field_name: str, index: int) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise RawSchemaError(
            f"Record {index}: field '{field_name}' must be a boolean or "
            f"null, got {type(value).__name__}."
        )
    return value


def parse_raw_record(raw: dict[str, Any], index: int = 0) -> RawIdentityRecord:
    if not isinstance(raw, dict):
        raise RawSchemaError(
            f"Record {index}: expected an object, got {type(raw).__name__}."
        )

    record_id = _require_str(raw.get("id"), "id", index)
    name = _require_str(raw.get("name"), "name", index)
    source = _require_str(raw.get("source"), "source", index)

    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise RawSchemaError(
            f"Record {index} ('{record_id}'): field 'metadata' must be an "
            f"object, got {type(metadata).__name__}."
        )

    return RawIdentityRecord(
        id=record_id,
        name=name,
        source=source,
        created=_optional_str(raw.get("created"), "created", index),
        last_used=_optional_str(raw.get("last_used"), "last_used", index),
        principal_kind=_optional_str(raw.get("principal_kind"), "principal_kind", index),
        interactive_login=_optional_bool(
            raw.get("interactive_login"), "interactive_login", index
        ),
        mfa_enabled=_optional_bool(raw.get("mfa_enabled"), "mfa_enabled", index),
        credential_type=_optional_str(
            raw.get("credential_type"), "credential_type", index
        ),
        is_break_glass=bool(raw.get("is_break_glass", False)),
        is_shared_admin=bool(raw.get("is_shared_admin", False)),
        naming_hint=_optional_str(raw.get("naming_hint"), "naming_hint", index),
        metadata=metadata,
    )


def load_raw_records(path: str | Path) -> list[RawIdentityRecord]:
    """Load and validate a JSON array of raw identity records from disk."""
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RawSchemaError(f"Raw input file not found: {path}") from exc
    except OSError as exc:
        raise RawSchemaError(f"Could not read raw input file '{path}': {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RawSchemaError(
            f"'{path}' is not valid JSON (line {exc.lineno}, col {exc.colno}): {exc.msg}"
        ) from exc

    if not isinstance(data, list):
        raise RawSchemaError(
            f"'{path}' must contain a JSON array at the top level, got "
            f"{type(data).__name__}."
        )

    return [parse_raw_record(item, i) for i, item in enumerate(data)]
