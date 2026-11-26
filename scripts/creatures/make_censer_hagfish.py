"""Blender 4.3+ static Censer Hagfish prototype.

Run: blender -b -t 4 --python-exit-code 1 --python make_censer_hagfish.py -- OUTPUT
"""
from math import cos, sin, tau
from pathlib import Path
import runpy
import sys

import bpy


def loft(name, sections, surface, sides=32, caps=True):
    """Build an elliptical loft along Y, keeping a continuous edge flow."""
    vertices = [
        (x + width * cos(tau * j / sides), y, z + height * sin(tau * j / sides))
        for x, y, z, width, height in sections
        for j in range(sides)
    ]
    faces = [
        (i * sides + j, i * sides + (j + 1) % sides,
         (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j)
        for i in range(len(sections) - 1)
        for j in range(sides)
    ]
    if caps:
        faces.extend((
            tuple(range(sides - 1, -1, -1)),
            tuple(range(len(vertices) - sides, len(vertices))),
        ))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(surface)
    uv = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
        for corner, loop in enumerate(polygon.loop_indices):
            row, column = divmod(mesh.loops[loop].vertex_index, sides)
            if len(polygon.vertices) == 4:
                start = polygon.vertices[0] % sides
                u = (start + (corner in (1, 2))) / sides
                value = (u, row / (len(sections) - 1))
            else:
                angle = tau * column / sides
                value = (.5 + .5 * cos(angle), .5 + .5 * sin(angle))
            uv.data[loop].uv = value
    if sections[1][1] > sections[0][1]:
        mesh.flip_normals()
    return obj


def build(output):
    helpers = runpy.run_path(str(Path(__file__).with_name("make_catacomb_crawler.py")))
    oval, cone, material, finish, add_light, aim = (
        helpers[name] for name in ("oval", "tapered", "material", "finish", "add_light", "aim")
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    skin = material("Oil-grey ribbon hide", (.065, .116, .123), .31, .33)
    ridge = material("Rust-red dorsal relief", (.141, .058, .033), .46, .29)
    lip = material("Wet funnel lip", (.191, .055, .040), .25, .30)
    throat = material("Wet throat fascia", (.19, .021, .016), .31, .30)
    sac = material("Taut sulfur gland", (.26, .088, .037), .27, .31)
    fold = material("Throat fold", (.109, .028, .017), .32, .30)
    bone = material("Ivory sensory barbs", (.37, .26, .13), .44, .19)
    darkness = material("Funnel interior", (.008, .005, .006), .55)

    ribbon = [
        (-.033, -.695, .417, .225, .146),
        (-.008, -.523, .395, .301, .161),
        (.074, -.327, .300, .320, .138),
        (.098, -.091, .240, .285, .114),
        (.066, .134, .192, .277, .100),
        (-.044, .356, .168, .270, .090),
        (-.178, .586, .147, .229, .073),
        (-.255, .745, .130, .151, .057),
        (-.219, .895, .116, .083, .037),
        (-.171, 1.002, .115, .049, .019),
        (-.103, 1.070, .121, .006, .009),
    ]
    body = loft("Flattened ribbon body", ribbon, skin)
    smooth = body.modifiers.new("Body curve", "SUBSURF")
    smooth.levels = 2
    smooth.render_levels = 2
    loft("Raised dorsal seam", [(x, y, z + .94 * h, .20 * w, .18 * h)
                                for x, y, z, w, h in ribbon], ridge, 16)
    for side in (-1, 1):
        fin = [(x + side * w * .83, y, z - .24 * h, w * .27, h * .20)
               for x, y, z, w, h in ribbon]
        loft(f"Lateral ribbon fin {side}", fin, ridge, 16)
        for i, (x, y, z, w, h) in enumerate(ribbon[2:8]):
            oval(f"Gill slit {side} {i}", (x + side * w * .86, y, z + .34 * h),
                 (.025, .047, .020), throat)

    # One continuous surface turns from the outer collar into the concave funnel.
    mouth = [
        (-.037, -.610, .435, .216, .144), (-.052, -.716, .468, .233, .177),
        (-.057, -.824, .489, .267, .198), (-.057, -.965, .516, .288, .222),
        (-.057, -1.037, .525, .257, .198), (-.056, -1.053, .523, .223, .167),
        (-.054, -.988, .512, .200, .148), (-.051, -.866, .489, .129, .099),
        (-.048, -.764, .468, .055, .043), (-.048, -.731, .465, .007, .009),
    ]
    funnel = loft("Concave feeding funnel", mouth, lip, 48, caps=False)
    for color in (skin, throat, darkness):
        funnel.data.materials.append(color)
    for polygon in funnel.data.polygons:
        ring = polygon.index // 48
        polygon.material_index = (
            1 if ring == 0 else 0 if ring < 5 else 2 if ring < 8 else 3
        )
    relief = funnel.modifiers.new("Rounded lip", "SUBSURF")
    relief.levels = 1
    relief.render_levels = 1
    for i in range(12):
        angle = tau * i / 12
        x, z = cos(angle), sin(angle)
        cone(f"Funnel inner barb {i}", (-.056 + .200 * x, -1.008, .522 + .150 * z),
             (-.055 + .163 * x, -1.071, .522 + .117 * z), .013, .0015, bone)
    for i, x in enumerate((-.208, -.052, .112), start=1):
        z = .166 + .014 * (i != 2)
        oval(f"Throat pressure sac {i}", (x, -.629, z), (.074, .116, .127), sac)
        cone(f"Sac duct {i}", (x, -.666, z + .065), (x * .64, -.458, .293),
             .044, .024, fold)
        for side in (-1, 1):
            cone(f"Sac relief {i} {side}", (x + side * .050, -.667, z - .077),
                 (x + side * .054, -.579, z + .074), .009, .005, lip)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output / "CenserHagfish.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )

    floor = material("Damp drainage stone", (.078, .080, .066), .62, .40)
    bpy.ops.mesh.primitive_plane_add(size=1200)
    finish("Preview floor", floor)
    scene.world = bpy.data.worlds.new("Catacomb air")
    scene.world.use_nodes = True
    light = scene.world.node_tree.nodes["Background"]
    light.inputs[0].default_value = (.13, .18, .21, 1)
    light.inputs[1].default_value = .33
    add_light("Warm torch", (-2.1, -2.4, 2.9), 340, (1, .65, .36), 1.7)
    add_light("Cold drain rim", (1.4, 1.7, 2.6), 410, (.40, .66, 1), 1.7)
    add_light("Mouth fill", (1.6, -2.4, 1.3), 102, (.70, .83, 1), 1.2)
    bpy.ops.object.camera_add(location=(2.55, -3.22, 1.27))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 58
    aim(scene.camera, (0, -.07, .35))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "CenserHagfish.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    output_dir = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build(output_dir)
