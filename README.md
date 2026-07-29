# argus

ARGUS is an identity-security platform: it discovers human and non-human
identities (NHIs) across client environments, classifies them, and helps
onboard NHIs into CyberArk for management.

## NHI engine

The `nhi_engine` package is the classifier component of the discovery
pipeline. It takes raw, per-identity signals collected from a source
(AWS IAM, Entra ID, Active Directory, Kubernetes, ...) and decides:

- **type** — `human` or `nhi`
- **subclass** — the source-specific principal kind (e.g. `iam_role`,
  `service_account`, `gmsa`)
- **classification_reason** — the concrete signal that drove the decision

### Classification rules

1. Accounts flagged `is_break_glass` or `is_shared_admin` are classified
   as `human` — they exist for human emergency/shared interactive use
   even though they aren't tied to one named person.
2. Records with `interactive_login: true` are classified as `human`.
3. Records with a recognized programmatic signal (a known
   `credential_type` or `principal_kind`) are classified as `nhi` and
   placed into one of six fixed NHI categories (see
   [issue #2's taxonomy](https://github.com/nadavgol/argus/issues/2)):
   cloud IAM principals, workload identities, application credentials,
   machine accounts, certificates, and agentic AI identities.
4. Records with no usable signal either way are classified as `nhi` with
   subclass `unclassified` and flagged for manual review — the engine
   never guesses `human` on missing data, since that would silently
   under-count NHIs.

### Usage

```bash
pip install -e .
nhi-engine classify --in raw_identities.json --out inventory.json
```

`raw_identities.json` is a JSON array of raw identity records (see
`testdata/raw_identities_small.json` for an example). `inventory.json` is
written in the shared inventory schema (`schema_version: "1.0"`,
`id`/`name`/`type`/`subclass`/`source`/`created`/`last_used`/
`classification_reason`/`metadata` per record) used by the rest of the
ARGUS pipeline, including the GUI.

### Running tests

```bash
pip install -e . -r requirements-dev.txt
pytest
```
