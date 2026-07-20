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
    resource type's skip_columns is treated as a tag. Empty cell values are skipped.
"""

import re
from dataclasses import dataclass
from pathlib import Path

FILENAME_PATTERN = re.compile(
    r"make_changes-(?P<resource_type>[a-z][a-z0-9-]*)-(?P<account_id>\d{12})-\d{8}-\d{6}(?:-[^.]+)?\.csv$"
)

NAME_COLUMN = "name"   # CSV column holding the human-readable name; never applied as a tag


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


def build_tags(row: dict, config: ResourceConfig) -> list[dict]:
    """Return [{Key, Value}] from a CSV row, skipping non-tag columns."""
    tags = []
    for col, val in row.items():
        val = val.strip()
        if not val:
            continue
        if col == NAME_COLUMN or col == "region" or col == config.id_column:
            continue
        if col in config.skip_columns:
            continue
        tags.append({"Key": col, "Value": val})
    return tags
