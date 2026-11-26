"""Validate the proposed identity mapping against the preserved graph catalog."""
import json
import re
import sys

def validate(graphs, mapping):
    expected = {}
    for f in graphs["floors"]:
        dungeon = {"abyss": "abyss", "eternity": "stair"}[f["dungeon"]]
        n = f["index"]
        if not 1 <= n <= 100:
            raise ValueError("invalid floor")
        if f["id"] in expected:
            raise ValueError("duplicate legacy floor")
        expected[f["id"]] = (f"{dungeon}_{n:03}", dungeon, n, f["duration_minutes"] * 60)
    seen = set()
    legacy = set()
    for r in mapping["records"]:
        key = r["legacy_id"]
        if key in legacy or r["id"] in seen or not re.fullmatch(r"[a-z][a-z0-9_]*", r["id"]):
            raise ValueError("invalid or duplicate identity")
        if expected.get(key) != (r["id"], r["dungeon_id"], r["floor"], r["duration_seconds"]):
            raise ValueError("mapping mismatch")
        legacy.add(key)
        seen.add(r["id"])
    required = {f"{d}_{n:03}" for d in ("abyss", "stair") for n in range(1, 101)}
    if legacy != set(expected) or seen != required:
        raise ValueError("incomplete mapping")
    return len(seen)

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        graphs = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        mapping = json.load(f)
    print(f"Validated {validate(graphs, mapping)} floor identities")
