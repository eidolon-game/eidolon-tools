"""Refine seven Buried Forest GLBs and verify the exported mechanical geometry."""

import argparse
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector, noise

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(TOOLS / "scripts/creatures"))
from refine_forest_landmarks import digest, tree_for
from refine_catacomb_armor import bounds, check_tangent_channels, import_glb, render, reset, statistics

ORIGINALS = TOOLS / "previews/buried-forest"
ASSETS = {
    "oblique_clearing_overlook": Path("oblique_clearing_overlook.glb"),
    "branch_terrace_ladder": Path("branch_terrace_ladder.glb"),
    "fern_basin_handwheel": Path("fern-basin/fern_basin_handwheel.glb"),
    "hollow_trunk_pin": Path("hollow-trunk/hollow_trunk_pin.glb"),
    "rootlet_canal_gate": Path("rootlet-canal/rootlet_canal_gate.glb"),
    "suspended_trunks_bridge": Path("suspended-trunks/suspended_trunks_bridge.glb"),
    "double_clearing_latch": Path("double-clearing/double_clearing_latch.glb"),
}
DETAILS = {
    "oblique_clearing_overlook": (0, -1.43, .72),
    "branch_terrace_ladder": (.35, -.20, -.48),
    "fern_basin_handwheel": (.67, -.32, 1.15),
    "hollow_trunk_pin": (0, -.53, 1.15),
    "rootlet_canal_gate": (.83, -.32, 2.88),
    "suspended_trunks_bridge": (-.84, -.59, .50),
    "double_clearing_latch": (1.12, -.45, 1.38),
}


def wear(obj, depth, cuts, surface, seed, preserve_top=False):
    """Cut grain and spalling into the surface using UV-preserving subdivision."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=cuts, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    matrix = obj.matrix_world
    world_to_local = matrix.inverted().to_3x3()
    normal_matrix = world_to_local.transposed()
    shift = Vector((5.693 + seed * 1.23, 17.132 + seed * .31, 2.669))
    lo, hi = bounds((obj,))
    # Timber bars built on local Z follow that axis, treads their local Y.
    grain_axis = 1 if obj.name.startswith("Tread ") else 0 if obj.name.startswith("Fallen oak trunk ") else 2
    for vertex in bm.verts:
        pos = matrix @ vertex.co
        normal = (normal_matrix @ vertex.normal).normalized()
        if preserve_top and pos.z > hi.z - .012 and normal.z > .18:
            continue
        if surface == "wood":
            sample = vertex.co.copy()
            sample[grain_axis] *= .055
            sample = sample * 87 + shift
            seams = max(0.0, noise.noise(sample) + .17)
            gouge = .13 * abs(noise.noise(sample * 2.3)) + .94 * seams ** 2
        elif surface == "stone":
            warp = noise.noise(pos * 3.6 + shift)
            bed = abs(math.sin((pos.z + .029 * warp + .037 * pos.x) * 104 + seed))
            flakes = max(0.0, noise.noise(pos * 16 + shift) + .19)
            gouge = min(1.0, .68 * flakes + .55 * (1 - bed) ** 4)
        else:
            # Forging and corrosion tend to pit broad faces without moving contact edges.
            pit = noise.noise(pos * 118 + shift)
            gouge = max(0.0, pit + .06) ** 2
        if pos.z > lo.z + .0001:
            vertex.co -= world_to_local @ (normal * (depth * gouge))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def match(objects, prefix):
    result = [obj for name, obj in objects.items() if name.startswith(prefix)]
    if not result:
        raise ValueError(f"Missing mesh prefix {prefix}")
    return sorted(result, key=lambda obj: obj.name)


def refine_overlook(objects):
    for index, name in enumerate(("Buried foundation", "Lower shale plate", "Slanted seam",
                                  "Walkable upper plate", "Rear fern shelf", "Outer shale fragment")):
        wear(objects[name], .079 if index < 3 else .039, 12, "stone", index, preserve_top=index == 3)
    wear(objects["Hanging roots"], .009, 3, "wood", 19)


def refine_ladder(objects):
    for index, obj in enumerate(match(objects, ("Rail ", "Hoist upright", "Hoist projecting branch"))):
        wear(obj, .037 if "Rail" in obj.name else .024, 10, "wood", index)
    for index in range(1, 12):
        wear(objects[f"Rung {index:02}"], .012, 5, "wood", index, preserve_top=True)
    for index, obj in enumerate(match(objects, ("Anchor plate ", "Axle cap ", "Rung collar "))):
        wear(obj, .0064, 3, "metal", index)
    wear(objects["Cast stone counterweight"], .028, 7, "stone", 47)


def refine_intake(objects):
    for index, obj in enumerate(match(objects, ("Ashlar ", "Apron stone", "Damp inlet sill", "Wet lintel",
                                                "Basalt cap", "Wheel mounting pedestal"))):
        wear(obj, .034, 7, "stone", index)
    for index, obj in enumerate(match(objects, ("Intake grille ", "Cast iron wheel rim", "Wheel spoke ",
                                                "Bronze rotating hub", "Pull grip", "Face lock nut"))):
        wear(obj, .005, 3, "metal", index)


def refine_trunk(objects):
    wear(objects["Ancient trunk"], .065, 5, "wood", 57)
    for index, name in enumerate(("Shaped plaque backing", "Pin head washer", "Twisted bronze pull loop",
                                  "Loop mounting stud")):
        wear(objects[name], .0058, 3, "metal", index)


def refine_gate(objects):
    for index, obj in enumerate(match(objects, ("Canal ashlar ", "External footing ", "Heavy stone lintel",
                                                "Marked river stone counterweight"))):
        wear(obj, .037, 6, "stone", index)
    for index, obj in enumerate(match(objects, ("Pillar root ", "Fork root "))):
        wear(obj, .014, 4, "wood", index)
    for index, obj in enumerate(match(objects, ("Gate cross strap ", "Gate upright ", "Counterweight iron strap ")),
                                start=50):
        wear(obj, .008, 4, "metal", index)


def refine_bridge(objects):
    wear(objects["Central layered islet"], .041, 8, "stone", 72, preserve_top=True)
    for index, obj in enumerate(match(objects, ("Fallen oak trunk ", "Railing post "))):
        wear(obj, .033, 8, "wood", index)
    for index in range(1, 20):
        wear(objects[f"Tread {index:02}"], .016, 7, "wood", index, preserve_top=True)
    for index, obj in enumerate(match(objects, ("Iron trunk cage ", "Post shoe ", "Deck end band "))):
        wear(obj, .009, 4, "metal", index)


def refine_latch(objects):
    for index, obj in enumerate(match(objects, ("Gate foot ", "Gate pier ", "Chipped gate lintel",
                                                "Stone index backing"))):
        wear(obj, .032, 7, "stone", index)
    for index, obj in enumerate(match(objects, ("Left upper root", "Root above latch", "Root across pier toe",
                                                "Oak hand grip"))):
        wear(obj, .016, 8, "wood", index)
    for index, obj in enumerate(match(objects, ("Forged latch handle", "Grip band ", "Iron strike backing"))):
        wear(obj, .007, 4, "metal", index)


RECIPES = dict(zip(ASSETS, (refine_overlook, refine_ladder, refine_intake, refine_trunk, refine_gate,
                          refine_bridge, refine_latch)))


def scene_contract():
    return {
        obj.name: {
            "parent": obj.parent.name if obj.parent else None,
            "type": obj.type,
            "transform": tuple(value for row in obj.matrix_local for value in row),
            "properties": {key: obj[key] for key in obj.keys()},
        }
        for obj in bpy.context.scene.objects
    }


def verify_contract(reference, candidate):
    assert reference.keys() == candidate.keys(), (reference.keys() - candidate.keys(), candidate.keys() - reference.keys())
    for name, expected in reference.items():
        actual = candidate[name]
        for field in ("parent", "type", "properties"):
            assert expected[field] == actual[field], (name, field, expected[field], actual[field])
        assert all(abs(old - new) < .00002 for old, new in zip(expected["transform"], actual["transform"])), name


def verify_tread(objects, xs, ys, elevation, distance=3.0):
    model = tree_for(objects.values())
    for x in xs:
        for y in ys:
            found, _, _, _ = model.ray_cast((x, y, elevation + distance), (0, 0, -1), distance + .02)
            assert found is not None and abs(found.z - elevation) < .012, (x, y, found)
    return len(xs) * len(ys)


def sweep_translation(group, fixed, moving, travel, steps):
    start = group.location.copy()
    obstacles = tree_for(fixed)
    for index in range(steps + 1):
        group.location = start + travel * (index / steps)
        bpy.context.view_layer.update()
        assert not obstacles.overlap(tree_for(moving)), (group.name, index)
    return steps + 1


def sweep_rotation(group, fixed, moving, axis, start, end, steps):
    group.rotation_mode = "XYZ"
    obstacles = tree_for(fixed)
    for index in range(steps + 1):
        group.rotation_euler[axis] = start + (end - start) * index / steps
        bpy.context.view_layer.update()
        assert not obstacles.overlap(tree_for(moving)), (group.name, index)
    return steps + 1


def verify_shapes(asset, objects):
    scene = bpy.context.scene.objects
    if asset == "oblique_clearing_overlook":
        return {"level_tread_samples": verify_tread(objects, [-1.5 + .5 * n for n in range(7)],
                                                    [-1.31 + .255 * n for n in range(5)], 1.1)}
    if asset == "branch_terrace_ladder":
        rungs = match(objects, tuple(f"Rung {n:02}" for n in range(1, 12)))
        assert len(rungs) == 11
        for rung in rungs:
            lo, hi = bounds((rung,))
            assert lo.x < -.57 and hi.x > .57
        hinge = scene["Ladder_Hinge_Pivot"]
        hinge.rotation_mode = "XYZ"
        axle = objects["Hinge axle"].matrix_world.copy()
        lowest = rungs[-1].matrix_world.translation.copy()
        hinge.rotation_euler.x += math.pi / 6
        bpy.context.view_layer.update()
        assert objects["Hinge axle"].matrix_world == axle
        assert (rungs[-1].matrix_world.translation - lowest).length > 1.50
        return {"full_width_rungs": len(rungs), "hinge_rotation_degrees": 30}
    if asset == "fern_basin_handwheel":
        group = scene["Handwheel_Pivot"]
        group.rotation_mode = "XYZ"
        center = group.matrix_world.translation.copy()
        fixed = objects["Stationary spindle collar"].matrix_world.copy()
        grip = objects["Pull grip"].matrix_world.translation.copy()
        group.rotation_euler.y += math.pi / 2
        bpy.context.view_layer.update()
        assert (group.matrix_world.translation - center).length < .00002
        assert objects["Stationary spindle collar"].matrix_world == fixed
        assert (objects["Pull grip"].matrix_world.translation - grip).length > .27
        return {"grip_rotation_degrees": 90}
    if asset == "hollow_trunk_pin":
        group = scene["Removable_Keyed_Pin"]
        fixed = match(objects, ("Ancient trunk", "Bronze keyway collar", "Iron socket throat"))
        moving = (objects["Keyed pin shaft"], objects["Pin key ridge"])
        return {"withdrawal_samples": sweep_translation(group, fixed, moving, Vector((0, -.58, 0)), 29)}
    if asset == "rootlet_canal_gate":
        scene["Saracinesca_Lift"].location.z += 2.25
        scene["Marked_Stone_Counterweight"].location.z -= 2.25
        bpy.context.view_layer.update()
        model = tree_for(objects.values())
        for nx in range(8):
            for nz in range(7):
                found, _, _, _ = model.ray_cast((-.78 + nx * 1.56 / 7, -1, .01 + nz * .355),
                                                (0, 1, 0), 2)
                assert found is None, (nx, nz, found)
        return {"raised_gate_clearance_rays": 56, "travel_m": 2.25}
    if asset == "suspended_trunks_bridge":
        treads = {f"Tread {index:02}": objects[f"Tread {index:02}"] for index in range(1, 20)}
        lane = verify_tread(treads, [-2.42 + index * .269 for index in range(19)], [-.65, 0, .65], .5405)
        group = scene["Suspended_Trunks_Swing_Pivot"]
        fixed = (objects["Central layered islet"],)
        moving = match(objects, ("Fallen oak trunk ", "Under-deck pivot yoke", "Railing post "))
        return {"deck_samples": lane,
                "sweep_samples": sweep_rotation(group, fixed, moving, 2, 0, math.pi / 2, 18)}
    group = scene["Two_Detent_Handle_Pivot"]
    group.rotation_mode = "XYZ"
    tooth = scene["Retractable_Index_Tooth"]
    obstacles = match(objects, ("Left outer tooth", "Central index crest", "Right outer tooth"))
    moving = (objects["Sliding index tooth"],)
    start, end = (math.radians(group[key]) for key in ("detent_a_degrees", "detent_b_degrees"))
    obstacle_tree = tree_for(obstacles)
    for detent in (start, end):
        group.rotation_euler.y = detent
        bpy.context.view_layer.update()
        assert not obstacle_tree.overlap(tree_for(moving)), detent
    tooth.location.y -= tooth["retract_before_turn_m"]
    return {"detents_checked": 2,
            "retracted_sweep_samples": sweep_rotation(group, obstacles, moving, 1, start, end, 37)}


def build(asset, catalog, directory, samples):
    relative = ASSETS[asset]
    original = ORIGINALS / relative
    reset()
    old = import_glb(original)
    reference = scene_contract()
    original_bounds = bounds(old.values())
    original_stats = statistics(old.values())
    output = directory / asset
    output.mkdir(parents=True, exist_ok=True)
    if samples:
        old_scene = list(bpy.context.scene.objects)
        render(output / "before.png", old_scene, original_bounds, False, samples)
        render(output / "before_detail.png", old_scene, original_bounds, True, samples, detail_focus=DETAILS[asset])
    original_checks = verify_shapes(asset, old)
    reset()
    objects = import_glb(catalog / "buried-forest" / relative)
    RECIPES[asset](objects)
    candidate = output / relative.name
    result = bpy.ops.export_scene.gltf(filepath=str(candidate), export_format="GLB", export_apply=True,
                                      export_extras=True, export_tangents=True)
    assert "FINISHED" in result
    tangents = check_tangent_channels(candidate)
    assert tangents > 0
    reset()
    new = import_glb(candidate)
    verify_contract(reference, scene_contract())
    new_stats = statistics(new.values())
    assert new_stats["triangles"] > original_stats["triangles"]
    assert all(abs(r - e) < .025 for r, e in zip(new_stats["bounds_m"], original_stats["bounds_m"])), new_stats
    assert abs(new_stats["floor_m"] - original_stats["floor_m"]) < .012, new_stats
    if samples:
        new_scene = list(bpy.context.scene.objects)
        render(output / "after.png", new_scene, original_bounds, False, samples)
        render(output / "after_detail.png", new_scene, original_bounds, True, samples, detail_focus=DETAILS[asset])
    checks = verify_shapes(asset, new)
    assert original_checks == checks, (original_checks, checks)
    report = {"asset": asset, "source_sha256": digest(original), "result_sha256": digest(candidate),
              "original": original_stats, "reimport": new_stats, "verified_transforms": len(reference),
              "textured_primitives_with_tangents": tangents, "geometric_checks": checks,
              "blender": bpy.app.version_string}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("VERIFIED", report, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_catalog", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--asset", choices=tuple(ASSETS), action="append")
    parser.add_argument("--samples", type=int, default=24, help="Use 0 to export and verify without renders")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    for asset in args.asset or ASSETS:
        build(asset, args.input_catalog.resolve(), args.output.resolve(), args.samples)


if __name__ == "__main__":
    main()
