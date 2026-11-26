"""Verify generated artifact integrity independently of Blender."""
import hashlib, json, re, struct, sys
from pathlib import Path
root = Path(sys.argv[1])
registry = json.loads(Path(__file__).with_name("registry.json").read_text())
report = json.loads((root / "report.json").read_text())
assets = registry["assets"]
ids = [a["id"] for a in assets]
assert len(ids) == len(set(ids))
assert all(re.fullmatch(r"asset\.[a-z0-9.]+", i) for i in ids)
asset = next(a for a in assets if a["id"] == report["id"])
assert report["status"] == "generated"
assert report["dimensions_m"] == asset["dimensions_m"]
assert set(report["files"]) == {asset["path"], "SM_Pipeline_Calibration.blend", "preview.png"}
for name, digest in report["files"].items():
    assert Path(name).name == name
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
data = (root / asset["path"]).read_bytes()
magic, version, size = struct.unpack_from("<4sII", data)
assert (magic, version, size) == (b"glTF", 2, len(data))
length, kind = struct.unpack_from("<I4s", data, 12)
assert kind == b"JSON"
doc = json.loads(data[20:20+length])
assert doc["meshes"] and doc["materials"]
for mesh in doc["meshes"]:
    for primitive in mesh["primitives"]:
        assert {"POSITION","NORMAL","TEXCOORD_0"} <= primitive["attributes"].keys()
assert (root / "preview.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
print("Artifact integrity and GLB structure passed; visual and UE review pending.")
