#!/usr/bin/env python3
"""
run_listings.py - loop  over resources.

Examples
--------
  awslogin(alias) <account-name>        
  python3 scripts/run-listings.py --skip-region me-central-1
  python3 scripts/run-listings.py --only rds --only s3
  python3 scripts/run-listings.py --exclude ecs --exclude eks --exclude dynamodb-table
"""

import argparse
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent      # stacklet/aws 
STACKLET = HERE.parent                        # stacklet/
sys.path.insert(0, str(HERE))
from static.selection import load_selection

DEFAULT_SCRIPT = HERE / "list-resource-aws.py"


def load_resource_types(script_path: Path) -> list:
    """Read RESOURCE_TYPES straight from the (hyphenated) listing script."""
    if not script_path.exists():
        sys.exit(f"ERROR: listing script not found at {script_path}\n"
                 f"       pass --script /path/to/list-resource-aws.py")
    spec = importlib.util.spec_from_file_location("_listing_mod", script_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod) 
    except Exception as e:
        sys.exit(f"ERROR: couldn't import {script_path.name} to read RESOURCE_TYPES ({e}).")
    if not hasattr(mod, "RESOURCE_TYPES"):
        sys.exit(f"ERROR: {script_path.name} has no RESOURCE_TYPES.")
    return list(mod.RESOURCE_TYPES)


def show_account(skip: bool) -> None:
    """Fail fast if awslogin wasn't run - otherwise every subprocess would fail."""
    if skip:
        return
    try:
        import boto3
        ident = boto3.Session().client("sts").get_caller_identity()
        print(f"Account : {ident['Account']}  ({ident['Arn']})\n")
    except Exception as e:
        sys.exit(f"ERROR: no valid AWS credentials ({e}).\n"
                 f"       Run your `awslogin <account>` alias first, then re-run "
                 f"(or pass --no-check to skip this).")


def main() -> None:
    p = argparse.ArgumentParser(description="Loop list-resource-aws.py over all resource types.")
    p.add_argument("--skip-region", metavar="REGION", action="append", default=[],
                   help="Region to skip; passed through to each listing (repeatable).")
    p.add_argument("--only", metavar="TYPE", action="append", default=[],
                   help="Run only these resource types (repeatable). Default: all.")
    p.add_argument("--exclude", metavar="TYPE", action="append", default=[],
                   help="Resource types to skip (repeatable).")
    p.add_argument("--script", type=Path, default=DEFAULT_SCRIPT,
                   help="Path to list-resource-aws.py (default: alongside this file).")
    p.add_argument("--stop-on-error", action="store_true",
                   help="Abort the whole run if any resource type fails.")
    p.add_argument("--no-check", action="store_true",
                   help="Skip the up-front credential/account check.")
    args = p.parse_args()

    show_account(args.no_check)

    all_types = load_resource_types(args.script)

    # Selection precedence: explicit --only > stacklet-resource.json > all types.
    try:
        selection = load_selection()
    except ValueError as e:
        sys.exit(f"ERROR: {e}")

    if args.only:
        requested = args.only
        source = "--only"
    elif selection:
        requested = selection
        source = "stacklet-resource.json"
    else:
        requested = None
        source = None

    if requested is not None:
        unknown = [t for t in requested if t not in all_types]
        if unknown and source == "--only":
            # Explicit override: a typo here is worth stopping for.
            sys.exit(f"ERROR: unknown {source} types: {', '.join(unknown)}\n"
                     f"       not in this account's registry ({len(all_types)} known types).")
        if unknown:
            # Selection file: don't fail on types with no config -- skip and report them.
            print(f"Skipping {len(unknown)} type(s) from {source} not in the "
                  f"registry ({len(all_types)} known): {', '.join(unknown)}")
        # Preserve registry order; drop any --exclude'd keys.
        types = [t for t in all_types if t in set(requested) and t not in set(args.exclude)]
        print(f"Using selection from {source} ({len(types)} type(s)).")
    else:
        types = [t for t in all_types if t not in set(args.exclude)]
        print("No selection in stacklet-resource.json (empty/missing) -> listing all types.")

    print(f"Listing {len(types)} resource type(s): {', '.join(types)}")
    if args.skip_region:
        print(f"Skipping regions: {', '.join(args.skip_region)}")

    skip_args = []
    for r in args.skip_region:
        skip_args += ["--skip-region", r]

    results = []
    for i, rt in enumerate(types, 1):
        print(f"\n{'=' * 60}\n[{i}/{len(types)}] {rt}\n{'=' * 60}")
        t0 = time.time()
        rc = subprocess.run(
            [sys.executable, str(args.script), "--resource-type", rt, *skip_args]
        ).returncode
        dt = time.time() - t0
        ok = rc == 0
        results.append((rt, ok, dt))
        if not ok:
            print(f"  -> {rt} FAILED (exit {rc}) after {dt:.1f}s", file=sys.stderr)
            if args.stop_on_error:
                sys.exit(f"Stopping: {rt} failed and --stop-on-error is set.")

    ok_n = sum(1 for _, ok, _ in results if ok)
    fail = [rt for rt, ok, _ in results if not ok]
    print(f"\n{'=' * 60}\nSUMMARY  ({ok_n}/{len(results)} succeeded)\n{'=' * 60}")
    for rt, ok, dt in results:
        print(f"  {'ok  ' if ok else 'FAIL'}  {rt:<28} {dt:6.1f}s")
    if fail:
        print(f"\nFailed: {', '.join(fail)}", file=sys.stderr)
        sys.exit(1)
    print("\nAll done. CSVs are in your outputs/ directory.")


if __name__ == "__main__":
    main()