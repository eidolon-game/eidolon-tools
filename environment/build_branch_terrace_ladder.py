"""Generate the Branch Terrace ladder and counterweight prototype with Blender."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def material(name, color, roughness, metallic=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = (*color, 1)
    shader = result.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return result


def beveled_box(name, dimensions, surface, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(surface)
    corners = obj.modifiers.new("Rounded edges", "BEVEL")
    corners.width = bevel
    corners.segments = 2
    normals = obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    normals.keep_sharp = True
    return obj


def bar(name, start, end, dimensions, surface, bevel=0.015):
    start, end = Vector(start), Vector(end)
    obj = beveled_box(name, (*dimensions, (end - start).length), surface, bevel)
    obj.location = (start + end) / 2
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def pin(name, center, radius, width, surface):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=width, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.y = math.pi / 2
    obj.data.materials.append(surface)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def cord(name, path, widths, surface, sides=8):
    points = [Vector(point) for point in path]
    vertices = []
    for row, (point, radius) in enumerate(zip(points, widths)):
        tangent = (points[min(row + 1, len(points) - 1)] - points[max(row - 1, 0)]).normalized()
        axis = tangent.cross(Vector((1, 0, 0))).normalized()
        across = tangent.cross(axis)
        for side in range(sides):
            theta = math.tau * side / sides
            vertices.append(point + radius * (axis * math.cos(theta) + across * math.sin(theta)))
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(path) - 1):
        for side in range(sides):
            current = row * sides + side
            following = row * sides + (side + 1) % sides
            faces.append((current, following, following + sides, current + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(surface)
    for polygon in data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def parent(name, parts):
    group = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(group)
    for part in parts:
        part.parent = group
    return group


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, center, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = power, color, size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    aim(obj, (0, -0.3, -1.38))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    wood = material("Dark heartwood", (0.103, 0.055, 0.033), 0.87)
    worn = material("Worn rung face", (0.177, 0.096, 0.048), 0.81)
    iron = material("Blackened iron", (0.083, 0.098, 0.11), 0.58, 0.68)
    studs = material("Oxidized fasteners", (0.139, 0.086, 0.043), 0.67, 0.59)
    slate = material("Counterweight slate", (0.087, 0.10, 0.11), 0.91)
    fiber = material("Twisted hemp", (0.208, 0.153, 0.095), 0.87)
    twig = material("Dry vine bark", (0.078, 0.046, 0.022), 0.93)
    leaf = material("Deep green vine", (0.052, 0.121, 0.061), 0.85)

    # X is the hinge axis. Its center is the moving ladder origin.
    def rung_y(z):
        return 0.23 * z

    rails = [
        bar(f"Rail {side}", (sign * 0.56, rung_y(-3.37), -3.37), (sign * 0.56, 0.025, 0.075),
            (0.13, 0.16), wood, 0.020)
        for side, sign in (("left", -1), ("right", 1))
    ]
    ladder = rails[:]
    for index in range(11):
        z = -0.25 - 0.29 * index
        y = rung_y(z) - 0.015
        ladder.append(bar(f"Rung {index + 1:02}", (-0.59, y, z), (0.59, y, z),
                          (0.080, 0.107), worn, 0.017))
    for side, sign in (("left", -1), ("right", 1)):
        x = sign * 0.56
        for index, z in enumerate((-0.09, -0.40, -1.57, -2.71, -3.16)):
            ladder.append(bar(f"Rung collar {side} {index}", (x, rung_y(z), z - 0.040),
                              (x, rung_y(z), z + 0.040), (0.147, 0.177), iron, 0.011))
    hinge = pin("Hinge axle", (0, 0, 0), 0.057, 1.36, iron)
    fixed = [hinge]
    for side, sign in (("left", -1), ("right", 1)):
        x = sign * 0.62
        fixed.append(pin(f"Axle cap {side}", (x * 1.12, 0, 0), 0.072, 0.035, studs))
        fixed.append(bar(f"Anchor plate {side}", (x, 0.047, 0.035), (x, 0.36, 0.035),
                         (0.143, 0.090), iron, 0.016))
        for y in (0.14, 0.31):
            fixed.append(pin(f"Anchor rivet {side} {y}", (x, y, 0.072), 0.022, 0.062, studs))

    fixed.extend([
        bar("Hoist upright", (.85, .24, -.13), (.85, .24, .59), (.14, .17), wood, 0.02),
        bar("Hoist projecting branch", (.84, .24, .52), (1.06, -.33, .52), (.16, .14), wood, 0.02),
        bar("Hoist diagonal brace", (.86, .21, .03), (1.02, -.25, .47), (.08, .08), iron, 0.012),
        pin("Weight pulley", (1.06, -.29, .44), .13, .066, wood),
        pin("Pulley hub", (1.06, -.29, .44), .055, .12, iron),
    ])
    weight = bar("Cast stone counterweight", (1.06, -.41, -1.55), (1.06, -.41, -1.06),
                 (.27, .24), slate, .055)
    counterweight = [weight]
    for z in (-1.17, -1.43):
        counterweight.append(bar(f"Weight band {z}", (1.06, -.41, z - .035), (1.06, -.41, z + .035),
                                 (.279, .247), iron, .014))
    fixed.append(cord("Hoist rope", [
        (1.06, -.41, -1.06), (1.06, -.415, -.37), (1.06, -.416, .43),
        (1.06, -.38, .53), (1.06, -.28, .568), (1.06, -.18, .53),
        (1.06, -.161, .43), (.94, -.167, .13), (.76, -.133, -.18), (.65, -.15, -.42),
    ], [0.018] * 10, fiber))

    vine_path = []
    for index in range(121):
        t = index / 120
        z = -0.36 - 2.86 * t
        # Keep the entire winding plant outside the central climb lane.
        vine_path.append((-.588 - .097 * math.cos(math.tau * t * 4.8),
                          rung_y(z) + .102 * math.sin(math.tau * t * 4.8), z))
    ladder.append(cord("Winding vine", vine_path, [.015 - .008 * (index / 120) for index in range(121)], twig))
    vertices, faces = [], []
    for index in range(11, 117, 9):
        x, y, z = vine_path[index]
        if x > -.55:
            continue
        offset = len(vertices)
        spread = .09 + .017 * math.sin(index)
        vertices.extend(((x, y, z), (x - spread * .54, y - .026, z - .03),
                         (x - spread, y - .068, z - .09), (x - spread * .23, y - .028, z - .08),
                         (x - spread * .48, y - .041, z - .055)))
        faces.extend(tuple(offset + corner for corner in face)
                     for face in ((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)))
    mesh = bpy.data.meshes.new("Folded vine leaves")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    leaves = bpy.data.objects.new("Folded vine leaves", mesh)
    bpy.context.collection.objects.link(leaves)
    leaves.data.materials.append(leaf)
    ladder.append(leaves)

    groups = (parent("Ladder_Hinge_Pivot", ladder), parent("Fixed_Terrace_Hoist", fixed),
              parent("Counterweight_Meshes", counterweight))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [*groups, *ladder, *fixed, *counterweight]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = groups[0]
    bpy.ops.export_scene.gltf(filepath=str(output / "branch_terrace_ladder.glb"), export_format="GLB",
                              use_selection=True, export_apply=True)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -3.47))
    bpy.context.object.data.materials.append(material("Preview floor", (.025, .033, .038), .91))
    world = bpy.data.worlds.new("Overcast fill")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.17, .25, .33, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .32
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (4.3, -10.3, .48)
    aim(camera, (.24, -.29, -1.39))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5.10
    scene.camera = camera
    light("Overcast key", (-1.9, -3.4, 1.5), (.74, .84, 1.0), 520, 2.2)
    light("Warm rim", (2.0, 2.1, .12), (1.0, .71, .46), 720, 1.8)
    light("Low blue fill", (2.9, -3.2, -2.45), (.56, .71, 1.0), 165, 2.0)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 690
    scene.render.resolution_y = 820
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "branch_terrace_ladder.png")
    scene["asset_status"] = "prototype_pending_unreal_import_and_traversal"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "branch_terrace_ladder.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
