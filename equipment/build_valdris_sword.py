"""Build an original Valdris recruit sword prototype with Blender 4.3."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def material(name, color, metallic, roughness):
    surface = bpy.data.materials.new(name)
    surface.use_nodes = True
    shader = surface.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return surface


def blade(steel, edge):
    # Cross sections preserve a center ridge and a distinct bevel on each edge.
    rows = [(0.105, 0.025, 0.0052), (0.13, 0.032, 0.0062),
            (0.64, 0.024, 0.0055), (0.80, 0.015, 0.0032)]
    vertices = []
    for z, width, thickness in rows:
        vertices.extend([
            (0, thickness, z), (-0.68 * width, thickness * 0.7, z),
            (-width, 0, z), (-0.68 * width, -thickness * 0.7, z),
            (0, -thickness, z), (0.68 * width, -thickness * 0.7, z),
            (width, 0, z), (0.68 * width, thickness * 0.7, z),
        ])
    faces = [tuple(reversed(range(8)))]
    for row in range(len(rows) - 1):
        start = row * 8
        for side in range(8):
            following = (side + 1) % 8
            faces.append((start + side, start + following, start + 8 + following, start + 8 + side))
    tip = len(vertices)
    vertices.append((0, 0, 0.91))
    start = (len(rows) - 1) * 8
    faces.extend((start + side, start + (side + 1) % 8, tip) for side in range(8))
    mesh = bpy.data.meshes.new("Ridge and bevel")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Blade", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(steel)
    obj.data.materials.append(edge)
    for polygon in mesh.polygons[1:]:
        polygon.material_index = int((polygon.index - 1) % 8 in (1, 2, 5, 6))
    return obj


def rounded_bar(name, center, size, surface, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(surface)
    modifier = obj.modifiers.new("Rounded forged edges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return obj


def ring(name, center, major, minor, surface):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=32, minor_segments=8, location=center,
        major_radius=major, minor_radius=minor,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(surface)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def point_at(obj, position):
    obj.rotation_euler = (Vector(position) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    point_at(obj, (0, 0, 0.38))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    world = bpy.data.worlds.new("Low ambient studio light")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs[0].default_value = (0.17, 0.20, 0.25, 1)
    world.node_tree.nodes.get("Background").inputs[1].default_value = 0.25

    steel = material("Forged steel", (0.28, 0.31, 0.33), 0.92, 0.29)
    edge = material("Honed steel", (0.52, 0.55, 0.57), 0.94, 0.22)
    bronze = material("Dark bronze", (0.24, 0.13, 0.047), 0.76, 0.37)
    leather = material("Brown grip leather", (0.065, 0.024, 0.014), 0.0, 0.68)
    wrap = material("Raised leather binding", (0.11, 0.049, 0.026), 0.0, 0.61)

    pieces = [blade(steel, edge)]
    pieces.append(rounded_bar("Centered crossguard", (0, 0, 0.104), (0.178, 0.035, 0.024), bronze, 0.008))
    for direction in (-1, 1):
        quillon = rounded_bar("Swept quillon", (direction * 0.095, 0, 0.111),
                             (0.051, 0.031, 0.023), bronze, 0.009)
        quillon.rotation_euler.y = direction * math.radians(-19)
        pieces.append(quillon)
    pieces.append(rounded_bar("Grip core", (0, 0, 0.015), (0.039, 0.035, 0.154), leather, 0.014))
    for index in range(9):
        binding = ring(f"Binding {index + 1}", (0, 0, -0.053 + index * 0.015), 0.0175, 0.0028, wrap)
        binding.rotation_euler.y = math.radians(9)
        pieces.append(binding)
    pieces.append(ring("Upper ferrule", (0, 0, 0.087), 0.019, 0.004, bronze))
    pieces.append(ring("Lower ferrule", (0, 0, -0.063), 0.018, 0.0035, bronze))
    pieces.append(rounded_bar("Wheel pommel", (0, 0, -0.088), (0.053, 0.025, 0.048), bronze, 0.011))

    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    glb = output / "valdris_recruit_sword.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True, export_apply=True)

    slate = material("Backdrop slate", (0.017, 0.022, 0.032), 0.13, 0.82)
    rounded_bar("Backdrop", (0, 0.15, 0.4), (2, 0.02, 2), slate, 0.002)
    camera = bpy.data.objects.new("Studio orthographic", bpy.data.cameras.new("Studio orthographic"))
    bpy.context.collection.objects.link(camera)
    camera.location = (0.5, -2.4, 0.67)
    point_at(camera, (0, 0, 0.402))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.20
    scene.camera = camera
    light("Key", (-0.42, -0.74, 0.85), 110, 0.66, (0.88, 0.93, 1.0))
    light("Fill", (0.48, -0.40, 0.16), 78, 0.57, (1.0, 0.80, 0.60))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 440
    scene.render.resolution_y = 680
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.filepath = str(output / "valdris_recruit_sword.png")
    scene["asset_status"] = "prototype_pending_unreal_import_and_art_review"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "valdris_recruit_sword.blend"))
    bpy.ops.render.render(write_still=True)
    print(json.dumps({"mesh_objects": len(pieces), "length_m": 1.022, "export": str(glb)}))


if __name__ == "__main__":
    main()
