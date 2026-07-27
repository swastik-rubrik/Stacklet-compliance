# Stacklet resource tagging

Bulk-apply Rubrik `rbrk_*` metadata to cloud resources — **tags** on AWS,
**labels** on GCP. Same three steps on both clouds:

```
list  →  fill  →  apply
```

Everything flows through CSVs (in `outputs/` and `inputs/`) so you can review
before anything is written. Empty cells and the literal `undefined` are
**never** written to the cloud.

## Setup (once)

```bash
cd stacklet
mkdir -p inputs outputs
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

Run all commands below from the `stacklet/` directory.

---

# AWS

### 1. Log in

```bash
awslogin <account>          # e.g. ss0 — credentials for that AWS account
```

Credentials are tied to one account; the account id is baked into every CSV
name and re-checked before any write.

### 2. Configure

- `aws/static/stacklet-resource.json` — which resource types to process,
  e.g. `["s3", "ebs", "rds"]`.
- `inputs/rbrk-values-<account-id>.json` — the default `rbrk_*` values for that
  account, e.g.

  ```json
  { "rbrk_env": "prod", "rbrk_owner": "sre" }
  ```

### 3. Run (automation)

```bash
# a) LIST every selected type -> outputs/<type>-<account>-<ts>.csv
python3 aws/run-listings.py

# b) FILL from the account defaults -> inputs/make_changes-*.csv (+ dry-run report)
#    No AWS writes. Review outputs/dry-run-*.txt.
python3 aws/automate-tagging-aws.py

# c) APPLY every make_changes file to AWS
python3 aws/automate-apply-aws.py
```

> **Manual (one resource type):**
> `python3 aws/update_tags-aws.py <make_changes-csv>` (dry run),
> add `--apply` to write. Or use the web UI: `python3 aws/tag-editor.py`.

### Extending

Add the type to `aws/static/resource_type_list.py` (list) and
`aws/static/resource_type_update.py` (update).

---

# GCP

### 1. Log in

```bash
gcloud auth application-default login    # once — your identity, not a project
```

Unlike AWS you don't re-log-in per project — you switch projects with
`--project`, else the current one is used (`$GOOGLE_CLOUD_PROJECT`, else your
ADC default). Your identity must have IAM access on the project.

### 2. Configure

- `inputs/rbrk-values-<project>.json` — default `rbrk_*` values for that project
  (same format as AWS).

> GCP label values must be lowercase `[a-z0-9_-]` (no dots/uppercase), or the
> API rejects them at apply.

### 3. Run (automation)

```bash
# a) LIST each type you need -> outputs/<type>-<project>-<ts>.csv
#    types: instance, disk, image, bucket, bq-dataset
python3 gcp/list-resource-gcp.py --resource-type bucket   # --project optional

# b) FILL from the project defaults -> inputs/make_changes-*.csv (+ dry-run)
python3 gcp/automate-tagging-gcp.py

# c) APPLY — defaults to the CURRENT project; no filename needed
python3 gcp/automate-apply-gcp.py
#   --project X       a specific project
#   --all-projects    every project's files
#   --dry-run         preview, writes nothing
```

> **Manual (one file):**
> `python3 gcp/update_tags-gcp.py <make_changes-csv>` (dry run),
> add `--apply` to write.

### Extending

Add one `GcpResourceConfig` entry to `RESOURCE_TYPES` in
`gcp/static/gcp_resource_types.py` (`meta_columns`, `list_fn`, `backend_fn`).
Everything else picks it up automatically.

---

## Layout

| Path | What |
|---|---|
| `inputs/` | `make_changes-*.csv` + defaults `rbrk-values-<id>.json` |
| `outputs/` | listing CSVs + dry-run/automation reports |
| `aws/` | AWS drivers, automation, and `aws/static/` registries |
| `gcp/` | GCP drivers, automation, and `gcp/static/` registry |
| `helpers.py` | shared CSV parsing / placeholder / report / project helpers |
