# Helper scripts for managing Stacklet

These scripts bulk-apply `rbrk_*` tags to AWS resources managed by Stacklet.

## Setup

```shell
# Run from the /stacklet directory
mkdir -p inputs outputs
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## ResourceConfig Update
You can add additional resource config in static/resource_type_list.py  and static/resource_type_update.py 


## Steps

**1. Create `inputs/rbrk-values-<account-id>.json`** — the values for the 6
`rbrk_*` tags for that account.

**2. Create `static/stacklet-resource.json`** — the list of resources to process
for that AWS account.

**3. Log in and list the resources:**

```shell
awslogin <account>          # e.g. ss0
python3 scripts/run-listings.py     # lists resources from stacklet-resource.json -> CSVs in outputs/
```

**4. Build the change files** (no AWS call):

```shell
python3 scripts/automate-tagging.py
```

Creates:
- `inputs/make_changes-<resource>-<account-id>-<timestamp>.csv`
  = **source of truth for the changes to make in real AWS cloud**
- `outputs/dry-run-make_changes-<resource>-<account-id>-<timestamp>.txt`
  = preview of those changes

**5. Apply to AWS** (the only step that writes to the cloud):

- **UI:** `python3 tag-editor.py` → *"Apply it directly"* → **Dry Run** → **Apply Tags**
- **CLI (one file):**
  ```shell
  python3 update_tags-aws.py <make_changes-csv>            # dry run (default)
  python3 update_tags-aws.py <make_changes-csv> --apply    # apply changes
  ```
- **All files at once:** `python3 scripts/automate-apply.py`

---

## Layout

| Path                              | What                                             |
|-----------------------------------|--------------------------------------------------|
| `outputs/`                        | Listing CSVs + dry-run reports (gitignored)      |
| `inputs/`                         | `make_changes-*.csv` + per-account defaults      |
| `static/resource_type_list.py`    | Registry for listing (list side)                 |
| `static/resource_type_update.py`  | Registry for tagging (update side)               |
| `static/stacklet-resource.json`   | Selection: which types a run processes           |
