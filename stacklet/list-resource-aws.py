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
from botocore.config import Config
from datetime import datetime, timezone
from pathlib import Path
from static.resource_type_list import ResourceConfig, RESOURCE_TYPES

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

CLIENT_CONFIG = Config(
    connect_timeout=5,
    read_timeout=15,
    retries={"max_attempts": 2, "mode": "standard"},
)

def get_account_id(session):
    return session.client("sts").get_caller_identity()["Account"]


def get_regions(session):
    ec2 = session.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def list_resources(session, owner_id, region, config: ResourceConfig) -> list:
    client_name = getattr(config, "client_name", "ec2")
    client = session.client(client_name, region_name=region, config=CLIENT_CONFIG)

    method = getattr(client, config.describe_method)
    kwargs = {config.owner_key: [owner_id]} if config.owner_key else {}
    kwargs.update(getattr(config, "extra_kwargs", {}) or {})
    results = method(**kwargs)[config.response_key]
    if config.result_filter:
        results = config.result_filter(results, owner_id)
    return results

def fetch_tags_for_arns(session, region, config, arns: list[str]) -> dict[str, list[dict]]:
    """Fetch tags in bulk for a list of ARNs using the Tagging API (Max 100 per call)."""
    if not arns:
        return {}
        
    # Global resources (like IAM) MUST be queried for tags in us-east-1
    client_region = "us-east-1" if getattr(config, "is_global", False) else region
    tag_client = session.client("resourcegroupstaggingapi", region_name=client_region, config=CLIENT_CONFIG)
    tags_by_arn = {}

    # Chunk ARNs into batches of 100
    for i in range(0, len(arns), 100):
        batch = arns[i:i + 100]
        try:
            response = tag_client.get_resources(ResourceARNList=batch)
            for resource in response.get("ResourceTagMappingList", []):
                tags_by_arn[resource["ResourceARN"]] = resource.get("Tags", [])
        except Exception as e:
            print(f"  Warning: Failed to fetch tags for batch in {region} ({e})", file=sys.stderr)

    return tags_by_arn

def main():
    parser = argparse.ArgumentParser(description="List AWS resources with their tags across all regions.")
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

    # Only scan regions where this service actually exists.
    client_name = getattr(config, "client_name", "ec2")
    serviceable = set(session.get_available_regions(client_name))
    if serviceable:
        before = len(regions)
        regions = [r for r in regions if r in serviceable]
        skipped = before - len(regions)
        if skipped:
            print(f"Note: {client_name} is not offered in {skipped} of your regions; "
                  f"skipping those.", file=sys.stderr)

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
            for r in resources:
                r["_arn"] = config.arn_formatter(r[config.id_field], region, owner_id)
            
            # Bulk fetch tags for all generated ARNs
            arns = [r["_arn"] for r in resources]
            tags_by_arn = fetch_tags_for_arns(session, region, config, arns)

            for r in resources:
                r["Tags"] = tags_by_arn.get(r["_arn"], [])
                all_resources.append({"region": region, **r})

            region_counts[region] = len(resources)
            print(f"  {region}: {len(resources)}", file=sys.stderr)

        is_global = getattr(config, "is_global", False)
        if is_global:
            print("  (Global resource: skipping remaining regions)", file=sys.stderr)
            break

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
            arn = r["_arn"]
            writer.writerow(
                [tag_map.get("Name", ""), r["region"], arn]
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
