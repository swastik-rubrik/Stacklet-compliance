#!/usr/bin/env python3
"""Automate the GCP apply step: push every make_changes CSV in inputs/ to GCP.

GCP sibling of automate-apply.py. Instead of naming a file per project, point it
at inputs/ and it finds every GCP make_changes-*.csv, filters to the resource
types in the registry (gcp/gcp_resource_types.py), requires an rbrk_* column,
and applies each via `update_tags-gcp.py <file> --apply`. AWS make_changes files
in the same folder are ignored (their type isn't a GCP type).

Usage:
    python3 gcp/automate-apply-gcp.py                 # apply every GCP make_changes file
    python3 gcp/automate-apply-gcp.py --only bucket   # restrict to specific types
    python3 gcp/automate-apply-gcp.py --project X      # only files for this project
    python3 gcp/automate-apply-gcp.py --dry-run        # preview (runs -s, writes NOTHING to GCP)
"""

import argparse
import csv
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent        # stacklet/gcp
STACKLET = HERE.parent                          # stacklet/
REPO = STACKLET.parent                          # repo root
for _p in (str(HERE), str(STACKLET)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from static.gcp_resource_types import RESOURCE_TYPES
from helpers import resolve_project, split_type_project

INPUT_DIR = REPO / "inputs"
OUTPUT_DIR = REPO / "outputs"
UPDATE_SCRIPT = HERE / "update_tags-gcp.py"

# make_changes-{type}-{project}-{YYYYMMDD}-{HHMMSS}[-comment].csv
_MC_RE = re.compile(r"^make_changes-(?P<body>.+?)-(?P<timestamp>\d{8}-\d{6})(?:-[^.]+)?\.csv$")


def find_make_changes_csvs(only_types=None, only_project=None):
    """GCP make_changes-*.csv files in inputs/ eligible for applying."""
    if not INPUT_DIR.exists():
        return []
    found = []
    for p in sorted(INPUT_DIR.glob("make_changes-*.csv")):
        m = _MC_RE.match(p.name)
        if not m:
            continue
        split = split_type_project(m.group("body"), RESOURCE_TYPES)
        if not split:
            continue   # not a GCP type -> likely an AWS make_changes file; ignore
        resource_type, project = split
        if only_types and resource_type not in only_types:
            continue
        if only_project and project != only_project:
            continue
        found.append((p, resource_type, project))
    return found


def has_rbrk_header(path: Path) -> bool:
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    return any(col.strip().startswith("rbrk_") for col in header)


def run_update(path: Path, dry_run: bool) -> dict:
    """Invoke update_tags-gcp.py <file> with --apply (or -s for dry-run)."""
    flag = "-s" if dry_run else "--apply"
    proc = subprocess.run(
        [sys.executable, str(UPDATE_SCRIPT), str(path), flag],
        capture_output=True, text=True,
    )
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def write_report(results: list[dict], skipped_no_rbrk: list[str], dry_run: bool) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = OUTPUT_DIR / f"gcp-apply-automation-report-{timestamp}.md"

    ok = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    lines = [
        f"# GCP apply automation report -- {timestamp} UTC",
        "",
        f"Processed {len(results)} make_changes file(s): {len(ok)} OK, {len(failed)} failed.",
        ("**Dry run -- nothing was written to GCP.**" if dry_run
         else "**Labels were written to GCP.**"),
    ]
    if skipped_no_rbrk:
        lines.append(f"Skipped (no rbrk_* column in header): {', '.join(skipped_no_rbrk)}")
    lines += ["", "## Summary", "", "| Type | Project | Result | File |", "|---|---|---|---|"]
    for r in results:
        tail = (r["run"]["stdout"] or "").strip().splitlines()
        summary = tail[-1] if tail else ("OK" if r["ok"] else "FAILED")
        lines.append(f"| {r['resource_type']} | {r['project']} | {summary} | {r['file']} |")
    lines.append("")

    if failed:
        lines += ["## Failed", ""]
        for r in failed:
            err = (r["run"]["stderr"] or r["run"]["stdout"] or "").strip().splitlines()
            lines.append(f"- **{r['file']}** ({r['resource_type']}, {r['project']}): "
                         f"{err[-1] if err else 'unknown error'}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="TYPE", help="Restrict to these resource types")
    parser.add_argument("--project", metavar="PROJECT",
                        help="Project whose make_changes files to apply (default: the current gcloud/ADC project)")
    parser.add_argument("--all-projects", action="store_true",
                        help="Apply every GCP make_changes file regardless of project (ignores --project)")
    parser.add_argument("--dry-run", action="store_true", help="Preview via update_tags-gcp -s; write NOTHING to GCP")
    args = parser.parse_args()

    only_types = set(args.only) if args.only else None
    if only_types:
        unknown = only_types - set(RESOURCE_TYPES)
        if unknown:
            sys.exit(f"ERROR: unknown --only types: {', '.join(sorted(unknown))}\n"
                     f"       known GCP types: {', '.join(RESOURCE_TYPES)}")

    # Default scope = the current project (resolved from --project / env / ADC),
    # so you never type a make_changes filename. --all-projects opts out.
    if args.all_projects:
        project = None
        print("Scope: ALL projects", file=sys.stderr)
    else:
        project = resolve_project(args.project)
        print(f"Scope: project '{project}'", file=sys.stderr)

    candidates = find_make_changes_csvs(only_types=only_types, only_project=project)
    if not candidates:
        where = "any project" if project is None else f"project '{project}'"
        print(f"No eligible GCP make_changes CSVs found in inputs/ for {where}.", file=sys.stderr)
        return

    # Guard: header must contain an rbrk_* column (same guard as the AWS apply automation).
    to_apply, skipped_no_rbrk = [], []
    for path, resource_type, project in candidates:
        if has_rbrk_header(path):
            to_apply.append((path, resource_type, project))
        else:
            skipped_no_rbrk.append(path.name)
            print(f"Skipping {path.name}: no rbrk_* column in header", file=sys.stderr)

    if not to_apply:
        print("Nothing to apply (no file had an rbrk_* column).", file=sys.stderr)
        return

    banner = "DRY RUN (nothing written to GCP)" if args.dry_run else "APPLYING labels to GCP"
    print(f"=== {banner} -- {len(to_apply)} file(s) ===", file=sys.stderr)

    results = []
    for path, resource_type, project in to_apply:
        print(f"Processing {path.name} ({resource_type}, {project})...", file=sys.stderr)
        run = run_update(path, args.dry_run)
        tail = (run["stdout"] or "").strip().splitlines()
        print(f"  {'OK' if run['ok'] else 'FAILED'}: {tail[-1] if tail else run['returncode']}", file=sys.stderr)
        results.append({"file": path.name, "resource_type": resource_type,
                        "project": project, "ok": run["ok"], "run": run})

    report_path = write_report(results, skipped_no_rbrk, args.dry_run)
    print(f"\nReport written to {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
