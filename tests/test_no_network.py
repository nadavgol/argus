"""Asserts the classifier package never imports networking modules.

The engine's architecture constraint (per epic #11) is that classification
is a pure, read-only data transform - no collector calls, no external
lookups. This is enforced statically here rather than by mocking sockets,
mirroring the intent of the GUI sibling's own no-network test.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULES = {"socket", "http", "http.client", "urllib", "urllib.request", "requests"}


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_no_networking_imports_in_package():
    package_dir = Path(__file__).parent.parent / "nhi_engine"
    for path in package_dir.rglob("*.py"):
        modules = _imported_modules(path.read_text())
        offending = modules & FORBIDDEN_MODULES
        assert not offending, f"{path} imports forbidden networking module(s): {offending}"
