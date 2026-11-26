"""Blender 4.3+ static Ossuary Tick prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_ossuary_tick.py -- OUTPUT
"""
import runpy
import sys
from pathlib import Path

import bpy


def build(output):
    helpers = runpy.run_path(str(Path(__file__).with_name("make_catacomb_crawler.py")))
    oval, tapered, material, finish, add_light, aim = (
        helpers[name] for name in ("oval", "tapered", "material", "finish", "add_light", "aim")
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    chitin = material("Oxidized chitin", (.11, .042, .020), .39, .29)
    shell = material("Ossuary calcium", (.35, .25, .14), .57, .30)
    edge = material("Black keratin", (.023, .020, .015), .28, .15)
    abdomen = material("Soft russet belly", (.24, .043, .026), .43, .27)
    eye = material("Dark obsidian eyes", (.023, .036, .027), .18)

    oval("Flattened abdomen", (0, .059, .197), (.208, .296, .112), abdomen)
    oval("Ossuary seed back", (0, .040, .266), (.204, .294, .146), chitin)
    for index in range(5):
        y = -.117 + .075 * index
        width = (.116, .161, .174, .148, .103)[index]
        plate = oval(f"Scute {index + 1}", (0, y, .342), (width, .065, .069), shell)
        plate.rotation_euler.x = (.09, .01, -.02, -.16, -.27)[index]
    oval("Head wedge", (0, -.199, .229), (.115, .127, .095), chitin)

    for side in (-1, 1):
        for index in range(4):
            y = -.142 + .087 * index
            origin = (side * .137, y, .217)
            upper = (side * (.280 + (.020 if index in (1, 2) else 0)), y + .022, .289 - .016 * index)
            outer = (side * (.337 - .012 * index), y - (.092 - .037 * index), .140)
            hook = (side * (.357 - .013 * index), outer[1] - .067, .049)
            point = (side * (.315 - .013 * index), hook[1] - .029, .008)
            tapered(f"Proximal {side} {index}", origin, upper, .044, .035, chitin)
            oval(f"Hinge {side} {index}", upper, (.040, .039, .036), shell)
            tapered(f"Forelimb {side} {index}", upper, outer, .038, .026, shell)
            tapered(f"Hook base {side} {index}", outer, hook, .028, .017, edge)
            tapered(f"Hook tip {side} {index}", hook, point, .018, .0035, edge)
        oval(f"Occluded eye {side}", (side * .083, -.261, .266), (.034, .037, .025), eye)
        tapered(f"Palp base {side}", (side * .057, -.263, .208),
                (side * .087, -.355, .178), .033, .025, chitin)
        tapered(f"Palp hook {side}", (side * .087, -.355, .178),
                (side * .039, -.409, .159), .026, .006, edge)

    # Include only creature geometry in the export.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "OssuaryTick.glb"), export_format="GLB", use_selection=True,
    )

    floor = material("Carbonate floor", (.074, .063, .054), .73, .41)
    bpy.ops.mesh.primitive_plane_add(size=100)
    finish("Preview floor", floor)
    world = bpy.data.worlds.new("Catacomb air")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.14, .17, .21, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .35
    add_light("Amber key", (-1.3, -1.3, 1.8), 144, (1, .68, .43), 1.0)
    add_light("Blue rim", (.9, 1.5, 1.7), 185, (.36, .58, 1), .8)
    bpy.ops.object.camera_add(location=(1.0, -1.43, .82))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 49
    aim(scene.camera, (0, -.025, .18))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "OssuaryTick.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
