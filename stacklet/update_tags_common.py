"""Shared CSV parsing and tag-column detection for make_changes provider scripts.

Imported by make_changes-aws.py, make_changes-gcp.py, make_changes-azure.py.
Provider-specific RESOURCE_TYPES dicts and cloud API calls live in each script.

Filename convention (all providers):
    make_changes-{resource_type}-{account_id}-{timestamp}[-comment].csv

    resource_type  Provider-defined (e.g. snapshots, volumes, instances)
    account_id     AWS account ID / GCP project number / Azure subscription ID
    comment        Optional free-text label after the timestamp (ignored by the script)

Tag column detection:
    Any CSV column that is not the resource ID, 'name', 'region', or in the
    resource type's skip_columns is treated as a tag. Placeholder values are
    skipped: an empty cell (tag absent) and the literal 'undefined' are never
    written to the cloud.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

FILENAME_PATTERN = re.compile(
    r"make_changes-(?P<resource_type>[a-z][a-z0-9-]*)-(?P<account_id>\d{12})-\d{8}-\d{6}(?:-[^.]+)?\.csv$"
)

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
    m = FILENAME_PATTERN.match(path.name)
    if not m:
        raise SystemExit(
            f"Filename '{path.name}' does not match expected pattern:\n"
            f"  make_changes-{{resource_type}}-{{account_id}}-YYYYMMDD-HHMMSS[-comment].csv\n"
            f"  Supported resource types: {', '.join(valid_types)}"
        )
    resource_type = m.group("resource_type")
    if resource_type not in valid_types:
        raise SystemExit(
            f"Unknown resource type '{resource_type}'.\n"
            f"Supported: {', '.join(valid_types)}\n"
            f"To add support, add an entry to RESOURCE_TYPES in the provider script."
        )
    return resource_type, m.group("account_id")


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
