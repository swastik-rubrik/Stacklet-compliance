#!/usr/bin/env python3
"""Apply GCP labels from a make_changes CSV to resources.

GCP's tagging equivalent is *labels*. This mirrors update_tags-aws.py but for
GCP, reusing the shared CSV/placeholder/report plumbing in update_tags_common.
Resource types (and their per-type label backends) are defined once in
gcp/gcp_resource_types.py, shared with list-resource-gcp.py.

Filename convention (shared with AWS/Azure):
    make_changes-{resource_type}-{project}-{timestamp}[-comment].csv
    e.g. make_changes-instance-my-proj-123-20260727-101112.csv

Key differences from AWS:
    * No Resource Groups Tagging API -> labels are set per-resource, not batched.
    * setLabels/patch REPLACE the whole label set, so we read current labels and
      MERGE the rbrk_* values over them (existing non-rbrk labels are preserved).
    * The target project is taken from the filename (or --project) and passed
      explicitly to every API call, so there is no "wrong account" foot-gun to
      guard against the way AWS credentials need verify_account.
    * GCP label keys/values must be lowercase [a-z0-9_-]; the API rejects
      anything else (e.g. "Prod" or a value with a "."). Such rows fail at apply
      and are reported per-resource.

Auth:
    Application Default Credentials. Run: gcloud auth application-default login

Usage:
    python3 update_tags-gcp.py <csv_file>            # dry run (default)
    python3 update_tags-gcp.py <csv_file> --apply    # apply changes
    python3 update_tags-gcp.py <csv_file> -v         # per-resource detail
    python3 update_tags-gcp.py <csv_file> -s         # dry-run counts + CSV report
"""

import argparse
import csv
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # stacklet/gcp
_STACKLET = _HERE.parent                          # stacklet/ (shared modules live here)
for _p in (str(_HERE), str(_STACKLET)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from static.gcp_resource_types import RESOURCE_TYPES
from helpers import (
    build_tags, parse_filename, TagChange, write_change_report, format_change_line,
)

OUTPUT_DIR = _STACKLET.parent / "outputs"          # repo-root/outputs


def process(config, project, rows, dry_run, verbose, verbose_out=sys.stdout):
    """rows = [(self_link, region, [{Key,Value}])]. Returns (tagged, errored, changes)."""
    tagged = errored = 0
    changes: list[TagChange] = []

    for self_link, region, new_tags in rows:
        try:
            read_current, apply_labels = config.backend_fn(self_link, project)
            current, fp = read_current()
        except Exception as e:
            print(f"  FAILED (read) {self_link}: {e}", file=sys.stderr)
            errored += 1
            continue

        merged = dict(current)
        res_changes: list[TagChange] = []
        for t in new_tags:
            k, v = t["Key"], t["Value"]
            if k not in current:
                res_changes.append(TagChange(self_link, region, k, "+", "", v))
            elif current[k] != v:
                res_changes.append(TagChange(self_link, region, k, "~", current[k], v))
            else:
                res_changes.append(TagChange(self_link, region, k, "=", current[k], v))
            merged[k] = v

        changes.extend(res_changes)
        needs = any(c.action in ("+", "~") for c in res_changes)

        if verbose and needs:
            print(f"  {self_link} ({region})", file=verbose_out)
            for c in res_changes:
                line = format_change_line(c)
                if line:
                    print(line, file=verbose_out)

        if dry_run:
            if needs:
                tagged += 1
            continue

        if not needs:
            continue
        try:
            apply_labels(merged, fp)
            tagged += 1
            if verbose:
                print(f"  Labeled {self_link} ({len(new_tags)} labels)", file=verbose_out)
        except Exception as e:
            print(f"  FAILED {self_link}: {e}", file=sys.stderr)
            errored += 1

    return tagged, errored, changes


def print_change_summary(changes: list[TagChange]) -> None:
    resources = len({c.resource_id for c in changes})
    adds      = sum(1 for c in changes if c.action == "+")
    updates   = sum(1 for c in changes if c.action == "~")
    unchanged = sum(1 for c in changes if c.action == "=")
    print(f"Label summary across {resources} resources:")
    print(f"  [+] {adds:>6}  would be added")
    print(f"  [~] {updates:>6}  would be updated")
    print(f"  [=] {unchanged:>6}  already correct")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply GCP labels from a make_changes CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("csv_file", type=Path, help="Path to make_changes CSV")
    parser.add_argument("--apply", action="store_true", help="Apply label changes (default: dry run)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-resource label details")
    parser.add_argument("--summarize", "-s", action="store_true",
                        help="Dry-run: fetch current labels, print counts, write comparison CSV")
    parser.add_argument("--project", default=None,
                        help="Override the project from the filename (used for bucket/bq API calls)")
    parser.add_argument("--log", metavar="FILE", nargs="?", const="",
                        help="Write verbose output to FILE; auto-named from input CSV if omitted (implies --verbose)")
    args = parser.parse_args()

    csv_path = args.csv_file
    if not csv_path.exists():
        raise SystemExit(f"File not found: {csv_path}")

    resource_type, project_from_name = parse_filename(csv_path, RESOURCE_TYPES)
    config = RESOURCE_TYPES[resource_type]
    project = args.project or project_from_name
    dry_run = not args.apply
    verbose = args.verbose or (args.log is not None)

    print(f"File          : {csv_path.name}")
    print(f"Resource type : {resource_type}")
    print(f"Project       : {project}")
    print(f"Mode          : {'DRY RUN (pass --apply to make changes)' if dry_run else 'APPLY'}")
    print()

    rows: list[tuple[str, str, list[dict]]] = []
    rows_skipped = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resource_id = (row.get(config.id_column) or "").strip()
            region = (row.get("region") or "").strip()
            if not resource_id:
                rows_skipped += 1
                continue
            tags = build_tags(row, config)
            if tags:
                rows.append((resource_id, region, tags))

    if rows_skipped:
        print(f"Skipped {rows_skipped} rows with missing {config.id_column}.")

    if not rows:
        print("No resources to process.")
        return

    if args.log is None:
        log_path = None
    elif args.log == "":
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        log_path = OUTPUT_DIR / f"dry-run-{csv_path.stem}.txt"
    else:
        log_path = Path(args.log)
    log_file = open(log_path, "w", encoding="utf-8") if log_path else None
    verbose_out = log_file or sys.stdout

    print(f"Processing {len(rows)} resource(s)...")
    try:
        tagged, errored, changes = process(
            config, project, rows, dry_run, verbose, verbose_out
        )
    finally:
        if log_file:
            log_file.close()

    print()
    if dry_run:
        if args.summarize and changes:
            print_change_summary(changes)
            print()
            outfile = write_change_report(changes, csv_path)
            print(f"Report written to {outfile}")
            print()
        print(f"DRY RUN: {tagged} resources would be labeled.")
        print("Run with --apply to make changes.")
    else:
        print(f"Done: {tagged} resources labeled.")
        if errored:
            sys.exit(1)


if __name__ == "__main__":
    main()
