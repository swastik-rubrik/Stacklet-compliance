#!/usr/bin/env python3
"""Batch-apply the `tagging_group` tag to cloud accounts / projects / subscriptions.

Unlike the resource-level scripts in ../stacklet/ (which tag individual EC2
instances, buckets, etc. from make_changes CSVs), this script operates at the
*account* level and is driven by a single JSON file:

    [
      {"provider": "aws",   "target_id": "212093141267",            "tag_value": "AppSec"},
      {"provider": "gcp",   "target_id": "infosec-stacklet-platform", "tag_value": "infosec_sre"},
      {"provider": "azure", "target_id": "00000000-0000-0000-0000-000000000000", "tag_value": "platform"}
    ]

For each entry it applies  tagging_group=<tag_value> via the provider's management API:
    AWS    -> Organizations tag_resource        (account)
    GCP    -> Resource Manager update_project    (project labels)
    Azure  -> Resource Management tags at scope  (subscription)

Design (mirrors ../stacklet/update_tags-*.py):
    * DRY RUN IS THE DEFAULT. Nothing is written unless you pass --apply.
    * Fetch existing tags first and MERGE - other tags are never touched.
    * If tagging_group already exists with a DIFFERENT value, we SKIP & WARN
      (the existing value is left in place) rather than overwrite it.
    * One failure never breaks the loop: it is logged and the next entry runs.

Auth (handled by the user, externally, before running):
    AWS    : aws sso login   (creds must be for the Org management/delegated-admin account)
    GCP    : gcloud auth application-default login
    Azure  : az login

Usage:
    python3 apply-tagging-group.py                          # dry run on resources.json
    python3 apply-tagging-group.py --input-file other.json  # dry run on another file
    python3 apply-tagging-group.py --apply                  # actually write tags
    python3 apply-tagging-group.py --verbose                # per-entry detail
"""

import argparse
import json
import re
import sys
from pathlib import Path

TAG_KEY_DEFAULT = "tagging_group"

# GCP labels: keys/values must be lowercase [a-z0-9_-], <=63 chars; keys start
# with a lowercase letter. The API rejects anything else, so we validate first.
_GCP_VALUE_RE = re.compile(r"^[a-z0-9_-]{1,63}$")
_GCP_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")


# --------------------------------------------------------------------------- #
# Per-entry decision: given the current tags, what should happen to our key?
# --------------------------------------------------------------------------- #
def decide_action(existing: dict[str, str], key: str, value: str) -> tuple[str, str]:
    """Return (action, message).

    action is one of:
        "add"      - key absent, we will add it
        "unchanged"- key present with the same value, nothing to do
        "conflict" - key present with a different value -> skip & warn
    """
    if key not in existing:
        return "add", f"{key}={value} (new)"
    if existing[key] == value:
        return "unchanged", f"{key}={value} already set"
    return (
        "conflict",
        f"{key} already set to '{existing[key]}', refusing to overwrite with '{value}'",
    )


# --------------------------------------------------------------------------- #
# AWS - Organizations (account-level tags). Organizations is a global service;
# we pin the client to us-east-1 (consistent with the repo's global-resource
# region handling).
# --------------------------------------------------------------------------- #
def tag_aws_account(target_id: str, key: str, value: str, dry_run: bool, verbose: bool) -> str:
    import boto3

    client = boto3.client("organizations", region_name="us-east-1")

    existing: dict[str, str] = {}
    paginator = client.get_paginator("list_tags_for_resource")
    for page in paginator.paginate(ResourceId=target_id):
        for t in page.get("Tags", []):
            existing[t["Key"]] = t["Value"]

    action, msg = decide_action(existing, key, value)
    if verbose or action == "conflict":
        print(f"    {msg}", file=sys.stderr if action == "conflict" else sys.stdout)

    if action == "unchanged":
        return "unchanged"
    if action == "conflict":
        return "skipped"
    if dry_run:
        print(f"    [dry-run] would tag account {target_id}: {key}={value}")
        return "would_apply"

    client.tag_resource(ResourceId=target_id, Tags=[{"Key": key, "Value": value}])
    print(f"    tagged account {target_id}: {key}={value}")
    return "applied"


# --------------------------------------------------------------------------- #
# GCP - Resource Manager (project labels). update_project with a labels mask
# REPLACES the label map, so we read + merge before writing.
# --------------------------------------------------------------------------- #
def tag_gcp_project(target_id: str, key: str, value: str, dry_run: bool, verbose: bool) -> str:
    from google.cloud import resourcemanager_v3
    from google.protobuf import field_mask_pb2

    if not _GCP_KEY_RE.match(key):
        raise ValueError(f"invalid GCP label key '{key}' (must match [a-z][a-z0-9_-]{{0,62}})")
    if not _GCP_VALUE_RE.match(value):
        raise ValueError(f"invalid GCP label value '{value}' (must match [a-z0-9_-]{{1,63}})")

    client = resourcemanager_v3.ProjectsClient()
    project = client.get_project(name=f"projects/{target_id}")
    existing = dict(project.labels)

    action, msg = decide_action(existing, key, value)
    if verbose or action == "conflict":
        print(f"    {msg}", file=sys.stderr if action == "conflict" else sys.stdout)

    if action == "unchanged":
        return "unchanged"
    if action == "conflict":
        return "skipped"
    if dry_run:
        print(f"    [dry-run] would label project {target_id}: {key}={value}")
        return "would_apply"

    merged = dict(existing)
    merged[key] = value
    project.labels = merged
    client.update_project(
        project=project,
        update_mask=field_mask_pb2.FieldMask(paths=["labels"]),
    ).result()
    print(f"    labeled project {target_id}: {key}={value}")
    return "applied"


# --------------------------------------------------------------------------- #
# Azure - Resource Management (subscription tags). create_or_update_at_scope
# REPLACES all tags at the scope, so we read + merge before writing.
# --------------------------------------------------------------------------- #
def tag_azure_subscription(target_id: str, key: str, value: str, dry_run: bool, verbose: bool) -> str:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.resource.resources.models import Tags, TagsResource

    scope = f"/subscriptions/{target_id}"
    credential = DefaultAzureCredential()
    client = ResourceManagementClient(credential, target_id)

    existing: dict[str, str] = {}
    try:
        current = client.tags.get_at_scope(scope)
        if current and current.properties and current.properties.tags:
            existing = dict(current.properties.tags)
    except Exception:
        # No tags yet at this scope is fine; treat as empty.
        existing = {}

    action, msg = decide_action(existing, key, value)
    if verbose or action == "conflict":
        print(f"    {msg}", file=sys.stderr if action == "conflict" else sys.stdout)

    if action == "unchanged":
        return "unchanged"
    if action == "conflict":
        return "skipped"
    if dry_run:
        print(f"    [dry-run] would tag subscription {target_id}: {key}={value}")
        return "would_apply"

    merged = dict(existing)
    merged[key] = value
    client.tags.begin_create_or_update_at_scope(
        scope, TagsResource(properties=Tags(tags=merged))
    ).result()
    print(f"    tagged subscription {target_id}: {key}={value}")
    return "applied"


PROVIDERS = {
    "aws": tag_aws_account,
    "gcp": tag_gcp_project,
    "azure": tag_azure_subscription,
}


# --------------------------------------------------------------------------- #
# Input handling
# --------------------------------------------------------------------------- #
def load_resources(path: Path) -> list[dict]:
    """Load + validate the JSON entry list. Malformed entries are dropped with a warning."""
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Could not parse JSON in {path}: {e}")

    if not isinstance(data, list):
        raise SystemExit(f"Expected a JSON list of resource objects in {path}.")

    valid: list[dict] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            print(f"  [skip] entry #{i}: not an object", file=sys.stderr)
            continue
        provider = (entry.get("provider") or "").strip().lower()
        target_id = (entry.get("target_id") or "").strip()
        tag_value = (entry.get("tag_value") or "").strip()
        if not provider or not target_id or not tag_value:
            print(
                f"  [skip] entry #{i}: needs provider, target_id, tag_value "
                f"(got {entry!r})",
                file=sys.stderr,
            )
            continue
        if provider not in PROVIDERS:
            print(
                f"  [skip] entry #{i}: unknown provider '{provider}' "
                f"(supported: {', '.join(PROVIDERS)})",
                file=sys.stderr,
            )
            continue
        valid.append({"provider": provider, "target_id": target_id, "tag_value": tag_value})
    return valid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-apply the tagging_group tag to AWS accounts, GCP projects, and Azure subscriptions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input-file", type=Path, default=Path(__file__).resolve().parent / "resources.json",
        help="JSON file listing resources (default: resources.json next to this script)",
    )
    parser.add_argument("--tag-key", default=TAG_KEY_DEFAULT, help=f"Tag key to apply (default: {TAG_KEY_DEFAULT})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-entry detail")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Actually write tags (default: dry run)")
    mode.add_argument("--dry-run", action="store_true", help="Explicitly force dry run (the default)")
    args = parser.parse_args()

    dry_run = not args.apply  # dry-run unless --apply is given
    key = args.tag_key

    resources = load_resources(args.input_file)

    print(f"Input file : {args.input_file}")
    print(f"Tag key    : {key}")
    print(f"Entries    : {len(resources)}")
    print(f"Mode       : {'DRY RUN (pass --apply to make changes)' if dry_run else 'APPLY'}")
    print()

    if not resources:
        print("No valid resources to process.")
        return

    counts = {"applied": 0, "would_apply": 0, "unchanged": 0, "skipped": 0, "failed": 0}

    for entry in resources:
        provider, target_id, tag_value = entry["provider"], entry["target_id"], entry["tag_value"]
        print(f"[{provider}] {target_id} -> {key}={tag_value}")
        handler = PROVIDERS[provider]
        try:
            status = handler(target_id, key, tag_value, dry_run, args.verbose)
            counts[status] = counts.get(status, 0) + 1
        except Exception as e:
            counts["failed"] += 1
            print(f"    ERROR: {e}", file=sys.stderr)
            continue  # keep going: one failure must not stop the batch

    print()
    print("Summary")
    print("-------")
    if dry_run:
        print(f"  would apply : {counts['would_apply']}")
    else:
        print(f"  applied     : {counts['applied']}")
    print(f"  unchanged   : {counts['unchanged']}")
    print(f"  skipped     : {counts['skipped']}  (conflict - existing value kept)")
    print(f"  failed      : {counts['failed']}")

    if dry_run:
        print("\nDRY RUN: no changes were made. Re-run with --apply to write tags.")

    if counts["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
