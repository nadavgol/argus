import json

import pytest

from nhi_engine.schema import RawSchemaError, load_raw_records, parse_raw_record


def test_parse_minimal_record():
    record = parse_raw_record({"id": "1", "name": "a", "source": "aws"})
    assert record.id == "1"
    assert record.name == "a"
    assert record.source == "aws"
    assert record.interactive_login is None
    assert record.metadata == {}


def test_parse_full_record():
    raw = {
        "id": "1",
        "name": "a",
        "source": "aws",
        "created": "2025-01-01T00:00:00Z",
        "last_used": "2026-01-01T00:00:00Z",
        "principal_kind": "iam_role",
        "interactive_login": False,
        "mfa_enabled": None,
        "credential_type": "access_key",
        "is_break_glass": False,
        "is_shared_admin": False,
        "naming_hint": "lambda-exec",
        "metadata": {"arn": "arn:aws:iam::111122223333:role/x"},
    }
    record = parse_raw_record(raw)
    assert record.principal_kind == "iam_role"
    assert record.interactive_login is False
    assert record.metadata["arn"].startswith("arn:aws")


@pytest.mark.parametrize("missing_field", ["id", "name", "source"])
def test_missing_required_field_raises(missing_field):
    raw = {"id": "1", "name": "a", "source": "aws"}
    del raw[missing_field]
    with pytest.raises(RawSchemaError):
        parse_raw_record(raw)


def test_non_dict_record_raises():
    with pytest.raises(RawSchemaError):
        parse_raw_record("not a dict")


def test_bad_metadata_type_raises():
    with pytest.raises(RawSchemaError):
        parse_raw_record({"id": "1", "name": "a", "source": "aws", "metadata": "nope"})


def test_bad_bool_field_raises():
    with pytest.raises(RawSchemaError):
        parse_raw_record({"id": "1", "name": "a", "source": "aws", "interactive_login": "yes"})


def test_load_raw_records_from_file(tmp_path):
    path = tmp_path / "raw.json"
    path.write_text(json.dumps([{"id": "1", "name": "a", "source": "aws"}]))
    records = load_raw_records(path)
    assert len(records) == 1
    assert records[0].id == "1"


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(RawSchemaError):
        load_raw_records(tmp_path / "does_not_exist.json")


def test_load_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json")
    with pytest.raises(RawSchemaError):
        load_raw_records(path)


def test_load_non_array_top_level_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"not": "an array"}))
    with pytest.raises(RawSchemaError):
        load_raw_records(path)
