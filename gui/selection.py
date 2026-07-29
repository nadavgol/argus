"""Onboarding selection state, default safe/platform mapping, and export.

The GUI never onboards anything itself - this module only builds an
in-memory selection and serializes it to selection.json. Running the
onboarder against that file is the CLI's job.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from gui.schema import InventoryFile, InventoryRecord

SELECTION_SCHEMA_VERSION = "1.0"

# Default CyberArk platform per collector source. This is the "default
# mapping rule" called for in the issue's open question: every NHI gets a
# sensible platform/safe assignment out of the box, and a consultant can
# still override either field per-record in the Selection view before
# export. Records are never force-required to have an explicit assignment.
DEFAULT_PLATFORM_BY_SOURCE = {
    "aws": "AWS Access Keys",
    "entra": "Azure Service Principal",
    "ad": "Windows Domain Account",
    "kubernetes": "Kubernetes ServiceAccount",
}
DEFAULT_PLATFORM_FALLBACK = "Generic Account"


class SelectionError(Exception):
    pass


def default_safe_name(record: InventoryRecord) -> str:
    return f"{record.source.upper()}-{record.subclass.upper()}"


def default_platform(record: InventoryRecord) -> str:
    return DEFAULT_PLATFORM_BY_SOURCE.get(record.source, DEFAULT_PLATFORM_FALLBACK)


@dataclass
class _SelectionEntry:
    safe: str
    platform: str


class SelectionState:
    """Tracks which records are selected for onboarding and their
    per-record safe/platform assignment.
    """

    def __init__(self, records: Iterable[InventoryRecord]):
        self._records_by_id: dict[str, InventoryRecord] = {r.id: r for r in records}
        self._selected: dict[str, _SelectionEntry] = {}

    def _record(self, record_id: str) -> InventoryRecord:
        try:
            return self._records_by_id[record_id]
        except KeyError:
            raise SelectionError(f"Unknown record id: {record_id!r}") from None

    def select(self, record_id: str) -> None:
        record = self._record(record_id)
        if not record.is_selectable:
            raise SelectionError(
                f"Record {record_id!r} is human-classified and cannot be "
                f"selected for onboarding."
            )
        if record_id not in self._selected:
            self._selected[record_id] = _SelectionEntry(
                safe=default_safe_name(record),
                platform=default_platform(record),
            )

    def deselect(self, record_id: str) -> None:
        self._selected.pop(record_id, None)

    def deselect_all(self) -> None:
        self._selected.clear()

    def select_many(self, records: Iterable[InventoryRecord]) -> int:
        """Bulk-select by filter result. Silently skips human records so a
        'select all filtered' action never has to know about eligibility
        rules. Returns the number newly selected.
        """
        added = 0
        for record in records:
            if not record.is_selectable:
                continue
            if record.id not in self._selected:
                self._selected[record.id] = _SelectionEntry(
                    safe=default_safe_name(record),
                    platform=default_platform(record),
                )
                added += 1
        return added

    def is_selected(self, record_id: str) -> bool:
        return record_id in self._selected

    @property
    def selected_ids(self) -> list[str]:
        return list(self._selected.keys())

    @property
    def count(self) -> int:
        return len(self._selected)

    def set_safe(self, record_id: str, safe: str) -> None:
        if record_id not in self._selected:
            raise SelectionError(f"Record {record_id!r} is not selected.")
        if not safe:
            raise SelectionError("Safe name must not be empty.")
        self._selected[record_id].safe = safe

    def set_platform(self, record_id: str, platform: str) -> None:
        if record_id not in self._selected:
            raise SelectionError(f"Record {record_id!r} is not selected.")
        if not platform:
            raise SelectionError("Platform must not be empty.")
        self._selected[record_id].platform = platform

    def get_safe(self, record_id: str) -> str:
        return self._selected[record_id].safe

    def get_platform(self, record_id: str) -> str:
        return self._selected[record_id].platform

    def to_export_dicts(self) -> list[dict[str, str]]:
        return [
            {"id": record_id, "safe": entry.safe, "platform": entry.platform}
            for record_id, entry in self._selected.items()
        ]

    def export(self, path: str | Path, inventory: InventoryFile) -> dict:
        """Write selection.json and return a summary dict describing what
        was written (used both by the Export view and by tests).
        """
        selections = self.to_export_dicts()
        payload = {
            "schema_version": SELECTION_SCHEMA_VERSION,
            "source_inventory_schema_version": inventory.schema_version,
            "source_inventory_path": inventory.source_path,
            "generated_at": datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "selections": selections,
        }
        Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        by_source: dict[str, int] = {}
        for record_id in self._selected:
            source = self._records_by_id[record_id].source
            by_source[source] = by_source.get(source, 0) + 1

        return {
            "path": str(path),
            "count": len(selections),
            "by_source": by_source,
        }
