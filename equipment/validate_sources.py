"""Validate department 13 registry and OBJ source geometry. All rights reserved."""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

def validate(root):
    data = json.loads((root / "Content/Eidolon/Equipment/registry.json").read_text())
    assert data["schema_version"] == 1 and data["units"] == "cm"
    seen = set()
    count = 0
    for a in data["assets"]:
        ident = a["asset_id"]
        assert re.fullmatch(r"[a-z0-9_]+", ident) and ident not in seen
        seen.add(ident)
        dims = a["dimensions_cm"]
        assert len(dims) == 3 and all(math.isfinite(x) and x > 0 for x in dims)
        assert a["rights"] and a["source"]
        if a["status"] != "graybox_source":
            continue
        path = (root / a["source_path"]).resolve()
        assert path.is_relative_to(root.resolve())
        verts, faces = [], []
        for line in path.read_text().splitlines():
            p = line.split()
            if not p:
                continue
            if p[0] == "v":
                verts.append(tuple(map(float, p[1:])))
            elif p[0] == "f":
                faces.append(tuple(map(int, p[1:])))
        assert verts and faces
        assert all(len(v) == 3 and all(map(math.isfinite, v)) for v in verts)
        edges = Counter()
        for face in faces:
            assert len(face) >= 3 and len(set(face)) == len(face)
            assert all(1 <= i <= len(verts) for i in face)
            for i, j in zip(face, face[1:] + face[:1]):
                edges[tuple(sorted((i, j)))] += 1
        assert all(n == 2 for n in edges.values())
        assert a["source_units"] == "m"
        for axis, dim in enumerate(dims):
            values = [v[axis] for v in verts]
            assert abs((max(values)-min(values))*100-dim) < 0.001
        count += 1
    return len(seen), count

if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Do not run with optimization")
    print("Validated registry entries and graybox sources:", validate(Path(sys.argv[1])))
