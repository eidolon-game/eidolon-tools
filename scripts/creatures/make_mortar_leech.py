"""Blender 4.3+ static Mortar Leech prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_mortar_leech.py -- OUTPUT
"""
from math import cos, sin, tau
from pathlib import Path
import runpy
import sys

import bpy


def build(output):
    here = Path(__file__).parent
    basics = runpy.run_path(str(here / "make_catacomb_crawler.py"))
    oval, cone, material, finish, add_light, aim = (
        basics[name] for name in ("oval", "tapered", "material", "finish", "add_light", "aim")
    )
    loft = runpy.run_path(str(here / "make_censer_hagfish.py"))["loft"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    skin = material("Wet mortar hide", (.070, .102, .092), .31, .36)
    tissue = material("Bruised collar fascia", (.165, .043, .034), .37, .33)
    ridge = material("Calcified holdfast", (.222, .194, .143), .59, .44)
    chitin = material("Oxidized hook chitin", (.042, .064, .052), .34, .32)
    dark = material("Recessed feeding pore", (.013, .007, .008), .48)
    ivory = material("Exposed rigid filament", (.514, .372, .169), .39, .22)

    # The loft uses Y as its axis. Rotate to world Z so its base stays at the floor.
    column = loft("Anchored soft column", [
        (0, .018, 0, .337, .320), (0, .085, 0, .371, .323),
        (-.018, .231, -.012, .302, .269), (-.026, .434, -.038, .239, .207),
        (-.006, .683, -.071, .244, .220), (.056, .937, -.061, .270, .237),
        (.102, 1.180, -.011, .258, .220), (.071, 1.412, .037, .214, .191),
        (.018, 1.591, .064, .250, .244),
        (-.014, 1.729, .061, .282, .258), (-.017, 1.840, .046, .205, .192),
    ], skin, sides=32)
    column.rotation_euler.x = tau / 4
    smooth = column.modifiers.new("Soft column profile", "SUBSURF")
    smooth.levels = 2
    smooth.render_levels = 2
    oval("Ground adhesion pad", (0, 0, .061), (.418, .405, .078), ridge)
    oval("Collar base", (-.012, -.054, 1.743), (.296, .276, .161), tissue)
    oval("Raised annular mantle", (-.017, -.045, 1.861), (.233, .223, .097), skin)
    oval("Filament socket", (-.017, -.053, 1.930), (.102, .102, .037), dark)

    for index in range(8):
        angle = tau * index / 8
        dx, dy = cos(angle), sin(angle)
        root = (dx * .257, dy * .235, .112)
        spur = (dx * (.493 + .017 * (index % 3)), dy * .468, .044)
        cone(f"Mineral holdfast {index}", root, spur, .112, .037, ridge)
        oval(f"Adhesion node {index}", spur, (.061, .059, .043), ridge)
    for index in range(5):
        angle = tau * index / 5
        dx, dy = cos(angle), sin(angle)
        rib = loft(f"Tension rib {index}", [
            (.307 * dx, .205, -.270 * dy, .043, .038),
            (-.036 + .238 * dx, .441, -.048 - .198 * dy, .032, .028),
            (.002 + .248 * dx, .719, -.066 - .207 * dy, .026, .025),
            (.064 + .267 * dx, .977, -.048 - .232 * dy, .025, .024),
            (.105 + .238 * dx, 1.187, .010 - .209 * dy, .028, .026),
            (.081 + .208 * dx, 1.405, .042 - .180 * dy, .025, .022),
            (.022 + .248 * dx, 1.588, .070 - .230 * dy, .023, .021),
        ], tissue, sides=12)
        rib.rotation_euler.x = tau / 4
        soft = rib.modifiers.new("Raised rib surface", "SUBSURF")
        soft.levels = 1

    for index in range(3):
        angle = tau * (index / 3 + .08)
        dx, dy = cos(angle), sin(angle)
        base = (-.014 + .194 * dx, -.046 + .188 * dy, 1.817)
        joint = (-.014 + .329 * dx, -.046 + .326 * dy, 1.987 + .023 * index)
        crook = (-.010 + .398 * dx, -.041 + .383 * dy, 2.120 + .025 * index)
        tip = (-.004 + .296 * dx, -.036 + .291 * dy, 2.196 + .021 * index)
        oval(f"Upper hook hinge {index + 1}", base, (.095, .096, .107), tissue)
        cone(f"Upper hook shaft {index + 1}", base, joint, .086, .071, chitin)
        cone(f"Upper hook crook {index + 1}", joint, crook, .074, .053, chitin)
        cone(f"Upper hook tip {index + 1}", crook, tip, .057, .006, chitin)

    cone("Central rigid filament", (-.017, -.053, 1.931), (-.009, -.113, 2.299),
         .050, .012, ivory)
    cone("Filament point", (-.009, -.113, 2.299), (-.008, -.126, 2.360),
         .014, .001, ivory)
    oval("Filament vulnerability band", (-.015, -.077, 2.077), (.054, .050, .023), tissue)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "MortarLeech.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Mortared flagstones", (.070, .078, .069), .74, .44)
    bpy.ops.mesh.primitive_plane_add(size=1200)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Catacomb atmosphere")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.14, .18, .20, 1)
    background.inputs[1].default_value = .31
    add_light("Amber key", (-2.3, -2.6, 3.6), 480, (1, .67, .40), 1.8)
    add_light("Cool rim", (2.1, 1.9, 3.4), 470, (.38, .66, 1), 1.7)
    add_light("Collar fill", (1.7, -2.5, 1.8), 128, (.71, .80, 1), 1.4)
    bpy.ops.object.camera_add(location=(3.13, -4.19, 2.36))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 55
    aim(scene.camera, (0, 0, 1.12))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 840
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "MortarLeech.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
