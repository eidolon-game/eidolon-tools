"""Add original PBR maps to the 22 static EIDOLON catalog models.

The source GLBs stay in place. The output keeps transforms, hierarchy and
geometry, with planar UVs on primitives that lacked a texture channel.
Requires Python, NumPy and Pillow. The surfaces are a review pass, not a rig.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

import numpy as np

from surface_tiles import render_maps


PREVIEW_ROOT = Path(__file__).resolve().parents[2] / "previews"
CATALOG_GROUPS = ("first-descent", "catacombs", "buried-forest")
JSON_CHUNK = b"JSON"
BIN_CHUNK = b"BIN\0"


def decode_glb(data):
    signature, version, total_length = struct.unpack_from("<4sII", data)
    json_length, json_chunk = struct.unpack_from("<I4s", data, 12)
    bin_start = 20 + json_length
    bin_length, bin_chunk = struct.unpack_from("<I4s", data, bin_start)
    if (signature != b"glTF" or version != 2 or total_length != len(data)
            or json_chunk != JSON_CHUNK or bin_chunk != BIN_CHUNK
            or bin_start + 8 + bin_length != len(data)):
        raise ValueError("Expected a single-buffer glTF 2.0 binary file")
    return json.loads(data[20:bin_start]), bytearray(data[bin_start + 8:])


def encode_glb(document, contents):
    document["buffers"][0]["byteLength"] = len(contents)
    document_bytes = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    document_bytes += b" " * (-len(document_bytes) % 4)
    contents.extend(b"\0" * (-len(contents) % 4))
    size = 12 + 8 + len(document_bytes) + 8 + len(contents)
    return (struct.pack("<4sII", b"glTF", 2, size) + struct.pack("<I4s", len(document_bytes), JSON_CHUNK)
            + document_bytes + struct.pack("<I4s", len(contents), BIN_CHUNK) + contents)


def append_view(document, data, payload, target=None):
    data.extend(b"\0" * (-len(data) % 4))
    view = {"buffer": 0, "byteOffset": len(data), "byteLength": len(payload)}
    if target:
        view["target"] = target
    data.extend(payload)
    document["bufferViews"].append(view)
    return len(document["bufferViews"]) - 1


def surface_for(name):
    label = name.casefold()
    words = set(re.findall(r"[a-z]+", label))
    if words & {"eye", "eyes", "ocelli", "beads", "glass"}:
        return None
    if words & {"iron", "steel", "fasteners"}:
        return "iron"
    if words & {"bronze", "verdigris"}:
        return "bronze"
    if words & {"slate", "shale", "stone", "limestone", "basalt", "bedrock", "calcite", "ashlar", "mineral", "tread"}:
        return "stone"
    if words & {"bark", "root", "roots", "rootstock"}:
        return "bark"
    if words & {"heartwood", "wood", "oak", "decking", "plank", "rung"}:
        return "wood"
    if words & {"rope", "hemp", "handline"}:
        return "rope"
    if words & {"fern", "moss", "vine"}:
        return "foliage"
    if words & {"bone", "enamel", "calcium", "calcified", "ivory"}:
        return "bone"
    if words & {"chitin", "scutes", "keratin", "cuticle"}:
        return "chitin"
    if words & {"leather", "binding"}:
        return "leather"
    return "hide"


def add_image(document, data, name, mime, pixels):
    image = {"name": name, "mimeType": mime, "bufferView": append_view(document, data, pixels)}
    images = document.setdefault("images", [])
    images.append(image)
    textures = document.setdefault("textures", [])
    textures.append({"name": name, "source": len(images) - 1})
    return len(textures) - 1


def position_array(document, data, index):
    accessor = document["accessors"][index]
    if accessor["componentType"] != 5126 or accessor["type"] != "VEC3" or "sparse" in accessor:
        raise ValueError("Expected packed float positions in the static catalog")
    view = document["bufferViews"][accessor["bufferView"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return np.ndarray((accessor["count"], 3), "<f4", data, offset, (view.get("byteStride", 12), 4)).copy()


def add_missing_uv(document, data, attributes):
    pos = position_array(document, data, attributes["POSITION"])
    centered = pos - pos.mean(axis=0)
    _, axes = np.linalg.eigh(centered.T.astype(np.float64) @ centered)
    plane = centered @ axes[:, [-1, -2]]
    width = max(np.ptp(plane, axis=0).max(), 1e-6)
    coordinates = np.ascontiguousarray(plane / width + .5, dtype="<f4")
    view = append_view(document, data, coordinates.tobytes(), 34962)
    attributes["TEXCOORD_0"] = len(document["accessors"])
    document["accessors"].append({"bufferView": view, "componentType": 5126, "count": len(pos), "type": "VEC2"})


def upgrade(source, destination, size):
    original = source.read_bytes()
    document, data = decode_glb(original)
    textured, cached = set(), {}
    for index, material in enumerate(document.get("materials", [])):
        family = surface_for(material.get("name", ""))
        if family is None:
            continue
        pbr = material.setdefault("pbrMetallicRoughness", {})
        if any(key in pbr for key in ("baseColorTexture", "metallicRoughnessTexture")) or "normalTexture" in material:
            continue
        roughness = round(pbr.get("roughnessFactor", 1) * 5) / 5
        metalness = round(pbr.get("metallicFactor", 1), 1) if family in ("iron", "bronze") else 0.0
        if family in ("stone", "bone", "bark", "wood", "rope", "foliage"):
            roughness = .8
        key = family, roughness, metalness
        if key not in cached:
            color, normal, packed = render_maps(family, size, roughness, metalness)
            prefix = f"{family}-{roughness:g}-{metalness:g}"
            cached[key] = (add_image(document, data, f"{prefix}-base-color", "image/jpeg", color),
                           add_image(document, data, f"{prefix}-normal", "image/png", normal),
                           add_image(document, data, f"{prefix}-roughness-metal", "image/png", packed))
        color, normal, packed = cached[key]
        pbr["baseColorTexture"] = {"index": color}
        pbr["metallicRoughnessTexture"] = {"index": packed}
        pbr["roughnessFactor"] = pbr["metallicFactor"] = 1
        material["normalTexture"] = {"index": normal, "scale": .78}
        textured.add(index)

    completed_uvs = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            if primitive.get("material") in textured and "TEXCOORD_0" not in attributes:
                add_missing_uv(document, data, attributes)
                completed_uvs += 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    output = encode_glb(document, data)
    destination.write_bytes(output)
    return {"source_sha256": sha256(original).hexdigest(), "output_sha256": sha256(output).hexdigest(),
            "textured_materials": len(textured), "completed_uv_primitives": completed_uvs,
            "images": len(document.get("images", []))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--size", type=int, choices=(512, 1024, 2048), default=1024)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(PREVIEW_ROOT) or PREVIEW_ROOT.is_relative_to(output):
        parser.error("Use an output directory separate from the original preview catalog")
    models = sorted(path for group in CATALOG_GROUPS for path in (PREVIEW_ROOT / group).rglob("*.glb"))
    records = []
    for model in models:
        relative = model.relative_to(PREVIEW_ROOT)
        report = upgrade(model, output / relative, args.size)
        records.append({"asset": relative.as_posix(), **report})
        print(f"{relative}: {report['textured_materials']} materials, {report['completed_uv_primitives']} UV fallbacks", flush=True)
    manifest = {"surface_source": "Original deterministic EIDOLON procedural maps", "resolution": args.size,
                "status": "surface-review candidates", "models": records}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
