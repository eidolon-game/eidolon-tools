"""Structural quest graph checks; not a runtime reachability proof."""
import json
import re
import sys
from pathlib import Path

ID = re.compile(r"^[a-z][a-z0-9_]*$")
def validate(data):
    if data.get("schema_version") != 1:
        raise ValueError("unsupported schema")
    quests = data["quests"]
    by_id = {}
    for q in quests:
        key = q["id"]
        if not ID.fullmatch(key) or key in by_id:
            raise ValueError(f"invalid/duplicate ID: {key}")
        by_id[key] = q
        if not 1 <= q["chapter"] <= 26 or not 1 <= q["act"] <= 10:
            raise ValueError(f"invalid chapter/act: {key}")
        for field in ("category", "title", "description", "npcs", "prerequisites", "objectives", "success", "failure", "dialogue", "rewards", "consequences", "dependencies", "discrepancy", "status"):
            if field not in q:
                raise ValueError(f"missing {field}: {key}")
        steps = q["objectives"]
        if not steps or len({s["id"] for s in steps}) != len(steps):
            raise ValueError(f"empty/duplicate objective: {key}")
        for s in steps:
            if not ID.fullmatch(s["id"]) or not ID.fullmatch(s["event"]) or type(s["required"]) is not int or s["required"] < 1:
                raise ValueError(f"invalid objective: {key}")
    deps = {k: set(q["prerequisites"] + q["dependencies"]) for k,q in by_id.items()}
    for k, refs in deps.items():
        if refs - by_id.keys():
            raise ValueError(f"missing dependency: {k}")
    reached = set()
    while True:
        new = {k for k, refs in deps.items() if refs <= reached}
        if new == reached:
            break
        reached = new
    if reached != by_id.keys():
        raise ValueError(f"cycle or prerequisite deadlock: {sorted(by_id.keys()-reached)}")
    main = sorted(q["chapter"] for q in quests if q["category"] == "main")
    if main != list(range(1,27)):
        raise ValueError("main chapter coverage")
    endings = data["endings"]
    if len(endings) != 4 or {e["id"] for e in endings} != {"custodian","origin","guild","freedom"}:
        raise ValueError("ending coverage")
    for e in endings:
        if not e["requires"] or not set(e["requires"]) <= reached:
            raise ValueError(f"unreachable ending: {e['id']}")
    return len(reached)

if __name__ == "__main__":
    try:
        print(f"PASS: {validate(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))} structurally reachable quests")
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
