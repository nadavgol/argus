"""Tkinter desktop application: Load, Inventory table, Detail, Selection, Export.

This module is intentionally thin - all filtering/sorting/search logic
lives in gui.model, all selection/export logic lives in gui.selection, and
all file parsing lives in gui.schema. app.py only wires those together to
widgets. It performs no network I/O and requests no credentials.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gui.model import SORT_COLUMNS, InventoryModel
from gui.schema import InventoryFile, SchemaError, load_inventory
from gui.selection import SelectionState, default_platform, default_safe_name

CHECKED = "☑"  # ☑
UNCHECKED = "☐"  # ☐
NOT_SELECTABLE = "—"  # em dash, shown for human-classified rows

COLUMNS = ("sel", "name", "type", "subclass", "source", "created", "last_used", "reason")
COLUMN_HEADINGS = {
    "sel": "",
    "name": "Name",
    "type": "Type",
    "subclass": "Subclass",
    "source": "Source",
    "created": "Created",
    "last_used": "Last Used",
    "reason": "Classification Reason",
}
COLUMN_TO_SORT_KEY = {
    "name": "name",
    "type": "type",
    "subclass": "subclass",
    "source": "source",
    "created": "created",
    "last_used": "last_used",
    "reason": "classification_reason",
}

ALL_FILTER_VALUE = "All"


class App:
    def __init__(self, root: tk.Tk, initial_inventory_path: str | None = None):
        self.root = root
        self.root.title("ARGUS Inventory Browser")
        self.root.geometry("1100x700")

        self.inventory: InventoryFile | None = None
        self.model: InventoryModel | None = None
        self.selection: SelectionState | None = None
        self.sort_by = "name"
        self.sort_desc = False
        self._row_order: list[str] = []  # record ids, in current display order

        self._build_widgets()

        if initial_inventory_path:
            self._load_path(initial_inventory_path)

    # -- widget construction -------------------------------------------------

    def _build_widgets(self) -> None:
        top = ttk.Frame(self.root, padding=6)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top, text="Load Inventory...", command=self.action_load_file).pack(
            side=tk.LEFT
        )
        self.loaded_file_var = tk.StringVar(value="No inventory loaded.")
        ttk.Label(top, textvariable=self.loaded_file_var).pack(side=tk.LEFT, padx=10)

        filters = ttk.Frame(self.root, padding=(6, 0))
        filters.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(filters, text="Source:").pack(side=tk.LEFT)
        self.source_var = tk.StringVar(value=ALL_FILTER_VALUE)
        self.source_combo = ttk.Combobox(
            filters, textvariable=self.source_var, state="readonly", width=16
        )
        self.source_combo.pack(side=tk.LEFT, padx=(2, 10))
        self.source_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_table())

        ttk.Label(filters, text="Subclass:").pack(side=tk.LEFT)
        self.subclass_var = tk.StringVar(value=ALL_FILTER_VALUE)
        self.subclass_combo = ttk.Combobox(
            filters, textvariable=self.subclass_var, state="readonly", width=20
        )
        self.subclass_combo.pack(side=tk.LEFT, padx=(2, 10))
        self.subclass_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_table())

        ttk.Label(filters, text="Search name:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar(value="")
        search_entry = ttk.Entry(filters, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(2, 10))
        self.search_var.trace_add("write", lambda *_a: self._refresh_table())

        # main split: table (left) / detail+selection (right)
        main = ttk.Frame(self.root)
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(main)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame, columns=COLUMNS, show="headings", selectmode="browse"
        )
        for col in COLUMNS:
            anchor = tk.CENTER if col == "sel" else tk.W
            self.tree.heading(
                col, text=COLUMN_HEADINGS[col],
                command=(lambda c=col: self._on_heading_click(c)),
            )
            width = 40 if col == "sel" else 130
            self.tree.column(col, width=width, anchor=anchor, stretch=(col != "sel"))
        self.tree.tag_configure("human", foreground="#888888")
        self.tree.tag_configure("selected", background="#e6f3ff")

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Button-1>", self._on_tree_click)

        side = ttk.Frame(main, padding=6, width=320)
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.pack_propagate(False)

        ttk.Label(side, text="Detail", font=("TkDefaultFont", 11, "bold")).pack(
            anchor=tk.W
        )
        self.detail_text = tk.Text(side, height=18, wrap=tk.WORD, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True, pady=(2, 8))

        ttk.Separator(side).pack(fill=tk.X, pady=4)
        ttk.Label(side, text="Onboarding Assignment", font=("TkDefaultFont", 11, "bold")).pack(
            anchor=tk.W
        )

        assign = ttk.Frame(side)
        assign.pack(fill=tk.X, pady=4)
        ttk.Label(assign, text="Safe:").grid(row=0, column=0, sticky=tk.W)
        self.safe_var = tk.StringVar(value="")
        self.safe_entry = ttk.Entry(assign, textvariable=self.safe_var, state=tk.DISABLED)
        self.safe_entry.grid(row=0, column=1, sticky=tk.EW, padx=4)
        ttk.Label(assign, text="Platform:").grid(row=1, column=0, sticky=tk.W)
        self.platform_var = tk.StringVar(value="")
        self.platform_entry = ttk.Entry(
            assign, textvariable=self.platform_var, state=tk.DISABLED
        )
        self.platform_entry.grid(row=1, column=1, sticky=tk.EW, padx=4)
        assign.columnconfigure(1, weight=1)
        self.safe_var.trace_add("write", lambda *_a: self._on_assignment_edited())
        self.platform_var.trace_add("write", lambda *_a: self._on_assignment_edited())

        ttk.Separator(side).pack(fill=tk.X, pady=4)
        bulk = ttk.Frame(side)
        bulk.pack(fill=tk.X, pady=4)
        ttk.Button(
            bulk, text="Select all (filtered)", command=self._select_all_filtered
        ).pack(fill=tk.X, pady=2)
        ttk.Button(bulk, text="Deselect all", command=self._deselect_all).pack(
            fill=tk.X, pady=2
        )
        self.count_var = tk.StringVar(value="0 selected")
        ttk.Label(side, textvariable=self.count_var).pack(anchor=tk.W, pady=(4, 8))

        ttk.Button(side, text="Export Selection...", command=self.action_export).pack(
            fill=tk.X, pady=(8, 0)
        )

        self._current_selected_id: str | None = None

    # -- load ------------------------------------------------------------

    def action_load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open inventory.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._load_path(path)

    def _load_path(self, path: str) -> None:
        try:
            inventory = load_inventory(path)
        except SchemaError as exc:
            messagebox.showerror("Could not load inventory", str(exc))
            return

        self.inventory = inventory
        self.model = InventoryModel(inventory.records)
        self.selection = SelectionState(inventory.records)
        self.sort_by = "name"
        self.sort_desc = False

        self.loaded_file_var.set(
            f"{inventory.source_path}  (schema {inventory.schema_version}, "
            f"{len(inventory.records)} records)"
        )
        self.source_combo["values"] = [ALL_FILTER_VALUE] + self.model.sources()
        self.source_var.set(ALL_FILTER_VALUE)
        self.subclass_combo["values"] = [ALL_FILTER_VALUE] + self.model.subclasses()
        self.subclass_var.set(ALL_FILTER_VALUE)
        self.search_var.set("")

        self._refresh_table()

    # -- table -------------------------------------------------------------

    def _current_filters(self) -> tuple[set[str], set[str], str]:
        sources = set()
        if self.source_var.get() not in (ALL_FILTER_VALUE, ""):
            sources = {self.source_var.get()}
        subclasses = set()
        if self.subclass_var.get() not in (ALL_FILTER_VALUE, ""):
            subclasses = {self.subclass_var.get()}
        return sources, subclasses, self.search_var.get()

    def _on_heading_click(self, col: str) -> None:
        sort_key = COLUMN_TO_SORT_KEY.get(col)
        if sort_key is None:
            return
        if self.sort_by == sort_key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_by = sort_key
            self.sort_desc = False
        self._refresh_table()

    def _refresh_table(self) -> None:
        if self.model is None:
            return
        sources, subclasses, search = self._current_filters()
        results = self.model.query(
            sources=sources,
            subclasses=subclasses,
            search=search,
            sort_by=self.sort_by,
            sort_desc=self.sort_desc,
        )

        self.tree.delete(*self.tree.get_children())
        self._row_order = []
        assert self.selection is not None
        for record in results:
            if record.is_selectable:
                mark = CHECKED if self.selection.is_selected(record.id) else UNCHECKED
            else:
                mark = NOT_SELECTABLE
            tags = []
            if record.is_human:
                tags.append("human")
            if record.is_selectable and self.selection.is_selected(record.id):
                tags.append("selected")
            self.tree.insert(
                "",
                tk.END,
                iid=record.id,
                values=(
                    mark,
                    record.name,
                    record.type,
                    record.subclass,
                    record.source,
                    record.created,
                    record.last_used,
                    record.classification_reason,
                ),
                tags=tuple(tags),
            )
            self._row_order.append(record.id)

        self._update_count()

    def _on_tree_click(self, event: tk.Event) -> None:
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        if col == f"#{COLUMNS.index('sel') + 1}":
            self._toggle_selection(row_id)

    def _toggle_selection(self, record_id: str) -> None:
        assert self.selection is not None and self.model is not None
        record = next((r for r in self.model.records if r.id == record_id), None)
        if record is None or not record.is_selectable:
            return
        if self.selection.is_selected(record_id):
            self.selection.deselect(record_id)
        else:
            self.selection.select(record_id)
        self._refresh_row(record_id)
        self._update_count()
        if self._current_selected_id == record_id:
            self._populate_assignment_fields(record_id)

    def _refresh_row(self, record_id: str) -> None:
        assert self.selection is not None and self.model is not None
        record = next((r for r in self.model.records if r.id == record_id), None)
        if record is None:
            return
        mark = (
            (CHECKED if self.selection.is_selected(record_id) else UNCHECKED)
            if record.is_selectable
            else NOT_SELECTABLE
        )
        current_values = list(self.tree.item(record_id, "values"))
        current_values[0] = mark
        self.tree.item(record_id, values=current_values)
        tags = []
        if record.is_human:
            tags.append("human")
        if record.is_selectable and self.selection.is_selected(record_id):
            tags.append("selected")
        self.tree.item(record_id, tags=tuple(tags))

    # -- detail / assignment ------------------------------------------------

    def _on_row_select(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        record_id = selection[0]
        self._current_selected_id = record_id
        self._populate_detail(record_id)
        self._populate_assignment_fields(record_id)

    def _populate_detail(self, record_id: str) -> None:
        assert self.model is not None
        record = next((r for r in self.model.records if r.id == record_id), None)
        if record is None:
            return
        lines = [
            f"ID: {record.id}",
            f"Name: {record.name}",
            f"Type: {record.type}",
            f"Subclass: {record.subclass}",
            f"Source: {record.source}",
            f"Created: {record.created}",
            f"Last used: {record.last_used}",
            f"Classification reason: {record.classification_reason}",
            "",
            "Raw metadata:",
            json.dumps(record.metadata, indent=2, sort_keys=True),
        ]
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.configure(state=tk.DISABLED)

    def _populate_assignment_fields(self, record_id: str) -> None:
        assert self.model is not None and self.selection is not None
        record = next((r for r in self.model.records if r.id == record_id), None)
        if record is None or not record.is_selectable:
            self.safe_var.set("")
            self.platform_var.set("")
            self.safe_entry.configure(state=tk.DISABLED)
            self.platform_entry.configure(state=tk.DISABLED)
            return

        if self.selection.is_selected(record_id):
            self._suspend_assignment_trace = True
            self.safe_var.set(self.selection.get_safe(record_id))
            self.platform_var.set(self.selection.get_platform(record_id))
            self._suspend_assignment_trace = False
            self.safe_entry.configure(state=tk.NORMAL)
            self.platform_entry.configure(state=tk.NORMAL)
        else:
            self._suspend_assignment_trace = True
            self.safe_var.set(default_safe_name(record))
            self.platform_var.set(default_platform(record))
            self._suspend_assignment_trace = False
            self.safe_entry.configure(state=tk.DISABLED)
            self.platform_entry.configure(state=tk.DISABLED)

    _suspend_assignment_trace = False

    def _on_assignment_edited(self) -> None:
        if self._suspend_assignment_trace:
            return
        if self._current_selected_id is None or self.selection is None:
            return
        record_id = self._current_selected_id
        if not self.selection.is_selected(record_id):
            return
        safe = self.safe_var.get()
        platform = self.platform_var.get()
        if safe:
            self.selection.set_safe(record_id, safe)
        if platform:
            self.selection.set_platform(record_id, platform)

    # -- bulk / export -------------------------------------------------------

    def _select_all_filtered(self) -> None:
        if self.model is None or self.selection is None:
            return
        sources, subclasses, search = self._current_filters()
        results = self.model.query(
            sources=sources, subclasses=subclasses, search=search, sort_by=self.sort_by,
            sort_desc=self.sort_desc,
        )
        self.selection.select_many(results)
        self._refresh_table()

    def _deselect_all(self) -> None:
        if self.selection is None:
            return
        self.selection.deselect_all()
        self._refresh_table()

    def _update_count(self) -> None:
        if self.selection is None:
            self.count_var.set("0 selected")
            return
        self.count_var.set(f"{self.selection.count} selected")

    def action_export(self) -> None:
        if self.selection is None or self.inventory is None:
            messagebox.showwarning("Nothing to export", "Load an inventory first.")
            return
        if self.selection.count == 0:
            messagebox.showwarning("Nothing to export", "No records are selected.")
            return
        path = filedialog.asksaveasfilename(
            title="Export selection.json",
            defaultextension=".json",
            initialfile="selection.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        summary = self.selection.export(path, self.inventory)
        details = "\n".join(f"  {src}: {n}" for src, n in sorted(summary["by_source"].items()))
        messagebox.showinfo(
            "Selection exported",
            f"Wrote {summary['count']} record(s) to {summary['path']}\n\n"
            f"By source:\n{details}",
        )


def main(argv: list[str] | None = None) -> None:
    import sys

    argv = sys.argv[1:] if argv is None else argv
    initial_path = argv[0] if argv else None

    root = tk.Tk()
    App(root, initial_inventory_path=initial_path)
    root.mainloop()


if __name__ == "__main__":
    main()
