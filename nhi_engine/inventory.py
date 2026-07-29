"""Build classified-inventory JSON output.

The output shape intentionally matches the inventory schema already
implemented and tested by the GUI (issue #7, gui/schema.py): top-level
`schema_version` + `records[]`, each record carrying
id/name/type/subclass/source/created/last_used/classification_reason/
metadata. Field names and the schema version string ("1.0") are kept
identical on purpose so a file written by this engine loads directly in
that GUI once both land on main.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nhi_engine.classifier import ClassificationResult, classify
from nhi_engine.schema import RawIdentityRecord

SCHEMA_VERSION = "1.0"


def build_record(raw: RawIdentityRecord, result: ClassificationResult) -> dict[str, Any]:
    return {
        "id": raw.id,
        "name": raw.name,
        "type": result.type,
        "subclass": result.subclass,
        "source": raw.source,
        "created": raw.created,
        "last_used": raw.last_used,
        "classification_reason": result.classification_reason,
        "metadata": raw.metadata,
    }


def build_inventory(records: list[RawIdentityRecord]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "records": [build_record(r, classify(r)) for r in records],
    }


def write_inventory(records: list[RawIdentityRecord], out_path: str | Path) -> None:
    inventory = build_inventory(records)
    out_path = Path(out_path)
    out_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
