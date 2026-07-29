import json

from nhi_engine.inventory import SCHEMA_VERSION, build_inventory, write_inventory
from nhi_engine.schema import RawIdentityRecord

REQUIRED_RECORD_FIELDS = (
    "id",
    "name",
    "type",
    "subclass",
    "source",
    "created",
    "last_used",
    "classification_reason",
    "metadata",
)


def test_build_inventory_schema_version():
    inventory = build_inventory([])
    assert inventory["schema_version"] == SCHEMA_VERSION == "1.0"
    assert inventory["records"] == []


def test_build_inventory_record_has_all_required_fields():
    record = RawIdentityRecord(id="1", name="a", source="aws", interactive_login=True)
    inventory = build_inventory([record])
    out = inventory["records"][0]
    for field_name in REQUIRED_RECORD_FIELDS:
        assert field_name in out


def test_build_inventory_matches_classification():
    record = RawIdentityRecord(id="1", name="a", source="aws", interactive_login=True)
    out = build_inventory([record])["records"][0]
    assert out["type"] == "human"
    assert out["id"] == "1"
    assert out["source"] == "aws"


def test_write_inventory_produces_valid_json_file(tmp_path):
    record = RawIdentityRecord(
        id="1", name="a", source="aws", principal_kind="iam_role", interactive_login=False
    )
    out_path = tmp_path / "inventory.json"
    write_inventory([record], out_path)

    data = json.loads(out_path.read_text())
    assert data["schema_version"] == "1.0"
    assert len(data["records"]) == 1
    assert data["records"][0]["type"] == "nhi"


def test_write_inventory_metadata_passthrough(tmp_path):
    record = RawIdentityRecord(
        id="1", name="a", source="aws", metadata={"arn": "arn:aws:iam::111122223333:role/x"}
    )
    out_path = tmp_path / "inventory.json"
    write_inventory([record], out_path)
    data = json.loads(out_path.read_text())
    assert data["records"][0]["metadata"]["arn"] == "arn:aws:iam::111122223333:role/x"
