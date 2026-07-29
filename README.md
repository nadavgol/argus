# argus

ARGUS discovers non-human identities (NHIs) across AWS, Entra, Active
Directory, and Kubernetes, and onboards them to CyberArk. This repo
currently contains the GUI: an offline desktop tool for reviewing a
discovery inventory and selecting which NHIs to onboard.

## GUI: inventory browser and onboarding selection

The GUI is a pure consumer of an `inventory.json` file produced by the
ARGUS collectors. It never calls AWS, Entra, AD, Kubernetes, or CyberArk,
handles no credentials, and makes no network calls of any kind - this is
enforced by `tests/test_no_network.py`. It loads the inventory, lets a
consultant review, filter, and search it, and writes an onboarding
`selection.json` back out. Running the onboarder against that selection
file remains a separate CLI command.

### Running the GUI

The GUI has no third-party runtime dependencies - it only needs Python's
standard library (including `tkinter`, which ships with most Python
installs).

```sh
python3 -m gui                       # opens the app; use "Load Inventory..."
python3 -m gui path/to/inventory.json  # opens the app with a file preloaded
```

### Views

1. **Load** - pick an `inventory.json` file. A schema version mismatch or
   malformed file produces a readable error dialog instead of crashing.
2. **Inventory table** - every record, sortable by clicking a column
   header, filterable by source and subclass, with free-text search on
   name.
3. **Detail pane** - the full record for the selected row, including raw
   collector metadata.
4. **Selection** - click the leftmost column to toggle a record for
   onboarding, or use "Select all (filtered)" to bulk-select whatever the
   current filter/search shows. Human-classified records are visible in
   the table but can never be selected. Each selected record gets a safe
   and platform assignment, pre-filled by a default mapping rule (see
   below) and editable per-record.
5. **Export** - writes `selection.json` and shows a summary of what was
   selected, grouped by source.

### Default safe/platform mapping rule

Every selected NHI is assigned a default CyberArk safe and platform based
on its source and subclass, so a consultant is never forced to fill in
every field by hand:

| Source     | Default platform          |
|------------|----------------------------|
| aws        | AWS Access Keys            |
| entra      | Azure Service Principal    |
| ad         | Windows Domain Account     |
| kubernetes | Kubernetes ServiceAccount  |

The default safe name is `{SOURCE}-{SUBCLASS}` (uppercased). Both the safe
and platform remain editable per-record in the Selection view before
export - the default is a starting point, not a requirement.

### `selection.json`

```json
{
  "schema_version": "1.0",
  "source_inventory_schema_version": "1.0",
  "source_inventory_path": "inventory.json",
  "generated_at": "2026-07-30T12:00:00Z",
  "selections": [
    {"id": "aws-role-lambda-exec-01", "safe": "AWS-IAM_ROLE", "platform": "AWS Access Keys"}
  ]
}
```

Every entry corresponds to a selected, non-human record; running the
onboarder against this file remains a separate step.

### Running the tests

```sh
pip3 install -r requirements-dev.txt
python3 -m pytest
```

The suite includes a fixture with 10,000 synthetic records
(`testdata/inventory_10000.json`, regenerated via
`testdata/generate_large_fixture.py`) used to assert the table loads and
renders in well under 2 seconds.
