"""Build the Hollow Trunk keyed pin and smoky-glass socket in Blender."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def surface(name, color, roughness, metal=0, noise=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    nodes = mat.node_tree.nodes
    shader = nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    if noise is not None:
        texture = nodes.new("ShaderNodeTexNoise")
        texture.inputs["Scale"].default_value = noise
        texture.inputs["Detail"].default_value = 4
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .37
        bump.inputs["Distance"].default_value = .024
        mat.node_tree.links.new(texture.outputs["Fac"], bump.inputs["Height"])
        mat.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def bevel(obj, amount):
    modifier = obj.modifiers.new("Worn edges", "BEVEL")
    modifier.width = amount
    modifier.segments = 2
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")


def box(name, center, dimensions, mat, rounding=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if rounding:
        bevel(obj, rounding)
    return obj


def cylinder(name, center, radius, depth, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def torus(name, center, radius, thickness, mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thickness,
                                     major_segments=48, minor_segments=8, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def cut(obj, cutter):
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new("Keyed socket cavity", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def bark_body(mat, rim):
    # Irregular trunk with stretched bark grooves and a broken crown.
    profile = ((.85, 0), (.81, .14), (.74, .36), (.68, .70), (.66, 1.02),
               (.62, 1.32), (.61, 1.56), (.57, 1.83))
    sides = 80
    vertices = []
    for row, (radius, height) in enumerate(profile):
        for index in range(sides):
            angle = math.tau * index / sides
            ripple = 1 + .088 * math.sin(7 * angle + .35 * row) + .036 * math.cos(19 * angle - .19 * row)
            z = height
            if row == len(profile) - 1:
                z += .10 * math.sin(5 * angle) + .065 * math.sin(11 * angle + .3)
            vertices.append((radius * ripple * math.cos(angle) - .08 * height,
                             .88 * radius * ripple * math.sin(angle) + .15, z))
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(profile) - 1):
        for index in range(sides):
            lower = row * sides + index
            next_vertex = row * sides + (index + 1) % sides
            faces.append((lower, next_vertex, next_vertex + sides, lower + sides))
    vertices.append((-.14, .15, 1.71))
    center = len(vertices) - 1
    start = (len(profile) - 1) * sides
    faces.extend((start + index, start + (index + 1) % sides, center) for index in range(sides))
    obj = mesh("Ancient trunk", vertices, faces, mat)
    obj.data.materials.append(rim)
    uv = obj.data.uv_layers.new(name="Bark UV")
    for polygon in obj.data.polygons[1:1 + (len(profile) - 1) * sides]:
        row, index = divmod(polygon.index - 1, sides)
        left, right = index / sides, (index + 1) / sides
        bottom, top = row / (len(profile) - 1), (row + 1) / (len(profile) - 1)
        for loop_index, coordinate in zip(polygon.loop_indices, ((left, bottom), (right, bottom), (right, top), (left, top))):
            uv.data[loop_index].uv = coordinate
    for polygon in obj.data.polygons[-sides:]:
        polygon.material_index = 1
        for loop_index in polygon.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = ((vertex.x + .78) / 1.56, (vertex.y + .63) / 1.56)
    return obj


def beam(name, start, end, cross, mat, rounding=.014):
    start, end = Vector(start), Vector(end)
    obj = box(name, (start + end) / 2, (*cross, (end - start).length), mat, rounding)
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, position, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = power, color, size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, -.20, 1.05))


def mount(name, parts, location=(0, 0, 0)):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = location
    bpy.context.view_layer.update()
    for obj in parts:
        transform = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = transform
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    bark = surface("Waterlogged bark", (.094, .052, .031), .88, noise=10)
    split = surface("Ancient split heartwood", (.18, .103, .057), .87, noise=17)
    iron = surface("Forged black iron", (.12, .14, .16), .49, .81)
    polished = surface("Worn pin iron", (.24, .27, .28), .40, .83)
    bronze = surface("Tarnished bronze", (.26, .126, .057), .45, .77)
    patina = surface("Verdigris marks", (.06, .159, .132), .60, .51)
    dark = surface("Socket recess", (.029, .041, .045), .77)
    glass = surface("Smoky glass", (.075, .119, .135), .20)
    glass_shader = glass.node_tree.nodes["Principled BSDF"]
    glass_shader.inputs["IOR"].default_value = 1.46
    glass_shader.inputs["Transmission Weight"].default_value = .32

    pin_z = .99
    trunk = bark_body(bark, split)
    bronze_socket = cylinder("Bronze keyway collar", (0, -.553, pin_z), .247, .135, bronze)
    throat = cylinder("Iron socket throat", (0, -.528, pin_z), .172, .136, iron)
    bore = cylinder("Temporary cylindrical cutter", (0, -.38, pin_z), .103, .82, dark)
    keyway = box("Temporary ridge cutter", (.112, -.38, pin_z), (.094, .82, .078), dark)
    for target in (trunk, bronze_socket, throat):
        cut(target, bore)
        cut(target, keyway)
    for cutter in (bore, keyway):
        bpy.data.objects.remove(cutter, do_unlink=True)
    fixed = [trunk, bronze_socket, throat,
             cylinder("Black recess cap", (0, .039, pin_z), .156, .018, dark)]
    for index in range(6):
        angle = math.tau * index / 6 + .25
        fixed.append(cylinder(f"Patina rivet {index + 1}",
                              (.202 * math.cos(angle), -.633, pin_z + .202 * math.sin(angle)),
                              .022, .036, patina))

    plate_z, plate_x = 1.43, -.054
    fixed.append(box("Shaped plaque backing", (plate_x, -.409, plate_z), (.46, .13, .245), bronze, .041))
    fixed.append(box("Smoky glass plate", (plate_x, -.489, plate_z), (.365, .04, .169), glass, .008))
    for i, x in enumerate((-.195, -.091, .016, .119)):
        height = .017 + i * .016
        fixed.append(beam(f"Etched index trace {i + 1}", (x, -.511, plate_z - .027),
                          (x + .026, -.511, plate_z - .027 + height), (.009, .004), patina, .0007))

    pin_parts = [
        cylinder("Keyed pin shaft", (0, -.370, pin_z), .079, .50, polished),
        box("Pin key ridge", (.101, -.386, pin_z), (.063, .46, .047), iron, .009),
        cylinder("Pin head washer", (0, -.666, pin_z), .128, .075, iron),
        torus("Twisted bronze pull loop", (0, -.756, pin_z), .123, .026, bronze),
        cylinder("Loop mounting stud", (0, -.716, pin_z), .055, .086, iron),
    ]
    fixed_root = mount("Ancient_Trunk_Socket", fixed)
    pivot = mount("Removable_Keyed_Pin", pin_parts, (0, -.630, pin_z))
    pivot["withdrawal_axis_blender"] = "local -Y"
    pivot["fully_clear_travel_m"] = .58
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [fixed_root, pivot, *fixed, *pin_parts]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pivot
    bpy.ops.export_scene.gltf(filepath=str(output / "hollow_trunk_pin.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_extras=True)

    # Pull the pin out for the still preview, exposing the shaft and key.
    pivot.location.y -= .62
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, -.006))
    bpy.context.object.data.materials.append(surface("Preview earth", (.035, .042, .046), .92, noise=11))
    world = bpy.data.worlds.new("Buried forest fill")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.13, .21, .29, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .31
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (3.1, -6.9, 2.9)
    aim(camera, (-.02, -.26, .99))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.75
    scene.camera = camera
    light("Cavern blue", (-2.0, -3.0, 3.35), (.63, .81, 1.0), 490, 1.6)
    light("Warm edge", (2.2, .3, 2.6), (1.0, .71, .45), 560, 1.2)
    light("Socket fill", (1.4, -3.4, 1.5), (.79, .88, 1.0), 140, 1.4)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 780
    scene.render.resolution_y = 740
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "hollow_trunk_pin.png")
    scene["asset_status"] = "prototype_pending_unreal_import_and_collision"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "hollow_trunk_pin.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
