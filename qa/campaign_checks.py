"""Independent campaign data and graph checks; no Unreal runtime claims."""
import argparse
import json
import re
from pathlib import Path
from collections import deque

def validate_campaign(data, story):
    errors = []
    chapters = data.get("chapters", [])
    endings = data.get("endings", [])
    if data.get("schema") != 1:
        errors.append("schema")
    if [c.get("id") for c in chapters] != list(range(1, 27)):
        errors.append("chapter IDs/order")
    if sorted({c.get("act") for c in chapters}) != list(range(1, 11)):
        errors.append("act coverage")
    canon = [(int(i), t) for i, t in re.findall(r"^## \*\*Capitolo (\d+) – (.*?)\*\*", story, re.M)]
    if canon != [(c.get("id"), c.get("title")) for c in chapters] or len(canon) != 26:
        errors.append("canonical chapter titles")
    for c in chapters:
        if type(c.get("target")) is not int or c["target"] < 0 or not c.get("objective") or not c.get("type"):
            errors.append(f"objective: {c.get('id')}")
        lines = c.get("dialogue", [])
        if len(lines) < 2 or any(not d.get("speaker") or not d.get("text") for d in lines):
            errors.append(f"dialogue: {c.get('id')}")
    if len(endings) != 4 or {e.get("id") for e in endings} != {"custodian", "origin", "guild", "freedom"} or any(not e.get("epilogue") for e in endings):
        errors.append("ending IDs/epilogues")
    by_id = {c.get("id"): c for c in chapters}
    if by_id.get(7, {}).get("target") != 100:
        errors.append("chapter 7 giant target")
    for i in (4, 23):
        if by_id.get(i, {}).get("type") != "dungeon":
            errors.append(f"dungeon chapter {i}")
    return errors

def unreachable(nodes, edges, entry, required):
    """Directed topology only. Locks and physical traversal are not modeled."""
    nodes = set(nodes)
    required = set(required)
    if entry not in nodes or not required <= nodes:
        raise ValueError("unknown entry or required node")
    adjacency = {n: [] for n in nodes}
    for a, b in edges:
        if a not in nodes or b not in nodes:
            raise ValueError("unknown edge endpoint")
        adjacency[a].append(b)
    seen = {entry}
    queue = deque([entry])
    while queue:
        for n in adjacency[queue.popleft()]:
            if n not in seen:
                seen.add(n)
                queue.append(n)
    return required - seen

def main():
    p = argparse.ArgumentParser()
    p.add_argument("campaign", type=Path)
    p.add_argument("story", type=Path)
    args = p.parse_args()
    errors = validate_campaign(json.loads(args.campaign.read_text(encoding="utf-8")), args.story.read_text(encoding="utf-8"))
    print(json.dumps({"scope": "campaign data only", "status": "failed" if errors else "passed", "errors": errors}))
    return int(bool(errors))

if __name__ == "__main__":
    raise SystemExit(main())
