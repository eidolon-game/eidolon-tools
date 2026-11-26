"""Validate the studio asset registry without Blender."""
import json
import re
from pathlib import Path

def validate(doc):
    if doc.get("schema_version") != 2:
        raise ValueError("Unsupported registry schema")
    assets = doc["assets"]
    by_id = {}
    aliases = set()
    for a in assets:
        key = a["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in by_id:
            raise ValueError("Invalid or duplicate ID: " + key)
        by_id[key] = a
        for alias in a.get("legacy_ids", []):
            if alias in aliases:
                raise ValueError("Duplicate alias")
            aliases.add(alias)
        if not all(a.get(k) for k in ("category", "author", "license", "source", "format", "path")):
            raise ValueError("Missing provenance")
        if a["status"] not in ("specified", "generated", "verified", "approved"):
            raise ValueError("Unknown status")
        if a["status"] != "specified" and not re.fullmatch(r"[0-9a-f]{64}", a.get("checksum") or ""):
            raise ValueError("Missing artifact checksum")
        if a["dimensions_cm"] != [round(v * 100, 6) for v in a["dimensions_m"]] or any(v <= 0 for v in a["dimensions_m"]) or len(a["dimensions_m"]) != 3:
            raise ValueError("Invalid unit conversion")
    if aliases & by_id.keys():
        raise ValueError("Alias shadows canonical ID")
    visiting, done = set(), set()
    def visit(key):
        if key in visiting:
            raise ValueError("Dependency cycle")
        if key in done:
            return
        if key not in by_id:
            raise ValueError("Missing dependency: " + key)
        visiting.add(key)
        for dep in by_id[key]["dependencies"]:
            visit(dep)
        visiting.remove(key)
        done.add(key)
    for key in by_id:
        visit(key)

if __name__ == "__main__":
    validate(json.loads(Path(__file__).with_name("registry.json").read_text()))
    print("Registry validated")
