"""Make the floor-21 Mine Borer and review the exported GLB in Blender."""

import argparse
from hashlib import sha256
import json
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector, noise
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "assets"))
from refine_catacomb_armor import add_ligament, bounds, check_tangent_channels, import_glb, mesh_object, render, reset, statistics
from refine_riftroot_tangle import TEXTURE_SIZE, image, tile_noise
from surface_tiles import cellular_seams

PIVOTS = ("MineBorer_Body", "MineBorer_Head", "MineBorer_Jaw",
          "MineBorer_ForeLeft", "MineBorer_ForeRight", "MineBorer_HindLeft", "MineBorer_HindRight",
          "MineBorer_RearPlateLeft", "MineBorer_RearPlateRight")
REAR_HINGE_SLOPE = -.51
REAR_CAMERA = (.57, -1.93, 1.22)


def material(name, color, roughness, kind=None, seed=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    tree = mat.node_tree
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    if kind is None:
        return mat
    rng = np.random.default_rng(seed)
    size = TEXTURE_SIZE
    u, v = np.meshgrid(np.arange(size) / size, np.arange(size) / size)
    broad = tile_noise(rng, u, v, 7, 9)
    grit = tile_noise(rng, u, v, 133, 119)
    speckle = tile_noise(rng, u, v, 271, 311)
    if kind == "ore":
        warp = v + .056 * broad
        seams = cellular_seams(size, 13, seed + 27) ** 2
        beds = tile_noise(rng, u, warp, 8, 74)
        iron = np.clip((beds * .60 + broad * .40 - .56) * 2.6, 0, .8)
        color_map = (.63 + .26 * broad + .23 * beds - .31 * seams)[..., None] * np.array(color)
        color_map += iron[..., None] * np.array([.084, .042, .016])
        relief = .43 * beds + .23 * grit + .16 * speckle - .40 * seams
        gloss = roughness + .26 * grit - .16 * iron
    else:
        pores = cellular_seams(size, 45, seed + 7)
        folds = tile_noise(rng, u + .022 * broad, v, 86, 17)
        color_map = (.61 + .30 * broad + .19 * folds - .16 * pores)[..., None] * np.array(color)
        relief = .43 * folds - .24 * pores + .19 * grit + .16 * speckle
        gloss = roughness + .18 * grit + .12 * pores
    du = (np.roll(relief, 1, 1) - np.roll(relief, -1, 1)) * 2.65
    dv = (np.roll(relief, -1, 0) - np.roll(relief, 1, 0)) * 2.65
    normal = np.stack((du, dv, np.ones_like(relief)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    for label, pixels, srgb, socket in (
            ("Base", color_map, True, "Base Color"),
            ("Roughness", gloss[..., None], False, "Roughness"),
            ("Normal", normal * .5 + .5, False, "Normal")):
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image(f"{name} {label}", pixels, color=srgb)
        if socket == "Normal":
            mapping = tree.nodes.new("ShaderNodeNormalMap")
            tree.links.new(tex.outputs["Color"], mapping.inputs["Color"])
            tree.links.new(mapping.outputs["Normal"], shader.inputs[socket])
        else:
            tree.links.new(tex.outputs["Color"], shader.inputs[socket])
    return mat


def joint(name, center, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    if parent:
        attach(obj, parent)
    return obj


def attach(obj, parent):
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world
    return obj


def smooth_path(control, steps):
    knots = list(map(Vector, control))
    for segment in range(len(knots) - 1):
        a = knots[max(0, segment - 1)]
        b, c = knots[segment:segment + 2]
        d = knots[min(len(knots) - 1, segment + 2)]
        for sample in range(steps):
            t = sample / steps
            yield (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t ** 2
                   + (-a + 3 * b - 3 * c + d) * t ** 3) * .5
    yield knots[-1]


def closed_form(name, control, mat, parent, seed, *, flatness=1.0, relief=.045, folds=0, steps=5, sides=42):
    """A closed organic cross section with UV seams kept in its corner data."""
    stations = list(smooth_path(control, steps))
    verts, faces, uvs, face_uvs = [], [], [], []
    perturb = Vector((seed * 1.28, seed * .11, 11.28))
    for index, form in enumerate(stations):
        center = Vector(form[:3])
        tangent = Vector(stations[min(index + 1, len(stations) - 1)][:3]) - Vector(stations[max(0, index - 1)][:3])
        along = tangent.normalized()
        side = along.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(along).normalized()
        if not side.length_squared:
            side, up = Vector((1, 0, 0)), Vector((0, 1, 0))
        t = index / (len(stations) - 1)
        for spoke in range(sides):
            ang = tau * spoke / sides
            cx, sy = cos(ang), sin(ang)
            cross = math_sign_pow(cx, flatness)
            profile = math_sign_pow(sy, flatness)
            radial = side * cross + up * profile
            pos = center + side * (cross * max(.006, form[3])) + up * (profile * max(.006, form[4]))
            chips = max(0, noise.noise(pos * 26 + perturb) - .14)
            broad = noise.noise(pos * 7 + perturb)
            pos += radial * (broad * .41 - chips) * min(relief, form[3] * .55, form[4] * .55)
            if folds:
                crease = max(0, sin(t * folds * tau + .36 * sin(ang * 3))) ** 4
                pos -= radial * (crease * .057 * sin(pi * t))
            verts.append(pos)
            uvs.append((spoke / sides, t))
            if index:
                current = index * sides + spoke
                following = index * sides + (spoke + 1) % sides
                face = (current - sides, current, following, following - sides)
                faces.append(face)
                face_uvs.append(((spoke / sides, (index - 1) / (len(stations) - 1)), (spoke / sides, t),
                                 ((spoke + 1) / sides, t), ((spoke + 1) / sides, (index - 1) / (len(stations) - 1))))
    for end in (0, 1):
        center_index = len(verts)
        verts.append(Vector(stations[-1 if end else 0][:3]))
        uvs.append((.5, .5))
        first = (len(stations) - 1) * sides if end else 0
        for spoke in range(sides):
            pair = (spoke, (spoke + 1) % sides)
            if end:
                pair = tuple(reversed(pair))
            faces.append((center_index, first + pair[0], first + pair[1]))
            face_uvs.append(((.5, .5),) + tuple((.5 + .47 * cos(k * tau / sides), .5 + .47 * sin(k * tau / sides))
                                              for k in pair))
    obj = mesh_object(name, verts, faces, uvs, mat)
    layer = obj.data.uv_layers.active
    for face, coordinates in zip(obj.data.polygons, face_uvs):
        face.use_smooth = len(face.vertices) == 4
        for loop, uv in zip(face.loop_indices, coordinates):
            layer.data[loop].uv = uv
    return attach(obj, parent)


def math_sign_pow(value, exponent):
    return abs(value) ** exponent if value >= 0 else -(abs(value) ** exponent)


def scute(name, center, size, side, mat, under, parent, seed):
    """Flaking dorsal plates with a distinct thick seam at the edge."""
    cx, cy, cz = center
    width, length, flank = size
    nx, ny = 27, 19
    verts, faces, uv = [], [], []
    for layer in (0, 1):
        for row in range(ny):
            v = row / (ny - 1)
            for col in range(nx):
                u = col / (nx - 1)
                x = cx + side * width * u * (1 - .20 * abs(2 * v - 1))
                split = sin(u * 12 + seed) * .036 + sin(u * 37 + seed * 2) * .013
                split += .052 * noise.noise(Vector((u * 11, v * 2.6, seed)))
                y = cy + length * (v - .48 + .23 * u ** 1.46 + split)
                z = cz - flank * u ** 1.67 + .072 * sin(v * pi) + .027 * sin(u * 13 + v * 3 + seed)
                spot = Vector((x * 9.3 + seed, y * 14.1, z * 12.6))
                chip = max(0, noise.noise(spot * 2.8) - .12)
                z += noise.noise(spot) * .053 - chip * .083
                thick = .076 + .026 * sin(v * pi) + .022 * sin(u * 8 + seed)
                verts.append((x, y, z - thick * layer))
                uv.append((u * .9 + .05, v * .9 + .05))
    count = nx * ny
    for layer in (0, 1):
        for row in range(ny - 1):
            for col in range(nx - 1):
                here = layer * count + row * nx + col
                face = (here, here + 1, here + nx + 1, here + nx)
                faces.append(face if side == (1 if not layer else -1) else face[::-1])
    boundary = (list(range(nx)) + [row * nx + nx - 1 for row in range(1, ny)]
                + list(range(count - 2, count - nx - 1, -1))
                + [row * nx for row in range(ny - 2, 0, -1)])
    for a, b in zip(boundary, boundary[1:] + boundary[:1]):
        face = (b, a, a + count, b + count)
        faces.append(face if side == 1 else face[::-1])
    obj = mesh_object(name, verts, faces, uv, mat)
    obj.data.materials.append(under)
    shell_faces = (nx - 1) * (ny - 1)
    layer = obj.data.uv_layers.active
    for face in obj.data.polygons:
        face.use_smooth = face.index < shell_faces * 2
        if face.index >= shell_faces:
            face.material_index = 1
        if face.index >= shell_faces * 2:
            edge = (face.index - shell_faces * 2) / len(boundary)
            for index, loop in enumerate(face.loop_indices):
                layer.data[loop].uv = (edge + (index in (1, 2)) / len(boundary), .13 + .16 * (index >= 2))
    return attach(obj, parent)


def foreleg_tendons(leg, sign, flank, material, pivot):
    bpy.context.view_layer.update()
    local = leg.matrix_world.inverted()
    direction = local.to_3x3() @ Vector((0, 1, 0))
    for row in range(5):
        points = []
        for index in range(13):
            t = index / 12
            x = sign * (.99 + .62 * t + (row - 2) * .061)
            z = 1.87 - 1.13 * t + (row - 2) * .011
            found, point, _, _ = leg.ray_cast(local @ Vector((x, -3, z)), direction, distance=4)
            if not found:
                raise ValueError(f"Tendon misses {leg.name} at row {row + 1}, sample {index + 1}")
            world = leg.matrix_world @ point
            world.y += .019 * cos(t * tau)
            points.append(world)
        fibre = add_ligament(f"Shoulder tension fibre {flank} {row + 1}", points, .021, material)
        attach(fibre, pivot)


def build_model(materials):
    ore, edge, shell, fascia, talon, dark, eye = materials
    body = joint(PIVOTS[0], (0, 0, 1.52))
    head = joint(PIVOTS[1], (0, -.99, 1.84), body)
    jaw = joint(PIVOTS[2], (0, -1.44, 1.34), head)
    closed_form("Segmented thorax and folded abdomen", (
        (0, -1.45, 1.76, .34, .43), (0, -1.04, 1.80, .90, .72),
        (0, -.43, 1.69, 1.11, 1.02), (0, .36, 1.53, 1.04, .99),
        (0, 1.04, 1.44, .82, .75), (0, 1.68, 1.39, .50, .44),
        (0, 1.93, 1.30, .14, .21)), shell, body, 74, folds=8, steps=12)
    closed_form("Spalled digging wedge", (
        (-.068, -2.84, 1.20, .074, .026), (-.01, -2.58, 1.30, .32, .096),
        (.038, -2.24, 1.50, .56, .217), (.028, -1.89, 1.68, .73, .38),
        (.01, -1.42, 1.82, .63, .48), (0, -.94, 1.81, .41, .31)),
        ore, head, 53, flatness=.56, relief=.128, steps=11)
    closed_form("Worn mineral keel along the wedge", (
        (-.068, -2.87, 1.211, .020, .020), (-.045, -2.65, 1.36, .105, .055),
        (.022, -2.28, 1.74, .19, .087), (.05, -1.86, 2.035, .234, .113),
        (.05, -1.55, 2.183, .201, .11), (.043, -1.36, 2.222, .087, .048)),
        edge, head, 212, flatness=.63, relief=.081, steps=10)
    closed_form("Retracted lower mandible", (
        (0, -2.63, 1.08, .12, .103), (0, -2.37, 1.09, .37, .153),
        (0, -1.99, 1.10, .53, .189), (0, -1.48, 1.28, .52, .225),
        (0, -1.16, 1.30, .28, .164)), shell, jaw, 11, flatness=.84, steps=7)
    for sign, flank in ((1, "Left"), (-1, "Right")):
        f = joint(f"MineBorer_Fore{flank}", (sign * .83, -.77, 1.85), body)
        h = joint(f"MineBorer_Hind{flank}", (sign * .62, 1.04, 1.46), body)
        p = joint(f"MineBorer_RearPlate{flank}", (sign * .64, 1.03, 2.075), body)
        p.rotation_euler.x = REAR_HINGE_SLOPE
        p["role"] = "rear_vulnerability"
        foreleg = closed_form(f"Foreleg digging muscle {flank}", (
            (sign * .62, -.58, 2.04, .30, .28), (sign * 1.007, -.61, 1.93, .47, .43),
            (sign * 1.43, -.77, 1.51, .49, .387), (sign * 1.49, -.73, 1.11, .35, .295),
            (sign * 1.61, -.98, .70, .43, .31), (sign * 1.68, -1.38, .44, .33, .23),
            (sign * 1.65, -1.61, .38, .24, .16)), shell, f, 26 + sign, relief=.067, folds=4, steps=9)
        closed_form(f"Hind leg hooked tarsus {flank}", (
            (sign * .56, .82, 1.58, .21, .29), (sign * .94, 1.08, 1.38, .35, .30),
            (sign * 1.26, 1.45 - .10 * sign, 1.00, .32, .24),
            (sign * 1.27, 1.64 - .14 * sign, .55, .19, .19),
            (sign * 1.36, 1.43 - .12 * sign, .28, .20, .16),
            (sign * 1.38, 1.12 - .10 * sign, .15, .15, .14)), shell, h, 75 + sign, relief=.068, steps=6)
        scute(f"Ore-streaked shoulder {flank}", (sign * .57, -.58 + .043 * sign, 2.65),
              (1.26, 1.02, .89), sign, ore, edge, f, 5.41 + sign)
        for row, (y, z, width, length, drop) in enumerate((
                (-.99, 2.69, .72, .37, .37), (-.57, 2.93, .79, .61, .44),
                (-.04, 2.83, .98, .67, .57), (.53, 2.58, .88, .61, .50),
                (1.12, 2.27, .76, .69, .42), (1.60, 1.99, .58, .55, .32))):
            pivot = p if row >= 4 else body
            scute(f"Overlapping ore lamina {flank} {row + 1}", (sign * .035, y + .048 * sign, z),
                  (width, length, drop), sign, ore if row < 4 else edge, shell, pivot, 3.19 * row + sign)
        for row in range(4):
            y = .73 + row * .26
            scute(f"Exposed rear chitin {flank} {row + 1}", (sign * .18, y, 2.39 - row * .153),
                  (.61 - .075 * row, .24, .36 - row * .035), sign, fascia, shell, body, 5.91 * row + sign)
        for index in range(3):
            x = 1.41 + .23 * index
            variation = .054 * (index - .5) + .069 * sign
            closed_form(f"Split shovel digit {flank} {index + 1}", (
                (sign * x, -1.32, .40, .139, .137),
                (sign * (x + .05), -1.57, .29, .162, .144),
                (sign * (x + .065), -1.82 - variation, .132, .124, .100),
                (sign * (x + .035), -2.06 - variation, .059, .065, .045),
                (sign * (x - .01), -2.17 - variation, .04, .015, .011)),
                talon, f, 29 + index * 6 + sign, flatness=.72, steps=7, sides=28)
        for index in range(2):
            x = 1.27 + .17 * index
            closed_form(f"Hind claw {flank} {index + 1}", (
                (sign * x, 1.28, .18, .096, .089),
                (sign * (x + .03), 1.06, .11, .101, .069),
                (sign * (x + .04), .81, .04, .012, .013)),
                talon, h, 20 + index + sign, steps=7, sides=24)
        foreleg_tendons(foreleg, sign, flank, fascia, f)
        closed_form(f"Eye recess {flank}", (
            (sign * .540, -2.29, 1.49, .033, .036),
            (sign * .697, -2.08, 1.573, .10, .075),
            (sign * .737, -1.78, 1.65, .035, .035)), dark, head, 98 + sign, steps=7, sides=24)
        closed_form(f"Narrow light-sensitive eye {flank}", (
            (sign * .693, -2.153, 1.555, .017, .012),
            (sign * .772, -2.087, 1.571, .038, .028),
            (sign * .784, -2.003, 1.583, .021, .014)), eye, head, 97 + sign, steps=5, sides=22)
        for index in range(3):
            y = -1.92 + .15 * index
            closed_form(f"Jaw hook {flank} {index + 1}", (
                (sign * (.43 + .035 * index), y, 1.12, .073, .071),
                (sign * (.51 + .035 * index), y - .04, 1.03, .049, .060),
                (sign * (.54 + .035 * index), y - .09, 1.026, .013, .011)),
                talon, jaw, 82 + index + sign, flatness=.88, steps=6, sides=24)


def prepare_preview(path):
    reset()
    meshes = list(import_glb(path).values())
    return list(bpy.context.scene.objects), bounds(meshes)


def set_rear_open(enabled):
    for direction, flank in ((1, "Left"), (-1, "Right")):
        plate = bpy.data.objects[f"MineBorer_RearPlate{flank}"]
        plate.rotation_mode = "QUATERNION"
        base = Quaternion((1, 0, 0), REAR_HINGE_SLOPE)
        opening = Quaternion((0, 1, 0), direction * 1.16 if enabled else 0)
        plate.rotation_quaternion = base @ opening
    bpy.context.view_layer.update()


def check_rear_motion():
    parts = [bpy.data.objects[f"Overlapping ore lamina {flank} 6"] for flank in ("Left", "Right")]
    weak_points = [bpy.data.objects[f"Exposed rear chitin {flank} 2"] for flank in ("Left", "Right")]
    anchors = [part.matrix_world.copy() for part in weak_points]
    closed = [bounds((part,))[1].z for part in parts]
    samples = []
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("Exposed rear chitin"):
            for index in range(0, len(obj.data.polygons), 16):
                face = obj.data.polygons[index]
                if face.normal.z > .1:
                    samples.append((obj, obj.matrix_world @ face.center))
    view = Vector((-REAR_CAMERA[0], -REAR_CAMERA[1], REAR_CAMERA[2])).normalized()

    def visible_samples():
        scene = bpy.context.scene
        depsgraph = bpy.context.evaluated_depsgraph_get()
        count = 0
        for target, point in samples:
            found, _, _, _, hit, _ = scene.ray_cast(depsgraph, point + view * 7, -view, distance=7.002)
            count += int(found and hit == target)
        return count

    occluded_pose = visible_samples()
    set_rear_open(True)
    rise = [bounds((part,))[1].z - height for part, height in zip(parts, closed)]
    assert min(rise) > .115, rise
    assert anchors == [part.matrix_world for part in weak_points]
    recovery_pose = visible_samples()
    assert recovery_pose > occluded_pose, (occluded_pose, recovery_pose)
    set_rear_open(False)
    return {"plate_lift_m_left_right": [round(delta, 3) for delta in rise],
            "cuticle_test_points": len(samples), "visible_closed": occluded_pose, "visible_recovery": recovery_pose}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--samples", type=int, default=24)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    reset()
    build_model((
        material("Iron-shale ore laminate", (.152, .143, .126), .69, "ore", 33),
        material("Fractured siderite edges", (.242, .179, .110), .77, "ore", 56),
        material("Basalt chitin", (.064, .052, .042), .61, "chitin", 72),
        material("Exposed ochre fascia", (.235, .093, .042), .56, "chitin", 91),
        material("Scraped digging keratin", (.088, .074, .053), .48, "chitin", 41),
        material("Orbital shadow", (.018, .012, .009), .62),
        material("Dull amber light-sensitive tissue", (.224, .078, .024), .36),
    ))
    path = output / "MineBorer.glb"
    assert "FINISHED" in bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB",
                                                  export_apply=True, export_extras=True, export_tangents=True)
    tangent_count = check_tangent_channels(path)
    nodes, model_bounds = prepare_preview(path)
    meshes = [obj for obj in nodes if obj.type == "MESH"]
    stats = statistics(meshes)
    assert 2.91 <= stats["bounds_m"][2] <= 3.12, stats
    assert abs(stats["floor_m"]) < .075, stats
    assert {obj.name for obj in nodes if obj.type == "EMPTY"} == set(PIVOTS)
    for flank in ("Left", "Right"):
        plate = bpy.data.objects[f"MineBorer_RearPlate{flank}"]
        assert plate["role"] == "rear_vulnerability" and len(plate.children) == 2
    assert tangent_count >= len(meshes) - 4
    rear_check = check_rear_motion()
    manifest = {"asset": "MineBorer.glb", "creature_id": "abyss_mine_borer",
                "authored_with": bpy.app.version_string, "result_sha256": sha256(path.read_bytes()).hexdigest(),
                "exported_pivots": list(PIVOTS), "reimport": stats,
                "normal_mapped_primitives_with_tangents": tangent_count, "embedded_images": len(bpy.data.images),
                "rear_motion_check": rear_check,
                "source": "Original EIDOLON meshes and procedural materials.", "status": "static mesh study"}
    (output / "verification.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("VERIFIED", manifest, flush=True)
    if args.samples:
        render(output / "front.png", nodes, model_bounds, False, args.samples)
        render(output / "front_detail.png", nodes, model_bounds, True, args.samples, detail_focus=(.24, -1.65, 1.63))
        body = bpy.data.objects[PIVOTS[0]]
        body.rotation_mode = "XYZ"
        body.rotation_euler.z = pi
        bpy.context.view_layer.update()
        rotated = bounds(meshes)
        render(output / "rear_closed.png", nodes, rotated, True, args.samples, detail_focus=(0, -1.25, 1.91),
               camera_direction=REAR_CAMERA)
        set_rear_open(True)
        render(output / "rear_open.png", nodes, rotated, True, args.samples, detail_focus=(0, -1.25, 1.91),
               camera_direction=REAR_CAMERA)


if __name__ == "__main__":
    main()
