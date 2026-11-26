"""Blender 4.3+ static Root Stalker prototype, ID abyss_forest_stalker.

Run: blender -b -t 4 --python-exit-code 1 --python make_root_stalker.py -- OUTPUT
"""
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
    loft = runpy.run_path(str(here / "make_censer_hagfish.py"))["loft"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    bark = material("Split ironwood bark", (.127, .063, .029), .64, .53)
    pale = material("Weathered grey bark", (.218, .176, .103), .70, .48)
    tendons = material("Amber exposed membrane", (.274, .067, .028), .43, .30)
    hide = material("Root-stock core", (.055, .032, .019), .56, .40)
    horn = material("Black climbing hooks", (.039, .029, .021), .48, .31)
    moss = material("Buried olive crust", (.095, .127, .042), .80, .40)
    eyes = material("Pale resin eyes", (.503, .311, .080), .31)

    def root(name, points, radii, surface):
        for i, (start, end) in enumerate(zip(points, points[1:])):
            cone(f"{name} {i + 1}", start, end, radii[i], radii[i + 1], surface)
            if i + 1 < len(points) - 1:
                knot = radii[i + 1] * 1.01
                oval(f"{name} knot {i + 1}", end, (knot, knot, knot), surface)

    trunk = loft("Sloped stalking torso", [
        (0, -.742, 1.922, .277, .191), (-.021, -.584, 2.020, .379, .307),
        (-.029, -.293, 2.070, .532, .390), (-.018, .041, 1.996, .429, .368),
        (.018, .342, 1.755, .339, .275), (.025, .681, 1.576, .323, .252),
        (.039, .866, 1.494, .182, .133),
    ], hide, sides=24)
    modifier = trunk.modifiers.new("Tensioned body silhouette", "SUBSURF")
    modifier.levels = modifier.render_levels = 2
    oval("High neck tendons", (-.017, -.612, 2.109), (.291, .359, .273), tendons)
    oval("Narrow pelvis", (.022, .600, 1.517), (.351, .407, .289), bark)

    for side in (-1, 1):
        for index in range(6):
            y = -.456 + .214 * index
            z = 2.226 - max(index - 2, 0) * .142
            plate = oval(f"Bark laminate {side} {index}", (side * (.229 - .018 * index), y, z),
                         (.171, .173, .183), pale if index % 3 else moss)
            plate.rotation_euler.z = .22 * side
            root(f"Strained flank fibre {side} {index}", [
                (side * (.259 - .020 * index), y - .040, z + .037),
                (side * (.432 - .020 * index), y + .032, z - .205),
                (side * (.272 - .020 * index), y + .055, z - .376),
            ], [.054, .046, .025], bark)
        front_hip = (side * .346, -.295, 2.025)
        front_elbow = (side * (.759 + side * .041), -.371 + side * .064, 1.427)
        front_wrist = (side * (.801 + side * .052), -.612 + side * .182, .286)
        front_foot = (side * (.829 + side * .051), -.792 + side * .182, .126)
        back_hip = (side * .268, .620, 1.553)
        back_knee = (side * (.613 - side * .033), .427, .930 + side * .045)
        back_hock = (side * (.650 - side * .025), .966 + side * .122, .487)
        back_foot = (side * (.735 - side * .020), .992 + side * .147, .121)
        oval(f"Forelimb shoulder shield {side}", front_hip, (.300, .311, .318), bark)
        root(f"Long forelimb {side}", [front_hip, front_elbow, front_wrist, front_foot],
             [.197, .146, .072, .061], bark)
        oval(f"Forelimb joint membrane {side}", front_elbow, (.179, .183, .175), tendons)
        oval(f"Forelimb knuckle shield {side}", front_wrist, (.124, .141, .137), pale)
        root(f"Folded hind limb {side}", [back_hip, back_knee, back_hock, back_foot],
             [.177, .143, .089, .060], bark)
        oval(f"Hind knee joint membrane {side}", back_knee, (.169, .176, .154), tendons)
        oval(f"Hind hock joint membrane {side}", back_hock, (.101, .108, .113), tendons)
        for i, foot in enumerate((front_foot, back_foot)):
            for digit in range(3):
                x = foot[0] + .076 * (digit - 1)
                offset = .055 * abs(digit - 1)
                root(f"Ground hook {side} {i} {digit}", [
                    (x, foot[1], foot[2]),
                    (x + side * .023, foot[1] - .224 + offset, .091),
                    (x + side * .012, foot[1] - .268 + offset, .013),
                ], [.050, .035, .005], horn)
        root(f"Scapular rake {side}", [
            (side * .264, -.405, 2.220), (side * .397, -.257, 2.576),
            (side * .498, -.155, 2.815), (side * .573, -.001, 2.950),
        ], [.105, .083, .043, .006], pale)

    head = loft("Split wooden face mask", [
        (-.013, -1.256, 1.828, .098, .076), (-.014, -1.198, 1.943, .176, .147),
        (-.016, -1.092, 2.059, .249, .210), (-.018, -.897, 2.117, .271, .259),
        (-.018, -.719, 2.103, .165, .171),
    ], pale, sides=12)
    for face in head.data.polygons:
        face.use_smooth = False
    oval("Long split mandible", (-.011, -1.121, 1.773), (.187, .252, .101), hide)
    for side in (-1, 1):
        eye_center = (side * .153 - .018, -1.114, 2.100)
        oval(f"Cut eye recess {side}", eye_center, (.077, .061, .084), horn)
        oval(f"Resin eye {side}", (eye_center[0], -1.161, 2.113), (.038, .028, .039), eyes)
        root(f"Jaw hook {side}", [
            (side * .114, -1.157, 1.782), (side * .184, -1.349, 1.750),
            (side * .192, -1.431, 1.854),
        ], [.073, .045, .007], horn)
        root(f"Facial bark crest {side}", [
            (side * .166, -.964, 2.135), (side * .238, -.941, 2.381),
            (side * .319, -.784, 2.506), (side * .354, -.626, 2.560),
        ], [.073, .054, .032, .005], bark)
    root("Trailing sweep root", [
        (.044, .795, 1.465), (.167, 1.132, 1.235), (.473, 1.446, 1.121),
        (.656, 1.786, 1.093), (.711, 2.039, 1.163), (.662, 2.238, 1.080),
    ], [.132, .111, .082, .057, .031, .005], bark)
    root("Trailing sweep fork", [
        (.473, 1.446, 1.121), (.318, 1.756, 1.004), (.284, 1.922, .925),
    ], [.063, .039, .005], pale)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "RootStalker.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Compressed forest litter", (.072, .079, .055), .76, .41)
    bpy.ops.mesh.primitive_plane_add(size=1500)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Buried forest air")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (.11, .17, .15, 1)
    bg.inputs[1].default_value = .32
    add_light("Warm forked-spore key", (-3.0, -4.1, 5.1), 820, (1, .72, .43), 2.5)
    add_light("Green vault rim", (4.0, 3.3, 4.4), 1050, (.42, .75, .67), 2.5)
    add_light("Face and tendon fill", (4.1, -4.4, 3.0), 382, (.69, .79, 1), 1.9)
    bpy.ops.object.camera_add(location=(5.88, -7.15, 3.86))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 65
    aim(scene.camera, (.13, .18, 1.44))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "RootStalker.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
