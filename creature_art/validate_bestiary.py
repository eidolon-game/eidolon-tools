"""Validate the proposed creature art registry; standard library only."""
import json
import math
import re
import sys
from pathlib import Path

def validate(data):
    errors = []
    if data.get("schemaVersion") != 1 or data.get("units") != "meters":
        errors.append("unsupported schema or units")
    seen = set()
    required = ("id", "name", "category", "height", "habitat", "silhouette",
                "materials", "locomotion", "attacks", "vulnerability", "anatomy",
                "behavior", "variants", "rig", "animations", "collision", "lod",
                "status", "provenance", "canonStatus", "revealChapter")
    for e in data.get("entries", []):
        ident = e.get("id", "")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+", ident) or ident in seen:
            errors.append(f"invalid or duplicate id: {ident}")
        else:
            seen.add(ident)
        for key in required:
            if not e.get(key):
                errors.append(f"{ident}: missing {key}")
        h = e.get("height")
        if not isinstance(h, (int, float)) or isinstance(h, bool) or not math.isfinite(h) or h <= 0:
            errors.append(f"{ident}: invalid height")
        elif e.get("category") == "giant" and not 5 <= h <= 40:
            errors.append(f"{ident}: giant outside canon scale")
        if e.get("status") == "specified" and e.get("asset") is not None:
            errors.append(f"{ident}: specification cannot claim asset")
    if not seen:
        errors.append("empty registry")
    return errors

if __name__ == "__main__":
    errors = validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    print("\n".join(errors) if errors else "Registry valid")
    raise SystemExit(bool(errors))
