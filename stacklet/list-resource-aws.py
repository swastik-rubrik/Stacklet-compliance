#!/usr/bin/env python3
"""List AWS resources with their tags across all regions.

Output: CSV written to ../outputs/{resource_type}-{account}-{timestamp}.csv
Columns: name, region, {resource_id}, {metadata...}, one column per rbrk_* tag.

Usage:
    python3 list-resource-aws.py
    python3 list-resource-aws.py --resource-type ami
    python3 list-resource-aws.py --resource-type prefix-list
    python3 list-resource-aws.py --resource-type ebs
    python3 list-resource-aws.py --skip-region ap-northeast-1

Extending to new resource types:
    Add an entry to RESOURCE_TYPES below.
"""

import argparse
import boto3
import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


@dataclass
class ResourceConfig:
    describe_method: str               # ec2 client method to call
    response_key: str                  # top-level key in the API response
    owner_key: str                     # ownership filter param ("OwnerIds" vs "Owners")
    id_field: str                      # API field name for the resource ID
    id_column: str                     # CSV column name for the ID
    meta_columns: list[str]            # non-tag metadata columns before rbrk_* tags
    extract_meta: Callable[[Any], list]
    trailing_columns: list[str]        # columns written after rbrk_* tags (e.g. description)
    extract_trailing: Callable[[Any], list]
    result_filter: Callable[[list, str], list] | None = None  # post-fetch filter when API lacks an owner param


RESOURCE_TYPES: dict[str, ResourceConfig] = {
    "snapshot": ResourceConfig(
        describe_method="describe_snapshots",
        response_key="Snapshots",
        owner_key="OwnerIds",
        id_field="SnapshotId",
        id_column="snapshot_id",
        meta_columns=["completion_time"],
        extract_meta=lambda s: [s.get("CompletionTime", "")],
        trailing_columns=["description"],
        extract_trailing=lambda s: [s.get("Description", "")],
    ),
    "ami": ResourceConfig(
        describe_method="describe_images",
        response_key="Images",
        owner_key="Owners",
        id_field="ImageId",
        id_column="image_id",
        meta_columns=["creation_date", "state", "architecture"],
        extract_meta=lambda i: [
            i.get("CreationDate", ""),
            i.get("State", ""),
            i.get("Architecture", ""),
        ],
        trailing_columns=["description"],
        extract_trailing=lambda i: [i.get("Description", "")],
    ),
    "ebs": ResourceConfig(
        describe_method="describe_volumes",
        response_key="Volumes",
        owner_key="",
        id_field="VolumeId",
        id_column="volume_id",
        meta_columns=["create_time", "size_gb", "state", "volume_type", "availability_zone"],
        extract_meta=lambda v: [
            v.get("CreateTime", ""),
            str(v.get("Size", "")),
            v.get("State", ""),
            v.get("VolumeType", ""),
            v.get("AvailabilityZone", ""),
        ],
        trailing_columns=[],
        extract_trailing=lambda _: [],
    ),
    "prefix-list": ResourceConfig(
        describe_method="describe_managed_prefix_lists",
        response_key="PrefixLists",
        owner_key="",
        id_field="PrefixListId",
        id_column="prefix_list_id",
        meta_columns=["prefix_list_name", "state", "max_entries", "address_family"],
        extract_meta=lambda p: [
            p.get("PrefixListName", ""),
            p.get("State", ""),
            str(p.get("MaxEntries", "")),
            p.get("AddressFamily", ""),
        ],
        trailing_columns=[],
        extract_trailing=lambda _: [],
        result_filter=lambda items, _: [i for i in items if i.get("OwnerId") != "aws"],
    ),
}


def get_account_id(session):
    return session.client("sts").get_caller_identity()["Account"]


def get_regions(session):
    ec2 = session.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def list_resources(session, owner_id, region, config: ResourceConfig) -> list:
    ec2 = session.client("ec2", region_name=region)
    method = getattr(ec2, config.describe_method)
    kwargs = {config.owner_key: [owner_id]} if config.owner_key else {}
    results = method(**kwargs)[config.response_key]
    if config.result_filter:
        results = config.result_filter(results, owner_id)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="List AWS resources with their tags across all regions."
    )
    parser.add_argument(
        "--resource-type", choices=list(RESOURCE_TYPES), default="snapshot",
        help="Resource type to list (default: snapshot)",
    )
    parser.add_argument(
        "--skip-region", metavar="REGION", action="append", default=[],
        help="Skip this region (may be repeated)",
    )
    args = parser.parse_args()

    config = RESOURCE_TYPES[args.resource_type]

    session = boto3.Session()
    owner_id = get_account_id(session)
    regions = [r for r in get_regions(session) if r not in args.skip_region]

    print(f"Account: {owner_id}", file=sys.stderr)
    print(f"Resource type: {args.resource_type}", file=sys.stderr)
    print(f"Scanning {len(regions)} regions...", file=sys.stderr)

    all_resources = []
    region_counts = {}

    for region in sorted(regions):
        try:
            resources = list_resources(session, owner_id, region, config)
        except Exception as e:
            print(f"  {region}: skipped ({e})", file=sys.stderr)
            continue

        if resources:
            all_resources.extend({"region": region, **r} for r in resources)
            region_counts[region] = len(resources)
            print(f"  {region}: {len(resources)}", file=sys.stderr)

    # Collect all unique rbrk_* tag keys across all resources
    rbrk_keys = sorted({
        t["Key"]
        for r in all_resources
        for t in (r.get("Tags") or [])
        if t["Key"].startswith("rbrk_")
    })

    # Write CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    outfile = OUTPUT_DIR / f"{args.resource_type}-{owner_id}-{timestamp}.csv"

    with open(outfile, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(
            ["name", "region", config.id_column]
            + config.meta_columns + rbrk_keys + config.trailing_columns
        )
        for r in all_resources:
            tag_map = {t["Key"]: t["Value"] for t in (r.get("Tags") or [])}
            writer.writerow(
                [tag_map.get("Name", ""), r["region"], r[config.id_field]]
                + config.extract_meta(r)
                + [tag_map.get(k, "") for k in rbrk_keys]
                + config.extract_trailing(r)
            )

    # Summary
    print(f"\nSummary:", file=sys.stderr)
    print(f"{'Region':<25} {args.resource_type:>12}", file=sys.stderr)
    print("-" * 38, file=sys.stderr)
    for region, count in sorted(region_counts.items()):
        print(f"{region:<25} {count:>12}", file=sys.stderr)
    print("-" * 38, file=sys.stderr)
    print(f"{'Total':<25} {len(all_resources):>12}", file=sys.stderr)
    print(f"\nOutput written to {outfile}", file=sys.stderr)


if __name__ == "__main__":
    main()
