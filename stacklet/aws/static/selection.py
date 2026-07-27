"""Single source of truth for which resource types a run should process.

The user edits `static/stacklet-resource.json` -- a plain JSON array of
resource-type keys, e.g. `["rds", "s3", "ebs"]` -- and both `run-listings.py`
and `automate-tagging.py` read it via :func:`load_selection` as their default
selection, so the list only lives in one place.
"""

import json
from pathlib import Path

SELECTION_FILE = Path(__file__).parent / "stacklet-resource.json"


def load_selection() -> list[str]:
    """Return the ordered, de-duplicated resource-type keys the user selected.
    """
    if not SELECTION_FILE.exists():
        return []

    try:
        data = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{SELECTION_FILE.name} is not valid JSON: {e}") from e

    if not isinstance(data, list) or any(not isinstance(x, str) or not x.strip() for x in data):
        raise ValueError(f"{SELECTION_FILE.name} must be a JSON array of non-empty strings")

    seen: set[str] = set()
    out: list[str] = []
    for x in (s.strip() for s in data):
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
