#!/usr/bin/env python3
"""List GCP resources with their labels.

Auth:
     Run once: gcloud auth application-default login
    Project is taken from --project, else $GOOGLE_CLOUD_PROJECT / $GCLOUD_PROJECT,
    else the ADC default project.

Usage:
    python3 list-resource-gcp.py --resource-type instance
    python3 list-resource-gcp.py --resource-type bucket --project my-proj-123

Extending to new resource types:
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # stacklet/gcp
_STACKLET = _HERE.parent                          # stacklet/
for _p in (str(_HERE), str(_STACKLET)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from static.gcp_resource_types import RESOURCE_TYPES
from helpers import resolve_project

OUTPUT_DIR = _STACKLET.parent / "outputs"          # repo-root/outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="List GCP resources with their labels.")
    parser.add_argument(
        "--resource-type", choices=list(RESOURCE_TYPES), default="instance",
        help="Resource type to list (default: instance)",
    )
    parser.add_argument(
        "--project", default=None,
        help="GCP project ID (default: $GOOGLE_CLOUD_PROJECT or ADC default)",
    )
    args = parser.parse_args()

    project = resolve_project(args.project)
    config = RESOURCE_TYPES[args.resource_type]
    meta_columns = list(config.meta_columns)

    print(f"Project       : {project}", file=sys.stderr)
    print(f"Resource type : {args.resource_type}", file=sys.stderr)
    print("Listing...", file=sys.stderr)

    resources = config.list_fn(project)

    # Collect all unique rbrk_* label keys across resources.
    rbrk_keys = sorted({
        k for r in resources for k in r["labels"] if k.startswith("rbrk_")
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    outfile = OUTPUT_DIR / f"{args.resource_type}-{project}-{timestamp}.csv"

    with open(outfile, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["name", "region", config.id_column] + meta_columns + rbrk_keys)
        for r in resources:
            writer.writerow(
                [r["name"], r["region"], r["self_link"]]
                + r["meta"]
                + [r["labels"].get(k, "") for k in rbrk_keys]
            )

    # Summary
    loc_counts: dict[str, int] = {}
    for r in resources:
        loc_counts[r["region"]] = loc_counts.get(r["region"], 0) + 1

    print(f"\nSummary:", file=sys.stderr)
    print(f"{'Location':<25} {args.resource_type:>12}", file=sys.stderr)
    print("-" * 38, file=sys.stderr)
    for loc, count in sorted(loc_counts.items()):
        print(f"{loc:<25} {count:>12}", file=sys.stderr)
    print("-" * 38, file=sys.stderr)
    print(f"{'Total':<25} {len(resources):>12}", file=sys.stderr)
    print(f"\nOutput written to {outfile}", file=sys.stderr)


if __name__ == "__main__":
    main()
