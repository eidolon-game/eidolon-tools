"""Validate the isolated animation catalog; no Unreal dependency."""
import argparse
import json
from pathlib import Path

def validate(data):
    if data.get("schema_version") != 1:
        raise ValueError("unsupported schema")
    rows = data["clips"] + data["cinematics"]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ID")
    expected = {f"cin.ch{i:02d}.primary" for i in range(1, 27)}
    expected |= {f"cin.ending.{i}" for i in range(1, 5)}
    if {r["id"] for r in data["cinematics"]} != expected:
        raise ValueError("campaign coverage mismatch")
    for row in data["cinematics"]:
        chapter = 26 if row["id"].startswith("cin.ending.") else int(row["id"][6:8])
        if row["chapter"] != chapter:
            raise ValueError("chapter mismatch")
    for row in rows:
        if row["asset"] is None and row.get("status", data["status"]) != "specified":
            raise ValueError("missing asset with non-specification status")
    for row in data["clips"]:
        if row["root_motion"] not in {"in_place", "authorized_montage"}:
            raise ValueError("invalid motion policy")
    return len(rows)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    args = parser.parse_args()
    print(f"Validated {validate(json.loads(args.catalog.read_text(encoding='utf-8')))} records")
