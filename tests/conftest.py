from __future__ import annotations

from pathlib import Path

import pytest

TESTDATA_DIR = Path(__file__).resolve().parent.parent / "testdata"


@pytest.fixture
def testdata_dir() -> Path:
    return TESTDATA_DIR


@pytest.fixture
def small_inventory_path() -> Path:
    return TESTDATA_DIR / "inventory_small.json"


@pytest.fixture
def bad_version_inventory_path() -> Path:
    return TESTDATA_DIR / "inventory_bad_version.json"


@pytest.fixture
def malformed_inventory_path() -> Path:
    return TESTDATA_DIR / "inventory_malformed.json"


@pytest.fixture
def invalid_record_inventory_path() -> Path:
    return TESTDATA_DIR / "inventory_invalid_record.json"


@pytest.fixture(scope="session")
def large_inventory_path() -> Path:
    return TESTDATA_DIR / "inventory_10000.json"


@pytest.fixture
def tk_root():
    """A withdrawn Tk root, or a skip if no display is available.

    Runs headless-safely: many CI environments (e.g. default Linux
    runners without Xvfb) have no display, and Tk() raises TclError in
    that case. Tests using this fixture are skipped rather than failed
    when that happens, since it reflects the environment, not the code.
    """
    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"No display available for Tk: {exc}")
        return
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()
