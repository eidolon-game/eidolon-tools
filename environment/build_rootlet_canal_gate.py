"""Generate EIDOLON's Rootlet Canal gate and marked counterweight in Blender."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def surface(name, color, roughness, metal=0, noise=None):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = (*color, 1)
    tree = result.node_tree
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    if noise is not None:
        grain = tree.nodes.new("ShaderNodeTexNoise")
        grain.inputs["Scale"].default_value = noise
        grain.inputs["Detail"].default_value = 3
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .35
        bump.inputs["Distance"].default_value = .035
        tree.links.new(grain.outputs["Fac"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return result


def block(name, center, dimensions, material, bevel=.015, seed=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if seed is not None:
        rng = random.Random(seed)
        for vertex in obj.data.vertices:
            for axis in range(3):
                vertex.co[axis] *= rng.uniform(.96, 1.04)
    obj.data.materials.append(material)
    if bevel:
        corners = obj.modifiers.new("Rounded worn edges", "BEVEL")
        corners.width = bevel
        corners.segments = 2
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def bar(name, start, end, dimensions, material, bevel=.012):
    start, end = Vector(start), Vector(end)
    obj = block(name, (start + end) / 2, (*dimensions, (end - start).length), material, bevel)
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def roller(name, center, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def cord(name, path, diameters, material, sides=8):
    points = [Vector(point) for point in path]
    vertices = []
    for row, (point, diameter) in enumerate(zip(points, diameters)):
        radius = diameter / 2
        tangent = (points[min(row + 1, len(path) - 1)] - points[max(0, row - 1)]).normalized()
        reference = Vector((1, 0, 0)) if abs(tangent.x) < .95 else Vector((0, 1, 0))
        base = tangent.cross(reference).normalized()
        across = tangent.cross(base)
        for side in range(sides):
            angle = math.tau * side / sides
            vertices.append(point + radius * (math.cos(angle) * base + math.sin(angle) * across))
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(path) - 1):
        for side in range(sides):
            start = row * sides + side
            next_vertex = row * sides + (side + 1) % sides
            faces.append((start, next_vertex, next_vertex + sides, start + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    geometry = bpy.data.meshes.new(name)
    geometry.from_pydata(vertices, [], faces)
    geometry.update()
    obj = bpy.data.objects.new(name, geometry)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in geometry.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def group(name, parts, position=(0, 0, 0)):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = position
    bpy.context.view_layer.update()
    for obj in parts:
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world
    return root


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, position, color, power, radius):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = power, radius, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, -.07, 2.1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    masonry = surface("Wet gray canal stone", (.084, .112, .124), .70, noise=21)
    seam = surface("Dark seepage stone", (.051, .077, .078), .66, noise=17)
    iron = surface("Forged sluice iron", (.058, .074, .085), .55, .72)
    bronze = surface("Old bronze fastenings", (.24, .129, .055), .58, .65)
    paint = surface("Faded ochre canal marker", (.24, .155, .052), .84)
    stone = surface("Counterweight river stone", (.14, .151, .13), .87, noise=26)
    root = surface("Tangled wet roots", (.063, .037, .018), .89, noise=25)
    hemp = surface("Braided hoist rope", (.155, .098, .048), .87)

    frame = []
    for side, sign in (("left", -1), ("right", 1)):
        frame.append(block(f"External footing {side}", (sign * 1.06, .07, .15), (.43, .78, .30), seam, .037, 11 + sign))
        for index in range(11):
            z = .454 + .367 * index
            frame.append(block(f"Canal ashlar {side} {index + 1}", (sign * 1.083, .07, z),
                               (.43, .65, .368), seam if index % 4 == 0 else masonry, .044, index * 91 + sign))
        for y in (-.164, .174):
            frame.append(bar(f"Gate guide {side} {y}", (sign * .89, y, .14), (sign * .89, y, 4.202),
                             (.069, .078), iron, .015))
        for z in (.43, 1.11, 1.82, 2.49, 3.16, 3.85):
            frame.append(roller(f"Guide rivet {side} {z}", (sign * .925, -.215, z), .028, .018, bronze))
    frame.append(block("Heavy stone lintel", (0, .054, 4.478), (2.49, .685, .308), masonry, .048, 31))
    frame.append(block("Inset beam", (0, -.205, 4.274), (2.02, .149, .148), iron, .024))
    frame.append(block("Counterweight mount", (1.46, -.215, 4.058), (.73, .43, .251), masonry, .047, 73))
    frame.append(bar("Side pulley beam", (1.05, -.261, 4.139), (1.70, -.261, 4.139), (.12, .144), iron, .021))
    for x, z, radius in ((0, 4.254, .123), (1.66, 4.135, .126)):
        frame.append(roller(f"Hoist wheel {x}", (x, -.22, z), radius, .12, bronze))
        frame.append(roller(f"Hoist axle {x}", (x, -.300, z), .053, .058, iron))
    frame.append(cord("Fixed span rope", [(0, -.302, 4.375), (.22, -.302, 4.333), (.68, -.302, 4.314),
                                          (1.12, -.302, 4.288), (1.57, -.302, 4.253),
                                          (1.66, -.302, 4.259), (1.742, -.302, 4.230)], [.024] * 7, hemp))
    for name, samples, diameters in [
        ("Pillar root left", [(-1.07,-.31,4.20), (-1.26,-.30,3.85),(-1.07,-.35,3.38),(-1.20,-.37,2.89),
                              (-1.21,-.38,2.24),(-1.16,-.37,1.69),(-1.37,-.36,1.01),(-1.40,-.56,.16)],
         [.078,.078,.067,.060,.057,.051,.042,.015]),
        ("Fork root left", [(-1.18,-.38,2.68),(-1.34,-.41,2.27),(-1.37,-.41,1.94),(-1.52,-.44,1.60)],
         [.039,.036,.028,.008]),
        ("Pillar root right", [(1.26,-.35,3.71),(1.14,-.35,3.42),(1.25,-.36,2.76),(1.34,-.36,2.33),
                               (1.13,-.35,1.71),(1.20,-.36,1.22),(1.24,-.32,.74),(1.35,-.44,.11)],
         [.06,.058,.062,.063,.056,.044,.030,.009]),
    ]:
        frame.append(cord(name, samples, diameters, root))

    gate = []
    for z in (.30, .96, 1.69):
        gate.append(bar(f"Gate cross strap {z}", (-.83, 0, z), (.83, 0, z), (.097, .113), iron, .011))
    for index in range(8):
        x = -.758 + index * .2165
        gate.append(bar(f"Gate upright {index + 1}", (x, 0, .115), (x, 0, 1.884),
                        (.073, .081), iron, .009))
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0, radius2=.053, depth=.121, location=(x, 0, .055))
        tooth = bpy.context.object
        tooth.name = f"Tapered gate tooth {index + 1}"
        tooth.rotation_euler.z = math.pi / 4
        tooth.data.materials.append(iron)
        gate.append(tooth)
        for z in (.30, .96, 1.69):
            gate.append(roller(f"Gate strap fastener {index + 1} {z}", (x, -.063, z), .018, .018, bronze))
    gate.append(bar("Central yoke", (0, 0, 1.693), (0, 0, 1.952), (.103, .098), iron, .012))
    gate.append(roller("Central hoist lug", (0, -.068, 1.869), .076, .065, bronze))

    weight_center = (1.742, -.304, 3.335)
    counterweight = [block("Marked river stone counterweight", weight_center, (.47, .39, .52), stone, .080, 24)]
    for z in (3.175, 3.512):
        counterweight.append(block(f"Counterweight iron strap {z}", (1.742,-.304,z), (.479, .401, .068), iron, .023))
    counterweight.append(bar("Counterweight hoist link", (1.742,-.304,3.54), (1.742,-.304,3.71),
                              (.047, .063), bronze, .013))
    glyph = [(1.590, -.509, 3.337), (1.742, -.509, 3.438), (1.895, -.509, 3.337),
             (1.742, -.509, 3.236), (1.590, -.509, 3.337)]
    for index, (start, end) in enumerate(zip(glyph, glyph[1:])):
        counterweight.append(bar(f"Ochre quadrant mark {index + 1}", start, end, (.016, .011), paint, .004))
    counterweight.append(bar("Ochre central mark", (1.742,-.511,3.287), (1.742,-.511,3.386), (.014, .012), paint, .003))

    fixed_root = group("Fixed_Canal_Frame", frame)
    gate_root = group("Saracinesca_Lift", gate)
    weight_root = group("Marked_Stone_Counterweight", counterweight, weight_center)
    gate_root["open_travel_m"] = 2.25
    gate_root["travel_axis_blender"] = "local +Z"
    weight_root["open_travel_m"] = 2.25
    weight_root["travel_axis_blender"] = "local -Z"
    leads = [
        cord("Vertical gate lead", [(0,-.214,1.938),(0,-.281,2.220),(0,-.302,4.371)], [.025]*3, hemp),
        cord("Vertical counterweight lead", [(1.742,-.302,4.230),(1.742,-.304,3.704)], [.025]*2, hemp),
    ]
    rope_root = group("Hoist_Leads_Static_Pose", leads)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [fixed_root, gate_root, weight_root, rope_root, *frame, *gate, *counterweight, *leads]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = gate_root
    bpy.ops.export_scene.gltf(filepath=str(output / "rootlet_canal_gate.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_extras=True)

    # Present a raised gate. Replace the parked-pose leads for the still.
    gate_root.location.z += 2.25
    weight_root.location.z -= 2.25
    rope_root.hide_render = True
    for obj in leads:
        obj.hide_render = True
    cord("Lifted gate lead preview", [(0,-.214,4.188),(0,-.302,4.371)], [.025]*2, hemp)
    cord("Lowered weight lead preview", [(1.742,-.302,4.230),(1.742,-.304,1.454)], [.025]*2, hemp)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.015))
    bpy.context.object.data.materials.append(surface("Preview cavern floor", (.024, .045, .052), .62, noise=29))
    world = bpy.data.worlds.new("Cavern ambient")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.14, .23, .32, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .29
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (4.1, -10.1, 4.27)
    aim(camera, (.30, -.12, 2.29))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5.36
    scene.camera = camera
    light("Overcast water", (-2.4, -3.8, 5.0), (.58, .79, 1.0), 980, 2.4)
    light("Ochre rim", (2.9, 1.67, 4.7), (1.0, .70, .49), 1140, 2.0)
    light("Floor fill", (3.1, -4.0, 1.8), (.54, .74, .91), 230, 2.4)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 710
    scene.render.resolution_y = 820
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "rootlet_canal_gate.png")
    scene["asset_status"] = "prototype_pending_unreal_import_collision_and_ropes"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "rootlet_canal_gate.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
