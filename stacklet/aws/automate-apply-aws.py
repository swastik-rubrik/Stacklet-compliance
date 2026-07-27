#!/usr/bin/env python3
"""Automate the apply step: push every make_changes CSV in inputs/ to AWS.

This is the automated equivalent of clicking tag-editor.py's "Apply Tags" button
(or running `update_tags-aws.py <file> --apply`) once per file. It iterates over
the make_changes-*.csv files sitting flat in inputs/ and applies each to AWS.

Usage:
    python3 scripts/automate-apply.py                    # apply every make_changes file for the selected types
    python3 scripts/automate-apply.py --only s3 ebs      # restrict to specific resource types
    python3 scripts/automate-apply.py --skip-region me-central-1
"""

import argparse
import csv
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent      # stacklet/aws (holds tag-editor.py, static/)
STACKLET = HERE.parent                        # stacklet/ (shared helpers.py)
for _p in (str(HERE), str(STACKLET)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_tag_editor = importlib.import_module("tag-editor")
OUTPUT_DIR = _tag_editor.OUTPUT_DIR
INPUT_DIR = _tag_editor.INPUT_DIR
apply_payload = _tag_editor.apply_payload

from helpers import FILENAME_PATTERN
from static.resource_type_update import RESOURCE_TYPES
from static.selection import load_selection


def find_make_changes_csvs(only_types=None):
    """Flat make_changes-*.csv files in inputs/ eligible for applying."""
    if not INPUT_DIR.exists():
        return []
    found = []
    for p in sorted(INPUT_DIR.glob("make_changes-*.csv")):
        m = FILENAME_PATTERN.match(p.name)
        if not m:
            print(f"Skipping {p.name}: doesn't match make_changes-<type>-<account>-<ts>.csv", file=sys.stderr)
            continue
        resource_type = m.group("resource_type")
        if resource_type not in RESOURCE_TYPES:
            print(f"Skipping {p.name}: resource type '{resource_type}' not in update-side registry", file=sys.stderr)
            continue
        if only_types and resource_type not in only_types:
            continue
        found.append((p, resource_type, m.group("account_id")))
    return found


def has_rbrk_header(path: Path) -> bool:
    """True if the CSV's header row has at least one rbrk_* column."""
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    return any(col.strip().startswith("rbrk_") for col in header)


def apply_one(path: Path, resource_type: str, account_id: str, skip_regions: list[str]) -> dict:
    """Apply one make_changes CSV to AWS. Returns a result dict."""
    result = {"file": path.name, "resource_type": resource_type, "account_id": account_id, "ok": False}
    try:
        payload = apply_payload({"make_changes_file": path.name, "skip_regions": skip_regions})
    except SystemExit as exc:
        result["error"] = f"apply aborted: {exc}"
        return result
    except Exception as exc:
        result["error"] = f"apply failed: {exc}"
        return result

    if not payload.get("ok"):
        result["error"] = payload.get("error", "unknown apply failure")
        return result

    result["ok"] = True
    result["apply"] = payload
    return result


def write_report(results: list[dict], skipped_no_rbrk: list[str], skip_regions: list[str]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = OUTPUT_DIR / f"apply-automation-report-{timestamp}.md"

    ok_results = [r for r in results if r["ok"]]
    failed_results = [r for r in results if not r["ok"]]

    lines = [
        f"# Apply automation report -- {timestamp} UTC",
        "",
        f"Applied {len(results)} make_changes file(s): {len(ok_results)} OK, {len(failed_results)} failed.",
        "**Tags were written to AWS.**",
    ]
    if skip_regions:
        lines.append(f"Skipped regions: {', '.join(skip_regions)}")
    if skipped_no_rbrk:
        lines.append(f"Skipped (no rbrk_* column in header): {', '.join(skipped_no_rbrk)}")
    lines.append("")

    if ok_results:
        lines += [
            "## Summary",
            "",
            "| Resource type | Account | Tagged | Unchanged | Errored | File |",
            "|---|---|---|---|---|---|",
        ]
        for r in ok_results:
            a = r["apply"]
            lines.append(
                f"| {r['resource_type']} | {r['account_id']} | "
                f"{a.get('total_tagged', 0)} | {a.get('total_unchanged', 0)} | "
                f"{a.get('total_errored', 0)} | {r['file']} |"
            )
        lines.append("")

    if failed_results:
        lines += ["## Failed", ""]
        for r in failed_results:
            lines.append(f"- **{r['file']}** ({r['resource_type']}, {r['account_id']}): {r['error']}")
        lines.append("")

    if ok_results:
        lines.append("## Per-file detail")
        for r in ok_results:
            a = r["apply"]
            lines += ["", f"### {r['resource_type']} -- {r['account_id']}", f"- File: `{r['file']}`"]
            if a.get("message"):
                lines.append(f"- {a['message']}")
                continue
            if a.get("rows_skipped"):
                lines.append(f"- Rows skipped (missing id/region): {a['rows_skipped']}")
            lines += ["", "| Region | Resources | Tagged | Unchanged | Errored |", "|---|---|---|---|---|"]
            for region, info in a.get("per_region", {}).items():
                lines.append(
                    f"| {region} | {info['resources']} | {info['tagged']} | "
                    f"{info.get('unchanged', 0)} | {info['errored']} |"
                )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="TYPE", help="Restrict to these resource types")
    parser.add_argument("--skip-region", metavar="REGION", action="append", default=[], help="Skip this region (may be repeated)")
    args = parser.parse_args()

    # Selection precedence: explicit --only > stacklet-resource.json > all files.
    try:
        selection = load_selection()
    except ValueError as e:
        sys.exit(f"ERROR: {e}")

    if args.only:
        only_types = set(args.only)
        print(f"Restricting to --only: {', '.join(sorted(only_types))}", file=sys.stderr)
    elif selection:
        only_types = set(selection)
        print(f"Restricting to stacklet-resource.json ({len(only_types)} type(s)): "
              f"{', '.join(selection)}", file=sys.stderr)
        unknown = [t for t in selection if t not in RESOURCE_TYPES]
        if unknown:
            print(f"Ignoring {len(unknown)} selected type(s) not in the update "
                  f"registry: {', '.join(unknown)}", file=sys.stderr)
    else:
        only_types = None
        print("No selection in stacklet-resource.json (empty/missing) -> "
              "applying every make_changes file in inputs/.", file=sys.stderr)

    candidates = find_make_changes_csvs(only_types=only_types)
    if not candidates:
        print("No eligible make_changes CSVs found in inputs/.", file=sys.stderr)
        return

    # The one guard: header must contain an rbrk_* column.
    to_apply, skipped_no_rbrk = [], []
    for path, resource_type, account_id in candidates:
        if has_rbrk_header(path):
            to_apply.append((path, resource_type, account_id))
        else:
            skipped_no_rbrk.append(path.name)
            print(f"Skipping {path.name}: no rbrk_* column in header", file=sys.stderr)

    if not to_apply:
        print("Nothing to apply (no file had an rbrk_* column).", file=sys.stderr)
        return

    results = []
    for path, resource_type, account_id in to_apply:
        print(f"Applying {path.name} ({resource_type}, {account_id})...", file=sys.stderr)
        result = apply_one(path, resource_type, account_id, args.skip_region)
        if result["ok"]:
            a = result["apply"]
            if a.get("message"):
                print(f"  OK: {a['message']}", file=sys.stderr)
            else:
                print(f"  OK: {a.get('total_tagged', 0)} tagged, "
                      f"{a.get('total_unchanged', 0)} already correct, "
                      f"{a.get('total_errored', 0)} errored", file=sys.stderr)
        else:
            print(f"  FAILED: {result['error']}", file=sys.stderr)
        results.append(result)

    report_path = write_report(results, skipped_no_rbrk, args.skip_region)
    print(f"\nReport written to {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
