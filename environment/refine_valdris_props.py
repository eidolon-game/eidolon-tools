"""Rebuild the original Valdris recruit sword and funerary urn in Blender 4.3."""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector
import numpy as np


TOOLS = Path(__file__).resolve().parents[1]


def load_builder(relative):
    spec = importlib.util.spec_from_file_location(relative.stem, TOOLS / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sword_base = load_builder(Path("equipment/build_valdris_sword.py"))
urn_base = load_builder(Path("environment/build_funerary_urn.py"))


def texture(directory, label, pixels, color_space):
    height, width, _ = pixels.shape
    image = bpy.data.images.new(label, width, height, alpha=True)
    image.colorspace_settings.name = color_space
    image.pixels.foreach_set(np.clip(pixels, 0, 1).astype(np.float32).ravel())
    image.filepath_raw = str(directory / f"{label}.png")
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def surface(directory, label, seed, color, metallic, roughness, style):
    size = 256
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[:size, :size] / size
    tau = 2 * np.pi
    broad = sum(
        np.sin(tau * (ku * u + kv * v) + rng.uniform(0, tau)) / 5
        for ku, kv in ((2, 3), (7, -4), (12, 9), (17, -12), (24, 19))
    )
    fine = rng.normal(0, 0.18, (size, size))
    if style == "metal":
        grain = np.sin(tau * (86 * u - 4 * v + 0.7 * broad)) * (0.36 + 0.30 * broad)
        pit = np.maximum(0, 0.8 * broad + fine - 0.52)
        contact = np.clip(np.sin(tau * (2 * u + v)) + broad - 0.43, 0, 1)
        relief = 0.11 * grain + 0.2 * fine - 0.8 * pit
        tint = 1 + 0.21 * broad + 0.16 * grain - 0.38 * pit + 0.18 * contact
        gloss = roughness + 0.08 * broad + 0.17 * pit - 0.1 * contact + 0.035 * fine
    elif style == "leather":
        grain = np.sin(tau * (54 * u + 17 * v + 1.8 * broad))
        folds = np.sin(tau * (3 * u - 8 * v + 0.35 * broad))
        relief = 0.12 * grain + 0.16 * folds + 0.27 * fine
        tint = 1 + 0.26 * folds + 0.35 * broad + 0.22 * fine
        gloss = roughness + 0.1 * broad + 0.07 * folds
    else:
        strata = np.sin(tau * (3 * u + 12 * v + 0.7 * broad)) * 0.26
        pits = np.maximum(0, 0.8 * broad + 1.9 * fine - 0.32)
        relief = 0.23 * strata + 0.37 * broad - 1.1 * pits
        # Abrasion along the circumferential edges catches more light than intact stone.
        contact = np.exp(-((v - 0.45) / 0.055) ** 2) * (0.4 + 0.6 * np.maximum(0, broad))
        tint = 1 + 0.52 * broad + 0.35 * strata - 0.25 * pits + 0.15 * contact
        gloss = roughness + 0.12 * pits + 0.06 * broad - 0.09 * contact

    base = np.ones((size, size, 4))
    base[:, :, :3] = np.asarray(color) * tint[:, :, None]
    y = (np.roll(relief, -1, axis=0) - np.roll(relief, 1, axis=0)) * 0.32
    x = (np.roll(relief, -1, axis=1) - np.roll(relief, 1, axis=1)) * 0.32
    scale = np.sqrt(1 + x * x + y * y)
    normal = np.ones_like(base)
    normal[:, :, 0] = 0.5 - 0.5 * x / scale
    normal[:, :, 1] = 0.5 - 0.5 * y / scale
    normal[:, :, 2] = 0.5 + 0.5 / scale
    orm = np.ones_like(base)
    orm[:, :, 1] = np.clip(gloss, 0.12, 0.96)
    orm[:, :, 2] = metallic

    mat = bpy.data.materials.new(label)
    mat.use_nodes = True
    tree = mat.node_tree
    shader = tree.nodes["Principled BSDF"]
    base_node = tree.nodes.new("ShaderNodeTexImage")
    base_node.image = texture(directory, f"{label}_basecolor", base, "sRGB")
    tree.links.new(base_node.outputs["Color"], shader.inputs["Base Color"])
    normal_node = tree.nodes.new("ShaderNodeTexImage")
    normal_node.image = texture(directory, f"{label}_normal", normal, "Non-Color")
    vector = tree.nodes.new("ShaderNodeNormalMap")
    tree.links.new(normal_node.outputs["Color"], vector.inputs["Color"])
    tree.links.new(vector.outputs["Normal"], shader.inputs["Normal"])
    mr_node = tree.nodes.new("ShaderNodeTexImage")
    mr_node.image = texture(directory, f"{label}_metalrough", orm, "Non-Color")
    split = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(mr_node.outputs["Color"], split.inputs["Color"])
    tree.links.new(split.outputs["Green"], shader.inputs["Roughness"])
    tree.links.new(split.outputs["Blue"], shader.inputs["Metallic"])
    return mat


def recalculate_normals(mesh):
    editable = bmesh.new()
    editable.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(editable, faces=editable.faces)
    editable.to_mesh(mesh)
    editable.free()


def blade(steel, edge):
    profile = np.array(((0.105, 0.025, 0.0052), (0.13, 0.032, 0.0062),
                        (0.64, 0.024, 0.0055), (0.80, 0.015, 0.0032)))
    wear = ((0.291, 0.008, 0.0016, -1), (0.486, 0.013, 0.0032, 1),
            (0.517, 0.007, 0.0013, 1), (0.702, 0.007, 0.0018, -1))
    heights = sorted({*profile[:, 0], *(round(at + span * shift, 5)
                                         for at, span, _, _ in wear for shift in (-1, -0.38, 0, 0.50, 1))})
    section = ((0, 1), (-0.60, 0.76), (-0.94, 0.16), (-1.0, 0.04),
               (-1.0, -0.04), (-0.94, -0.16), (-0.60, -0.76), (0, -1),
               (0.60, -0.76), (0.94, -0.16), (1.0, -0.04), (1.0, 0.04),
               (0.94, 0.16), (0.60, 0.76))
    count = len(section)
    vertices, faces = [], [tuple(reversed(range(count)))]
    for z in heights:
        width = np.interp(z, profile[:, 0], profile[:, 1])
        thickness = np.interp(z, profile[:, 0], profile[:, 2])
        for side, height in section:
            reduction = sum(
                depth * max(0, 1 - abs(z - at) / span) ** 0.72
                for at, span, depth, direction in wear if side * direction > 0.70
            )
            hammer = 0.00017 * math.sin(141 * z + side * 5) * (1 - abs(side))
            vertices.append((side * (width - reduction), height * (thickness + hammer), z))
    for row in range(len(heights) - 1):
        for i in range(count):
            nxt = (i + 1) % count
            faces.append((row * count + i, row * count + nxt, (row + 1) * count + nxt, (row + 1) * count + i))
    tip = len(vertices)
    vertices.append((0, 0, 0.91))
    last = (len(heights) - 1) * count
    faces.extend((last + i, last + (i + 1) % count, tip) for i in range(count))

    mesh = bpy.data.meshes.new("Forged blade with modeled edge chips")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Blade", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(steel)
    mesh.materials.append(edge)
    uv = mesh.uv_layers.new(name="Blade UV")
    for polygon in mesh.polygons:
        n = (polygon.index - 1) % count
        polygon.material_index = int(polygon.index > 0 and n in (1, 2, 3, 4, 5, 8, 9, 10, 11, 12))
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
            x, y, z = vertex.co
            if polygon.index == 0:
                xy = (0.5 + x / 0.065, 0.5 + y / 0.016)
            elif vertex.index == tip:
                xy = ((n + 0.5) / count, 0.999)
            else:
                side_index = vertex.index % count
                if side_index == 0 and n == count - 1:
                    side_index = count
                xy = (side_index / count, (z - 0.104) / 0.807)
            uv.data[loop_index].uv = xy
    recalculate_normals(mesh)
    return obj


def relief_rivet(name, center, radius, thickness, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=center)
    piece = bpy.context.object
    piece.name = name
    piece.scale.y = thickness / radius
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    piece.data.materials.append(material)
    for face in piece.data.polygons:
        face.use_smooth = True
    return piece


def build_sword(directory):
    steel = surface(directory, "sword_forged_steel", 12, (0.53, 0.56, 0.59), 0.92, 0.37, "metal")
    edge = surface(directory, "sword_honed_edge", 67, (0.69, 0.72, 0.73), 0.94, 0.25, "metal")
    bronze = surface(directory, "sword_dark_bronze", 91, (0.44, 0.28, 0.14), 0.74, 0.47, "metal")
    leather = surface(directory, "sword_grip_leather", 43, (0.25, 0.12, 0.07), 0.0, 0.67, "leather")
    pieces = [blade(steel, edge)]
    round_bar = sword_base.rounded_bar
    pieces.append(round_bar("Centered crossguard", (0, 0, 0.104), (0.178, 0.035, 0.024), bronze, 0.007))
    for direction in (-1, 1):
        quillon = round_bar("Swept quillon", (direction * 0.095, 0, 0.111), (0.051, 0.031, 0.023), bronze, 0.008)
        quillon.rotation_euler.y = math.radians(-19 * direction)
        pieces.append(quillon)
    pieces.append(round_bar("Grip core", (0, 0, 0.015), (0.039, 0.035, 0.154), leather, 0.014))
    for index in range(9):
        wrap = sword_base.ring(f"Raised binding {index + 1}", (0, 0, -0.053 + index * 0.015), 0.0175, 0.0028, leather)
        wrap.rotation_euler.y = math.radians(9)
        pieces.append(wrap)
    pieces.extend(sword_base.ring(label, (0, 0, z), radius, minor, bronze) for label, z, radius, minor in (
        ("Upper ferrule", 0.087, 0.019, 0.004), ("Lower ferrule", -0.063, 0.018, 0.0035),
    ))
    pieces.append(round_bar("Wheel pommel", (0, 0, -0.088), (0.053, 0.025, 0.048), bronze, 0.011))
    for direction in (-1, 1):
        pieces.append(relief_rivet("Peened tang", (0, 0.013 * direction, -0.088), 0.0095, 0.0035, steel))
        for x in (-0.035, 0.035):
            pieces.append(relief_rivet("Guard pin", (x, 0.0171 * direction, 0.104), 0.0047, 0.0022, steel))
    return pieces


def chipped(piece, points, erosion):
    for vertex in piece.data.vertices:
        x, y, z = vertex.co
        radius = math.hypot(x, y)
        if radius == 0:
            continue
        theta = math.atan2(y, x)
        cut = sum(depth * max(0.0, 1 - abs(math.remainder(theta - angle, math.tau)) / width)
                  * max(0.0, 1 - abs(z - level) / height) for angle, level, width, height, depth in points)
        wobble = erosion * (0.59 * math.sin(19 * theta + 31 * z) + 0.41 * math.sin(41 * theta - 7 * z))
        radius_factor = (radius + wobble - cut) / radius
        vertex.co.x *= radius_factor
        vertex.co.y *= radius_factor
    recalculate_normals(piece.data)
    piece.data.update()


def build_urn(directory):
    stone = surface(directory, "urn_cut_basalt", 91, (0.23, 0.24, 0.25), 0.0, 0.82, "stone")
    bronze = surface(directory, "urn_oxidized_bronze", 56, (0.41, 0.25, 0.15), 0.71, 0.54, "metal")
    patina = surface(directory, "urn_weathered_seal", 37, (0.23, 0.40, 0.33), 0.61, 0.59, "metal")
    revolve = urn_base.revolve
    body = revolve("Basalt urn body", [
        (0.145, 0.0), (0.153, 0.003), (0.161, 0.010), (0.164, 0.019),
        (0.164, 0.037), (0.160, 0.045), (0.149, 0.059), (0.145, 0.084),
        (0.176, 0.130), (0.216, 0.181), (0.248, 0.252), (0.266, 0.336),
        (0.267, 0.452), (0.250, 0.503), (0.211, 0.551), (0.152, 0.582),
        (0.142, 0.606), (0.142, 0.639), (0.154, 0.646), (0.159, 0.653),
        (0.159, 0.660), (0.153, 0.665), (0.132, 0.665), (0.127, 0.659),
        (0.127, 0.609), (0.149, 0.564), (0.194, 0.530), (0.232, 0.483),
        (0.247, 0.432), (0.244, 0.342), (0.221, 0.259), (0.182, 0.190),
        (0.137, 0.139), (0.117, 0.095),
    ], stone, segments=112)
    lid = revolve("Removable basalt lid", [
        (0.155, 0.667), (0.161, 0.672), (0.162, 0.681), (0.156, 0.698),
        (0.123, 0.715), (0.082, 0.728), (0.039, 0.731), (0.034, 0.736),
        (0.033, 0.752), (0.043, 0.763), (0.038, 0.777), (0.030, 0.786), (0.021, 0.790),
    ], stone, segments=96)
    chipped(body, ((-1.38, 0.662, 0.24, 0.045, 0.019), (-0.82, 0.029, 0.20, 0.035, 0.011),
                   (0.62, 0.657, 0.19, 0.034, 0.013), (-1.86, 0.420, 0.33, 0.065, 0.007)), 0.0016)
    chipped(lid, ((-1.66, 0.679, 0.27, 0.032, 0.015), (-0.79, 0.679, 0.16, 0.025, 0.011)), 0.0011)
    for vertex in lid.data.vertices:
        vertex.co.z -= 0.667
    lid.location.z = 0.667
    lower = revolve("Lower bronze band", [
        (0.258, 0.325), (0.266, 0.327), (0.271, 0.332), (0.273, 0.341),
        (0.270, 0.348), (0.265, 0.351), (0.258, 0.349),
    ], bronze, closed=True, segments=96)
    upper = revolve("Upper bronze band", [
        (0.260, 0.465), (0.268, 0.466), (0.271, 0.470), (0.268, 0.482),
        (0.262, 0.486), (0.256, 0.488), (0.252, 0.486), (0.252, 0.465),
    ], bronze, closed=True, segments=96)
    chipped(lower, ((-1.42, 0.333, 0.16, 0.013, 0.004),), 0.00065)
    chipped(upper, ((-0.97, 0.479, 0.18, 0.02, 0.004),), 0.00054)
    seal = urn_base.seal_mesh(patina)
    bpy.context.view_layer.objects.active = seal
    seal.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")
    seal.select_set(False)
    bevel = seal.modifiers.new("Worn cast relief edges", "BEVEL")
    bevel.segments = 2
    bevel.width = 0.0013
    seal.modifiers.new("Weighted relief faces", "WEIGHTED_NORMAL")
    return [body, lid, lower, upper, seal]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    return scene


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio(scene, target, camera_location, scale, resolution):
    world = bpy.data.worlds.new("Neutral studio")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (0.32, 0.35, 0.40, 1.0)
    background.inputs[1].default_value = 0.25
    camera = bpy.data.objects.new("Review camera", bpy.data.cameras.new("Review camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = camera_location
    aim(camera, target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    scene.camera = camera
    for name, position, watts, size, color in (
        ("Key", (0.68, -0.92, 1.32), 88, 0.73, (1.0, 0.84, 0.70)),
        ("Soft fill", (-0.67, -0.73, 0.47), 56, 0.82, (0.69, 0.80, 1.0)),
        ("Rake", (-0.48, 0.31, 1.04), 100, 0.49, (0.88, 0.93, 1.0)),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size, light.color = watts, size, color
        source = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(source)
        source.location = position
        aim(source, target)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return camera


def bounds(objects):
    corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return [
        round(max(p[axis] for p in corners) - min(p[axis] for p in corners), 5)
        for axis in range(3)
    ]


def render_preview(scene, destination):
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)


def export_asset(directory, label, builder, is_urn, render):
    scene = reset()
    textures = directory / "textures"
    textures.mkdir(exist_ok=True)
    pieces = builder(textures)
    bpy.context.view_layer.update()
    original_bounds = bounds(pieces)
    bpy.ops.object.select_all(action="DESELECT")
    for piece in pieces:
        triangulate = piece.modifiers.new("Triangulated tangent export", "TRIANGULATE")
        triangulate.keep_custom_normals = True
        piece.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    glb = directory / f"{label}.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True,
                              export_apply=True, export_tangents=True)
    if not render:
        return glb, original_bounds
    target = (0, 0, 0.40)
    location = (1.34, -2.68, 1.27) if is_urn else (0.36, -2.7, 0.68)
    camera = studio(scene, target, location, 1.06 if is_urn else 1.20, (660, 700) if is_urn else (540, 740))
    scene["asset_status"] = "prototype_pending_engine_import_and_art_review"
    bpy.context.preferences.filepaths.save_version = 0
    blend = directory / f"{label}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    render_preview(scene, directory / f"{label}.png")
    if is_urn:
        lid = next(piece for piece in pieces if piece.name == "Removable basalt lid")
        lid.location = (0.0, 0.0, 0.91)
        lid.rotation_euler.y = math.radians(21)
        camera.location = (1.20, -2.36, 1.62)
        aim(camera, (0, 0, 0.56))
        camera.data.ortho_scale = 1.17
        render_preview(scene, directory / f"{label}_lid_review.png")
    else:
        camera.location = (0.31, -1.58, 0.37)
        aim(camera, (0, 0, 0.21))
        camera.data.ortho_scale = 0.73
        render_preview(scene, directory / f"{label}_edge_review.png")
    return glb, original_bounds


def reimport(glb, expected_bounds, lid_required):
    raw = glb.read_bytes()
    assert raw[:4] == b"glTF"
    metadata_size, metadata_type = struct.unpack_from("<II", raw, 12)
    assert metadata_type == 0x4E4F534A
    gltf = json.loads(raw[20:20 + metadata_size])
    mapped = []
    for material in gltf["materials"]:
        assert "normalTexture" in material, material["name"]
        pbr = material["pbrMetallicRoughness"]
        assert "baseColorTexture" in pbr and "metallicRoughnessTexture" in pbr, material["name"]
        mapped.append(material["name"])
    assert all("TEXCOORD_0" in primitive["attributes"] and "TANGENT" in primitive["attributes"]
               for mesh in gltf["meshes"] for primitive in mesh["primitives"])
    reset()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.context.view_layer.update()
    imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    assert imported and all(len(obj.data.uv_layers) for obj in imported)
    imported_bounds = bounds(imported)
    assert all(abs(first - second) < 0.0005 for first, second in zip(imported_bounds, expected_bounds))
    lid = bpy.data.objects.get("Removable basalt lid")
    if lid_required:
        assert lid and bpy.data.objects.get("Basalt urn body")
        assert abs(lid.location.z - 0.667) < 0.00001
    return {
        "asset": glb.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "mesh_objects": len(imported),
        "triangles": sum(len(obj.data.polygons) for obj in imported),
        "dimensions_m": imported_bounds,
        "pbr_materials": mapped,
        "separate_lid_pivot_m": 0.667 if lid_required else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--skip-renders", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    sword, sword_bounds = export_asset(directory, "valdris_recruit_sword", build_sword, False, not args.skip_renders)
    urn, urn_bounds = export_asset(directory, "valdris_funerary_urn", build_urn, True, not args.skip_renders)
    manifest = {
        "blender": bpy.app.version_string,
        "source": "Original Valdris prototypes refined with modeled and procedural surface wear.",
        "assets": [reimport(sword, sword_bounds, False), reimport(urn, urn_bounds, True)],
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
