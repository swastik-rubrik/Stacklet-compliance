#!/usr/bin/env python3
"""Apply AWS tags from a make_changes CSV to resources.

Filename convention (parsed automatically):
    make_changes-{resource_type}-{account_id}-{timestamp}.csv

    resource_type  Supported: snapshots, volumes, instances, amis, security-groups, prefix-lists, ebs
    account_id     12-digit AWS account number; validated against active credentials

Usage:
    python3 make_changes-aws.py <csv_file>              # dry run (default)
    python3 make_changes-aws.py <csv_file> --apply      # apply changes
    python3 make_changes-aws.py <csv_file> --verbose    # per-resource output (useful with --apply)
    python3 make_changes-aws.py <csv_file> --summarize  # dry-run analysis: counts + CSV report
    python3 make_changes-aws.py --help

Tag column detection:
    Any CSV column that is not the resource ID, 'region', or in the resource
    type's skip list is treated as a tag to apply. The 'name' column maps to
    the AWS 'Name' tag key. Empty values are skipped.

Extending to new resource types:
    Add an entry to RESOURCE_TYPES below with the correct id_column and
    skip_columns for that resource's CSV format.

CSV column suggestions for richer workflows:
    - 'resource_type' column to support mixed-type CSVs in a single file
    - Use 'tag:' prefix on column names (e.g. 'tag:rbrk_owner') to self-describe
      which columns are tags, eliminating the need for per-type skip lists
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

import boto3

from cloud_platforms_python.update_tags_common import ResourceConfig, build_tags, parse_filename

_BATCH_SIZE = 1_000
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

RESOURCE_TYPES: dict[str, ResourceConfig] = {
    "snapshot": ResourceConfig(
        id_column="snapshot_id",
        skip_columns=frozenset({"completion_time", "description"}),
    ),
    "volume": ResourceConfig(
        id_column="volume_id",
        skip_columns=frozenset({"create_time", "size_gb", "state", "description"}),
    ),
    "instance": ResourceConfig(
        id_column="instance_id",
        skip_columns=frozenset({"launch_time", "state", "instance_type", "vpc_id", "subnet_id"}),
    ),
    "ami": ResourceConfig(
        id_column="image_id",
        skip_columns=frozenset({"creation_date", "state", "description", "architecture"}),
    ),
    "security-group": ResourceConfig(
        id_column="group_id",
        skip_columns=frozenset({"description", "vpc_id"}),
    ),
    "prefix-list": ResourceConfig(
        id_column="prefix_list_id",
        skip_columns=frozenset({"prefix_list_name", "state", "max_entries", "address_family"}),
    ),
    "ebs": ResourceConfig(
        id_column="volume_id",
        skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
    ),
}


class TagChange(NamedTuple):
    resource_id: str
    region: str
    tag_key: str
    action: str    # "+" add, "~" update, "=" unchanged
    old_value: str
    new_value: str


_DESCRIBE_TAGS_CHUNK = 200  # AWS hard limit on filter values per describe_tags call

def fetch_current_tags(ec2_client, resource_ids: list[str]) -> dict[str, dict[str, str]]:
    """Return {resource_id: {tag_key: tag_value}} for the given resource IDs."""
    current: dict[str, dict[str, str]] = defaultdict(dict)
    paginator = ec2_client.get_paginator("describe_tags")
    for i in range(0, len(resource_ids), _DESCRIBE_TAGS_CHUNK):
        chunk = resource_ids[i : i + _DESCRIBE_TAGS_CHUNK]
        for page in paginator.paginate(
            Filters=[{"Name": "resource-id", "Values": chunk}]
        ):
            for tag in page["Tags"]:
                current[tag["ResourceId"]][tag["Key"]] = tag["Value"]
    return dict(current)


def verify_account(session: boto3.Session, expected: str) -> None:
    actual = session.client("sts").get_caller_identity()["Account"]
    if actual != expected:
        raise SystemExit(
            f"Account mismatch!\n"
            f"  Filename says  : {expected}\n"
            f"  Active creds   : {actual}\n"
            f"Check your AWS_PROFILE or credential configuration."
        )


def tag_resources_ec2(
    session: boto3.Session,
    region: str,
    resources: list[tuple[str, list[dict]]],
    dry_run: bool,
    verbose: bool,
    summarize: bool,
    verbose_out=sys.stdout,
) -> tuple[int, int, list[TagChange]]:
    """Tag EC2 resources in one region. Returns (tagged, errored, changes).

    Resources sharing identical tag sets are batched into single API calls
    (up to _BATCH_SIZE resources per call). When verbose or summarize is set
    in dry-run mode, current tags are fetched and compared per resource.
    """
    ec2 = session.client("ec2", region_name=region)
    tagged = errored = 0
    changes: list[TagChange] = []

    # Pre-fetch current tags for all resources in this region in one pass.
    current_by_id: dict[str, dict[str, str]] = {}
    if dry_run and (verbose or summarize):
        current_by_id = fetch_current_tags(ec2, [rid for rid, _ in resources])

    # Group by tag fingerprint so resources with identical tags share a call.
    groups: dict[tuple, list[str]] = defaultdict(list)
    tags_by_fp: dict[tuple, list[dict]] = {}
    for resource_id, tags in resources:
        fp = tuple(sorted((t["Key"], t["Value"]) for t in tags))
        groups[fp].append(resource_id)
        tags_by_fp[fp] = tags

    for fp, ids in groups.items():
        tags = tags_by_fp[fp]
        for i in range(0, len(ids), _BATCH_SIZE):
            batch = ids[i : i + _BATCH_SIZE]
            if dry_run:
                if verbose or summarize:
                    for rid in batch:
                        existing = current_by_id.get(rid, {})
                        if verbose:
                            print(f"  {rid} ({region})", file=verbose_out)
                        for t in tags:
                            key, new_val = t["Key"], t["Value"]
                            if key not in existing:
                                action, old_val = "+", ""
                            elif existing[key] != new_val:
                                action, old_val = "~", existing[key]
                            else:
                                action, old_val = "=", existing[key]
                            if verbose and action != "=":
                                if action == "~":
                                    print(f"    [{action}] {key}: {old_val} → {new_val}", file=verbose_out)
                                else:
                                    print(f"    [{action}] {key} = {new_val}", file=verbose_out)
                            if summarize:
                                changes.append(TagChange(rid, region, key, action, old_val, new_val))
                tagged += len(batch)
            else:
                try:
                    ec2.create_tags(Resources=batch, Tags=tags)
                    if verbose:
                        for rid in batch:
                            print(f"  Tagged {rid} ({len(tags)} tags)", file=verbose_out)
                    tagged += len(batch)
                except Exception as exc:
                    print(f"  ERROR batch [{batch[0]} …]: {exc}", file=sys.stderr)
                    errored += len(batch)

    return tagged, errored, changes


def write_change_report(changes: list[TagChange], input_path: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / f"dry-run-{input_path.stem}.csv"
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["resource_id", "region", "tag_key", "action", "old_value", "new_value"])
        for c in changes:
            writer.writerow([c.resource_id, c.region, c.tag_key, c.action, c.old_value, c.new_value])
    return outfile


def print_change_summary(changes: list[TagChange]) -> None:
    resources = len({c.resource_id for c in changes})
    adds      = sum(1 for c in changes if c.action == "+")
    updates   = sum(1 for c in changes if c.action == "~")
    unchanged = sum(1 for c in changes if c.action == "=")
    print(f"Tag summary across {resources} resources:")
    print(f"  [+] {adds:>6}  would be added")
    print(f"  [~] {updates:>6}  would be updated")
    print(f"  [=] {unchanged:>6}  already correct")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply AWS tags from a make_changes CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("csv_file", type=Path, help="Path to make_changes CSV")
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply tag changes (default: dry run)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-resource tag details; shows change indicators in dry run, confirmations in --apply",
    )
    parser.add_argument(
        "--summarize", "-s", action="store_true",
        help="Dry-run only: fetch current tags, print aggregate counts, write comparison CSV to output/",
    )
    parser.add_argument(
        "--skip-region", metavar="REGION", action="append", default=[],
        help="Skip this region (may be repeated)",
    )
    parser.add_argument(
        "--log", metavar="FILE", nargs="?", const="",
        help="Write verbose output to FILE; auto-named from input CSV if FILE omitted (implies --verbose)",
    )
    parser.add_argument(
        "--skip-account-check", action="store_true",
        help="Skip verifying active credentials match the account in the filename",
    )
    args = parser.parse_args()

    csv_path = args.csv_file
    if not csv_path.exists():
        raise SystemExit(f"File not found: {csv_path}")

    resource_type, account_id = parse_filename(csv_path, RESOURCE_TYPES)
    config = RESOURCE_TYPES[resource_type]
    dry_run = not args.apply
    verbose = args.verbose or (args.log is not None)

    print(f"File          : {csv_path.name}")
    print(f"Resource type : {resource_type}")
    print(f"Account ID    : {account_id}")
    print(f"Mode          : {'DRY RUN (pass --apply to make changes)' if dry_run else 'APPLY'}")
    print()

    session = boto3.Session()

    if not args.skip_account_check:
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

    if rows_skipped:
        print(f"Skipped {rows_skipped} rows with missing resource ID or region.")

    for region in args.skip_region:
        if by_region.pop(region, None) is not None:
            print(f"Skipped region: {region}")

    if not by_region:
        print("No resources to process.")
        return

    total_tagged = 0
    total_errored = 0
    all_changes: list[TagChange] = []

    print(f"{'Region':<25} {'Resources':>10}")
    print("-" * 36)

    if args.log is None:
        log_path = None
    elif args.log == "":
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        log_path = OUTPUT_DIR / f"dry-run-{csv_path.stem}.txt"
    else:
        log_path = Path(args.log)
    log_file = open(log_path, "w", encoding="utf-8") if log_path else None
    verbose_out = log_file or sys.stdout

    try:
        for region in sorted(by_region):
            resources = by_region[region]
            print(f"{region:<25} {len(resources):>10}")

            tagged, errored, changes = tag_resources_ec2(
                session, region, resources, dry_run, verbose, args.summarize, verbose_out
            )
            total_tagged += tagged
            total_errored += errored
            all_changes.extend(changes)
    finally:
        if log_file:
            log_file.close()

    print("-" * 36)
    print(f"{'Total':<25} {total_tagged + total_errored:>10}")
    print()

    if dry_run:
        if args.summarize and all_changes:
            print_change_summary(all_changes)
            print()
            outfile = write_change_report(all_changes, csv_path)
            print(f"Report written to {outfile}")
            print()
        print(f"DRY RUN: {total_tagged} resources would be tagged.")
        print("Run with --apply to make changes.")
    else:
        print(f"Done: {total_tagged} resources tagged.")
        if total_errored:
            sys.exit(1)


if __name__ == "__main__":
    main()
