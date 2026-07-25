#!/usr/bin/env python3
"""Local web UI to fill "undefined" rbrk_* tag values in a list-resource CSV.
Run:
    python3 tag-editor.py           
    python3 tag-editor.py --port 9000
    python3 tag-editor.py --no-browser

Flow:
    1. Pick a CSV from outputs/ .
    2. rbrk_* columns are auto-detected. The UI shows how many cells are
       "undefined" per column. Values you saved as account defaults prefill the
       inputs automatically.
    3. Enter a value for each rbrk_* tag you want to set (leave blank to skip
       that column). The same value is applied to every resource that needs it.
    4. Preview, then write a pipeline-ready make_changes-*.csv into inputs/.

Apply directly:
    Already have a make_changes-*.csv in inputs/? Pick it from the "Apply it
    directly" dropdown to skip the fill/write step and go straight to the
    Apply-to-AWS panel (dry run + apply). 

Fill rule :
    Only columns you enter a value for are touched, and their placeholder cells
    are filled -- both empty cells (the tag is absent on the resource) and literal
    "undefined" cells get the value. Unmarked columns are left exactly as-is, so
    those tags are not changed on AWS. Cells that already hold a real value are
    left untouched too (unless overwrite is set).


Outputs: make_changes CSV -> inputs/dry-run .txt report -> outputs/ . No AWS calls.
"""

import argparse
import csv
import importlib
import json
import re
import sys
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import boto3

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE.parent / "outputs"   # source list CSVs (read) + dry-run change logs (write)
INPUT_DIR = HERE.parent / "inputs"     # generated make_changes CSVs (write)

sys.path.insert(0, str(HERE))
from update_tags_common import (
    FILENAME_PATTERN, TagChange, write_change_report_txt,
    build_tags, parse_filename, is_placeholder,
)
from static.resource_type_update import RESOURCE_TYPES

_update_tags_aws = importlib.import_module("update_tags-aws")
tag_resources_aws = _update_tags_aws.tag_resources_aws
apply_tags_for_type = _update_tags_aws.apply_tags_for_type
verify_account    = _update_tags_aws.verify_account
fetch_current_tags = _update_tags_aws.fetch_current_tags


_META_RE = re.compile(r"^(?:make_changes-)?(?P<resource_type>[a-z][a-z0-9-]*)-(?P<account_id>\d{12})-\d{8}-\d{6}")

def is_undefined(value: str) -> bool:
    return (value or "").strip().lower() == "undefined"


def rbrk_columns(fieldnames: list[str]) -> list[str]:
    return [c for c in fieldnames if c.startswith("rbrk_")]


# --- Per-account rbrk value store ------------------------------------------
# rbrk_* values are provided once per account and remembered on disk so later
# CSVs for the same account prefill their inputs. Stored in inputs/ (gitignored).

def _account_values_path(account_id: str) -> Path:
    """Path to the per-account value store, validating the 12-digit account id."""
    if not re.fullmatch(r"\d{12}", account_id or ""):
        raise ValueError("invalid account id")
    return (INPUT_DIR / f"rbrk-values-{account_id}.json").resolve()


def load_account_values(account_id: str) -> dict:
    """Return the stored {rbrk_key: value} map for an account ({} if none/invalid)."""
    try:
        path = _account_values_path(account_id)
    except ValueError:
        return {}
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


def save_account_values(account_id: str, values: dict) -> dict:
    """Merge non-empty rbrk_* values into the account store and return the result.
    """
    path = _account_values_path(account_id)
    clean = {
        k: str(v).strip()
        for k, v in (values or {}).items()
        if isinstance(k, str) and k.startswith("rbrk_") and str(v).strip()
    }
    merged = load_account_values(account_id)
    merged.update(clean)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")
    return merged


def guess_id_column(fieldnames: list[str]) -> str:
    for c in fieldnames:
        if c.endswith("_id"):
            return c
    return fieldnames[2] if len(fieldnames) > 2 else ""


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = [dict(r) for r in reader]
    return fieldnames, rows


def make_changes_name(input_name: str) -> str:
    return input_name if input_name.startswith("make_changes-") else "make_changes-" + input_name


def safe_output_csv(name: str) -> Path:
    """Resolve `name` to a .csv strictly inside OUTPUT_DIR (no path traversal)."""
    base = Path(name).name
    if not base.lower().endswith(".csv"):
        raise ValueError("not a .csv file")
    path = (OUTPUT_DIR / base).resolve()
    if path.parent != OUTPUT_DIR.resolve():
        raise ValueError("path outside outputs/")
    return path


def apply_values(fieldnames: list[str], rows: list[dict], values: dict, overwrite: bool) -> tuple[list[dict], dict]:
    """Return (new_rows, stats). Fills only the rbrk_* columns given a value.
    stats = {per_col_filled, total_filled, rows_changed}
    """
    rbrk = rbrk_columns(fieldnames)
    new_rows = [dict(r) for r in rows]
    per_col = {c: 0 for c in rbrk}
    rows_changed = 0

    for orig, r in zip(rows, new_rows):
        changed = False
        for c in rbrk:
            fill_val = (values.get(c) or "").strip()
            if not fill_val:
                continue  # unmarked column: leave the cell untouched
            cur = orig.get(c) or ""
            # Fill both empty cells (tag absent) and literal "undefined" -> a
            # placeholder gets the account default. Real existing values are only
            # replaced when overwrite is set.
            if overwrite or is_placeholder(cur):
                if cur.strip() != fill_val:
                    per_col[c] += 1
                    changed = True
                r[c] = fill_val
        if changed:
            rows_changed += 1

    stats = {
        "per_col_filled": per_col,
        "total_filled": sum(per_col.values()),
        "rows_changed": rows_changed,
    }
    return new_rows, stats


def load_payload(name: str) -> dict:
    path = safe_output_csv(name)
    fieldnames, rows = read_csv(path)
    rbrk = rbrk_columns(fieldnames)

    per_col_missing = {c: sum(1 for r in rows if is_placeholder(r.get(c, ""))) for c in rbrk}
    rows_with_missing = sum(1 for r in rows if any(is_placeholder(r.get(c, "")) for c in rbrk))

    out_name = make_changes_name(path.name)
    meta = _META_RE.match(path.name)
    account_id = meta.group("account_id") if meta else ""

    return {
        "ok": True,
        "file": path.name,
        "fieldnames": fieldnames,
        "rbrk": rbrk,
        "id_col": guess_id_column(fieldnames),
        "name_col": "name" if "name" in fieldnames else "",
        "region_col": "region" if "region" in fieldnames else "",
        "meta": {
            "resource_type": meta.group("resource_type") if meta else "",
            "account_id": account_id,
        },
        "account_values": load_account_values(account_id) if account_id else {},
        "out_name": out_name,
        "out_valid": bool(FILENAME_PATTERN.match(out_name)),
        "rows": rows,
        "stats": {
            "total_rows": len(rows),
            "rows_with_missing": rows_with_missing,
            "per_col_missing": per_col_missing,
        },
    }


def compute_payload(body: dict) -> dict:
    path = safe_output_csv(body["file"])
    fieldnames, rows = read_csv(path)
    values = body.get("values") or {}
    overwrite = bool(body.get("overwrite"))
    new_rows, stats = apply_values(fieldnames, rows, values, overwrite)
    return {
        "ok": True,
        "fieldnames": fieldnames,
        "rbrk": rbrk_columns(fieldnames),
        "rows": new_rows,
        "stats": stats,
    }


def _fill_changes(fieldnames: list[str], orig_rows: list[dict], new_rows: list[dict],) -> list[TagChange]:
    """Turn this run's rbrk_* fills into TagChange rows for the dry-run report.
    """
    rbrk = rbrk_columns(fieldnames)
    id_col = guess_id_column(fieldnames)
    changes: list[TagChange] = []
    for orig, new in zip(orig_rows, new_rows):
        rid = (orig.get(id_col) or "").strip()
        region = (orig.get("region") or "").strip()
        for c in rbrk:
            o = (orig.get(c) or "").strip()
            n = (new.get(c) or "").strip()
            if n and n != o and not is_undefined(n):
                action = "+" if o == "" else "~"
                changes.append(TagChange(rid, region, c, action, o, n))
    return changes


def write_payload(body: dict) -> dict:
    path = safe_output_csv(body["file"])
    fieldnames, rows = read_csv(path)
    values = body.get("values") or {}
    overwrite = bool(body.get("overwrite"))
    new_rows, stats = apply_values(fieldnames, rows, values, overwrite)

    out_name = make_changes_name(path.name)

    # 1. Corrected make_changes CSV -> inputs/ (this is the input to update_tags-aws.py)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = INPUT_DIR / out_name
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(new_rows)

    # Dry-run .txt report -> outputs/dry-run-<stem>.txt
    report_path = write_change_report_txt(_fill_changes(fieldnames, rows, new_rows), csv_path)

    meta = _META_RE.match(path.name)
    account_id = meta.group("account_id") if meta else ""
    account_values = save_account_values(account_id, values) if account_id else {}

    warnings = []
    if not FILENAME_PATTERN.match(out_name):
        warnings.append(
            f"'{out_name}' does not match the make_changes pattern, so "
            f"update_tags-aws.py will reject it. Rename to "
            f"make_changes-<type>-<12-digit-account>-YYYYMMDD-HHMMSS.csv."
        )

    return {
        "ok": True,
        "out_name": out_name,
        "out_path": str(csv_path),
        "report_name": report_path.name,
        "report_path": str(report_path),
        "out_valid": bool(FILENAME_PATTERN.match(out_name)),
        "stats": stats,
        "account_values": account_values,
        "warnings": warnings,
    }


def _safe_input_csv(name: str) -> Path:
    """Resolve `name` to a .csv strictly inside INPUT_DIR."""
    base = Path(name).name
    if not base.lower().endswith(".csv"):
        raise ValueError("not a .csv file")
    path = (INPUT_DIR / base).resolve()
    if path.parent != INPUT_DIR.resolve():
        raise ValueError("path outside inputs/")
    return path


def apply_dry_run_payload(body: dict) -> dict:
    """
    Connects to real AWS, fetches current tags, and returns a per-resource diff.
    """
    csv_name = body.get("make_changes_file", "")
    skip_regions = body.get("skip_regions", [])

    csv_path = _safe_input_csv(csv_name)
    if not csv_path.exists():
        return {"ok": False, "error": f"File not found: {csv_path.name}"}

    resource_type, account_id = parse_filename(csv_path, RESOURCE_TYPES)
    config = RESOURCE_TYPES[resource_type]

    session = boto3.Session()
    verify_account(session, account_id)

    by_region: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    rows_skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resource_id = (row.get(config.id_column) or "").strip()
            region = (row.get("region") or "").strip()
            if not resource_id or not region:
                rows_skipped += 1
                continue
            # build_tags skips both empty and "undefined",
            tags = build_tags(row, config)
            if tags:
                by_region[region].append((resource_id, tags))

    for region in skip_regions:
        by_region.pop(region, None)

    if not by_region:
        return {"ok": True, "message": "No resources to process.", "changes": [], "per_region": {}}

    all_changes: list[TagChange] = []
    per_region: dict[str, dict] = {}

    for region in sorted(by_region):
        resources = by_region[region]
        # Call the dry-run function (dispatches to the right tagger per type)
        tagged, errored, changes = apply_tags_for_type(
            session, region, resources, resource_type,
            dry_run=True, verbose=False, summarize=True,
        )
        all_changes.extend(changes)
        per_region[region] = {"resources": len(resources), "tagged": tagged, "errored": errored}

    # Aggregate summary
    total_resources = len({c.resource_id for c in all_changes})
    adds      = sum(1 for c in all_changes if c.action == "+")
    updates   = sum(1 for c in all_changes if c.action == "~")
    unchanged = sum(1 for c in all_changes if c.action == "=")

    return {
        "ok": True,
        "resource_type": resource_type,
        "account_id": account_id,
        "rows_skipped": rows_skipped,
        "per_region": per_region,
        "summary": {
            "total_resources": total_resources,
            "adds": adds,
            "updates": updates,
            "unchanged": unchanged,
        },
        "changes": [
            {"resource_id": c.resource_id, "region": c.region,
             "tag_key": c.tag_key, "action": c.action,
             "old_value": c.old_value, "new_value": c.new_value}
            for c in all_changes
        ],
    }


def save_account_values_payload(body: dict) -> dict:
    """POST handler: merge-save per-account rbrk defaults, return the stored map."""
    account_id = (body.get("account_id") or "").strip()
    try:
        saved = save_account_values(account_id, body.get("values") or {})
        return {
            "ok": True,
            "account_id": account_id,
            "values": saved,
            "path": str(_account_values_path(account_id)),
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


def apply_payload(body: dict) -> dict:
    """Apply tags to real AWS — same logic as `update_tags-aws.py --apply`."""
    csv_name = body.get("make_changes_file", "")
    skip_regions = body.get("skip_regions", [])

    csv_path = _safe_input_csv(csv_name)
    if not csv_path.exists():
        return {"ok": False, "error": f"File not found: {csv_path.name}"}

    resource_type, account_id = parse_filename(csv_path, RESOURCE_TYPES)
    config = RESOURCE_TYPES[resource_type]

    session = boto3.Session()
    verify_account(session, account_id)

    by_region: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    rows_skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resource_id = (row.get(config.id_column) or "").strip()
            region = (row.get("region") or "").strip()
            if not resource_id or not region:
                rows_skipped += 1
                continue
            tags = build_tags(row, config)
            if tags:
                by_region[region].append((resource_id, tags))

    for region in skip_regions:
        by_region.pop(region, None)

    if not by_region:
        return {"ok": True, "message": "No resources to process.", "per_region": {}}

    total_tagged = 0
    total_errored = 0
    total_unchanged = 0
    per_region: dict[str, dict] = {}

    for region in sorted(by_region):
        resources = by_region[region]
        # Call the apply function (dispatches per type; only changed are tagged)
        tagged, errored, _ = apply_tags_for_type(
            session, region, resources, resource_type,
            dry_run=False, verbose=False, summarize=False,
        )
        unchanged = len(resources) - tagged - errored
        total_tagged += tagged
        total_errored += errored
        total_unchanged += unchanged
        per_region[region] = {
            "resources": len(resources), "tagged": tagged,
            "errored": errored, "unchanged": unchanged,
        }

    return {
        "ok": True,
        "resource_type": resource_type,
        "account_id": account_id,
        "rows_skipped": rows_skipped,
        "total_tagged": total_tagged,
        "total_errored": total_errored,
        "total_unchanged": total_unchanged,
        "per_region": per_region,
    }


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>rbrk tag filler</title>
<style>
  :root {
    --bg:#0f1420; --panel:#171d2b; --line:#2a3346; --text:#e6ebf5; --muted:#9aa7bd;
    --accent:#5b8cff; --ok:#3fb950; --warn:#e3b341; --bad:#f0616d;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  header { padding:16px 22px; border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:17px; font-weight:650; }
  header p { margin:4px 0 0; color:var(--muted); font-size:12.5px; }
  main { max-width:1180px; margin:0 auto; padding:20px 22px 60px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:10px;
    padding:16px 18px; margin-bottom:18px; }
  .row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  label.fld { font-size:12px; color:var(--muted); display:block; margin-bottom:4px; }
  select, input[type=text] { background:#0d1220; color:var(--text);
    border:1px solid var(--line); border-radius:7px; padding:8px 10px; font-size:13.5px; }
  select { min-width:340px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
    gap:12px 16px; margin-top:6px; }
  .grid .cell input { width:100%; }
  .hint { font-size:11.5px; color:var(--muted); margin-top:3px; }
  .hint b { color:var(--warn); }
  button { background:var(--accent); color:#fff; border:0; border-radius:8px;
    padding:9px 16px; font-size:13.5px; font-weight:600; cursor:pointer; }
  button.ghost { background:transparent; border:1px solid var(--line); color:var(--text); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .stat { display:inline-flex; gap:6px; align-items:baseline; margin-right:18px; }
  .stat b { font-size:18px; } .stat span { color:var(--muted); font-size:12px; }
  .tablewrap { overflow:auto; max-height:520px; border:1px solid var(--line); border-radius:8px; }
  table { border-collapse:collapse; width:100%; font-size:12.5px; }
  th, td { text-align:left; padding:6px 9px; border-bottom:1px solid var(--line); white-space:nowrap; }
  th { position:sticky; top:0; background:#12182600; backdrop-filter:blur(3px);
    background:#141b29; color:var(--muted); font-weight:600; z-index:1; }
  td.mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  td.missing { color:var(--bad); }
  td.filled  { color:var(--ok); font-weight:600; }
  td.blanked { color:var(--warn); font-style:italic; }
  .msg { padding:10px 12px; border-radius:8px; font-size:13px; margin-top:10px; }
  .msg.ok { background:rgba(63,185,80,.12); border:1px solid rgba(63,185,80,.4); }
  .msg.warn { background:rgba(227,179,65,.12); border:1px solid rgba(227,179,65,.4); }
  .msg.err { background:rgba(240,97,109,.12); border:1px solid rgba(240,97,109,.4); }
  code { background:#0d1220; padding:1px 5px; border-radius:5px; }
  .spacer { flex:1; }
  .pill { font-size:11px; padding:2px 8px; border-radius:20px; border:1px solid var(--line); color:var(--muted); }
  /* Apply-to-AWS panel */
  .apply-panel { border-color:var(--accent); }
  .apply-panel h3 { margin:0 0 10px; font-size:14.5px; font-weight:600; }
  .apply-panel .region-table { width:100%; margin-top:8px; font-size:12.5px; }
  .apply-panel .region-table th { background:var(--bg); }
  .chip { display:inline-flex; align-items:center; gap:4px; background:#0d1220;
    border:1px solid var(--line); border-radius:5px; padding:3px 8px; font-size:12px; margin:2px; }
  .chip .x { cursor:pointer; color:var(--muted); font-weight:bold; }
  .chip .x:hover { color:var(--bad); }
  button.danger { background:var(--bad); }
  .change-row-add { color:var(--ok); } .change-row-upd { color:var(--warn); } .change-row-eq { color:var(--muted); }
  .summary-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; margin:10px 0; }
  .summary-card { background:var(--bg); border:1px solid var(--line); border-radius:8px; padding:10px 12px; text-align:center; }
  .summary-card b { display:block; font-size:20px; margin-bottom:2px; }
  .summary-card span { font-size:11px; color:var(--muted); }
</style>
</head>
<body>
<header>
  <h1>Stacklet Compliance Remediation</h1>
  <p>Replace undefined in rbrk_ tags with appropriate values</p>
</header>
<main>
  <div class="panel">
    <div class="row">
      <div>
        <label class="fld">Source CSV (from outputs/)</label>
        <select id="file"></select>
      </div>
      <button class="ghost" onclick="loadFiles()">&#8635; Refresh list</button>
      <div class="spacer"></div>
      <span id="outname" class="pill"></span>
    </div>
    <div id="loaderr"></div>
  </div>

  <div class="panel">
    <div class="row">
      <div>
        <label class="fld">Already have a make_changes file? Apply it directly (from inputs/)</label>
        <select id="mcfile"></select>
      </div>
      <button class="ghost" onclick="loadInputFiles()">&#8635; Refresh</button>
      <button onclick="loadExisting()">Load for apply &darr;</button>
    </div>
    <div class="hint">Skips the fill/write step &mdash; use this when the make_changes CSV is already prepared.</div>
  </div>

  <div class="panel" id="editor" style="display:none">
    <div class="row" style="margin-bottom:10px">
      <div class="stat"><b id="s-total">0</b><span>resources</span></div>
      <div class="stat"><b id="s-missing">0</b><span>rows with undefined</span></div>
      <div class="spacer"></div>
      <span id="acct-defaults" class="pill"></span>
    </div>
    <label class="fld">Values to apply (blank = leave that column alone; prefilled from account defaults)</label>
    <div class="grid" id="inputs"></div>
    <div class="row" style="margin-top:14px">
      <button onclick="preview()">Preview changes</button>
      <button class="ghost" onclick="writeFile()">Write make_changes file</button>
      <div class="spacer"></div>
      <button class="ghost" onclick="saveDefaults()" title="Remember these values for this account">&#128190; Save account defaults</button>
    </div>
    <div id="result"></div>
  </div>

  <div class="panel" id="tablepanel" style="display:none">
    <div class="row" style="margin-bottom:8px">
      <strong id="tabletitle">Rows needing values</strong>
      <span class="spacer"></span>
      <span class="pill" id="tablecount"></span>
    </div>
    <div class="tablewrap"><table id="table"></table></div>
  </div>

  <div class="panel apply-panel" id="applypanel" style="display:none">
    <h3>&#9729; Apply to AWS</h3>
    <div class="row" style="margin-bottom:10px">
      <div>
        <label class="fld">Make-changes file</label>
        <code id="apply-file"></code>
      </div>
      <div class="spacer"></div>
      <div>
        <label class="fld">Resource type</label>
        <span id="apply-restype" class="pill"></span>
      </div>
      <div>
        <label class="fld">Account</label>
        <span id="apply-account" class="pill"></span>
      </div>
    </div>
    <div style="margin-bottom:10px">
      <label class="fld">Skip regions (comma-separated)</label>
      <input type="text" id="apply-skip-regions" value="me-central-1" style="width:100%;max-width:500px" placeholder="e.g. me-central-1, ap-southeast-3">
    </div>
    <div class="row">
      <button onclick="applyDryRun()">Dry Run (AWS)</button>
      <button class="danger" id="apply-btn" onclick="applyTags()">Apply Tags</button>
    </div>
    <div id="apply-result"></div>
    <div id="apply-details" style="margin-top:10px"></div>
  </div>
</main>

<script>
let DATA = null;          // /api/load payload for the current file
let WRITTEN_FILE = null;  // name of the last make_changes file written
const $ = (id) => document.getElementById(id);

async function loadFiles() {
  const r = await fetch('/api/files');
  const j = await r.json();
  const sel = $('file');
  sel.innerHTML = '';
  if (!j.files.length) {
    $('loaderr').innerHTML = '<div class="msg warn">No CSV files found in outputs/. Run list-resource-aws.py first.</div>';
    $('editor').style.display = 'none';
    $('tablepanel').style.display = 'none';
    return;
  }
  $('loaderr').innerHTML = '';
  for (const f of j.files) {
    const o = document.createElement('option'); o.value = f; o.textContent = f; sel.appendChild(o);
  }
  sel.onchange = loadFile;
  await loadFile();
}

async function loadFile() {
  const file = $('file').value;
  const r = await fetch('/api/load?file=' + encodeURIComponent(file));
  const j = await r.json();
  if (!j.ok) { $('loaderr').innerHTML = '<div class="msg err">' + (j.error || 'load failed') + '</div>'; return; }
  DATA = j;
  $('outname').textContent = '→ ' + j.out_name + (j.out_valid ? '' : '  (name will be rejected!)');
  $('s-total').textContent = j.stats.total_rows;
  $('s-missing').textContent = j.stats.rows_with_missing;
  renderAcctPill();
  renderInputs(j);
  $('editor').style.display = '';
  $('result').innerHTML = '';
  renderTable(missingRows(j.rows, j.rbrk), j, 'Rows needing values (current)', null);
}

function renderAcctPill() {
  const acct = (DATA && DATA.meta && DATA.meta.account_id) || '?';
  const n = Object.keys((DATA && DATA.account_values) || {}).length;
  $('acct-defaults').textContent = n
    ? ('⚙ ' + n + ' stored default(s) for account ' + acct)
    : ('no stored defaults for account ' + acct);
}

async function saveDefaults() {
  if (!DATA) return;
  const acct = DATA.meta && DATA.meta.account_id;
  if (!acct) { $('result').innerHTML = '<div class="msg err">No 12-digit account id in the filename; cannot save defaults.</div>'; return; }
  const body = { account_id: acct, values: collectValues() };
  const r = await fetch('/api/account-values', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!j.ok) { $('result').innerHTML = '<div class="msg err">' + escapeHtml(j.error || 'save failed') + '</div>'; return; }
  DATA.account_values = j.values;
  renderAcctPill();
  renderInputs(DATA);
  $('result').innerHTML = '<div class="msg ok">Saved <b>' + Object.keys(j.values).length +
    '</b> account default(s) for ' + escapeHtml(j.account_id) + ' &rarr; <code>' + escapeHtml(j.path) + '</code></div>';
}

function renderInputs(j) {
  const wrap = $('inputs'); wrap.innerHTML = '';
  if (!j.rbrk.length) { wrap.innerHTML = '<div class="hint">No rbrk_* columns in this file.</div>'; return; }
  const stored = j.account_values || {};
  for (const c of j.rbrk) {
    const miss = j.stats.per_col_missing[c] || 0;
    const pre = stored[c] || '';                    // prefill from account defaults
    const div = document.createElement('div'); div.className = 'cell';
    div.innerHTML =
      '<label class="fld">' + c + '</label>' +
      '<input type="text" data-col="' + c + '" value="' + escapeHtml(pre) + '" placeholder="leave blank to skip">' +
      '<div class="hint">' + (miss ? '<b>' + miss + '</b> undefined' : 'all set') +
      (pre ? ' &middot; <span style="color:var(--accent)">account default</span>' : '') + '</div>';
    wrap.appendChild(div);
  }
}

function collectValues() {
  const values = {};
  document.querySelectorAll('#inputs input[data-col]').forEach(i => {
    const v = i.value.trim(); if (v) values[i.dataset.col] = v;
  });
  return values;
}

function missingRows(rows, rbrk) {
  return rows.map((r, i) => ({ r, i })).filter(x => rbrk.some(c => isFillable(x.r[c])));
}
// A cell is fillable when it's a placeholder: empty (tag absent) OR "undefined".
function isUndefined(v) { return (v || '').trim().toLowerCase() === 'undefined'; }
function isFillable(v) { const s = (v || '').trim(); return s === '' || s.toLowerCase() === 'undefined'; }

// original rows are DATA.rows; `newRows` (optional) is the previewed result.
function renderTable(entries, j, title, newRows) {
  $('tablepanel').style.display = '';
  $('tabletitle').textContent = title;
  $('tablecount').textContent = entries.length + ' rows';
  const cols = [j.name_col, j.region_col, j.id_col].filter(Boolean).concat(j.rbrk);
  const t = $('table');
  let html = '<thead><tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr></thead><tbody>';
  for (const { r, i } of entries.slice(0, 400)) {
    html += '<tr>';
    for (const c of cols) {
      const origVal = (r[c] == null ? '' : r[c]);
      let val = origVal, cls = '';
      const isId = (c === j.id_col);
      if (j.rbrk.includes(c)) {
        if (newRows) {
          const nv = newRows[i][c] == null ? '' : newRows[i][c];
          if (isFillable(origVal) && nv && !isFillable(nv)) { val = nv; cls = 'filled'; }
          else if (isFillable(origVal)) { val = origVal || '(empty)'; cls = 'missing'; }
          else val = nv;
        } else if (isFillable(origVal)) { cls = 'missing'; }
      }
      html += '<td class="' + (isId ? 'mono ' : '') + cls + '">' + escapeHtml(val) + '</td>';
    }
    html += '</tr>';
  }
  html += '</tbody>';
  if (entries.length > 400) html += '<caption style="color:var(--muted);padding:6px">showing first 400 of ' + entries.length + '</caption>';
  t.innerHTML = html;
}

function escapeHtml(s) { return String(s).replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m])); }

async function preview() {
  const body = { file: DATA.file, values: collectValues(), overwrite: false };
  const r = await fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!j.ok) { $('result').innerHTML = '<div class="msg err">' + (j.error || 'preview failed') + '</div>'; return; }
  const s = j.stats;
  $('result').innerHTML = '<div class="msg ok">Preview: <b>' + s.total_filled + '</b> cells would be filled across <b>' +
    s.rows_changed + '</b> rows. Unmarked columns stay "undefined". Nothing written yet.</div>';
  renderTable(missingRows(DATA.rows, DATA.rbrk), DATA, 'Preview (green = filled, red = stays undefined)', j.rows);
}

async function writeFile() {
  const body = { file: DATA.file, values: collectValues(), overwrite: false };
  const r = await fetch('/api/write', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!j.ok) { $('result').innerHTML = '<div class="msg err">' + (j.error || 'write failed') + '</div>'; return; }
  const s = j.stats;
  let msg = '<div class="msg ' + (j.warnings.length ? 'warn' : 'ok') + '">' +
    'CSV &rarr; <code>' + escapeHtml(j.out_path) + '</code><br>' +
    'dry-run report &rarr; <code>' + escapeHtml(j.report_path) + '</code><br>' +
    '<b>' + s.total_filled + '</b> cells filled, <b>' + s.rows_changed + '</b> rows changed.';
  if (j.warnings.length) msg += '<br>&#9888; ' + j.warnings.map(escapeHtml).join('<br>&#9888; ');
  msg += '</div>';
  $('result').innerHTML = msg;
  if (j.account_values) { DATA.account_values = j.account_values; renderAcctPill(); }
  renderTable(missingRows(DATA.rows, DATA.rbrk), DATA, 'Written result (green = filled, red = stays undefined)', null);

  // Show apply panel if make_changes file was written successfully
  WRITTEN_FILE = j.out_name;
  if (j.out_valid) {
    showApplyPanel(j.out_name);
  }
}

async function loadInputFiles() {
  const sel = $('mcfile');
  sel.innerHTML = '';
  try {
    const r = await fetch('/api/input-files');
    const j = await r.json();
    if (!j.ok || !j.files.length) {
      const o = document.createElement('option');
      o.value = ''; o.textContent = '(no make_changes files in inputs/)';
      sel.appendChild(o);
      return;
    }
    for (const f of j.files) {
      const o = document.createElement('option'); o.value = f; o.textContent = f; sel.appendChild(o);
    }
  } catch (e) {
    const o = document.createElement('option');
    o.value = ''; o.textContent = '(could not list inputs/)';
    sel.appendChild(o);
  }
}

// Point the Apply-to-AWS panel at an existing make_changes file, no fill/write needed.
function loadExisting() {
  const f = $('mcfile').value;
  if (!f) { alert('No make_changes file selected.'); return; }
  WRITTEN_FILE = f;
  showApplyPanel(f);
  $('applypanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showApplyPanel(fileName) {
  $('applypanel').style.display = '';
  $('apply-file').textContent = fileName;
  // Parse resource type and account from the filename
  const m = fileName.match(/^make_changes-([a-z][a-z0-9-]*)-([0-9]{12})-/);
  $('apply-restype').textContent = m ? m[1] : '?';
  $('apply-account').textContent = m ? m[2] : '?';
  $('apply-result').innerHTML = '';
  $('apply-details').innerHTML = '';
}

function getSkipRegions() {
  const raw = $('apply-skip-regions').value.trim();
  return raw ? raw.split(',').map(s => s.trim()).filter(Boolean) : [];
}

async function applyDryRun() {
  if (!WRITTEN_FILE) return;
  $('apply-result').innerHTML = '<div class="msg warn">Connecting to AWS&hellip; fetching current tags&hellip;</div>';
  $('apply-details').innerHTML = '';
  const body = { make_changes_file: WRITTEN_FILE, skip_regions: getSkipRegions() };
  try {
    const r = await fetch('/api/apply-dry-run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!j.ok) { $('apply-result').innerHTML = '<div class="msg err">' + escapeHtml(j.error || 'dry-run failed') + '</div>'; return; }
    if (j.message) { $('apply-result').innerHTML = '<div class="msg warn">' + escapeHtml(j.message) + '</div>'; return; }
    const s = j.summary;
    $('apply-result').innerHTML =
      '<div class="summary-grid">' +
        '<div class="summary-card"><b>' + s.total_resources + '</b><span>resources</span></div>' +
        '<div class="summary-card"><b style="color:var(--ok)">' + s.adds + '</b><span>[+] would be added</span></div>' +
        '<div class="summary-card"><b style="color:var(--warn)">' + s.updates + '</b><span>[~] would be updated</span></div>' +
        '<div class="summary-card"><b style="color:var(--muted)">' + s.unchanged + '</b><span>[=] already correct</span></div>' +
      '</div>';
    // Region breakdown
    let html = '<table class="region-table"><thead><tr><th>Region</th><th>Resources</th></tr></thead><tbody>';
    for (const [reg, info] of Object.entries(j.per_region)) {
      html += '<tr><td>' + escapeHtml(reg) + '</td><td>' + info.resources + '</td></tr>';
    }
    html += '</tbody></table>';
    // Per-resource change details (limit to 200)
    if (j.changes && j.changes.length) {
      html += '<div style="margin-top:12px"><strong>Tag changes (' + j.changes.length + ')</strong></div>';
      html += '<div class="tablewrap" style="max-height:320px;margin-top:6px"><table>';
      html += '<thead><tr><th>Resource ID</th><th>Region</th><th>Tag</th><th>Action</th><th>Old</th><th>New</th></tr></thead><tbody>';
      for (const c of j.changes.slice(0, 200)) {
        const cls = c.action === '+' ? 'change-row-add' : c.action === '~' ? 'change-row-upd' : 'change-row-eq';
        html += '<tr class="' + cls + '"><td class="mono">' + escapeHtml(c.resource_id) + '</td><td>' + escapeHtml(c.region) +
          '</td><td>' + escapeHtml(c.tag_key) + '</td><td>' + escapeHtml(c.action) + '</td><td>' +
          escapeHtml(c.old_value) + '</td><td>' + escapeHtml(c.new_value) + '</td></tr>';
      }
      html += '</tbody></table></div>';
      if (j.changes.length > 200) html += '<div class="hint">Showing first 200 of ' + j.changes.length + ' changes</div>';
    }
    $('apply-details').innerHTML = html;
  } catch (e) {
    $('apply-result').innerHTML = '<div class="msg err">Error: ' + escapeHtml(String(e)) + '</div>';
  }
}

async function applyTags() {
  if (!WRITTEN_FILE) return;
  if (!confirm('Apply tags to real AWS resources?\n\nFile: ' + WRITTEN_FILE + '\nSkip regions: ' + (getSkipRegions().join(', ') || '(none)') + '\n\nThis will modify AWS resource tags. Continue?')) return;
  $('apply-result').innerHTML = '<div class="msg warn">Applying tags to AWS&hellip;</div>';
  $('apply-details').innerHTML = '';
  const body = { make_changes_file: WRITTEN_FILE, skip_regions: getSkipRegions() };
  try {
    const r = await fetch('/api/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!j.ok) { $('apply-result').innerHTML = '<div class="msg err">' + escapeHtml(j.error || 'apply failed') + '</div>'; return; }
    if (j.message) { $('apply-result').innerHTML = '<div class="msg warn">' + escapeHtml(j.message) + '</div>'; return; }
    const hasErrors = j.total_errored > 0;
    $('apply-result').innerHTML =
      '<div class="msg ' + (hasErrors ? 'err' : 'ok') + '">' +
      '<b>' + j.total_tagged + '</b> resources tagged successfully.' +
      (hasErrors ? ' <b>' + j.total_errored + '</b> resources errored.' : '') +
      '</div>';
    // Region breakdown
    let html = '<table class="region-table"><thead><tr><th>Region</th><th>Resources</th><th>Tagged</th><th>Errored</th></tr></thead><tbody>';
    for (const [reg, info] of Object.entries(j.per_region)) {
      html += '<tr><td>' + escapeHtml(reg) + '</td><td>' + info.resources + '</td><td style="color:var(--ok)">' + info.tagged + '</td><td style="color:var(--bad)">' + info.errored + '</td></tr>';
    }
    html += '</tbody></table>';
    $('apply-details').innerHTML = html;
  } catch (e) {
    $('apply-result').innerHTML = '<div class="msg err">Error: ' + escapeHtml(String(e)) + '</div>';
  }
}

loadFiles();
loadInputFiles();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif parsed.path == "/api/files":
                files = sorted(
                    p.name for p in OUTPUT_DIR.glob("*.csv")
                    if not p.name.startswith("make_changes-")
                ) if OUTPUT_DIR.exists() else []
                self._json({"ok": True, "files": files})
            elif parsed.path == "/api/input-files":
                # Existing make_changes CSVs in inputs/, ready to apply directly.
                files = sorted(
                    (p.name for p in INPUT_DIR.glob("make_changes-*.csv")),
                    reverse=True,
                ) if INPUT_DIR.exists() else []
                self._json({"ok": True, "files": files})
            elif parsed.path == "/api/load":
                name = parse_qs(parsed.query).get("file", [""])[0]
                self._json(load_payload(name))
            elif parsed.path == "/api/account-values":
                account_id = parse_qs(parsed.query).get("account_id", [""])[0]
                self._json({"ok": True, "account_id": account_id,
                            "values": load_account_values(account_id)})
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except SystemExit as exc:
            # parse_filename() / verify_account() raise SystemExit (great for the
            # CLI, fatal in a request thread). Catch it here so the browser gets a
            # readable error instead of a dropped connection ("Failed to fetch").
            self._json({"ok": False, "error": str(exc) or "operation aborted"}, 400)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            if parsed.path == "/api/preview":
                self._json(compute_payload(body))
            elif parsed.path == "/api/write":
                self._json(write_payload(body))
            elif parsed.path == "/api/apply-dry-run":
                self._json(apply_dry_run_payload(body))
            elif parsed.path == "/api/apply":
                self._json(apply_payload(body))
            elif parsed.path == "/api/account-values":
                self._json(save_account_values_payload(body))
            else:
                self._json({"ok": False, "error": "not found"}, 404)
        except SystemExit as exc:
            self._json({"ok": False, "error": str(exc) or "operation aborted"}, 400)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local UI to fill undefined rbrk_* tags.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open the browser")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    url = f"http://localhost:{args.port}"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)

    print(f"Tag filler running at {url}")
    print(f"Reading CSVs from : {OUTPUT_DIR}")
    print(f"Writing CSVs to   : {INPUT_DIR}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
