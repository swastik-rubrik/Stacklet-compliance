# apply-tagging-group.py

Batch-applies the `tagging_group` tag to cloud **accounts / projects / subscriptions**
from a single JSON file.

## Why this is a new script (not an edit of `../stacklet/update_tags-*.py`)

The existing scripts tag **individual resources** (EC2 instances, volumes, buckets)
read from `make_changes-*.csv`, using:

- AWS: Resource Groups Tagging API (`resourcegroupstaggingapi`) on ARNs
- GCP: per-resource label backends

This task tags at the **account level**, which needs entirely different management
APIs. So this is a standalone script that reuses the *patterns* (dry-run default,
fetch → merge → write, per-item error isolation) rather than the code.

## Input format (`resources.json`)

```json
[
  {"provider": "aws",   "target_id": "212093141267",             "tag_value": "AppSec"},
  {"provider": "gcp",   "target_id": "infosec-stacklet-platform", "tag_value": "infosec_sre"},
  {"provider": "azure", "target_id": "<subscription-guid>",       "tag_value": "platform"}
]
```

- `provider` — `aws` | `gcp` | `azure`
- `target_id` — AWS account ID / GCP project ID / Azure subscription ID
- `tag_value` — value for the `tagging_group` tag

Entries missing a field, or with an unknown provider, are skipped with a warning.

## What each provider does

| Provider | API | Call |
|----------|-----|------|
| AWS | Organizations | `list_tags_for_resource` → `tag_resource` (client pinned to **us-east-1**, since Organizations is global) |
| GCP | Resource Manager | `get_project` → merge `.labels` → `update_project` (`update_mask=labels`) |
| Azure | Resource Management | `tags.get_at_scope` → merge → `begin_create_or_update_at_scope` on `/subscriptions/{id}` |

All three **fetch existing tags first and merge** — other tags/labels are never
removed.

## Key behaviours

- **Dry-run is the default.** Nothing is written unless you pass `--apply`.
  `--dry-run` is also accepted to state it explicitly; it is mutually exclusive
  with `--apply`.
- **Conflict → skip & warn.** If `tagging_group` already exists with a *different*
  value, the existing value is kept and a warning is printed (never overwritten).
  The tag is only added when absent.
- **One failure never breaks the loop.** Each entry is wrapped in `try/except`;
  failures are logged and the batch continues. Exit code is `1` if any entry failed.
- **GCP validation.** GCP label keys/values must match `[a-z0-9_-]` (lowercase);
  invalid values fail that single entry with a clear message.

## Usage

```bash
# Dry run (default) on resources.json
python3 apply-tagging-group.py

# Dry run on a different file, with per-entry detail
python3 apply-tagging-group.py --input-file other.json --verbose

# Actually write tags
python3 apply-tagging-group.py --apply
```

## Auth (done by the user before running)

- AWS: `aws sso login` — credentials must be for the Org management or
  delegated-admin account, otherwise `tag_resource` is denied.
- GCP: `gcloud auth application-default login`
- Azure: `az login`

## Setup: virtual environment

This project uses its **own** virtualenv, separate from `../stacklet/.venv`.
Create it once inside `custom-tagging/`, then install the dependencies into it.

```bash
# From the custom-tagging/ directory
cd /Users/swastiksharma/Desktop/Stacklet/sre-scripts/custom-tagging

# 1. Create the venv (named .venv)
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate          # macOS / Linux (zsh/bash)
# .venv\Scripts\activate           # Windows PowerShell

# 3. Upgrade pip and install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 4. Run the script (dry run by default)
python3 apply-tagging-group.py

# When finished
deactivate
```

Subsequent runs only need `source .venv/bin/activate` before invoking the script.

> Note: add `.venv/` to `.gitignore` so the environment isn't committed.

## Dependencies

See `requirements.txt`:

```
boto3
google-cloud-resource-manager
azure-identity
azure-mgmt-resource
```

## Exit codes

- `0` — all entries applied / would-apply / unchanged / skipped
- `1` — at least one entry failed
