# sre-scripts

SRE helper scripts for Stacklet.

## Cloud resource tagging/labelling

Bulk-apply Rubrik `rbrk_*` metadata to cloud resources — **tags** on AWS,
**labels** on GCP — via the same `list → fill → dry-run → apply` flow.

- **Full guide (both clouds):** [`stacklet/README.md`](stacklet/README.md)
- **GCP deep-dive:** [`GCP-TAGGING.md`](GCP-TAGGING.md)
