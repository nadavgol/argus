from pathlib import Path

from nhi_engine.inventory import build_inventory
from nhi_engine.schema import load_raw_records

FIXTURE = Path(__file__).parent.parent / "testdata" / "raw_identities_small.json"

EXPECTED_TYPES = {
    "aws-user-jsmith-01": "human",
    "aws-role-lambda-exec-01": "nhi",
    "k8s-sa-payments-01": "nhi",
    "ad-svc-backup-01": "nhi",
    "generic-break-glass-01": "human",
    "generic-mystery-01": "nhi",
}


def test_fixture_classifies_as_expected():
    records = load_raw_records(FIXTURE)
    inventory = build_inventory(records)
    by_id = {r["id"]: r for r in inventory["records"]}

    assert set(by_id) == set(EXPECTED_TYPES)
    for record_id, expected_type in EXPECTED_TYPES.items():
        assert by_id[record_id]["type"] == expected_type, record_id

    assert by_id["generic-mystery-01"]["subclass"] == "unclassified"
