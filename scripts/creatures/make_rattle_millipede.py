"""Blender 4.3+ static Rattle Millipede prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_rattle_millipede.py -- OUTPUT
"""
from math import atan2, cos, sin, tau
from pathlib import Path
import runpy
import sys

import bpy
from mathutils import Vector


def build(output):
    here = Path(__file__).parent
    basics = runpy.run_path(str(here / "make_catacomb_crawler.py"))
    oval, cone, material, finish, add_light, aim = (
        basics[name] for name in ("oval", "tapered", "material", "finish", "add_light", "aim")
    )
    prism = runpy.run_path(str(here / "make_lintel_mantis.py"))["prism"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    cuticle = material("Soot-brown cuticle", (.058, .038, .026), .42, .30)
    joint_skin = material("Copper flexion bands", (.164, .050, .026), .47, .32)
    plates = material("Buried ivory scutes", (.343, .263, .149), .49, .36)
    plates_dark = material("Mineral-backed scutes", (.208, .176, .123), .55, .38)
    fan = material("Oxidized sound plates", (.313, .130, .052), .42, .39)
    dark = material("Black sensory cuticle", (.025, .018, .018), .32, .20)
    eye = material("Warm ocelli", (.381, .206, .052), .23)

    def centerline(t):
        phase = tau * (.91 * t - .15)
        return (
            Vector((.230 * sin(phase), -1.414 + 3.034 * t, .182 - .094 * t)),
            atan2(-.230 * tau * .91 * cos(phase), 3.034),
        )

    def place(center, yaw, offset):
        x, y, z = offset
        return center + Vector((cos(yaw) * x - sin(yaw) * y,
                                sin(yaw) * x + cos(yaw) * y, z))

    for index in range(18):
        t = index / 17
        center, yaw = centerline(t)
        scale = 1 - .63 * t
        segment_skin = oval(f"Flexion segment {index + 1:02}", center,
                            (.222 * scale, .130, .119 * scale), joint_skin)
        segment_skin.rotation_euler.z = yaw
        shell = oval(f"Dorsal segment {index + 1:02}", place(center, yaw, (0, -.020, .070 * scale)),
                     (.245 * scale, .114, .120 * scale), plates if index % 3 else plates_dark)
        shell.rotation_euler.z = yaw
        for side in (-1, 1):
            for pair in (-1, 1):
                hip = place(center, yaw, (side * .168 * scale, .041 * pair, -.043 * scale))
                knee = place(center, yaw, (side * .278 * scale, .041 * pair + .024, -.066 * scale))
                foot = place(center, yaw, (side * .315 * scale, .041 * pair + .058, .006 - center.z))
                cone(f"Leg root {index} {side} {pair}", hip, knee, .024 * scale, .018 * scale, cuticle)
                cone(f"Leg toe {index} {side} {pair}", knee, foot, .018 * scale, .0025, dark)
        if 2 <= index <= 14:
            for side in (-1, 1):
                raised = side == 1
                root = side * .165 * scale
                extension = .195 if raised else .069
                height = (.300 if raised else .089) * scale
                outline = [
                    (root, -.057, .03 * scale), (root + side * extension * .55, -.046, height * .77),
                    (root + side * extension, .046, height + .09),
                    (root + side * extension * .92, .088, height * .53),
                    (root + side * extension * .36, .056, .035),
                ]
                tip_name = "Raised rattle plate" if raised else "Folded rattle plate"
                prism(f"{tip_name} {index + 1:02}",
                      [tuple(place(center, yaw, point)) for point in reversed(outline)],
                      .020 * scale, fan if raised else plates_dark)

    head, yaw = centerline(0)
    cap = oval("Blunt sensory head", place(head, yaw, (0, -.19, .018)), (.216, .210, .138), cuticle)
    cap.rotation_euler.z = yaw
    for side in (-1, 1):
        jaw_root = place(head, yaw, (side * .129, -.237, -.024))
        jaw_hook = place(head, yaw, (side * .100, -.356, -.081))
        cone(f"Feeding palp {side}", jaw_root, jaw_hook, .052, .012, dark)
        for i in range(3):
            point = place(head, yaw, (side * (.128 + .018 * i), -.267 + .029 * i, .081))
            oval(f"Ocellus {side} {i}", point, (.025, .025, .018), eye)
        antenna = [place(head, yaw, (side * x, y, z)) for x, y, z in (
            (.118, -.243, .085), (.168, -.357, .102), (.221, -.468, .072),
        )]
        cone(f"Antenna root {side}", antenna[0], antenna[1], .021, .011, cuticle)
        cone(f"Antenna tip {side}", antenna[1], antenna[2], .012, .002, dark)

    tail, yaw = centerline(1)
    start = place(tail, yaw, (0, .031, .022))
    end = place(tail, yaw, (0, .188, .018))
    cone("Flattened striking tail", start, end, .077, .013, plates_dark)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "RattleMillipede.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Catacomb perimeter stone", (.066, .069, .072), .71, .41)
    bpy.ops.mesh.primitive_plane_add(size=1200)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Catacomb atmosphere")
    scene.world.use_nodes = True
    light = scene.world.node_tree.nodes["Background"]
    light.inputs[0].default_value = (.13, .16, .21, 1)
    light.inputs[1].default_value = .35
    add_light("Warm key", (2.1, -2.7, 3.5), 430, (1, .68, .43), 1.8)
    add_light("Cool rim", (-2.1, 2.3, 3.4), 465, (.43, .65, 1), 1.7)
    add_light("Head fill", (.45, -3.3, 2.4), 135, (.76, .83, 1), 1.4)
    bpy.ops.object.camera_add(location=(3.53, -3.78, 3.02))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 53
    aim(scene.camera, (0, -.03, .24))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "RattleMillipede.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
