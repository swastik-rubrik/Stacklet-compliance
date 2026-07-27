#!/usr/bin/env python3
"""Automate the GCP tagging pipeline: fill listing CSVs -> make_changes -> dry-run.

GCP sibling of automate-tagging.py. Deliberately standalone: it does NOT depend
on the AWS-only tag-editor.py. For every GCP listing CSV sitting flat in
outputs/ (named {type}-{project}-{timestamp}.csv), this:

    1. Loads that project's saved rbrk_* defaults from
       inputs/rbrk-values-<project>.json (same flat {rbrk_key: value} format the
       AWS store uses, just keyed by project instead of a 12-digit account).
    2. Fills placeholder cells (empty or the literal "undefined") in the rbrk_*
       columns with those defaults. Real existing values are left untouched
       unless --overwrite is passed. Writes make_changes-{type}-{project}-{ts}.csv
       to inputs/. No GCP calls in this step.
    3. Unless --no-dry-run, runs `update_tags-gcp.py <make_changes> -s` (dry run:
       reads current labels from GCP, diffs, writes outputs/dry-run-*.csv). No
       writes to GCP.
    4. Writes one combined report, outputs/gcp-tagging-automation-report-<ts>.md.

The apply step is never run here -- apply each file with
`update_tags-gcp.py <make_changes_file> --apply` after reviewing.

Usage:
    python3 gcp/automate-tagging-gcp.py
    python3 gcp/automate-tagging-gcp.py --only bucket instance
    python3 gcp/automate-tagging-gcp.py --no-dry-run
    python3 gcp/automate-tagging-gcp.py --overwrite
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent        # stacklet/gcp
STACKLET = HERE.parent                          # stacklet/
REPO = STACKLET.parent                          # repo root (holds outputs/, inputs/)
for _p in (str(HERE), str(STACKLET)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from helpers import is_placeholder, split_type_project   # shared helpers
from static.gcp_resource_types import RESOURCE_TYPES      # single source of truth

UPDATE_SCRIPT = HERE / "update_tags-gcp.py"

OUTPUT_DIR = REPO / "outputs"
INPUT_DIR = REPO / "inputs"

# Listing CSV: {type}-{project}-{YYYYMMDD}-{HHMMSS}.csv (no make_changes prefix).
# Anchor on the timestamp; the type/project split is resolved against
# RESOURCE_TYPES (longest matching key wins), like update_tags_common.parse_filename.
_LISTING_RE = re.compile(r"^(?P<body>.+?)-(?P<timestamp>\d{8}-\d{6})\.csv$")


def find_listing_csvs(only_types=None):
    """Flat GCP listing CSVs in outputs/ eligible for processing."""
    if not OUTPUT_DIR.exists():
        return []
    found = []
    for p in sorted(OUTPUT_DIR.glob("*.csv")):
        if p.name.startswith("make_changes-") or p.name.startswith("dry-run-"):
            continue
        m = _LISTING_RE.match(p.name)
        if not m:
            continue
        split = split_type_project(m.group("body"), RESOURCE_TYPES)
        if not split:
            continue   # not a GCP type -> likely an AWS listing; leave it alone
        resource_type, project = split
        if only_types and resource_type not in only_types:
            continue
        found.append((p, resource_type, project))
    return found


def project_values_path(project: str) -> Path:
    return INPUT_DIR / f"rbrk-values-{project}.json"


def load_project_values(project: str) -> dict:
    """Return the stored {rbrk_key: value} map for a project ({} if none)."""
    path = project_values_path(project)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: str(v).strip()
        for k, v in data.items()
        if isinstance(k, str) and k.startswith("rbrk_") and str(v).strip()
    }


def fill_and_write(path: Path, project: str, values: dict, overwrite: bool) -> dict:
    """Fill rbrk_* placeholders and write make_changes CSV to inputs/. Returns stats."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = [dict(r) for r in reader]

    rbrk_cols = [c for c in fieldnames if c.startswith("rbrk_")]
    per_col = {c: 0 for c in rbrk_cols}
    rows_changed = 0
    for r in rows:
        changed = False
        for c in rbrk_cols:
            fill_val = (values.get(c) or "").strip()
            if not fill_val:
                continue   # no default for this column -> leave cell as-is
            cur = r.get(c) or ""
            if overwrite or is_placeholder(cur):
                if cur.strip() != fill_val:
                    r[c] = fill_val
                    per_col[c] += 1
                    changed = True
        if changed:
            rows_changed += 1

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_name = f"make_changes-{path.name}"
    out_path = INPUT_DIR / out_name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "out_name": out_name,
        "out_path": str(out_path),
        "rbrk_cols": rbrk_cols,
        "total_filled": sum(per_col.values()),
        "rows_changed": rows_changed,
        "row_count": len(rows),
    }


def run_dry_run(make_changes_path: Path) -> dict:
    """Invoke update_tags-gcp.py <file> -s and capture the outcome."""
    proc = subprocess.run(
        [sys.executable, str(UPDATE_SCRIPT), str(make_changes_path), "-s"],
        capture_output=True, text=True,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def process_one(path: Path, resource_type: str, project: str, do_dry_run: bool, overwrite: bool) -> dict:
    result = {"file": path.name, "resource_type": resource_type, "project": project, "ok": False}
    values = load_project_values(project)
    result["had_project_values"] = bool(values)

    try:
        fill = fill_and_write(path, project, values, overwrite)
    except Exception as exc:
        result["error"] = f"fill step failed: {exc}"
        return result
    result["fill"] = fill

    if do_dry_run:
        dr = run_dry_run(Path(fill["out_path"]))
        result["dry_run"] = dr
        if not dr["ok"]:
            # A GCP permission/API error here is informative, not fatal to the batch.
            result["error"] = (dr["stderr"] or dr["stdout"] or "dry-run failed").strip().splitlines()[-1]
            return result

    result["ok"] = True
    return result


def write_report(results: list[dict], did_dry_run: bool) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = OUTPUT_DIR / f"gcp-tagging-automation-report-{timestamp}.md"

    ok = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    lines = [
        f"# GCP tagging automation report -- {timestamp} UTC",
        "",
        f"Processed {len(results)} listing CSV(s): {len(ok)} OK, {len(failed)} failed.",
        "",
        "**Apply step was NOT run.** Review, then apply each file with "
        "`update_tags-gcp.py <make_changes_file> --apply`.",
        "",
        "## Summary",
        "",
        "| Type | Project | Rows | Cells filled | Make-changes file |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        f = r.get("fill", {})
        lines.append(
            f"| {r['resource_type']} | {r['project']} | {f.get('row_count', '-')} | "
            f"{f.get('total_filled', '-')} | {f.get('out_name', '-')} |"
        )
    lines.append("")

    if failed:
        lines += ["## Failed / needs attention", ""]
        for r in failed:
            lines.append(f"- **{r['file']}** ({r['resource_type']}, {r['project']}): {r.get('error', 'unknown')}")
        lines.append("")

    for r in ok:
        f = r["fill"]
        lines += [
            f"### {r['resource_type']} -- {r['project']}",
            f"- Make-changes CSV: `{f['out_path']}`",
            f"- Cells filled: {f['total_filled']} across {f['rows_changed']} row(s)"
            + ("" if r["had_project_values"] else " (no stored defaults for this project)"),
        ]
        if did_dry_run and r.get("dry_run"):
            tail = (r["dry_run"]["stdout"] or "").strip().splitlines()
            if tail:
                lines.append(f"- Dry-run: {tail[-1]}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="TYPE", help="Restrict to these resource types")
    parser.add_argument("--no-dry-run", action="store_true", help="Only fill + write make_changes; skip the GCP dry-run")
    parser.add_argument("--overwrite", action="store_true", help="Also overwrite real (non-placeholder) rbrk_ values with defaults")
    args = parser.parse_args()

    only_types = set(args.only) if args.only else None
    if only_types:
        unknown = only_types - set(RESOURCE_TYPES)
        if unknown:
            sys.exit(f"ERROR: unknown --only types: {', '.join(sorted(unknown))}\n"
                     f"       known GCP types: {', '.join(RESOURCE_TYPES)}")

    listings = find_listing_csvs(only_types=only_types)
    if not listings:
        print("No eligible GCP listing CSVs found in outputs/.", file=sys.stderr)
        return

    do_dry_run = not args.no_dry_run
    results = []
    for path, resource_type, project in listings:
        print(f"Processing {path.name} ({resource_type}, {project})...", file=sys.stderr)
        result = process_one(path, resource_type, project, do_dry_run, args.overwrite)
        f = result.get("fill", {})
        if result["ok"]:
            print(f"  OK: filled {f.get('total_filled', 0)} cell(s) -> {f.get('out_name')}", file=sys.stderr)
        else:
            print(f"  {'FILLED but dry-run issue' if f else 'FAILED'}: {result.get('error')}", file=sys.stderr)
        results.append(result)

    report_path = write_report(results, do_dry_run)
    print(f"\nReport written to {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
