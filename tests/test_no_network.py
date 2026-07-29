"""Asserts the GUI package never performs network I/O.

Two layers of defense: a static scan of every module under gui/ for
forbidden network-related imports, and a runtime test that patches the
socket layer to raise if touched while exercising a full load -> filter
-> select -> export workflow.
"""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

from gui.model import InventoryModel
from gui.schema import load_inventory
from gui.selection import SelectionState

GUI_DIR = Path(__file__).resolve().parent.parent / "gui"

FORBIDDEN_MODULES = {
    "socket",
    "ssl",
    "urllib",
    "urllib.request",
    "urllib.error",
    "urllib3",
    "http.client",
    "httplib",
    "requests",
    "aiohttp",
    "httpx",
    "boto3",
    "botocore",
    "azure",
    "kubernetes",
    "paramiko",
    "ftplib",
    "smtplib",
    "telnetlib",
    "xmlrpc.client",
}


def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _is_forbidden(module_name: str) -> bool:
    return any(
        module_name == forbidden or module_name.startswith(forbidden + ".")
        for forbidden in FORBIDDEN_MODULES
    )


def test_no_forbidden_network_imports_anywhere_in_gui_package():
    py_files = sorted(GUI_DIR.rglob("*.py"))
    assert py_files, "expected to find .py files under gui/"

    offenders: dict[str, set[str]] = {}
    for path in py_files:
        imported = _imported_module_names(path.read_text(encoding="utf-8"))
        forbidden_here = {m for m in imported if _is_forbidden(m)}
        if forbidden_here:
            offenders[str(path.relative_to(GUI_DIR.parent))] = forbidden_here

    assert not offenders, f"forbidden network imports found: {offenders}"


class _NetworkAttempt(AssertionError):
    pass


def _blocked_socket(*_args, **_kwargs):
    raise _NetworkAttempt("gui package attempted to open a socket")


def test_full_workflow_never_touches_the_network(
    monkeypatch, small_inventory_path, tmp_path
):
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    monkeypatch.setattr(socket, "create_connection", _blocked_socket)

    inventory = load_inventory(small_inventory_path)
    model = InventoryModel(inventory.records)
    state = SelectionState(inventory.records)

    results = model.query(sources={"aws"}, search="role", sort_by="name")
    assert results

    state.select_many(results)
    assert state.count > 0

    summary = state.export(tmp_path / "selection.json", inventory)
    assert summary["count"] == state.count
