"""Blender 4.3+ static creature prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_catacomb_crawler.py -- OUTPUT
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def material(name, color, roughness, noise=0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    result.use_nodes = True
    nodes = result.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    if noise:
        texture = nodes.new("ShaderNodeTexNoise")
        texture.inputs["Scale"].default_value = 14
        texture.inputs["Detail"].default_value = 3
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = noise
        bump.inputs["Distance"].default_value = .035
        result.node_tree.links.new(texture.outputs["Fac"], bump.inputs["Height"])
        result.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return result


def finish(name, surface):
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(surface)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def oval(name, point, scale, surface):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=point)
    obj = finish(name, surface)
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def tapered(name, start, end, start_radius, end_radius, surface):
    line = Vector(end) - Vector(start)
    midpoint = Vector(start) + line * .5
    bpy.ops.mesh.primitive_cone_add(
        vertices=16, radius1=start_radius, radius2=end_radius,
        depth=line.length, location=midpoint,
    )
    obj = finish(name, surface)
    obj.rotation_euler = line.to_track_quat("Z", "Y").to_euler()
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_light(name, point, power, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = point
    aim(light, (0, 0, 1))


def build(output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    dark = material("Wet fascia", (.026, .011, .012), .28, .34)
    tendon = material("Exposed throat", (.19, .021, .016), .31, .30)
    plates = [
        material("Aged bone", (.30, .23, .16), .46, .38),
        material("Dark bone", (.19, .13, .083), .49, .39),
        material("Pale weathered bone", (.48, .37, .25), .43, .34),
    ]
    keratin = material("Blue-black keratin", (.023, .034, .036), .30, .22)
    enamel = material("Worn tooth enamel", (.63, .49, .29), .39, .22)
    amber = material("Clouded amber eyes", (.54, .22, .035), .24)
    oval("Thorax", (0, .26, 1.04), (.54, 1.01, .41), dark)
    oval("Abdomen", (0, .98, .93), (.44, .74, .37), dark)
    oval("Neck", (0, -.64, .95), (.38, .55, .27), tendon)
    oval("Skull", (0, -1.01, 1.12), (.46, .46, .28), plates[0])
    oval("Lower throat", (0, -1.02, .74), (.27, .40, .16), tendon)

    for index in range(7):
        y = -.54 + index * .27
        width = .53 - max(index - 3, 0) * .055
        shell = oval(f"Dorsal plate {index + 1}", (0, y, 1.31), (width, .24, .22), plates[index % 3])
        shell.rotation_euler.z = (-1) ** index * .08
        tapered(f"Dorsal spur {index + 1}", (0, y, 1.44), (0, y + .23, 1.98 - abs(index - 2) * .045), .102, .018, keratin)
        for side in (-1, 1):
            tapered(f"Rib {index + 1} {side}", (side * width * .78, y, 1.35),
                    (side * .58, y + .09, .78), .085, .035, plates[(index + 1) % 3])

    for side in (-1, 1):
        for index in range(3):
            y = -.58 + index * .71
            shoulder = (side * .36, y, 1.13)
            joint = (side * (1.00 - index * .08), y + .30, 1.37 - .13 * index)
            foot = (side * (1.34 - index * .13), y - .32 + index * .12, .11)
            tapered(f"Humerus {side} {index}", shoulder, joint, .20, .13, dark)
            tapered(f"Ulna {side} {index}", joint, foot, .14, .068, plates[index])
            oval(f"Knee plate {side} {index}", joint, (.19, .19, .18), plates[2])
            oval(f"Ankle {side} {index}", foot, (.11, .13, .10), dark)
            for toe in range(3):
                claw = (foot[0] + (toe - 1) * .11, foot[1] - .24 + abs(toe - 1) * .035, .025)
                tapered(f"Claw {side} {index} {toe}", foot, claw, .047, .008, keratin)

        hinge = (side * .26, -1.06, .87)
        jaw = (side * .45, -1.48, .62)
        fang = (side * .24, -1.72, .79)
        tapered(f"Mandible hinge {side}", hinge, jaw, .14, .103, plates[1])
        tapered(f"Mandible hook {side}", jaw, fang, .106, .017, plates[2])
        for i in range(4):
            x = side * (.13 + i * .055)
            y = -1.44 + i * .032
            tapered(f"Upper tooth {side} {i}", (x, y, .99), (x, y - .031, .76 - (i % 2) * .025), .039, .007, enamel)
            tapered(f"Lower tooth {side} {i}", (side * (.41 - i * .029), -1.50 - i * .052, .66),
                    (side * (.39 - i * .029), -1.51 - i * .052, .79), .033, .006, enamel)
        for index in range(2):
            point = (side * (.33 + index * .057), -1.31 + index * .145, 1.22 + index * .019)
            oval(f"Eye socket {side} {index}", point, (.09, .09, .063), keratin)
            oval(f"Eye {side} {index}", (point[0] + side * .031, point[1] - .055, point[2]),
                 (.05, .041, .036), amber)
        tapered(f"Cranial horn {side}", (side * .34, -1.01, 1.27),
                (side * .57, -.56, 1.67), .12, .016, plates[1])

    creature = [obj for obj in scene.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    # Export creature components only. Preview stage and procedural bump stay in Blender.
    for obj in creature:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = creature[0]
    bpy.ops.export_scene.gltf(
        filepath=str(output / "CatacombCrawler.glb"), export_format="GLB", use_selection=True,
    )

    floor = material("Damp slate", (.055, .068, .072), .62, .45)
    bpy.ops.mesh.primitive_plane_add(size=200)
    finish("Preview floor", floor)
    world = bpy.data.worlds.new("Catacomb atmosphere")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.13, .17, .21, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .28
    add_light("Torch key", (-3, -3, 4), 670, (1, .63, .35), 3)
    add_light("Cold vault rim", (2, 3, 4), 980, (.37, .67, 1), 2.8)
    add_light("Front fill", (3, -4, 2), 190, (.70, .80, 1), 2)
    bpy.ops.object.camera_add(location=(4.25, -5.85, 3.0))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 53
    aim(scene.camera, (0, -.06, .93))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "CatacombCrawler.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "CatacombCrawler.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
