"""Blender 4.3+ static Vault Pincer prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_vault_pincer.py -- OUTPUT
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

    shell = material("Veined vault limestone", (.229, .186, .119), .54, .38)
    edge = material("Abraded calcite", (.377, .324, .240), .58, .37)
    weathered = material("Old black scutes", (.066, .065, .051), .47, .38)
    chitin = material("Russet load-bearing chitin", (.178, .067, .037), .37, .32)
    exposed = material("Soft hinge fascia", (.268, .055, .040), .35, .26)
    charcoal = material("Dark gripping surfaces", (.033, .026, .019), .39, .28)
    amber = material("Dim amber sensory beads", (.427, .224, .037), .26)

    def slab(name, sections, surface, rim, bevel_size):
        plate = loft(name, sections, surface, sides=10)
        plate.data.materials.append(rim)
        for face in plate.data.polygons:
            face.use_smooth = False
            face.material_index = int(face.index % 10 in (5, 9))
        bevel = plate.modifiers.new("Stone shell bevel", "BEVEL")
        bevel.width = bevel_size
        bevel.segments = 2
        return plate

    oval("Flattened inner body", (0, .117, .533), (.510, .540, .191), chitin)
    slab("Slab carapace", [
        (0, -.418, .604, .324, .108), (-.032, -.305, .671, .564, .169),
        (-.030, -.029, .710, .655, .191), (-.026, .300, .695, .626, .164),
        (-.042, .529, .640, .468, .108), (-.045, .648, .555, .213, .063),
    ], shell, edge, .018)
    for index, (y, width, z) in enumerate(((-.241, .499, .794), (-.025, .559, .849),
                                            (.191, .541, .831), (.395, .438, .761))):
        dorsal = oval(f"Carapace buttress {index + 1}", (-.022, y, z),
                       (width, .092, .057), edge if index % 2 else weathered)
        dorsal.rotation_euler.z = -.033 + .021 * index
    for side in (-1, 1):
        for index in range(4):
            y = -.234 + .201 * index
            root = (side * .455, y, .507)
            hinge = (side * (.704 + .035 * (index % 2)), y + .067, .507 - .020 * index)
            foot = (side * (.946 - .044 * index), y + (.113 * index - .125), .056)
            oval(f"Leg socket {side} {index}", root, (.114, .097, .106), exposed)
            cone(f"Leg proximal shell {side} {index}", root, hinge, .086, .065, chitin)
            oval(f"Leg hinge {side} {index}", hinge, (.079, .079, .076), shell)
            cone(f"Leg shank {side} {index}", hinge, foot, .068, .030, weathered)
            cone(f"Foot hook {side} {index}", foot,
                 (side * (abs(foot[0]) - .042), foot[1] - .047, .014), .034, .004, charcoal)
        stalk = (side * .182, -.406, .529)
        tip = (side * .251, -.527, .619)
        cone(f"Eye stalk {side}", stalk, tip, .051, .029, chitin)
        oval(f"Eye socket {side}", tip, (.062, .065, .048), charcoal)
        oval(f"Sensory bead {side}", (tip[0], tip[1] - .035, tip[2]), (.039, .035, .029), amber)

    # The raised chela has a broad impact slab and two distinct fingers.
    large_hinge = (.652, -.331, .621)
    large_elbow = (.923, -.359, .752)
    large_wrist = (1.015, -.595, .798)
    oval("Large chela shoulder", large_hinge, (.174, .134, .142), exposed)
    cone("Large chela upper arm", large_hinge, large_elbow, .141, .116, weathered)
    cone("Large chela forearm", large_elbow, large_wrist, .121, .148, chitin)
    palm = [
        (1.016, -1.005, .824, .121, .119), (1.012, -.936, .862, .230, .208),
        (1.036, -.812, .879, .274, .216), (1.064, -.663, .836, .236, .182),
        (1.035, -.557, .795, .132, .126),
    ]
    slab("Large chela impact palm", palm, shell, edge, .014)
    slab("Large chela fixed sweeping finger", [
        (1.112, -1.206, .752, .014, .026), (1.234, -1.151, .793, .062, .078),
        (1.255, -1.059, .844, .105, .110), (1.192, -.953, .855, .112, .123),
    ], shell, charcoal, .010)
    slab("Large chela mobile counterfinger", [
        (.919, -1.154, .729, .016, .021), (.792, -1.085, .766, .063, .072),
        (.812, -.975, .811, .095, .111), (.883, -.903, .826, .112, .115),
    ], edge, charcoal, .009)
    for index, (x, y, z) in enumerate(((1.134, -1.089, .808), (1.159, -1.024, .827),
                                         (.889, -1.026, .798), (.928, -.976, .823))):
        dx = .048 if index > 1 else -.048
        cone(f"Inner tooth {index + 1}", (x, y, z), (x + dx, y - .018, z - .027),
             .027, .004, charcoal)

    light_hinge = (-.482, -.243, .506)
    light_elbow = (-.696, -.422, .520)
    light_wrist = (-.695, -.613, .494)
    oval("Light appendage exposed hinge", light_hinge, (.115, .105, .102), exposed)
    cone("Light appendage upper arm", light_hinge, light_elbow, .079, .056, chitin)
    cone("Light appendage forearm", light_elbow, light_wrist, .061, .067, weathered)
    oval("Light appendage palm", (-.695, -.691, .488), (.088, .147, .076), shell)
    for index, side in enumerate((-1, 1)):
        root = (-.695 + side * .057, -.751, .493)
        joint = (-.695 + side * .086, -.858, .480)
        tip = (-.695 + side * .032, -.918, .466)
        cone(f"Light appendage finger base {index + 1}", root, joint, .035, .026, shell)
        cone(f"Light appendage finger tip {index + 1}", joint, tip, .025, .004, charcoal)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "VaultPincer.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Vault flagstone", (.066, .075, .075), .71, .38)
    bpy.ops.mesh.primitive_plane_add(size=1200)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Vault air")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.13, .16, .20, 1)
    background.inputs[1].default_value = .32
    add_light("Torch key", (-2.3, -2.5, 3.0), 360, (1, .67, .41), 1.65)
    add_light("Cold vault rim", (2.5, 2.0, 3.1), 415, (.39, .66, 1), 1.65)
    add_light("Chela fill", (2.1, -2.8, 2.1), 130, (.70, .82, 1), 1.25)
    bpy.ops.object.camera_add(location=(2.62, -3.91, 2.14))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 56
    aim(scene.camera, (.15, -.23, .49))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "VaultPincer.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
