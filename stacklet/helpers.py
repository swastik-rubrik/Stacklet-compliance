"""Shared CSV parsing and tag-column detection for make_changes provider scripts.

Filename convention (all providers):
    make_changes-{resource_type}-{account_id}-{timestamp}.csv

    resource_type  Provider-defined (e.g. snapshots, volumes, instances)
    account_id     AWS account ID / GCP project number / Azure subscription ID

Tag column detection:
    Any CSV column that is not the resource ID, 'name', 'region', or in the
    resource type's skip_columns is treated as a tag. Placeholder values are
    skipped: an empty cell (tag absent) and the literal 'undefined' are never
    written to the cloud.
"""

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

# AWS-strict validator (account_id = 12 digits). Kept for callers that only need
# a boolean "is this a well-formed AWS make_changes name?" check (e.g. tag-editor).
FILENAME_PATTERN = re.compile(r"make_changes-(?P<resource_type>[a-z][a-z0-9-]*)-(?P<account_id>\d{12})-\d{8}-\d{6}(?:-[^.]+)?\.csv$")

# accepts any account_id shape - AWS 12-digit account IDs AND GCP project IDs (lowercase letters/digits/hyphens, variable length) -- without ambiguity.
_PARSE_PATTERN = re.compile(r"make_changes-(?P<body>.+?)-(?P<timestamp>\d{8}-\d{6})(?:-[^.]+)?\.csv$")

NAME_COLUMN = "name"   # CSV column holding the human-readable name; never applied as a tag

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

class TagChange(NamedTuple):
    resource_id: str
    region: str
    tag_key: str
    action: str    # "+" add, "~" update, "=" unchanged
    old_value: str
    new_value: str


def write_change_report(changes: list[TagChange], input_path: Path) -> Path:
    """Write a dry-run change report to outputs/dry-run-{input_stem}.csv."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / f"dry-run-{input_path.stem}.csv"
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["resource_id", "region", "tag_key", "action", "old_value", "new_value"])
        for c in changes:
            writer.writerow([c.resource_id, c.region, c.tag_key, c.action, c.old_value, c.new_value])
    return outfile


@dataclass(frozen=True)
class ResourceConfig:
    """Describes how CSV columns map to a resource type."""
    id_column: str           # CSV column holding the resource ID
    skip_columns: frozenset  # CSV columns that are metadata, not tags


def parse_filename(path: Path, valid_types: dict) -> tuple[str, str]:
    """Return (resource_type, account_id) parsed from a make_changes filename.

    Exits with a clear error if the filename doesn't match the convention or
    the resource type isn't in valid_types.
    """
    m = _PARSE_PATTERN.match(path.name)
    if not m:
        raise SystemExit(
            f"Filename '{path.name}' does not match expected pattern:\n"
            f"  make_changes-{{resource_type}}-{{account_id}}-YYYYMMDD-HHMMSS[-comment].csv\n"
            f"  Supported resource types: {', '.join(valid_types)}"
        )
    body = m.group("body")   # "{resource_type}-{account_id}"

    # resource_type = longest valid key such that body == key or body starts with key + "-".
    candidates = [t for t in valid_types if body == t or body.startswith(f"{t}-")]
    if not candidates:
        raise SystemExit(
            f"Unknown resource type in '{path.name}'.\n"
            f"Supported: {', '.join(valid_types)}\n"
            f"To add support, add an entry to RESOURCE_TYPES in the provider script."
        )
    resource_type = max(candidates, key=len)

    account_id = body[len(resource_type) + 1:]   # drop "resource_type-"
    if not account_id:
        raise SystemExit(
            f"Could not parse account_id/project from '{path.name}'.\n"
            f"  Expected: make_changes-{resource_type}-{{account_id}}-YYYYMMDD-HHMMSS.csv"
        )
    return resource_type, account_id


def is_placeholder(value: str) -> bool:
    """True if a tag value must never be written: empty or the literal 'undefined'.
    """
    v = (value or "").strip()
    return v == "" or v.lower() == "undefined"


def build_tags(row: dict, config: ResourceConfig) -> list[dict]:
    """Return [{Key, Value}] from a CSV row, skipping non-tag and placeholder cells.

    A column is skipped when it is metadata (name/region/id/skip_columns) or when
    its value is a placeholder (empty or the literal 'undefined'). This is the
    single chokepoint that keeps dry-run and apply consistent: neither writes an
    empty tag nor a literal 'undefined' back to the cloud.
    """
    tags = []
    for col, val in row.items():
        if col == NAME_COLUMN or col == "region" or col == config.id_column:
            continue
        if col in config.skip_columns:
            continue
        if is_placeholder(val):
            continue
        tags.append({"Key": col, "Value": val.strip()})
    return tags


def format_change_line(c: TagChange) -> str | None:
    """One indented verbose line for a change, or None if unchanged ('=').

    Shared by update_tags-aws.py --log and tag-editor so both render identically:
        [~] key: old → new       (update)
        [+] key = new            (add)
        [-] key: old → (removed) (remove)
    """
    if c.action == "=":
        return None
    if c.action == "~":
        return f"    [~] {c.tag_key}: {c.old_value} → {c.new_value}"
    if c.action == "-":
        return f"    [-] {c.tag_key}: {c.old_value} → (removed)"
    return f"    [+] {c.tag_key} = {c.new_value}"


def write_change_report_txt(changes: list[TagChange], input_path: Path) -> Path:
    """Write a human-readable dry-run report to outputs/dry-run-{stem}.txt.

    Same per-resource layout as update_tags-aws.py --log:
        <rid> (<region>)
            [~] key: old → new
            [+] key = new
    Resources are grouped in first-seen order; only resources with at least one
    change are listed.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / f"dry-run-{input_path.stem}.txt"

    by_resource: dict[tuple[str, str], list[str]] = {}
    for c in changes:
        line = format_change_line(c)
        if line is None:
            continue
        by_resource.setdefault((c.resource_id, c.region), []).append(line)

    with open(outfile, "w", encoding="utf-8") as f:
        for (rid, region), lines in by_resource.items():
            f.write(f"  {rid} ({region})\n")
            for line in lines:
                f.write(line + "\n")
    return outfile


def resolve_project(explicit: str | None = None) -> str:
    """Return the GCP project to act on.

    Precedence: explicit arg -> $GOOGLE_CLOUD_PROJECT / $GCLOUD_PROJECT -> the
    Application Default Credentials project (the "present" project you logged in
    with). Shared by the GCP lister and apply automations so "just use the
    current project" behaves identically everywhere.
    """
    if explicit:
        return explicit
    env = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if env:
        return env
    try:
        import google.auth
        _, project = google.auth.default()
    except Exception as e:
        raise SystemExit(
            f"Could not determine GCP project ({e}).\n"
            f"Pass --project, set $GOOGLE_CLOUD_PROJECT, or run "
            f"'gcloud auth application-default login'."
        )
    if not project:
        raise SystemExit(
            "No default project found. Pass --project or set $GOOGLE_CLOUD_PROJECT."
        )
    return project


def split_type_project(body: str, valid_types) -> tuple[str, str] | None:
    """Split a '<resource_type>-<account_or_project>' body against known types.
    """
    candidates = [t for t in valid_types if body == t or body.startswith(f"{t}-")]
    if not candidates:
        return None
    rtype = max(candidates, key=len)
    ident = body[len(rtype) + 1:]
    return (rtype, ident) if ident else None
