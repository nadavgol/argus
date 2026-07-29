"""End-to-end smoke tests through the real Tkinter widget tree.

Skipped automatically (via the tk_root fixture) when no display is
available, which is common on default headless CI runners. Where a
display is available, these exercise the same code paths a user
clicking through the app would hit.
"""

from __future__ import annotations

import json
import time

from gui.app import App


def test_app_loads_small_fixture_and_populates_tree(tk_root, small_inventory_path):
    app = App(tk_root)
    app._load_path(str(small_inventory_path))

    assert len(app.tree.get_children()) == 12
    assert "schema 1.0" in app.loaded_file_var.get()


def test_app_schema_mismatch_shows_readable_error_not_crash(
    tk_root, bad_version_inventory_path, monkeypatch
):
    app = App(tk_root)

    captured = {}

    def fake_showerror(title, message):
        captured["title"] = title
        captured["message"] = message

    monkeypatch.setattr("gui.app.messagebox.showerror", fake_showerror)

    app._load_path(str(bad_version_inventory_path))

    assert captured, "expected a schema-mismatch error dialog to be shown"
    assert "0.9" in captured["message"]
    assert app.inventory is None
    assert len(app.tree.get_children()) == 0


def test_app_toggle_selection_respects_human_records(tk_root, small_inventory_path):
    app = App(tk_root)
    app._load_path(str(small_inventory_path))

    nhi_id = "aws-role-lambda-exec-01"
    human_id = "aws-user-jsmith-01"

    app._toggle_selection(nhi_id)
    assert app.selection.is_selected(nhi_id) is True

    app._toggle_selection(human_id)
    assert app.selection.is_selected(human_id) is False


def test_app_select_all_filtered_and_deselect_all(tk_root, small_inventory_path):
    app = App(tk_root)
    app._load_path(str(small_inventory_path))

    app.source_var.set("aws")
    app._select_all_filtered()
    assert app.selection.count == 3  # 3 aws nhi records; the 1 aws human record is skipped

    app._deselect_all()
    assert app.selection.count == 0


def test_app_export_writes_selection_file(
    tk_root, small_inventory_path, tmp_path, monkeypatch
):
    app = App(tk_root)
    app._load_path(str(small_inventory_path))
    app._toggle_selection("aws-role-lambda-exec-01")

    out_path = tmp_path / "selection.json"
    monkeypatch.setattr("gui.app.filedialog.asksaveasfilename", lambda **kw: str(out_path))
    monkeypatch.setattr("gui.app.messagebox.showinfo", lambda *a, **k: None)

    app.action_export()

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["selections"] == [
        {
            "id": "aws-role-lambda-exec-01",
            "safe": "AWS-IAM_ROLE",
            "platform": "AWS Access Keys",
        }
    ]


def test_app_renders_10000_records_under_2_seconds(tk_root, large_inventory_path):
    app = App(tk_root)

    start = time.perf_counter()
    app._load_path(str(large_inventory_path))
    tk_root.update_idletasks()
    elapsed = time.perf_counter() - start

    assert len(app.tree.get_children()) == 10_000
    assert elapsed < 2.0, f"rendering 10,000 records took {elapsed:.3f}s"
