"""Generate the Double Clearing rootbound latch and its two preview poses."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


PIVOT = Vector((1.20, -.609, 1.105))
DETENTS_DEGREES = (-37, 37)
TOOTH_RETRACTION_M = .070


def surface(name, rgb, roughness, metal=0, grain=None):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*rgb, 1)
    tree = material.node_tree
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    if grain is not None:
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = grain
        noise.inputs["Detail"].default_value = 3
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .32
        bump.inputs["Distance"].default_value = .038
        tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def box(name, location, dimensions, material, bevel=.014, seed=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if seed is not None:
        rng = random.Random(seed)
        for vertex in obj.data.vertices:
            for axis in range(3):
                vertex.co[axis] *= rng.uniform(.95, 1.04)
    obj.data.materials.append(material)
    if bevel:
        edges = obj.modifiers.new("Weathered outlines", "BEVEL")
        edges.width = bevel
        edges.segments = 2
        obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return obj


def bar(name, first, second, dimensions, material, rounding=.010):
    first, second = Vector(first), Vector(second)
    obj = box(name, (first + second) / 2, (*dimensions, (second - first).length), material, rounding)
    obj.rotation_euler = (second - first).to_track_quat("Z", "Y").to_euler()
    return obj


def cylinder(name, location, radius, width, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=width, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def mesh(name, vertices, faces, material):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def index_arc(name, start_angle, end_angle, material):
    steps = max(4, round((end_angle - start_angle) / 2))
    cross_section = ((.313, -.542), (.413, -.542), (.413, -.497), (.313, -.497))
    vertices = []
    for index in range(steps + 1):
        angle = math.radians(start_angle + (end_angle - start_angle) * index / steps)
        vertices.extend((PIVOT.x + radius * math.sin(angle), y, PIVOT.z + radius * math.cos(angle))
                        for radius, y in cross_section)
    faces = [(3, 2, 1, 0)]
    for step in range(steps):
        for corner in range(4):
            current = step * 4 + corner
            following = step * 4 + (corner + 1) % 4
            faces.append((current, following, following + 4, current + 4))
    faces.append(tuple(range(len(vertices) - 4, len(vertices))))
    result = mesh(name, vertices, faces, material)
    edges = result.modifiers.new("Battered index edges", "BEVEL")
    edges.width = .003
    edges.segments = 2
    return result


def root_mesh(name, coordinates, sizes, material):
    centers = [Vector(point) for point in coordinates]
    count = 8
    vertices = []
    for row, (center, radius) in enumerate(zip(centers, sizes)):
        tangent = (centers[min(row + 1, len(centers) - 1)] - centers[max(0, row - 1)]).normalized()
        right = tangent.cross(Vector((0, 1, 0))).normalized()
        across = tangent.cross(right)
        for index in range(count):
            angle = math.tau * index / count
            vertices.append(center + radius * (right * math.cos(angle) + across * math.sin(angle)))
    faces = [tuple(reversed(range(count)))]
    for row in range(len(centers) - 1):
        for corner in range(count):
            start = row * count + corner
            following = row * count + (corner + 1) % count
            faces.append((start, following, following + count, start + count))
    faces.append(tuple(range(len(vertices) - count, len(vertices))))
    result = mesh(name, vertices, faces, material)
    for polygon in result.data.polygons[1:-1]:
        polygon.use_smooth = True
    return result


def group(name, location, parts):
    parent = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(parent)
    parent.location = location
    bpy.context.view_layer.update()
    for obj in parts:
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
    return parent


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, position, hue, power, radius):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = power, radius, hue
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (.52, -.2, 1.29))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    stone = surface("Rain-dark gate ashlar", (.088, .112, .123), .75, grain=22)
    damp = surface("Old damp and worn stone", (.055, .071, .075), .64, grain=13)
    iron = surface("Black iron latch", (.068, .095, .111), .53, .76)
    worn = surface("Polished contact iron", (.21, .25, .27), .38, .83)
    bronze = surface("Weathered bronze index", (.202, .131, .066), .52, .76)
    patina = surface("Green bronze wear", (.041, .153, .112), .58, .61)
    ochre = surface("Faded amber path mark", (.31, .192, .053), .73)
    bark = surface("Exposed gate root", (.069, .038, .021), .86, grain=21)
    grip = surface("Ancient grip oak", (.146, .079, .037), .79, grain=18)

    frame = []
    for sign, side in ((-1, "left"), (1, "right")):
        x = sign * 1.184
        frame.append(box(f"Gate foot {side}", (x, .029, .138), (.628, .77, .29), damp, .063, 21 + sign))
        for index in range(6):
            frame.append(box(f"Gate pier {side} {index + 1}", (x, .043, .417 + index * .364),
                             (.60, .656, .375), stone if index % 4 != 2 else damp, .040,
                             index * 53 + sign))
    frame.extend([
        box("Chipped gate lintel", (0, .033, 2.640), (3.05, .716, .32), stone, .052, 20),
        box("Iron strike backing", (1.195, -.315, 1.24), (.567, .115, .765), iron, .047),
        box("Stone index backing", (1.20, -.409, 1.343), (.564, .065, .422), damp, .022),
        cylinder("Fixed arbor collar", (1.20, -.441, 1.105), .119, .084, bronze),
        cylinder("Fixed arbor rear spindle", (1.20, -.494, 1.105), .061, .031, worn),
    ])
    for side, x in (("left", .943), ("right", 1.455)):
        frame.append(cylinder(f"Backing bolt {side} low", (x, -.388, .971), .027, .030, patina))
        frame.append(cylinder(f"Backing bolt {side} high", (x, -.449, 1.568), .026, .025, patina))
    for name, start, end in (("Left outer tooth", -53, -43), ("Central index crest", -31, 31),
                             ("Right outer tooth", 43, 53)):
        frame.append(index_arc(name, start, end, bronze))
    for index, angle in enumerate(DETENTS_DEGREES):
        heading = Vector((math.sin(math.radians(angle)), 0, math.cos(math.radians(angle))))
        center = Vector((PIVOT.x, -.470, PIVOT.z)) + heading * .448
        frame.append(bar(f"Detent paint mark {index + 1}", center - heading * .024, center + heading * .024,
                         (.023, .013), ochre, .003))
    for index in range(5):
        x = .967 + .11 * index
        frame.append(bar(f"Old index wear trace {index + 1}", (x, -.451, 1.542), (x + .021, -.450, 1.567),
                         (.010, .005), patina, .001))
    frame.extend([
        root_mesh("Left upper root", [(-1.34,-.32,2.66),(-1.20,-.34,2.45),(-1.38,-.38,2.19),
                                      (-1.30,-.40,1.84),(-1.44,-.41,1.39),(-1.47,-.49,.43)],
                  (.078,.061,.067,.054,.048,.011), bark),
        root_mesh("Root above latch", [(1.16,-.33,2.70),(1.19,-.38,2.48),(1.37,-.43,2.22),
                                       (1.49,-.45,1.96),(1.47,-.45,1.73),(1.50,-.44,1.61)],
                  (.067,.059,.048,.037,.028,.008), bark),
        root_mesh("Root across pier toe", [(1.47,-.37,1.07),(1.51,-.43,.83),(1.43,-.42,.53),
                                           (1.59,-.46,.31),(1.66,-.49,.10)],
                  (.037,.031,.028,.020,.007), bark),
    ])

    handle = [
        cylinder("Moving arbor cap", (1.20, -.608, 1.105), .087, .089, iron),
        cylinder("Polished pin front", (1.20, -.662, 1.105), .044, .039, worn),
        bar("Forged latch handle", (1.20,-.626,1.148), (1.20,-.626,1.680),
            (.065,.064), iron, .014),
        bar("Oak hand grip", (1.20,-.633,1.543), (1.20,-.633,1.747),
            (.094,.079), grip, .025),
    ]
    for z in (1.548, 1.719):
        handle.append(box(f"Grip band {z}", (1.20,-.634,z), (.102,.086,.034), bronze, .007))
    tooth_parts = [box("Sliding index tooth", (1.20,-.527,1.468), (.040,.069,.087), worn, .008)]
    fixed = group("Fixed_Rootbound_Gate_Frame", (0, 0, 0), frame)
    tooth = group("Retractable_Index_Tooth", (1.20, -.527, 1.468), tooth_parts)
    pivot = group("Two_Detent_Handle_Pivot", PIVOT, [*handle, tooth])
    pivot["rotation_axis_blender"] = "local +Y"
    pivot["detent_a_degrees"] = DETENTS_DEGREES[0]
    pivot["detent_b_degrees"] = DETENTS_DEGREES[1]
    tooth["retraction_axis_blender"] = "local -Y"
    tooth["retract_before_turn_m"] = TOOTH_RETRACTION_M
    pivot.rotation_euler.y = math.radians(DETENTS_DEGREES[0])

    bpy.ops.object.select_all(action="DESELECT")
    for obj in [fixed, pivot, tooth, *frame, *handle, *tooth_parts]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pivot
    bpy.ops.export_scene.gltf(filepath=str(output / "double_clearing_latch.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_extras=True)

    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, -.020))
    bpy.context.object.data.materials.append(surface("Preview slate ground", (.028, .045, .052), .75, grain=21))
    world = bpy.data.worlds.new("Cavern ambient")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.12, .22, .29, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .30
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (3.65, -7.9, 3.14)
    aim(camera, (.19, -.08, 1.26))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.15
    scene.camera = camera
    light("Blue forest key", (-2.5,-3.10,3.80), (.59,.78,1.0), 720, 2.1)
    light("Amber edge", (3.1,1.3,3.16), (1.0,.70,.46), 840, 1.9)
    light("Direct latch fill", (2.3,-3.15,1.95), (.70,.88,.89), 194, 1.47)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 34
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 800
    scene.render.resolution_y = 740
    scene.render.resolution_percentage = 100
    scene["asset_status"] = "prototype_pending_unreal_import_collision_and_puzzle_binding"
    scene.render.filepath = str(output / "double_clearing_latch.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "double_clearing_latch.blend"))
    bpy.ops.render.render(write_still=True)
    pivot.rotation_euler.y = math.radians(DETENTS_DEGREES[1])
    aim(camera, (1.14, -.44, 1.29))
    camera.data.ortho_scale = 1.54
    scene.render.filepath = str(output / "double_clearing_latch_detent_b.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
