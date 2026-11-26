"""Build the original Buried Forest arch prototype with Blender."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def material(name, color, roughness, grain):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    # Grain affects the Blender preview; the GLB carries the base PBR values.
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = grain
    noise.inputs["Detail"].default_value = 3
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.025
    tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def root_mesh(name, path, radii, surfaces, phase, sides=10):
    centers = [Vector(point) for point in path]
    vertices = []
    for row, center in enumerate(centers):
        prev = centers[max(0, row - 1)]
        following = centers[min(len(centers) - 1, row + 1)]
        tangent = (following - prev).normalized()
        right = tangent.cross(Vector((0, 1, 0))).normalized()
        front = tangent.cross(right).normalized()
        for side in range(sides):
            angle = math.tau * side / sides
            ridge = 1 + 0.16 * math.sin(3 * angle + row * 0.7 + phase)
            ring = right * math.cos(angle) + front * math.sin(angle) * 0.79
            vertices.append(center + ring * radii[row] * ridge)
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(centers) - 1):
        for side in range(sides):
            start = row * sides + side
            following = row * sides + (side + 1) % sides
            faces.append((start, following, following + sides, start + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for surface in surfaces:
        mesh.materials.append(surface)
    uv = mesh.uv_layers.new(name="Bark UV")
    for polygon in mesh.polygons[1:-1]:
        row, side = divmod(polygon.index - 1, sides)
        polygon.use_smooth = True
        polygon.material_index = int((side + round(phase)) % 4 == 0)
        left, right = side / sides, (side + 1) / sides
        bottom, top = row / (len(centers) - 1), (row + 1) / (len(centers) - 1)
        for loop_index, coordinate in zip(polygon.loop_indices, ((left, bottom), (right, bottom), (right, top), (left, top))):
            uv.data[loop_index].uv = coordinate
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def rock(name, location, dimensions, surface, rotation):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    for vertex in obj.data.vertices:
        wave = 1.0 + 0.18 * math.sin(vertex.co.x * 8.6 + vertex.co.y * 4.3 + vertex.co.z * 7.9)
        vertex.co *= wave
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = rotation
    obj.data.materials.append(surface)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, position, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = power, color, size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, 0, 1.8))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    bark = material("Buried bark", (0.091, 0.049, 0.032), 0.85, 7)
    ridge = material("Exposed bark ridge", (0.17, 0.096, 0.047), 0.80, 12)
    shale = material("Broken shale", (0.095, 0.116, 0.126), 0.83, 14)
    moss = material("Old moss", (0.080, 0.101, 0.044), 0.89, 19)

    pieces = [root_mesh("Main vault root", [
        (-1.14, 0.00, 0.22), (-1.17, 0.05, 0.79), (-1.12, 0.02, 1.43),
        (-1.13, -0.05, 2.13), (-1.02, 0.01, 2.77), (-0.71, 0.12, 3.31),
        (-0.24, 0.09, 3.61), (0.29, 0.17, 3.54), (0.70, 0.11, 3.20),
        (0.99, -0.01, 2.71), (1.13, 0.08, 2.10), (1.17, 0.01, 1.33),
        (1.14, -0.07, 0.69), (1.17, 0.01, 0.17),
    ], (.23, .23, .22, .21, .24, .26, .29, .26, .25, .22, .23, .22, .22, .24), (bark, ridge), 0.3, 14)]
    branches = [
        ("Left grasping root", [(-1.28, -0.56, 0.10), (-1.21, -0.39, 0.42), (-1.06, -0.24, 0.90),
                                (-1.16, -0.20, 1.31), (-1.33, -0.12, 1.78), (-1.27, -0.13, 2.16),
                                (-1.10, -0.10, 2.52)], (.11, .14, .145, .12, .09, .06, .019), 1.4),
        ("Right grasping root", [(1.40, 0.55, 0.11), (1.23, 0.41, 0.29), (1.04, 0.30, 0.71),
                                 (1.08, 0.15, 1.10), (1.30, 0.17, 1.58), (1.24, 0.07, 2.16),
                                 (0.93, 0.03, 2.65)], (.055, .13, .135, .14, .10, .06, .016), 3.4),
        ("Rear crown fork", [(-1.37, 0.45, 1.59), (-1.11, 0.45, 2.29), (-0.99, 0.40, 2.94),
                             (-0.62, 0.43, 3.53), (-0.17, 0.47, 3.79), (0.17, 0.38, 4.05)],
         (.05, .115, .14, .145, .097, .018), 2.8),
        ("Right crown fork", [(1.30, -0.30, 1.44), (1.25, -0.22, 2.20), (1.07, -0.19, 2.79),
                              (0.78, -0.16, 3.32), (0.49, -.22, 3.58), (0.28, -0.32, 3.93)],
         (.05, .08, .105, .12, .075, .012), 1.9),
        ("Left crown spur", [(-.72, .11, 3.30), (-.85, .08, 3.55), (-1.02, -.10, 3.72)],
         (.11, .071, .012), 4.1),
    ]
    for name, path, radii, phase in branches:
        pieces.append(root_mesh(name, path, radii, (bark, ridge), phase))
    stones = [
        ("Left footing", (-1.15, 0.11, .22), (.63, 1.01, .50), shale, (.06, -.12, .10)),
        ("Broken left upright", (-1.19, -.04, .69), (.37, .57, .82), shale, (-.10, -.20, .13)),
        ("Left moss fragment", (-1.30, -.37, .24), (.34, .43, .30), moss, (.18, .11, .22)),
        ("Right footing", (1.15, -.04, .23), (.61, .93, .54), shale, (.07, .17, -.12)),
        ("Broken right upright", (1.24, .09, .72), (.38, .58, .92), shale, (.08, .14, -.18)),
        ("Right moss fragment", (1.26, .33, .30), (.38, .44, .35), moss, (.19, .15, .10)),
    ]
    for name, location, dimensions, surface, rotation in stones:
        pieces.append(rock(name, location, dimensions, surface, rotation))

    # Evaluate extents once, so that the snapped floor origin is usable in level placement.
    bpy.context.view_layer.update()
    ground_z = min((obj.matrix_world @ vertex.co).z for obj in pieces for vertex in obj.data.vertices)
    for obj in pieces:
        obj.location.z -= ground_z
    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.export_scene.gltf(filepath=str(output / "buried_forest_root_arch.glb"),
                              export_format="GLB", use_selection=True)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.002))
    bpy.context.object.data.materials.append(material("Preview floor", (0.035, 0.043, 0.046), 0.91, 16))
    world = bpy.data.worlds.new("Low overcast fill")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.22, 0.29, 0.38, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.31
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (2.62, -9.2, 4.08)
    aim(camera, (0, 0, 2.02))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5.25
    scene.camera = camera
    light("Warm key", (1.1, -3.2, 4.9), (1.0, 0.78, 0.52), 940, 2.4)
    light("Cold rim", (-2.8, 1.3, 4.2), (0.48, 0.66, 1.0), 1300, 2.1)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "buried_forest_root_arch.png")
    scene["asset_status"] = "prototype_pending_collision_unreal_import_and_art_review"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "buried_forest_root_arch.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
