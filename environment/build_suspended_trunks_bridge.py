"""Generate EIDOLON's Suspended Trunks bridge with Blender."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def surface(name, rgb, roughness, metallic=0, grain=None):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    shader = nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if grain is not None:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = grain
        noise.inputs["Detail"].default_value = 4
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = .026
        bump.inputs["Strength"].default_value = .40
        material.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        material.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def box(name, center, dimensions, material, size=.014):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    modifier = obj.modifiers.new("Beveled edges", "BEVEL")
    modifier.width = size
    modifier.segments = 2
    obj.modifiers.new("Face-weighted normals", "WEIGHTED_NORMAL")
    return obj


def beam(name, start, end, section, material, size=.010):
    start, end = Vector(start), Vector(end)
    obj = box(name, (start + end) / 2, (*section, (end - start).length), material, size)
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def cylinder(name, center, radius, depth, material, sides=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=depth, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def mesh(name, vertices, faces, surfaces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for material in surfaces:
        data.materials.append(material)
    return obj


def tube(name, points, radii, surfaces, sides=10, irregularity=0):
    centers = [Vector(point) for point in points]
    vertices = []
    for row, (center, radius) in enumerate(zip(centers, radii)):
        tangent = (centers[min(len(centers) - 1, row + 1)] - centers[max(0, row - 1)]).normalized()
        axis = tangent.cross(Vector((0, 0, 1))).normalized()
        across = tangent.cross(axis)
        for spoke in range(sides):
            angle = math.tau * spoke / sides
            variation = 1 + irregularity * math.sin(3 * angle + .66 * row)
            vertices.append(center + radius * variation * (axis * math.cos(angle) + across * math.sin(angle)))
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(centers) - 1):
        for spoke in range(sides):
            start = row * sides + spoke
            following = row * sides + (spoke + 1) % sides
            faces.append((start, following, following + sides, start + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    obj = mesh(name, vertices, faces, surfaces)
    uv = obj.data.uv_layers.new(name="Bark or fiber UV")
    for polygon in obj.data.polygons[1:-1]:
        row, spoke = divmod(polygon.index - 1, sides)
        polygon.material_index = int(len(surfaces) > 1 and spoke % 5 == 2)
        polygon.use_smooth = True
        lo, hi = row / (len(centers) - 1), (row + 1) / (len(centers) - 1)
        left, right = spoke / sides, (spoke + 1) / sides
        for loop_index, point in zip(polygon.loop_indices, ((left, lo), (right, lo), (right, hi), (left, hi))):
            uv.data[loop_index].uv = point
    if len(surfaces) > 1:
        obj.data.polygons[0].material_index = 1
        obj.data.polygons[-1].material_index = 1
    return obj


def island(stone, seams):
    profile = ((.63, -1.17), (.71, -.96), (.88, -.57), (1.01, -.39), (.98, -.19), (.92, -.095))
    count = 18
    rng = random.Random(471)
    outline = [rng.uniform(.9, 1.07) for _ in range(count)]
    vertices = []
    for row, (radius, z) in enumerate(profile):
        for index, factor in enumerate(outline):
            angle = math.tau * index / count
            variation = factor * (1 + .05 * math.sin(5 * angle + .9 * row))
            offset = 0 if row == len(profile) - 1 else .028 * math.sin(4 * angle + row)
            vertices.append((radius * variation * math.cos(angle), radius * variation * math.sin(angle), z + offset))
    faces = [tuple(reversed(range(count)))]
    for row in range(len(profile) - 1):
        for index in range(count):
            current = row * count + index
            following = row * count + (index + 1) % count
            faces.append((current, following, following + count, current + count))
    faces.append(tuple(range(len(vertices) - count, len(vertices))))
    obj = mesh("Central layered islet", vertices, faces, (stone, seams))
    for polygon in obj.data.polygons[1:-1]:
        row, index = divmod(polygon.index - 1, count)
        polygon.material_index = int(row == 3 or index % 9 == 2)
    return obj


def group(name, parts):
    parent = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(parent)
    bpy.context.view_layer.update()
    for obj in parts:
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
    return parent


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, position, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = power, size, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, 0, .05))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    bark = surface("Water-darkened oak", (.080, .041, .020), .89, grain=9)
    cut = surface("Exposed wood grain", (.155, .083, .039), .86, grain=14)
    plank = surface("Worn terrace decking", (.126, .071, .032), .88, grain=17)
    damp = surface("Damp plank variation", (.084, .050, .023), .84, grain=13)
    iron = surface("Black iron", (.051, .071, .083), .62, .74)
    bronze = surface("Worn bronze fastener", (.19, .100, .042), .56, .68)
    rope = surface("Worn hemp handline", (.144, .102, .052), .93)
    shale = surface("Wet islet shale", (.081, .107, .109), .71, grain=23)
    strata = surface("Dark shale seams", (.043, .061, .068), .83, grain=25)
    ochre = surface("Ochre navigation mark", (.24, .159, .047), .84)

    fixed = [island(shale, strata),
             cylinder("Recessed pivot capstone", (0, 0, -.11), .59, .14, shale),
             cylinder("Fixed bottom bearing", (0, 0, .005), .292, .072, iron),
             cylinder("Fixed polished ring", (0, 0, .055), .210, .026, bronze)]
    for index in range(4):
        theta = math.tau * index / 4
        heading = Vector((math.cos(theta), math.sin(theta), 0))
        lateral = Vector((-heading.y, heading.x, 0))
        tip = heading * .84 + Vector((0, 0, -.086))
        for sign in (-1, 1):
            heel = tip - heading * .11 + lateral * sign * .043
            fixed.append(beam(f"Islet direction mark {index} {sign}", heel, tip,
                              (.019, .010), ochre, .003))

    moving = [
        cylinder("Rotating bronze pivot shoe", (0, 0, .094), .199, .041, bronze),
        box("Under-deck pivot yoke", (0, 0, .180), (.39, 1.41, .134), iron, .024),
    ]
    for sign in (-1, 1):
        name = "north" if sign > 0 else "south"
        center_y = sign * .59
        axis_points = [(-2.69, center_y, .280), (-2.10, center_y + sign * .021, .280),
                       (-1.21, center_y, .279), (-.35, center_y + sign * .017, .273),
                       (.43, center_y, .278), (1.31, center_y + sign * .017, .279),
                       (2.16, center_y - sign * .019, .284), (2.69, center_y, .288)]
        moving.append(tube(f"Fallen oak trunk {name}", axis_points,
                           (.137, .168, .164, .153, .153, .158, .148, .131),
                           (bark, cut), 16, .11))
        for x in (-2.38, -.28, .28, 2.38):
            moving.append(box(f"Iron trunk cage {name} {x}", (x, center_y, .282),
                              (.105, .347, .347), iron, .021))
        posts = (-2.25, -.84, .84, 2.25)
        for x, lean in zip(posts, (-1, 1, -1, 1)):
            y = sign * .78
            moving.append(beam(f"Railing post {name} {x}", (x, y, .406), (x + .031 * lean, y, 1.188),
                               (.111, .120), bark, .018))
            moving.append(box(f"Post shoe {name} {x}", (x, y, .457), (.126, .143, .145), iron, .017))
            moving.append(cylinder(f"Post cap {name} {x}", (x + .025 * lean, y, 1.178), .066, .038, bronze, 16))
        for segment, (left, right) in enumerate(zip(posts, posts[1:])):
            strand = [(left + (right - left) * index / 8, sign * .777,
                       1.112 - .101 * math.sin(math.pi * index / 8)) for index in range(9)]
            moving.append(tube(f"Sagging handline {name} {segment}", strand, [.018] * 9, (rope,)))
    for index in range(19):
        x = -2.42 + index * .269
        length = 1.63 if index % 4 else 1.68
        moving.append(box(f"Tread {index + 1:02}", (x, 0, .488), (.266, length, .105),
                          damp if index % 5 in (1, 3) else plank, .006))
        for sign in (-1, 1):
            moving.append(cylinder(f"Tread pin {index + 1:02} {sign}", (x, sign * .69, .542),
                                   .014, .010, bronze, 12))
    for x in (-2.54, 2.54):
        moving.append(box(f"Deck end band {x}", (x, 0, .472), (.071, 1.65, .081), iron, .013))

    fixed_root = group("Fixed_Central_Islet", fixed)
    pivot = group("Suspended_Trunks_Swing_Pivot", moving)
    pivot["rotation_axis_blender"] = "local +Z"
    pivot["alternate_heading_degrees"] = 90
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [fixed_root, pivot, *fixed, *moving]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pivot
    bpy.ops.export_scene.gltf(filepath=str(output / "suspended_trunks_bridge.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_extras=True)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -1.175))
    bpy.context.object.data.materials.append(surface("Preview cavern floor", (.026, .047, .055), .63, grain=22))
    world = bpy.data.worlds.new("Cool mist ambient")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.14, .25, .31, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .30
    camera = bpy.data.objects.new("Bridge preview camera", bpy.data.cameras.new("Bridge preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (5.9, -7.6, 5.3)
    aim(camera, (0, 0, .015))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 6.15
    scene.camera = camera
    light("Overcast cavern light", (-3.4, -3.7, 4.9), (.60, .79, 1.0), 930, 2.8)
    light("Bronze rim light", (3.1, 2.0, 4.0), (1.0, .71, .47), 1190, 2.5)
    light("Low wet-rock bounce", (4.0, -3.7, 1.25), (.65, .88, .95), 220, 2.6)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 880
    scene.render.resolution_y = 690
    scene.render.resolution_percentage = 100
    scene["asset_status"] = "prototype_pending_unreal_import_collision_and_landing_alignment"
    scene.render.filepath = str(output / "suspended_trunks_bridge.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "suspended_trunks_bridge.blend"))
    bpy.ops.render.render(write_still=True)
    pivot.rotation_euler.z = math.pi / 2
    scene.render.filepath = str(output / "suspended_trunks_bridge_turned.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
