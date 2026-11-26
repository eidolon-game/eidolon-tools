"""Split the approved Mine Borer GLB into pivot-local glTF meshes for Unreal."""

import argparse
from hashlib import sha256
import json
from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_mine_borer import PIVOTS, REAR_CAMERA, set_rear_open
from refine_catacomb_armor import bounds, check_tangent_channels, import_glb, render, reset, statistics

SOURCE = Path(__file__).resolve().parents[2] / "previews/lost-mines/mine-borer"
ACTOR_ORIGIN_M = (0.0, 0.0, 1.48)
PARTS = {
    "Body": PIVOTS[0],
    "Head": PIVOTS[1],
    "RearLeft": PIVOTS[7],
    "RearRight": PIVOTS[8],
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def ue_cm(point):
    """Change Blender -Y forward and +Z up to Unreal +X forward and +Z up."""
    return [round(value * 100, 5) for value in (-point.y, -point.x, point.z)]


def ue_bounds(objects):
    values = [ue_cm(obj.matrix_world @ vertex.co) for obj in objects for vertex in obj.data.vertices]
    return {key: [combine(axis) for axis in zip(*values)] for key, combine in (("min", min), ("max", max))}


def part_meshes(objects, pivots):
    split = {name: [] for name in pivots}
    names = {pivot.name: name for name, pivot in pivots.items()}
    for obj in objects:
        parent = obj.parent
        while parent and parent.name not in names:
            parent = parent.parent
        if parent is None:
            raise ValueError(f"No Mine Borer pivot owns {obj.name}")
        split[names[parent.name]].append(obj)
    return split


def cloud(meshes):
    return [obj.matrix_world @ point.co for obj in meshes for point in obj.data.vertices]


def max_point_difference(reference, actual):
    lookup = KDTree(len(reference))
    for index, point in enumerate(reference):
        lookup.insert(point, index)
    lookup.balance()
    return max(lookup.find(point)[2] for point in actual)


def assert_geometry(reference, actual, label):
    assert reference and actual
    error = max(max_point_difference(reference, actual), max_point_difference(actual, reference))
    if error > .00004:
        raise ValueError(f"{label} differs from the source by {error:.6f} m")
    return round(error * 1000, 6)


def export_part(source, output, name):
    reset()
    objects = list(import_glb(source).values())
    pivots = {part: bpy.data.objects[pivot] for part, pivot in PARTS.items()}
    pivot = pivots[name]
    meshes = part_meshes(objects, pivots)[name]
    reference = cloud(meshes)
    source_triangles = statistics(meshes)["triangles"]
    position = pivot.matrix_world.translation.copy()
    matrix = pivot.matrix_world.copy()
    bpy.ops.object.select_all(action="DESELECT")
    for item in meshes:
        original = item.matrix_world.copy()
        original.translation -= position
        item.parent = None
        item.matrix_world = original
        item.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    merged.name = f"SM_MineBorer_{name}"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    path = output / f"{merged.name}.glb"
    assert "FINISHED" in bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_apply=True,
                                                  export_tangents=True, use_selection=True)
    tangent_count = check_tangent_channels(path)
    assert tangent_count
    reset()
    imported = list(import_glb(path).values())
    assert len(imported) == 1
    actual = imported[0]
    local_bounds = ue_bounds(imported)
    assert statistics(imported)["triangles"] == source_triangles
    actual.location += position
    bpy.context.view_layer.update()
    delta = assert_geometry(reference, cloud(imported), name)
    return {"name": name, "file": path.name, "sha256": digest(path),
            "pivot_cm": ue_cm(position - Vector(ACTOR_ORIGIN_M)),
            "local_bounds_cm": local_bounds, "triangles": source_triangles,
            "textured_primitives_with_tangents": tangent_count,
            "rest_error_mm": delta}, matrix


def reassemble(source, parts, pivots, directory, samples):
    reset()
    authoring = list(import_glb(source).values())
    rest = cloud(authoring)
    set_rear_open(True)
    recovery = cloud(authoring)
    opened = {name: bpy.data.objects[reference].matrix_world.copy() for name, reference in PARTS.items()}
    left = (opened["RearLeft"] @ pivots["RearLeft"].inverted()).to_quaternion()
    right = (opened["RearRight"] @ pivots["RearRight"].inverted()).to_quaternion()
    assert abs(left.dot(right.inverted())) > .99999
    axis, radians = left.to_axis_angle()
    # Rotation axes pick up an extra sign when converting to a left-handed frame.
    hinge = {"axis": [round(value, 7) for value in (axis.y, axis.x, -axis.z)], "radians": round(radians, 7)}
    reset()
    meshes = {}
    for part in parts:
        mesh, = load_new(directory / part["file"])
        meshes[part["name"]] = mesh
        mesh.location += pivots[part["name"]].translation
    bpy.context.view_layer.update()
    assert_geometry(rest, cloud(meshes.values()), "whole rest pose")
    rest_bounds = bounds(meshes.values())
    nodes = list(meshes.values())
    if samples:
        render(directory / "assembled_front.png", nodes, rest_bounds, False, samples)
    for name, mesh in meshes.items():
        rest_pivot = pivots[name]
        open_pivot = opened[name]
        mesh.matrix_world = open_pivot @ rest_pivot.inverted() @ mesh.matrix_world
    bpy.context.view_layer.update()
    delta = assert_geometry(recovery, cloud(meshes.values()), "whole recovery pose")
    if samples:
        for mesh in nodes:
            mesh.matrix_world = Matrix.Rotation(pi, 4, "Z") @ mesh.matrix_world
        bpy.context.view_layer.update()
        render(directory / "assembled_recovery.png", nodes, bounds(nodes), True, samples,
               detail_focus=(0, -1.25, 1.91), camera_direction=REAR_CAMERA)
    return delta, hinge


def load_new(path):
    existing = set(bpy.context.scene.objects)
    result = bpy.ops.import_scene.gltf(filepath=str(path))
    assert "FINISHED" in result
    bpy.context.view_layer.update()
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj not in existing]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--samples", type=int, default=0)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    source = SOURCE / "MineBorer.glb"
    verification = json.loads((SOURCE / "verification.json").read_text(encoding="utf-8"))
    assert digest(source) == verification["result_sha256"]
    parts = []
    matrices = {}
    for name in PARTS:
        manifest, matrices[name] = export_part(source, directory, name)
        parts.append(manifest)
    recovery_error, hinge = reassemble(source, parts, matrices, directory, args.samples)
    manifest = {"source_glb_sha256": digest(source), "blender": bpy.app.version_string,
                "units": "Unreal centimeters", "reassembled_recovery_error_mm": recovery_error,
                "rear_open_from_rest": hinge,
                "parts": parts}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("VERIFIED", manifest, flush=True)


if __name__ == "__main__":
    main()
