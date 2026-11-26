"""Blender 4.3+ static Lintel Mantis prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_lintel_mantis.py -- OUTPUT
"""
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def prism(name, outline, depth, surface):
    """Create a beveled chitin plate from a side-view outline."""
    count = len(outline)
    vertices = [
        (x + side * depth / 2, y, z)
        for side in (-1, 1)
        for x, y, z in outline
    ]
    faces = [
        tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count)),
        *((i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count)),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()
    plate = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(plate)
    mesh.materials.append(surface)
    uv = mesh.uv_layers.new(name="UVMap")
    min_y = min(v[1] for v in outline)
    min_z = min(v[2] for v in outline)
    span_y = max(v[1] for v in outline) - min_y
    span_z = max(v[2] for v in outline) - min_z
    for loop in mesh.loops:
        _, y, z = vertices[loop.vertex_index]
        uv.data[loop.index].uv = ((y - min_y) / span_y, (z - min_z) / span_z)
    bevel = plate.modifiers.new("Chitin rim", "BEVEL")
    bevel.width = depth * .22
    bevel.segments = 2
    return plate


def build(output):
    helpers = runpy.run_path(str(Path(__file__).with_name("make_catacomb_crawler.py")))
    oval, tapered, material, finish, add_light, aim = (
        helpers[name] for name in ("oval", "tapered", "material", "finish", "add_light", "aim")
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    chitin = material("Slate-green thoracic chitin", (.039, .090, .065), .33, .32)
    fascia = material("Brown thoracic fascia", (.063, .028, .021), .43, .20)
    bone = material("Calcified rib ridge", (.22, .24, .13), .43, .37)
    blade = material("Worn obsidian keratin", (.018, .028, .029), .29, .32)
    tooth = material("Pale chitin edge", (.37, .32, .18), .36, .18)
    amber = material("Amber compound eyes", (.67, .29, .044), .25, .10)
    membrane = material("Mottled wing membrane", (.135, .074, .042), .51, .25)

    oval("Vertical thorax", (0, .058, 1.01), (.212, .226, .366), chitin)
    oval("Abdominal taper", (0, .351, .498), (.198, .248, .282), fascia)
    oval("Head", (0, -.159, 1.325), (.234, .159, .128), chitin)
    tapered("Ventral keel", (0, -.145, .669), (0, -.150, 1.225), .064, .120, bone)
    for side in (-1, 1):
        oval(f"Compound eye {side}", (side * .164, -.262, 1.348), (.099, .081, .071), amber)
        tapered(f"Jaw {side}", (side * .102, -.252, 1.318),
                (side * .049, -.370, 1.225), .052, .008, blade)
        tapered(f"Antennal root {side}", (side * .092, -.186, 1.423),
                (side * .118, -.302, 1.558), .021, .013, bone)
        tapered(f"Antennal tip {side}", (side * .118, -.302, 1.558),
                (side * .177, -.344, 1.655), .013, .002, blade)
        for index in range(4):
            z = .821 + index * .095
            tapered(f"Thoracic rib {side} {index}", (side * .082, -.145, z),
                    (side * .216, .054, z + .034), .031, .019, bone)
        for index in range(3):
            origin = (side * .146, .091 + index * .161, .814 - index * .126)
            knee = (side * (.55 + index * .018), .007 + index * .155, .613 - index * .072)
            foot = (side * (.705 - index * .042), -.410 + index * .535, .051)
            tapered(f"Femur {side} {index}", origin, knee, .075, .043, chitin)
            oval(f"Leg hinge {side} {index}", knee, (.056, .06, .056), bone)
            tapered(f"Shin {side} {index}", knee, foot, .046, .023, blade)
            tapered(f"Clinging foot {side} {index}", foot,
                    (foot[0] + side * .048, foot[1] - .058, .014), .026, .006, tooth)

        shoulder = (side * .154, .015, 1.241)
        elbow = (side * .469, -.344, 1.174)
        hinge = (side * .465, -.390, 1.414)
        tapered(f"Raptorial upper arm {side}", shoulder, elbow, .083, .061, chitin)
        oval(f"Raptorial elbow {side}", elbow, (.077, .077, .087), bone)
        tapered(f"Raptorial folding joint {side}", elbow, hinge, .063, .045, blade)
        outline = [
            (side * .462, -.431, 1.365), (side * .438, -.475, 1.578),
            (side * .361, -.397, 1.773), (side * .263, -.219, 1.883),
            (side * .285, -.305, 1.791), (side * .342, -.413, 1.681),
            (side * .388, -.512, 1.516), (side * .409, -.517, 1.378),
        ]
        if side > 0:
            outline.reverse()
        prism(f"Curved raptorial blade {side}", outline, .069, blade)
        for index in range(4):
            z = 1.429 + index * .079
            x = side * (.412 - index * .023)
            y = -.486 + index * .024
            tapered(f"Blade tooth {side} {index}", (x, y, z),
                    (x - side * .031, y - .092, z + .032), .021, .004, tooth)

        wing = [
            (side * .145, .203, 1.265), (side * .375, .349, 1.202),
            (side * .448, .549, .926), (side * .498, .744, .673),
            (side * .302, .718, .717), (side * .237, .462, .870),
        ]
        if side > 0:
            wing.reverse()
        prism(f"Short wing membrane {side}", wing, .026, membrane)
        for index, target in enumerate(wing):
            origin = (side * .153, .220, 1.266)
            if (Vector(target) - Vector(origin)).length > .1:
                tapered(f"Wing vein {side} {index}", origin, target, .022, .007, chitin)

    for obj in bpy.context.scene.objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(output / "LintelMantis.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Vault limestone", (.065, .077, .080), .69, .42)
    bpy.ops.mesh.primitive_plane_add(size=100)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Vault atmosphere")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.13, .17, .20, 1)
    background.inputs[1].default_value = .32
    add_light("Warm key", (-2.1, -2.9, 3.3), 375, (1, .69, .41), 1.65)
    add_light("Cold rim", (1.2, 2.2, 2.8), 420, (.38, .63, 1), 1.4)
    add_light("Fill", (2.5, -1.4, 1.7), 95, (.68, .85, 1), 1.4)
    bpy.ops.object.camera_add(location=(2.40, -3.43, 2.09))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 57
    aim(scene.camera, (0, .085, .915))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "LintelMantis.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
