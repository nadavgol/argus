from __future__ import annotations

import time

import pytest

from gui.model import InventoryModel
from gui.schema import load_inventory


@pytest.fixture
def model(small_inventory_path):
    inventory = load_inventory(small_inventory_path)
    return InventoryModel(inventory.records)


def test_sources_and_subclasses_are_distinct_and_sorted(model):
    assert model.sources() == ["ad", "aws", "entra", "kubernetes"]
    assert "iam_role" in model.subclasses()
    assert model.subclasses() == sorted(model.subclasses())


def test_filter_by_source(model):
    results = model.query(sources={"aws"})
    assert len(results) == 4
    assert all(r.source == "aws" for r in results)


def test_filter_by_subclass(model):
    results = model.query(subclasses={"service_account"})
    assert len(results) == 3
    assert all(r.subclass == "service_account" for r in results)


def test_filter_by_source_and_subclass_combined(model):
    results = model.query(sources={"ad"}, subclasses={"service_account"})
    assert [r.id for r in results] == ["ad-svc-sqlbackup-01"]


def test_search_is_case_insensitive_substring_on_name(model):
    results = model.query(search="JANE")
    assert [r.name for r in results] == ["jane.smith"]

    results = model.query(search="svc")
    assert {r.name for r in results} == {"svc-sqlbackup"}


def test_search_with_no_match_returns_empty(model):
    assert model.query(search="no-such-record-name") == []


def test_no_filters_returns_all_records(model):
    assert len(model.query()) == len(model)


def test_sort_by_name_ascending_and_descending(model):
    asc = model.query(sort_by="name", sort_desc=False)
    desc = model.query(sort_by="name", sort_desc=True)
    assert [r.name for r in asc] == sorted(r.name for r in asc)
    assert [r.name for r in desc] == sorted((r.name for r in desc), reverse=True)


def test_sort_by_last_used(model):
    results = model.query(sort_by="last_used", sort_desc=True)
    values = [r.last_used for r in results]
    assert values == sorted(values, reverse=True)


def test_unknown_sort_column_raises(model):
    with pytest.raises(ValueError):
        model.query(sort_by="not_a_real_column")


def test_combined_filter_and_search(model):
    results = model.query(sources={"aws"}, search="role")
    assert {r.id for r in results} == {
        "aws-role-lambda-exec-01",
        "aws-role-readonly-analyst-01",
    }


def test_10000_record_fixture_loads_and_queries_under_2_seconds(large_inventory_path):
    start = time.perf_counter()
    inventory = load_inventory(large_inventory_path)
    big_model = InventoryModel(inventory.records)

    assert len(big_model) == 10_000

    # Exercise a representative combination of filter + search + sort, the
    # same shape of query the table view issues on every keystroke.
    big_model.query(sources={"aws"}, search="iam", sort_by="last_used", sort_desc=True)
    big_model.query()
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"loading + querying 10,000 records took {elapsed:.3f}s"
