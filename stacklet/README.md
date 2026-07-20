# Helper scripts for managing Stacklet

The current script were primarily created to updates tags on resources under the control of Stacklet.

## Initialize your environment

```shell
# Execute the following from the /stacklet directory

mkdir inputs outputs
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Scripts

Recommended debug execution parameters for each of the 2 current scripts are in `.vscode/launch.json`.

### Retrieve details

`list-resource-aws.py` <br>
Generates a CSV with details for the specified resource type. The file will be saved to the `outputs/` directory

### Example execution

```shell
list-resource-aws.py --resource-type "snapshot" --skip-region me-central-1
```

### Updating tags


`update_tags-aws.py`
Update values for tags. Uses a source CSV for input. The input filename is used to determine details like resource type, so its format is critical for proper execution. It also requires the prefix of `make_changes-`.<br>
For example: <br>
  `make_changes-snapshot-917345645813-20260714-000007.csv`

NOTE: the default `launch.json` configuration passes the currently selected file in VS code.

```shell
# Dry-run: shows what would change. This should only include "rbrk_" tags for now
update_tags-aws.py make_changes-csv_filename --skip-region me-central-1 --log

# After validatin output
update_tags-aws.py make_changes-csv_filename --skip-region me-central-1 --apply
