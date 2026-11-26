"""Check an EIDOLON static material review against the original GLB catalog."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

from refine_catalog_surfaces import CATALOG_GROUPS, PREVIEW_ROOT, decode_glb, surface_for


def inspect_model(model, root, resolution):
    relative = model["asset"]
    original = (PREVIEW_ROOT / relative).read_bytes()
    rendered = (root / relative).read_bytes()
    assert sha256(original).hexdigest() == model["source_sha256"], f"{relative}: source changed"
    assert sha256(rendered).hexdigest() == model["output_sha256"], f"{relative}: output changed"
    source, source_data = decode_glb(original)
    result, result_data = decode_glb(rendered)
    assert result_data.startswith(source_data), f"{relative}: original geometry or UV buffer changed"
    for field in ("nodes", "scenes", "scene", "skins", "animations"):
        assert result.get(field) == source.get(field), f"{relative}: {field} changed"

    materials = result["materials"]
    expected = {index for index, entry in enumerate(source["materials"])
                if surface_for(entry.get("name", "")) is not None}
    assert len(expected) == model["textured_materials"], f"{relative}: some materials missed review"
    for index in expected:
        material = materials[index]
        pbr = material["pbrMetallicRoughness"]
        indices = [pbr["baseColorTexture"]["index"], pbr["metallicRoughnessTexture"]["index"],
                   material["normalTexture"]["index"]]
        assert len(set(indices)) == 3, f"{relative}: packed channels and normals must be separate"

    for mesh in result["meshes"]:
        for primitive in mesh["primitives"]:
            if primitive.get("material") in expected:
                attributes = primitive["attributes"]
                uv = result["accessors"][attributes["TEXCOORD_0"]]
                assert uv["type"] == "VEC2", f"{relative}: invalid UV channel"
                assert uv["count"] == result["accessors"][attributes["POSITION"]]["count"]

    assert len(result["images"]) == model["images"], f"{relative}: image list changed"
    for image in result["images"]:
        view = result["bufferViews"][image["bufferView"]]
        start = view["byteOffset"]
        with Image.open(BytesIO(result_data[start:start + view["byteLength"]])) as pixels:
            assert pixels.size == (resolution, resolution), f"{relative}: wrong image resolution"
            pixels.verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    root = parser.parse_args().output
    review = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    expected = {path.relative_to(PREVIEW_ROOT).as_posix() for group in CATALOG_GROUPS
                for path in (PREVIEW_ROOT / group).rglob("*.glb")}
    assert {model["asset"] for model in review["models"]} == expected, "Incomplete review catalog"
    for model in review["models"]:
        inspect_model(model, root, review["resolution"])
    print(f"Checked {len(expected)} GLBs, embedded maps, UV coverage and original geometry")


if __name__ == "__main__":
    main()
