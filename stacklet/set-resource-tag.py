import argparse
import csv
import sys
import yaml

parser = argparse.ArgumentParser(description="Update tag column values in a CSV file")
parser.add_argument("--csv-file", required=True, help="Path to the CSV file")

mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--yaml-file", help="YAML file listing tag columns; sets empty cells to 'undefined'")
mode.add_argument("--target-column", help="Single column name to update")

parser.add_argument("--new-value", help="Value to set (required with --target-column)")
args = parser.parse_args()

if args.target_column and not args.new_value:
    parser.error("--new-value is required when using --target-column")

# Read CSV
with open(args.csv_file, mode="r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

if args.yaml_file:
    with open(args.yaml_file, "r") as f:
        config = yaml.safe_load(f)
    tags = config.get("tags", {})
    if not tags:
        sys.exit("No tags found in YAML file")

    updated = 0
    for row in rows:
        for column, value in tags.items():
            if not row.get(column) or row.get(column) == "undefined":
                row[column] = value
                updated += 1

    print(f"Set {updated} empty cell(s) across {len(tags)} tag column(s)")

else:
    for row in rows:
        row[args.target_column] = args.new_value

    print(f"Updated '{args.target_column}' to '{args.new_value}' for all {len(rows)} row(s)")

# Write back
with open(args.csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
