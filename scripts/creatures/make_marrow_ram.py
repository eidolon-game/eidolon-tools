"""Blender 4.3+ static Marrow Ram prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_marrow_ram.py -- OUTPUT
"""
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

    hide = material("Oxidized marrow hide", (.112, .065, .041), .49, .37)
    flank = material("Exposed amber fascia", (.259, .104, .045), .42, .28)
    bone = material("Calcified shoulder plates", (.460, .379, .249), .59, .42)
    keratin = material("Weathered cranial shield", (.211, .167, .123), .49, .43)
    worn = material("Pale impact edge", (.450, .346, .209), .47, .30)
    dark = material("Burnished hoof", (.031, .026, .022), .34, .27)
    amber = material("Low-set amber eye", (.365, .119, .020), .25)

    oval("Low barrel body", (0, .19, .784), (.52, .828, .346), hide)
    oval("Forequarter hump", (0, -.424, .948), (.655, .461, .437), hide)
    oval("Hindquarter hump", (0, .658, .970), (.565, .469, .366), hide)
    oval("Low neck", (0, -.780, .859), (.423, .409, .279), flank)
    oval("Underslung muzzle", (0, -.978, .558), (.244, .292, .127), dark)

    for side in (-1, 1):
        for index in range(5):
            y = -.277 + index * .216
            rib = oval(f"Flank plate {side} {index}", (side * (.49 - .028 * abs(index - 2)), y, .872),
                       (.123, .145, .232), bone)
            rib.rotation_euler.x = -.19 + .09 * index
            rib.rotation_euler.y = side * -.39
        for index, (y, z, width) in enumerate(((-.564, 1.313, .411), (-.335, 1.371, .434),
                                                (.543, 1.303, .394), (.746, 1.299, .354))):
            tapered_plate = oval(f"Dorsal collar {side} {index}", (side * .194, y, z),
                                 (width, .192, .108), bone)
            tapered_plate.rotation_euler.y = -side * .23
        for end in (0, 1):
            y = -.565 if end == 0 else .762
            hip = (side * (.467 if end == 0 else .431), y, .923)
            knee = (side * (.716 if end == 0 else .616), y + (-.063 if end == 0 else .139), .515)
            hoof = (side * (.784 if end == 0 else .689), y + (-.147 if end == 0 else .035), .122)
            oval(f"Shoulder muscle {side} {end}", hip, (.259, .272, .300), flank)
            cone(f"Upper leg {side} {end}", hip, knee, .180, .121, hide)
            cone(f"Lower leg {side} {end}", knee, hoof, .119, .076, keratin)
            oval(f"Kneecap {side} {end}", knee, (.123, .135, .122), bone)
            for toe in (-1, 1):
                oval(f"Cloven hoof {side} {end} {toe}", (hoof[0] + toe * .061, hoof[1] - .034, .089),
                     (.074, .149, .084), dark)
        oval(f"Orbital ridge {side}", (side * .369, -.921, .749), (.104, .145, .100), dark)
        oval(f"Eye {side}", (side * .423, -.986, .748), (.039, .056, .032), amber)
        cone(f"Shield shoulder ridge {side}", (side * .399, -.683, 1.279),
             (side * .534, -.522, 1.502), .115, .020, worn)
        cone(f"Offset brow crest {side}", (side * .199, -.910, 1.230),
             (side * .285, -.721, 1.442 + .025 * side), .079, .013, worn)
        cone(f"Jaw tusk {side}", (side * .193, -1.052, .560),
             (side * .293, -1.222, .620), .062, .013, worn)

    # Section widths taper toward the low impact edge and broaden above the brow.
    cranial = [
        (0, -1.430, .673, .057, .053),
        (0, -1.351, .743, .212, .117),
        (0, -1.230, .845, .345, .188),
        (0, -1.044, .946, .451, .245),
        (0, -.844, 1.016, .492, .270),
        (0, -.670, 1.026, .454, .236),
        (0, -.605, .978, .271, .128),
    ]
    shield = loft("Cranial wedge shield", cranial, keratin, 12)
    shield.data.materials.append(worn)
    for face in shield.data.polygons:
        face.use_smooth = False
        face.material_index = int(face.index < 12)
    bevel = shield.modifiers.new("Worn impact bevel", "BEVEL")
    bevel.width = .017
    bevel.segments = 2
    cone("Forehead median ridge", (0, -1.276, .891), (0, -.758, 1.315), .025, .068, bone)
    cone("Short tail root", (0, 1.022, .852), (0, 1.180, .716), .085, .047, hide)
    cone("Short tail tip", (0, 1.180, .716), (.092, 1.263, .635), .047, .008, hide)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "MarrowRam.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Calcite passage", (.073, .083, .086), .69, .39)
    bpy.ops.mesh.primitive_plane_add(size=1200)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Passage air")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.13, .17, .20, 1)
    background.inputs[1].default_value = .30
    add_light("Warm key", (-2.4, -2.6, 3.5), 460, (1, .70, .43), 1.9)
    add_light("Cold outline", (1.8, 2.9, 3.5), 550, (.39, .63, 1), 1.8)
    add_light("Flank fill", (2.4, -1.0, 1.8), 145, (.71, .82, 1), 1.6)
    bpy.ops.object.camera_add(location=(3.25, -4.10, 2.12))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 56
    aim(scene.camera, (0, -.03, .77))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "MarrowRam.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
