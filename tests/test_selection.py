from __future__ import annotations

import json

import pytest

from gui.schema import load_inventory
from gui.selection import (
    SelectionError,
    SelectionState,
    default_platform,
    default_safe_name,
)


@pytest.fixture
def inventory(small_inventory_path):
    return load_inventory(small_inventory_path)


@pytest.fixture
def state(inventory):
    return SelectionState(inventory.records)


def _record(inventory, record_id):
    return next(r for r in inventory.records if r.id == record_id)


def test_default_mapping_rule_by_source(inventory):
    aws_record = _record(inventory, "aws-role-lambda-exec-01")
    assert default_safe_name(aws_record) == "AWS-IAM_ROLE"
    assert default_platform(aws_record) == "AWS Access Keys"

    entra_record = _record(inventory, "entra-sp-billing-sync-01")
    assert default_platform(entra_record) == "Azure Service Principal"

    ad_record = _record(inventory, "ad-svc-sqlbackup-01")
    assert default_platform(ad_record) == "Windows Domain Account"

    k8s_record = _record(inventory, "k8s-sa-payments-worker-01")
    assert default_platform(k8s_record) == "Kubernetes ServiceAccount"


def test_select_and_deselect(state, inventory):
    record_id = "aws-role-lambda-exec-01"
    assert state.is_selected(record_id) is False

    state.select(record_id)
    assert state.is_selected(record_id) is True
    assert state.count == 1

    state.deselect(record_id)
    assert state.is_selected(record_id) is False
    assert state.count == 0


def test_selecting_human_record_raises(state):
    with pytest.raises(SelectionError):
        state.select("aws-user-jsmith-01")
    assert state.count == 0


def test_select_many_skips_human_records(state, inventory):
    added = state.select_many(inventory.records)
    human_ids = {r.id for r in inventory.records if r.is_human}
    nhi_ids = {r.id for r in inventory.records if r.is_selectable}

    assert added == len(nhi_ids)
    assert set(state.selected_ids) == nhi_ids
    assert human_ids.isdisjoint(state.selected_ids)


def test_set_safe_and_platform_override(state):
    record_id = "aws-role-lambda-exec-01"
    state.select(record_id)
    state.set_safe(record_id, "Custom-Safe-01")
    state.set_platform(record_id, "Custom Platform")
    assert state.get_safe(record_id) == "Custom-Safe-01"
    assert state.get_platform(record_id) == "Custom Platform"


def test_set_safe_requires_record_to_be_selected_first(state):
    with pytest.raises(SelectionError):
        state.set_safe("aws-role-lambda-exec-01", "whatever")


def test_set_safe_rejects_empty_value(state):
    record_id = "aws-role-lambda-exec-01"
    state.select(record_id)
    with pytest.raises(SelectionError):
        state.set_safe(record_id, "")


def test_deselect_all(state, inventory):
    state.select_many(inventory.records)
    assert state.count > 0
    state.deselect_all()
    assert state.count == 0


def test_export_round_trips_selected_ids_no_humans_safe_platform_populated(
    state, inventory, tmp_path
):
    state.select_many(inventory.records)
    override_id = "entra-sp-terraform-ci-01"
    state.set_safe(override_id, "Custom-Safe")
    state.set_platform(override_id, "Custom Platform")

    out_path = tmp_path / "selection.json"
    summary = state.export(out_path, inventory)

    assert summary["count"] == state.count
    assert out_path.exists()

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["schema_version"]
    assert written["source_inventory_schema_version"] == inventory.schema_version

    selections = written["selections"]
    written_ids = {entry["id"] for entry in selections}

    # every selected id present
    assert written_ids == set(state.selected_ids)

    # no human records included
    human_ids = {r.id for r in inventory.records if r.is_human}
    assert written_ids.isdisjoint(human_ids)

    # safe/platform populated for each
    for entry in selections:
        assert entry["safe"]
        assert entry["platform"]

    overridden = next(e for e in selections if e["id"] == override_id)
    assert overridden["safe"] == "Custom-Safe"
    assert overridden["platform"] == "Custom Platform"


def test_export_summary_counts_by_source(state, inventory, tmp_path):
    state.select("aws-role-lambda-exec-01")
    state.select("aws-role-readonly-analyst-01")
    state.select("entra-sp-billing-sync-01")

    summary = state.export(tmp_path / "selection.json", inventory)
    assert summary["by_source"] == {"aws": 2, "entra": 1}
