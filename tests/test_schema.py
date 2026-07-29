from __future__ import annotations

import pytest

from gui.schema import (
    InventoryFileError,
    InventoryValidationError,
    SchemaVersionError,
    load_inventory,
)


def test_load_valid_small_inventory(small_inventory_path):
    inventory = load_inventory(small_inventory_path)
    assert inventory.schema_version == "1.0"
    assert len(inventory.records) == 12

    by_id = {r.id: r for r in inventory.records}
    nhi = by_id["aws-role-lambda-exec-01"]
    assert nhi.type == "nhi"
    assert nhi.is_selectable is True
    assert nhi.is_human is False

    human = by_id["aws-user-jsmith-01"]
    assert human.type == "human"
    assert human.is_selectable is False
    assert human.is_human is True

    assert nhi.metadata["account_id"] == "111122223333"


def test_schema_version_mismatch_is_readable(bad_version_inventory_path):
    with pytest.raises(SchemaVersionError) as excinfo:
        load_inventory(bad_version_inventory_path)
    message = str(excinfo.value)
    assert "0.9" in message
    assert "1.0" in message
    # message must be sentence-like and readable, not a raw traceback dump
    assert "Traceback" not in message


def test_malformed_json_raises_readable_error_not_crash(malformed_inventory_path):
    with pytest.raises(InventoryFileError) as excinfo:
        load_inventory(malformed_inventory_path)
    assert "not valid JSON" in str(excinfo.value)


def test_missing_file_raises_readable_error(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(InventoryFileError) as excinfo:
        load_inventory(missing)
    assert "not found" in str(excinfo.value)


def test_invalid_record_missing_field_is_readable(invalid_record_inventory_path):
    with pytest.raises(InventoryValidationError) as excinfo:
        load_inventory(invalid_record_inventory_path)
    message = str(excinfo.value)
    assert "last_used" in message
    assert "classification_reason" in message


def test_top_level_not_an_object(tmp_path):
    path = tmp_path / "list_at_top.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(InventoryValidationError):
        load_inventory(path)


def test_record_with_invalid_type_value(tmp_path):
    path = tmp_path / "bad_type.json"
    path.write_text(
        """
        {
          "schema_version": "1.0",
          "records": [
            {
              "id": "x", "name": "x", "type": "robot", "subclass": "x",
              "source": "aws", "created": "2025-01-01T00:00:00Z",
              "last_used": "2025-01-01T00:00:00Z",
              "classification_reason": "x"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(InventoryValidationError) as excinfo:
        load_inventory(path)
    assert "type" in str(excinfo.value)
