"""Validate First Descent prototype manifest (stdlib only). All rights reserved."""
import json
import re
import sys
from pathlib import Path

def validate(data):
    if data.get("schema_version") != 1 or data.get("units") != "cm":
        raise ValueError("Unsupported schema or units")
    assets = data["assets"]
    ids = [a["id"] for a in assets]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Empty or duplicate asset IDs")
    for asset in assets:
        if not re.fullmatch(r"env_asset_[a-z0-9_]+", asset["id"]):
            raise ValueError("Invalid asset ID")
        size = asset["size_cm"]
        if len(size) != 3 or any(type(v) not in (int, float) or not 0 < v < 100000 for v in size):
            raise ValueError("Invalid dimensions")
        if asset["pivot"] != "bottom_center" or asset["rights"] != "all_rights_reserved":
            raise ValueError("Missing pivot or rights")
    return len(ids)

if __name__ == "__main__":
    print("Validated", validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))), "prototype specifications")
