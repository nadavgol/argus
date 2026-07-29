"""Deterministically regenerate testdata/inventory_10000.json.

Run with: python3 testdata/generate_large_fixture.py
The output is committed to the repo so tests don't depend on regenerating
it; re-run this script only if the fixture needs to change.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

RECORD_COUNT = 10_000
SEED = 20260729

SOURCES_AND_SUBCLASSES = {
    "aws": ["iam_role", "iam_user"],
    "entra": ["service_principal", "user"],
    "ad": ["service_account", "computer_account", "user"],
    "kubernetes": ["service_account"],
}
HUMAN_SUBCLASSES = {"user"}


def build_record(index: int, rng: random.Random) -> dict:
    source = rng.choice(list(SOURCES_AND_SUBCLASSES.keys()))
    subclass = rng.choice(SOURCES_AND_SUBCLASSES[source])
    is_human = subclass in HUMAN_SUBCLASSES and rng.random() < 0.5
    record_type = "human" if is_human else "nhi"

    created_year = rng.randint(2019, 2025)
    created_month = rng.randint(1, 12)
    created_day = rng.randint(1, 28)
    last_used_year = rng.randint(created_year, 2026)
    last_used_month = rng.randint(1, 12)
    last_used_day = rng.randint(1, 28)

    name = f"{source}-{subclass}-{index:06d}"
    reason = (
        "Interactive sign-in events observed."
        if is_human
        else f"No interactive sign-in events; matches {subclass} naming convention."
    )

    return {
        "id": f"{source}-{subclass}-{index:06d}",
        "name": name,
        "type": record_type,
        "subclass": subclass,
        "source": source,
        "created": f"{created_year:04d}-{created_month:02d}-{created_day:02d}T00:00:00Z",
        "last_used": f"{last_used_year:04d}-{last_used_month:02d}-{last_used_day:02d}T00:00:00Z",
        "classification_reason": reason,
        "metadata": {
            "index": index,
            "synthetic": True,
        },
    }


def main() -> None:
    rng = random.Random(SEED)
    records = [build_record(i, rng) for i in range(RECORD_COUNT)]
    payload = {"schema_version": "1.0", "records": records}

    out_path = Path(__file__).parent / "inventory_10000.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
