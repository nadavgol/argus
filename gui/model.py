"""Pure in-memory query logic over a loaded inventory.

No I/O, no tkinter here - this module is what makes the inventory table
sortable, filterable, and searchable, and it is the part of the GUI most
worth unit-testing directly (including for performance against a
10,000-record fixture).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from gui.schema import InventoryRecord

SORT_COLUMNS = (
    "name",
    "type",
    "subclass",
    "source",
    "created",
    "last_used",
    "classification_reason",
)


@dataclass(frozen=True)
class _Indexed:
    record: InventoryRecord
    name_lower: str


class InventoryModel:
    """Queryable, sortable, filterable view over a fixed set of records.

    Construction is O(n) and query() is O(n log n) worst case (when
    sorting); both are cheap enough to stay well under the 2s budget for
    10,000 records on every keystroke of a search box.
    """

    def __init__(self, records: Iterable[InventoryRecord]):
        self._indexed: tuple[_Indexed, ...] = tuple(
            _Indexed(record=r, name_lower=r.name.lower()) for r in records
        )

    def __len__(self) -> int:
        return len(self._indexed)

    @property
    def records(self) -> tuple[InventoryRecord, ...]:
        return tuple(i.record for i in self._indexed)

    def sources(self) -> list[str]:
        return sorted({i.record.source for i in self._indexed})

    def subclasses(self) -> list[str]:
        return sorted({i.record.subclass for i in self._indexed})

    def query(
        self,
        *,
        sources: set[str] | None = None,
        subclasses: set[str] | None = None,
        search: str = "",
        sort_by: str = "name",
        sort_desc: bool = False,
    ) -> list[InventoryRecord]:
        """Return records matching the given filters, sorted by column.

        sources / subclasses: when non-empty, only records whose source or
        subclass is in the given set are included (None or empty means "no
        filter" for that dimension).
        search: case-insensitive substring match against record name.
        sort_by: one of SORT_COLUMNS.
        """
        if sort_by not in SORT_COLUMNS:
            raise ValueError(f"Unknown sort column: {sort_by!r}")

        needle = search.strip().lower()
        source_filter = sources or None
        subclass_filter = subclasses or None

        matches = []
        for item in self._indexed:
            r = item.record
            if source_filter is not None and r.source not in source_filter:
                continue
            if subclass_filter is not None and r.subclass not in subclass_filter:
                continue
            if needle and needle not in item.name_lower:
                continue
            matches.append(r)

        matches.sort(key=lambda r: getattr(r, sort_by), reverse=sort_desc)
        return matches
