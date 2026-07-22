# Helper scripts for managing Stacklet

These scripts bulk-apply `rbrk_*` tags to AWS resources managed by Stacklet.

## Initialize your environment

```shell
# Run from the /stacklet directory
mkdir -p inputs outputs
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## The workflow

```
awslogin  →  list  →  fill (tag-editor)  →  dry-run  →  apply
```

1. **Log in** — `awslogin <account>`. Credentials must match the account you tag.
2. **List** resources → CSV in `outputs/`.
3. **Fill** the `undefined` `rbrk_*` cells → `make_changes-*.csv` in `inputs/`.
4. **Dry-run** against live AWS to preview the exact tag changes.
5. **Apply** — the only step that writes to AWS. Always manual.

---

## Scripts

### 1. List resources — `list-resource-aws.py`

One resource type → one CSV in `outputs/`.

```shell
python3 list-resource-aws.py --resource-type snapshot --skip-region me-central-1
```

Loop over **every** type in `static/resource_type_list.py` with `run-listings.py`:

```shell
python3 run-listings.py --skip-region me-central-1        # all types
python3 run-listings.py --only rds --only s3              # just these
python3 run-listings.py --exclude ecr                     # all but these
```

### 2. Fill + apply (UI) — `tag-editor.py`

Local web UI at http://localhost:8765.

```shell
python3 tag-editor.py
```

- Pick a listing CSV from `outputs/`, enter each `rbrk_*` value once (blank =
  skip that column), **Preview**, then **Write make_changes file** → `inputs/`.
- Values can be saved as **per-account defaults** so later CSVs prefill.
- **Apply to AWS** panel: **Dry Run (AWS)** shows the diff vs. live tags, then
  **Apply Tags** writes them.
- **Already have a `make_changes-*.csv`?** Pick it from the *"Apply it
  directly"* dropdown to jump straight to the Apply-to-AWS panel — no
  fill/write needed.

Only literal `undefined` cells are ever filled; empty cells and real values are
left untouched, so nothing unexpected reaches AWS.

### 3. Dry-run / apply (CLI) — `update_tags-aws.py`

The CLI equivalent of the UI's apply panel. The filename must keep the
`make_changes-<type>-<account>-<timestamp>.csv` format — it's how the script
learns the resource type and account.

```shell
# Dry-run (default): shows what would change
python3 update_tags-aws.py make_changes-snapshot-<account>-<ts>.csv --skip-region me-central-1 --log

# Apply, after reviewing the dry-run
python3 update_tags-aws.py make_changes-snapshot-<account>-<ts>.csv --skip-region me-central-1 --apply
```

### 4. Automate fill + dry-run — `automate-tagging.py`

Runs steps 3–4 (write make_changes + AWS dry-run, using each account's saved
defaults) across **every** listing CSV in `outputs/`, and writes one combined
report to `outputs/tagging-automation-report-<ts>.md`. It **never applies** —
apply stays manual. See `automate-tagging.md`.

```shell
python3 automate-tagging.py                    # every eligible CSV in outputs/
python3 automate-tagging.py --only ecr s3      # restrict to types
python3 automate-tagging.py --skip-region me-central-1
```

---

## Layout

| Path                          | What                                             |
|-------------------------------|--------------------------------------------------|
| `outputs/`                    | Listing CSVs + dry-run reports (gitignored)      |
| `inputs/`                     | `make_changes-*.csv` + per-account defaults      |
| `static/resource_type_list.py`| Registry for listing (list side)                 |
| `static/resource_type_update.py`| Registry for tagging (update side)             |
| `docs/`                       | Per-change notes                                 |

