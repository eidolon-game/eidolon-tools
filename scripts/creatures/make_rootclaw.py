"""Blender 4.3+ static Rootclaw boss prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_rootclaw.py -- OUTPUT
"""
from pathlib import Path
import runpy
import sys

import bpy
from mathutils import Vector


def build(output):
    basics = runpy.run_path(str(Path(__file__).with_name("make_catacomb_crawler.py")))
    oval, cone, material, finish, add_light, aim = (
        basics[name] for name in ("oval", "tapered", "material", "finish", "add_light", "aim")
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    core = material("Dark living bedrock", (.071, .079, .064), .49, .48)
    stone = material("Rootbound limestone", (.237, .226, .159), .64, .46)
    strata = material("Erased calcite layers", (.369, .334, .236), .61, .44)
    bark = material("Red heartwood", (.106, .040, .019), .58, .55)
    fibers = material("Exposed dry roots", (.248, .106, .052), .55, .46)
    hinge = material("Exposed resin hinge", (.332, .058, .028), .31, .35)
    dark = material("Charred stone tips", (.053, .042, .033), .50, .40)
    amber = material("Dull amber eyes", (.415, .170, .033), .29)

    def rock(name, point, scale, surface):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=point)
        obj = finish(name, surface)
        for vertex in obj.data.vertices:
            x, y, z = vertex.co
            setback = 1 + .09 * x * y + .07 * y * z - .04 * x * z
            vertex.co = (x * scale[0] * setback, y * scale[1] * setback, z * scale[2] * setback)
        for polygon in obj.data.polygons:
            polygon.use_smooth = False
        # Icospheres created by Blender carry generated UV coordinates.
        return obj

    def woody_path(name, points, radii, surface):
        for index, (start, end) in enumerate(zip(points, points[1:])):
            cone(f"{name} {index + 1:02}", start, end, radii[index], radii[index + 1], surface)
            if index + 1 < len(points) - 1:
                radius = radii[index + 1] * 1.04
                oval(f"{name} knot {index + 1:02}", end, (radius, radius, radius), surface)

    oval("Lifted barrel torso", (-.087, .257, 1.442), (.743, .918, .469), core)
    oval("High shoulder saddle", (-.080, -.204, 1.653), (.791, .515, .452), core)
    rock("Stone mantle crown", (-.268, .106, 1.970), (.602, .675, .340), stone)
    rock("Stone mantle haunch", (-.320, .745, 1.739), (.583, .453, .319), stone)
    rock("Stone mantle near buttress", (.498, -.316, 1.801), (.425, .489, .322), strata)
    rock("Stone mantle far buttress", (-.627, -.252, 1.698), (.424, .453, .335), strata)
    rock("Mantle spine shard", (-.285, .401, 2.169), (.230, .485, .195), strata)
    rock("Low frontal faceplate", (-.122, -.701, 1.300), (.451, .291, .269), stone)
    oval("Retractable mandibular sling", (-.117, -.781, 1.058), (.349, .315, .167), hinge)
    rock("Mandible prow", (-.087, -1.044, 1.103), (.305, .244, .149), dark)

    for side in (-1, 1):
        x = -.11 + side * .226
        cone(f"Mandible barb {side}", (x, -.916, 1.087), (x + side * .054, -1.242, 1.127),
             .072, .010, fibers)
        oval(f"Eye trough {side}", (x, -.879, 1.381), (.102, .074, .051), dark)
        oval(f"Eye {side}", (x, -.935, 1.373), (.047, .033, .028), amber)
        for index in range(3):
            y = -.168 + .507 * index
            shoulder = (-.081 + side * (.501 - .035 * index), y, 1.412 - .136 * index)
            elbow = (-.121 + side * (1.078 - .065 * index), y + .124, 1.329 - .193 * index)
            wrist = (-.122 + side * (1.420 - .080 * index), y + .181 + .066 * index, .240)
            foot = (-.109 + side * (1.531 - .076 * index), y + .103 + .061 * index, .045)
            woody_path(f"Strut {side} {index}", [shoulder, elbow, wrist, foot],
                       [.205, .154, .083, .039], bark)
            rock(f"Upright knee cap {side} {index}", elbow, (.184, .208, .217), stone)
            cone(f"Split toe {side} {index}", wrist, (foot[0] - side * .112, foot[1] - .100, .027),
                 .066, .012, dark)

    woody_path("Dorsal root sweep", [(-.648, -.371, 1.746), (-.592, -.411, 2.158),
              (-.279, -.151, 2.328), (.158, .278, 2.377), (.244, .783, 2.321),
              (.102, 1.183, 2.446), (-.008, 1.341, 2.575)],
              [.101, .122, .128, .103, .078, .049, .005], bark)
    woody_path("Dorsal root fork", [(-.279, -.151, 2.328), (-.380, .369, 2.390),
              (-.599, .765, 2.386), (-.787, .967, 2.518)], [.096, .077, .048, .005], fibers)
    woody_path("Shoulder root clasp", [(.153, -.141, 1.875), (.376, -.478, 2.044),
              (.642, -.371, 2.114), (.621, -.043, 1.838), (.541, .194, 1.570)],
              [.055, .094, .077, .054, .012], bark)
    woody_path("Rear root fan", [(-.501, .404, 1.931), (-.576, .723, 1.973),
              (-.545, 1.051, 1.809), (-.681, 1.316, 1.626)],
              [.062, .078, .068, .010], fibers)

    # The chela is a lifted stone mass held on exposed radial roots.
    shoulder = (.605, -.325, 1.456)
    joint = (1.103, -.551, 1.361)
    palm = (1.625, -.904, 1.529)
    oval("Heavy side exposed hinge", shoulder, (.248, .260, .260), hinge)
    woody_path("Heavy chela frame", [shoulder, joint, palm], [.191, .250, .310], bark)
    rock("Heavy arm buttress", (1.153, -.565, 1.441), (.324, .260, .293), stone)
    rock("Heavy chela broken keystone", (1.737, -.868, 1.609), (.541, .454, .467), stone)
    rock("Heavy chela pale strike face", (1.947, -1.088, 1.530), (.357, .328, .359), strata)
    fixed = [(1.991, -1.089, 1.583), (2.271, -1.360, 1.430),
             (2.573, -1.560, 1.151), (2.625, -1.787, .955)]
    moving = [(1.590, -1.019, 1.464), (1.606, -1.382, 1.226),
              (1.861, -1.583, .980), (2.135, -1.674, .875)]
    for label, line in (("Heavy curved fixed jaw", fixed), ("Heavy curved mobile jaw", moving)):
        woody_path(label, line, [.233, .211, .131, .013], dark)
        rock(f"{label} stone lip", line[1], (.209, .188, .181), stone)
        rock(f"{label} strike tooth", line[2], (.121, .112, .138), strata)
    woody_path("Chela binding root", [(1.339, -.745, 1.866), (1.652, -1.018, 2.056),
              (1.906, -1.150, 1.971), (2.124, -1.079, 1.670), (2.007, -.872, 1.422)],
              [.041, .077, .074, .053, .013], fibers)
    woody_path("Chela binding fork", [(1.906, -1.150, 1.971), (2.101, -1.308, 1.786),
              (2.354, -1.518, 1.547), (2.573, -1.582, 1.212)],
              [.060, .054, .039, .007], bark)
    oval("Light appendage hinge", (-.501, -.557, 1.205), (.144, .169, .126), hinge)
    woody_path("Light bracing forelimb", [(-.501, -.557, 1.205), (-.891, -.673, 1.096),
              (-1.112, -.923, .919)], [.119, .103, .082], bark)
    for index in range(2):
        woody_path(f"Light bracing hook {index + 1}", [
            (-1.112 - .087 * index, -.923, .919), (-1.137 - .070 * index, -1.132, .802),
            (-1.042 - .170 * index, -1.266, .696),
        ], [.066, .050, .007], dark)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "Rootclaw.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Antechamber stone", (.064, .069, .062), .71, .43)
    bpy.ops.mesh.primitive_plane_add(size=1500)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Antechamber air")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.12, .17, .20, 1)
    background.inputs[1].default_value = .33
    add_light("Warm torch key", (-3.5, -3.6, 5.5), 1000, (1, .70, .44), 2.5)
    add_light("Cold crown rim", (3.3, 3.5, 4.8), 1200, (.37, .66, 1), 2.3)
    add_light("Sweep face fill", (4.1, -4.7, 2.8), 380, (.77, .87, 1), 2)
    bpy.ops.object.camera_add(location=(5.44, -8.63, 4.19))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 58
    aim(scene.camera, (.51, -.17, 1.23))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "Rootclaw.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
