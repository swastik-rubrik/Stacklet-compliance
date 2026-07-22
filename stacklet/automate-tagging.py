#!/usr/bin/env python3
"""Automate the tagging pipeline from listing CSV through the AWS dry-run.

For every listing CSV sitting flat in outputs/ , this:
    1. Loads that account's saved rbrk_* defaults (inputs/rbrk-values-<account>.json).
    2. Fills "undefined" cells with those defaults -- the same thing tag-editor.py's "Write make_changes file" button does. Writes
       make_changes-*.csv to inputs/ and a local dry-run-*.txt to outputs/.
       No AWS calls in this step.
    3. Runs the AWS-backed dry run -- the same thing tag-editor.py's
       "Dry Run (AWS)" button does. Fetches current tags and diffs them
       against the fill. Still no writes to AWS.
    4. Writes one combined report, outputs/tagging-automation-report-<ts>.md,
       covering every resource type processed in this run.

Usage:
    python3 automate-tagging.py                    # process every eligible listing CSV in outputs/
    python3 automate-tagging.py --only ecr s3      # restrict to specific resource types
    python3 automate-tagging.py --skip-region me-central-1
"""

import argparse
import importlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_tag_editor = importlib.import_module("tag-editor")
OUTPUT_DIR = _tag_editor.OUTPUT_DIR
INPUT_DIR = _tag_editor.INPUT_DIR
load_account_values = _tag_editor.load_account_values
write_payload = _tag_editor.write_payload
apply_dry_run_payload = _tag_editor.apply_dry_run_payload

from static.resource_type_update import RESOURCE_TYPES

_LISTING_RE = re.compile(r"^(?P<resource_type>[a-z][a-z0-9-]*)-(?P<account_id>\d{12})-\d{8}-\d{6}\.csv$")


def find_listing_csvs(only_types=None):
    """Flat, top-level listing CSVs in outputs/ eligible for processing."""
    if not OUTPUT_DIR.exists():
        return []
    found = []
    for p in sorted(OUTPUT_DIR.glob("*.csv")):
        if p.name.startswith("make_changes-") or p.name.startswith("dry-run-"):
            continue
        m = _LISTING_RE.match(p.name)
        if not m:
            print(f"Skipping {p.name}: doesn't match <type>-<account>-<timestamp>.csv", file=sys.stderr)
            continue
        resource_type = m.group("resource_type")
        if resource_type not in RESOURCE_TYPES:
            print(f"Skipping {p.name}: resource type '{resource_type}' not in update-side registry", file=sys.stderr)
            continue
        if only_types and resource_type not in only_types:
            continue
        found.append((p, resource_type, m.group("account_id")))
    return found


def process_one(path: Path, resource_type: str, account_id: str, skip_regions: list[str]) -> dict:
    """Run the fill step + AWS dry-run for one listing CSV. Returns a result dict."""
    result = {"file": path.name, "resource_type": resource_type, "account_id": account_id, "ok": False}

    values = load_account_values(account_id)
    result["had_account_values"] = bool(values)

    try:
        write_result = write_payload({"file": path.name, "values": values, "overwrite": False})
    except Exception as exc:
        result["error"] = f"write step failed: {exc}"
        return result

    result["write"] = write_result
    if write_result.get("warnings"):
        result["error"] = "; ".join(write_result["warnings"])
        return result

    try:
        dry_run_result = apply_dry_run_payload({
            "make_changes_file": write_result["out_name"],
            "skip_regions": skip_regions,
        })
    except SystemExit as exc:
        result["error"] = f"AWS dry-run aborted: {exc}"
        return result
    except Exception as exc:
        result["error"] = f"AWS dry-run failed: {exc}"
        return result

    if not dry_run_result.get("ok"):
        result["error"] = dry_run_result.get("error", "unknown dry-run failure")
        return result

    result["ok"] = True
    result["dry_run"] = dry_run_result
    return result


def write_report(results: list[dict], skip_regions: list[str]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = OUTPUT_DIR / f"tagging-automation-report-{timestamp}.md"

    ok_results = [r for r in results if r["ok"]]
    failed_results = [r for r in results if not r["ok"]]

    lines = [
        f"# Tagging automation report -- {timestamp} UTC",
        "",
        f"Processed {len(results)} listing CSV(s): {len(ok_results)} OK, {len(failed_results)} failed.",
    ]
    if skip_regions:
        lines.append(f"Skipped regions: {', '.join(skip_regions)}")
    lines += [
        "",
        "**Apply step was NOT run.** Review below, then apply manually via "
        "tag-editor.py's \"Apply Tags\" button or "
        "`update_tags-aws.py <make_changes_file> --apply`.",
        "",
    ]

    if ok_results:
        lines += [
            "## Summary",
            "",
            "| Resource type | Account | Resources | Adds | Updates | Unchanged | Make-changes file |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in ok_results:
            dr = r["dry_run"]
            s = dr.get("summary", {"total_resources": 0, "adds": 0, "updates": 0, "unchanged": 0})
            lines.append(
                f"| {r['resource_type']} | {r['account_id']} | {s['total_resources']} | "
                f"{s['adds']} | {s['updates']} | {s['unchanged']} | {r['write']['out_name']} |"
            )
        lines.append("")

    if failed_results:
        lines.append("## Failed")
        lines.append("")
        for r in failed_results:
            lines.append(f"- **{r['file']}** ({r['resource_type']}, {r['account_id']}): {r['error']}")
        lines.append("")

    if ok_results:
        lines.append("## Per-type detail")
        for r in ok_results:
            dr = r["dry_run"]
            w = r["write"]
            lines += [
                "",
                f"### {r['resource_type']} -- {r['account_id']}",
                f"- Listing CSV: `{r['file']}`",
                f"- Make-changes CSV: `{w['out_path']}`",
                f"- Local dry-run report: `{w['report_path']}`",
                f"- Cells filled: {w['stats']['total_filled']} across {w['stats']['rows_changed']} rows"
                + ("" if r["had_account_values"] else " (no stored account defaults were found for this account)"),
            ]
            if dr.get("message"):
                lines.append(f"- {dr['message']}")
                continue
            if dr.get("rows_skipped"):
                lines.append(f"- Rows skipped (missing id/region): {dr['rows_skipped']}")
            lines += ["", "| Region | Resources | Tagged (would-be) | Errored |", "|---|---|---|---|"]
            for region, info in dr.get("per_region", {}).items():
                lines.append(f"| {region} | {info['resources']} | {info['tagged']} | {info['errored']} |")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="TYPE", help="Restrict to these resource types")
    parser.add_argument("--skip-region", metavar="REGION", action="append", default=[], help="Skip this region (may be repeated)")
    args = parser.parse_args()

    listings = find_listing_csvs(only_types=set(args.only) if args.only else None)
    if not listings:
        print("No eligible listing CSVs found in outputs/.", file=sys.stderr)
        return

    results = []
    for path, resource_type, account_id in listings:
        print(f"Processing {path.name} ({resource_type}, {account_id})...", file=sys.stderr)
        result = process_one(path, resource_type, account_id, args.skip_region)
        if result["ok"]:
            dr = result["dry_run"]
            if dr.get("message"):
                print(f"  OK: {dr['message']}", file=sys.stderr)
            else:
                s = dr["summary"]
                print(f"  OK: {s['total_resources']} resources, additions-{s['adds']} updates-{s['updates']} unchanged-{s['unchanged']}", file=sys.stderr)
        else:
            print(f"  FAILED: {result['error']}", file=sys.stderr)
        results.append(result)

    report_path = write_report(results, args.skip_region)
    print(f"\nReport written to {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
