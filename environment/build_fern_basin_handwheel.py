"""Build the Fern Basin intake and sluice handwheel prototype in Blender."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def surface(name, color, roughness, metal=0, grain=None):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    tree = material.node_tree
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    if grain is not None:
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = grain
        noise.inputs["Detail"].default_value = 3
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .32
        bump.inputs["Distance"].default_value = .024
        tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def beveled_block(name, location, dimensions, material, bevel=.022, seed=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if seed is not None:
        rng = random.Random(seed)
        for vertex in obj.data.vertices:
            for axis in range(3):
                vertex.co[axis] *= rng.uniform(.91, 1.05)
    obj.data.materials.append(material)
    edge = obj.modifiers.new("Soft weathered edges", "BEVEL")
    edge.width = bevel
    edge.segments = 3
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def beam(name, start, end, cross, material, bevel=.012):
    start, end = Vector(start), Vector(end)
    obj = beveled_block(name, (start + end) / 2, (*cross, (end - start).length), material, bevel)
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def cylinder(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def ring(name, location, radius, thickness, material):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thickness,
                                     major_segments=56, minor_segments=10, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def fern_cluster(sites, material, gray_green):
    vertices, faces = [], []
    rng = random.Random(311)
    for x, y, z, size in sites:
        center = Vector((x, y, z))
        for frond in range(6):
            angle = math.tau * frond / 6 + rng.uniform(-.25, .25)
            direction = Vector((math.cos(angle), math.sin(angle), 0))
            across = Vector((-direction.y, direction.x, 0))
            reach = size * rng.uniform(.66, 1.03)
            height = size * rng.uniform(.46, .87)

            def point(t):
                return center + direction * (reach * math.sin(t * 1.83)) + Vector((0, 0, height * math.sin(t * 2.17)))

            offset = len(vertices)
            for index in range(11):
                t = index / 10
                mid = point(t)
                width = .007 * (1 - .80 * t)
                vertices.extend((mid + across * width, mid - across * width))
                if index:
                    i = offset + index * 2
                    faces.append((i - 2, i - 1, i + 1, i))
            for index in range(9):
                t = .17 + .087 * index
                mid = point(t)
                length = reach * (.21 - .13 * t) * math.sin((.30 + .62 * t) * math.pi)
                for sign in (-1, 1):
                    tip = mid + across * (sign * length) + direction * (length * .69)
                    spread = direction * (length * .26)
                    rib = mid.lerp(tip, .54)
                    i = len(vertices)
                    vertices.extend((mid, rib - spread, tip, rib + spread, rib + Vector((0, 0, .13 * length))))
                    triangles = ((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4))
                    if sign > 0:
                        triangles = tuple(reversed(face) for face in triangles)
                    faces.extend(tuple(i + corner for corner in face) for face in triangles)
    data = bpy.data.meshes.new("Curled fern clusters")
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new("Curled fern clusters", data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.data.materials.append(gray_green)
    for polygon in data.polygons:
        polygon.material_index = int(polygon.index % 5 in (1, 3))
    return obj


def point_camera(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, center, hue, power, radius):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = power, radius, hue
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    point_camera(obj, (0, -.16, .93))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    stone = surface("Wet basalt ashlar", (.090, .119, .131), .49, grain=16)
    wet = surface("Water-stained basalt", (.049, .072, .077), .35, grain=25)
    iron = surface("Blackened sluice iron", (.070, .084, .09), .53, .77)
    bronze = surface("Oxidized bronze", (.21, .12, .056), .53, .72)
    patina = surface("Bronze verdigris", (.057, .185, .148), .57, .60)
    green = surface("Fern shadow green", (.038, .13, .058), .72)
    frond = surface("Fern gray green", (.082, .19, .095), .76)

    fixed = [
        beveled_block("Apron stone", (0, 0, .114), (2.28, .91, .23), stone, .075, 20),
        beveled_block("Damp inlet sill", (-.24, -.064, .26), (1.45, .65, .16), wet, .037, 5),
        beveled_block("Return wall left", (-.81, .24, .99), (.31, .45, 1.48), stone, .055, 22),
        beveled_block("Return wall right", (.34, .22, .99), (.26, .45, 1.48), stone, .051, 26),
    ]
    for side, x in (("left", -.78), ("right", .325)):
        for index, z in enumerate((.415, .691, .974, 1.253, 1.522)):
            fixed.append(beveled_block(f"Ashlar {side} {index + 1}", (x, -.12, z),
                                      (.32, .43, .274), stone if index % 3 else wet, .035,
                                      index + (15 if side == "left" else 40)))
    fixed.extend([
        beveled_block("Wet lintel", (-.227, -.097, 1.698), (1.49, .53, .222), wet, .06, 61),
        beveled_block("Basalt cap", (-.27, -.088, 1.86), (1.59, .57, .133), stone, .043, 62),
        beveled_block("Shadow behind intake", (-.226, .415, .943), (1.15, .10, 1.30), wet, .026, 68),
        beveled_block("Wheel mounting pedestal", (.79, .014, .40), (.42, .52, .67), wet, .053, 77),
        beveled_block("Wheel valve body", (.79, -.03, .94), (.32, .35, .50), iron, .063),
    ])
    # The face stays partially open and reads as an intake behind its iron grate.
    for index in range(7):
        x = -.59 + index * .121
        fixed.append(beam(f"Intake grille {index + 1}", (x, .10, .313), (x + .025, .124, 1.592),
                          (.033, .034), iron, .008))
    for z in (.46, 1.28):
        fixed.append(beam(f"Crosspiece {z}", (-.645, .084, z), (.204, .085, z + .011),
                          (.037, .052), iron, .009))
    fixed.append(beam("Sluice actuator rail", (.27, -.12, 1.44), (.79, -.155, 1.44),
                      (.071, .083), iron, .014))

    wheel_center = Vector((.79, -.49, 1.15))
    fixed.append(cylinder("Stationary spindle collar", (.79, -.245, 1.15), .10, .18, bronze))
    fixed.append(cylinder("Stationary mounting flange", (.79, -.195, 1.15), .136, .062, iron))
    for index in range(8):
        angle = math.tau * index / 8 + math.pi / 8
        fixed.append(cylinder(f"Mount flange bolt {index + 1}",
                              (.79 + .111 * math.cos(angle), -.232, 1.15 + .111 * math.sin(angle)),
                              .017, .032, patina))
    fixed.append(fern_cluster([(-1.01, -.26, .225, .29), (-.96, .18, .229, .22),
                              (.81, -.31, .23, .23), (.96, -.20, .23, .19),
                              (-.89, .19, 1.87, .17)], green, frond))

    moving = [
        ring("Cast iron wheel rim", wheel_center, .312, .032, iron),
        cylinder("Bronze rotating hub", wheel_center + Vector((0, -.013, 0)), .107, .15, bronze),
        cylinder("Iron rotating axle", wheel_center + Vector((0, .095, 0)), .064, .24, iron),
        ring("Verdigris hub collar", wheel_center + Vector((0, -.094, 0)), .072, .012, patina),
        cylinder("Face lock nut", wheel_center + Vector((0, -.107, 0)), .047, .045, iron),
    ]
    for index in range(5):
        angle = math.tau * index / 5 + .22
        direction = Vector((math.cos(angle), 0, math.sin(angle)))
        moving.append(beam(f"Wheel spoke {index + 1}", wheel_center + direction * .08,
                           wheel_center + direction * .305, (.054, .042), iron, .013))
        xy = wheel_center + direction * .288 + Vector((0, -.031, 0))
        moving.append(cylinder(f"Oxidized spoke rivet {index + 1}", xy, .025, .026, patina))
    moving.append(cylinder("Pull grip", wheel_center + Vector((.094, -.066, .294)), .044, .178, bronze))
    moving.append(cylinder("Pull grip cap", wheel_center + Vector((.094, -.166, .294)), .048, .033, patina))

    frame = bpy.data.objects.new("Fixed_Intake_Frame", None)
    pivot = bpy.data.objects.new("Handwheel_Pivot", None)
    for obj in (frame, pivot):
        bpy.context.collection.objects.link(obj)
    pivot.location = wheel_center
    pivot["rotation_axis_blender"] = "local Y"
    bpy.context.view_layer.update()
    for group, parts in ((frame, fixed), (pivot, moving)):
        for obj in parts:
            world_transform = obj.matrix_world.copy()
            obj.parent = group
            obj.matrix_world = world_transform

    bpy.ops.object.select_all(action="DESELECT")
    for obj in [frame, pivot, *fixed, *moving]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pivot
    bpy.ops.export_scene.gltf(filepath=str(output / "fern_basin_handwheel.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_extras=True)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.035))
    bpy.context.object.data.materials.append(surface("Preview ground", (.040, .058, .061), .45, grain=22))
    world = bpy.data.worlds.new("Cavern fill")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.10, .21, .28, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .34
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (3.2, -6.8, 3.0)
    point_camera(camera, (.08, -.11, .96))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 3.10
    scene.camera = camera
    light("Overcast water light", (-1.9, -2.4, 3.6), (.62, .82, 1.0), 510, 1.8)
    light("Amber rim", (2.0, 1.3, 2.9), (1.0, .70, .44), 620, 1.4)
    light("Sluice bounce", (1.9, -2.4, 1.2), (.71, .90, .81), 130, 1.6)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 780
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "fern_basin_handwheel.png")
    scene["asset_status"] = "prototype_pending_unreal_import_hydraulics_and_collision"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "fern_basin_handwheel.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
