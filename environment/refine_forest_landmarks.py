"""Refine the Buried Forest arch and Vein Overlook with exported detail.

Run Blender in background with this script, then the asset output directory after --.
The existing EIDOLON GLBs supply the original silhouettes. All added geometry and PBR
maps are generated here from deterministic numeric seeds.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "previews" / "buried-forest"
ASSETS = {
    "buried_forest_root_arch": ROOT / "buried_forest_root_arch.glb",
    "vein_overlook_balcony": ROOT / "vein-overlook" / "vein_overlook_balcony.glb",
}
ARCH_SPINE = (
    (-1.14, 0.00, .28), (-1.17, .05, .85), (-1.12, .02, 1.49),
    (-1.13, -.05, 2.19), (-1.02, .01, 2.83), (-.71, .12, 3.37),
    (-.24, .09, 3.67), (.29, .17, 3.60), (.70, .11, 3.26),
    (.99, -.01, 2.77), (1.13, .08, 2.16), (1.17, .01, 1.39),
    (1.14, -.07, .75), (1.17, .01, .23),
)
PORTAL = ((-.80, .80), (-1.30, .68), (.015, 2.70))


def noise(rng, u, v, nx, ny):
    values = rng.uniform(0, 1, (ny, nx))
    x, y = u * nx, v * ny
    ix, iy = x.astype(np.int32), y.astype(np.int32)
    fx, fy = x - ix, y - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = values[iy % ny, ix % nx] * (1 - fx) + values[iy % ny, (ix + 1) % nx] * fx
    b = values[(iy + 1) % ny, ix % nx] * (1 - fx) + values[(iy + 1) % ny, (ix + 1) % nx] * fx
    return a * (1 - fy) + b * fy


def texture_maps(kind, size=768):
    rng = np.random.default_rng({"bark": 19517, "slate": 89105, "tread": 71262}[kind])
    v, u = np.mgrid[:size, :size] / size
    coarse = noise(rng, u, v, 8, 8)
    mid = noise(rng, u, v, 37, 31)
    grit = noise(rng, u, v, 205, 173)
    if kind == "bark":
        warp = u + .051 * (noise(rng, u, v, 12, 8) - .5) + .013 * np.sin(math.tau * (v * 3 + u * 4))
        grain_breaks = noise(rng, u, v, 55, 28)
        splits = np.clip((grain_breaks - .26) * 2.2, 0, 1)
        fissure = ((.5 + .5 * np.cos(math.tau * (warp * 43 + .45 * mid))) ** 16) * splits
        fibers = np.sin(math.tau * (warp * 146 + .22 * grit)) * .5 + .5
        fray = noise(rng, u, v, 64, 12)
        scale_edges = (.5 + .5 * np.cos(math.tau * (v * 24 + 3.2 * mid))) ** 18
        scale_edges *= np.clip((fray - .37) * 2.8, 0, 1)
        field = (.51 + .36 * coarse + .25 * mid + .05 * fibers) * (1 - .71 * fissure - .20 * scale_edges)
        hue = (.192 + .13 * fray, .11 + .085 * fray, .067 + .064 * coarse)
        height = .00031 * fibers + .0018 * mid + .0014 * fray - .0028 * fissure - .0014 * scale_edges + .00038 * grit
        roughness = .72 + .17 * fray + .06 * fissure - .06 * fibers
    elif kind == "slate":
        warp = v + .018 * (noise(rng, u, v, 8, 6) - .5)
        seam = (.5 + .5 * np.cos(math.tau * (25 * warp + .29 * mid))) ** 19
        seam *= np.clip((noise(rng, u, v, 29, 22) - .13) * 2.2, 0, 1)
        chips = np.maximum(0, noise(rng, u, v, 16, 23) - .63)
        fissure = (.5 + .5 * np.cos(math.tau * (17 * u + 13 * v + .8 * coarse))) ** 24
        field = (.62 + .27 * coarse + .21 * mid + .17 * grit) * (1 - .54 * seam - .18 * fissure)
        hue = (.247 + .16 * chips, .269 + .11 * coarse, .286 + .08 * coarse)
        height = .00062 * grit + .0012 * mid + .0016 * chips - .0014 * seam - .0005 * fissure
        roughness = .78 + .12 * coarse - .10 * grit + .07 * seam
    else:
        patches = noise(rng, u, v, 12, 11)
        toolmarks = (.5 + .5 * np.sin(math.tau * (31 * u + 17 * v + 1.1 * mid))) ** 27
        toolmarks *= np.clip((patches - .46) * 3, 0, .85)
        grain = np.maximum(0, grit - .67)
        field = .58 + .19 * coarse + .17 * mid + .15 * patches - .12 * toolmarks
        hue = (.273 + .24 * grain, .255 + .23 * grain, .217 + .21 * grain)
        height = .00086 * grit + .00096 * mid + .0014 * grain - .00021 * toolmarks
        roughness = .86 + .07 * coarse - .12 * patches
    color = np.stack([np.clip(channel * field, 0, 1) for channel in hue], axis=-1)
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * size / 2
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * size / 2
    normal = np.stack((-dx, -dy, np.ones_like(dx)), axis=-1)
    normal = .5 + .5 * normal / np.linalg.norm(normal, axis=-1, keepdims=True)
    orm = np.stack((np.ones_like(roughness), np.clip(roughness, 0, 1), np.zeros_like(roughness)), axis=-1)
    return {"Albedo": color, "Normal": normal, "ORM": orm}


def packed_image(name, pixels, output, is_color):
    height, width, _ = pixels.shape
    image = bpy.data.images.new(name, width=width, height=height, alpha=False)
    image.colorspace_settings.name = "sRGB" if is_color else "Non-Color"
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[:, :, :3] = pixels
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(output / f"{name}.png")
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def material(name, images=None, color=(.12, .07, .037), roughness=.86):
    surface = bpy.data.materials.new(name)
    surface.diffuse_color = (*color, 1)
    surface.use_nodes = True
    nodes = surface.node_tree.nodes
    links = surface.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    if images:
        sources = {}
        for channel, image in images.items():
            texture = nodes.new("ShaderNodeTexImage")
            texture.label = channel
            texture.image = image
            sources[channel] = texture.outputs["Color"]
        links.new(sources["Albedo"], shader.inputs["Base Color"])
        packed = nodes.new("ShaderNodeSeparateColor")
        links.new(sources["ORM"], packed.inputs["Color"])
        links.new(packed.outputs["Green"], shader.inputs["Roughness"])
        links.new(packed.outputs["Blue"], shader.inputs["Metallic"])
        normal = nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value = .8
        links.new(sources["Normal"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return surface


def build_mesh(name, vertices, faces, surface, uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(surface)
    if uvs:
        layer = data.uv_layers.new(name="Detail UV")
        for loop in data.loops:
            layer.data[loop.index].uv = uvs[loop.vertex_index]
    return obj


def world_triangles(obj):
    obj.data.calc_loop_triangles()
    return [tuple(obj.matrix_world @ obj.data.vertices[i].co for i in tri.vertices)
            for tri in obj.data.loop_triangles]


def tree_for(objects):
    vertices, triangles = [], []
    for obj in objects:
        for face in world_triangles(obj):
            start = len(vertices)
            vertices.extend(face)
            triangles.append((start, start + 1, start + 2))
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True)


def clip_polygon(poly, axis, boundary, direction):
    result = []
    for current, previous in zip(poly, poly[-1:] + poly[:-1]):
        a = direction * (previous[axis] - boundary)
        b = direction * (current[axis] - boundary)
        if (a < 0) != (b < 0):
            result.append(previous.lerp(current, a / (a - b)))
        if b >= 0:
            result.append(current)
    return result


def intersects_bounds(face, bounds):
    polygon = list(face)
    for axis, (low, high) in enumerate(bounds):
        polygon = clip_polygon(polygon, axis, low, 1)
        if polygon:
            polygon = clip_polygon(polygon, axis, high, -1)
        if not polygon:
            return False
    return True


def clear_arch(objects):
    # Move the old footings out of the native 1.60 m portal without changing the crown.
    for obj in objects:
        matrix, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            point = matrix @ vertex.co
            if point.z <= 2.735 and abs(point.x) < .841:
                point.x = math.copysign(.841, point.x)
                vertex.co = inverse @ point
    bpy.context.view_layer.update()


def project_uv(obj, scale):
    layer = obj.data.uv_layers.active or obj.data.uv_layers.new(name="Stone UV")
    axes = obj.matrix_world.to_3x3()
    for poly in obj.data.polygons:
        normal = axes @ poly.normal
        fixed = max(range(3), key=lambda axis: abs(normal[axis]))
        i, j = ((1, 2), (0, 2), (0, 1))[fixed]
        for index in poly.loop_indices:
            point = obj.matrix_world @ obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = (point[i] * scale, point[j] * scale)


def add_fiber(tube, points, radius, phase):
    vertices, faces, uv = tube
    start = len(vertices)
    sides = 5
    for row, (point, normal) in enumerate(points):
        tangent = (points[min(row + 1, len(points) - 1)][0] - points[max(row - 1, 0)][0]).normalized()
        side = normal.cross(tangent).normalized()
        if side.length_squared < .1:
            side = Vector((1, 0, 0))
        taper = .24 + .76 * max(0, math.sin(math.pi * row / (len(points) - 1))) ** .55
        for index in range(sides):
            angle = math.tau * index / sides
            vertices.append(point + radius * taper * (side * math.cos(angle) + normal * .55 * math.sin(angle)))
            uv.append(((index / sides + phase) % 1, row * .076 + phase))
    for row in range(len(points) - 1):
        for index in range(sides):
            a = start + row * sides + index
            b = start + row * sides + (index + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.extend((tuple(reversed(range(start, start + sides))),
                  tuple(range(len(vertices) - sides, len(vertices)))))


def interpolate_spine(spine, t):
    segment = min(int(t), len(spine) - 2)
    local = t - segment
    a, b = spine[max(0, segment - 1)], spine[segment]
    c, d = spine[segment + 1], spine[min(len(spine) - 1, segment + 2)]
    return .5 * (2 * b + (c - a) * local + (2 * a - 5 * b + 4 * c - d) * local ** 2
                 + (-a + 3 * b - 3 * c + d) * local ** 3)


def sculpt_vault(spine, bark):
    radii = (.23, .23, .22, .21, .24, .26, .29, .26, .25, .22, .23, .22, .22, .24)
    vertices = []
    sides, rings = 34, 125
    for row in range(rings):
        t = (len(spine) - 1) * row / (rings - 1)
        center = interpolate_spine(spine, t)
        tangent = (interpolate_spine(spine, min(len(spine) - 1, t + .025))
                   - interpolate_spine(spine, max(0, t - .025))).normalized()
        u = tangent.cross(Vector((0, 1, 0))).normalized()
        v = tangent.cross(u)
        division = min(int(t), len(radii) - 2)
        base = radii[division] + (radii[division + 1] - radii[division]) * (t - division)
        for side in range(sides):
            angle = math.tau * side / sides
            ridge = (1 + .125 * math.sin(3 * angle + t * .68)
                     + .036 * math.sin(7 * angle - t * 1.1) + .018 * math.cos(13 * angle + t * 4.7))
            vertices.append(center + base * ridge * (u * math.cos(angle) + .79 * v * math.sin(angle)))
    faces = [tuple(reversed(range(sides)))]
    for row in range(rings - 1):
        for side in range(sides):
            a, b = row * sides + side, row * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    obj = build_mesh("Main vault root", vertices, faces, bark)
    layer = obj.data.uv_layers.new(name="Longitudinal bark UV")
    for poly in obj.data.polygons[1:-1]:
        poly.use_smooth = True
        row, side = divmod(poly.index - 1, sides)
        lo, hi = side / sides, (side + 1) / sides
        bottom, top = row / (rings - 1), (row + 1) / (rings - 1)
        for index, position in zip(poly.loop_indices, ((lo, bottom), (hi, bottom), (hi, top), (lo, top))):
            layer.data[index].uv = position
    return obj


def refine_arch(objects, bark, slate, splinter, chip):
    spine = [Vector(point) for point in ARCH_SPINE]
    original = next(obj for obj in objects if obj.name == "Main vault root")
    objects.remove(original)
    bpy.data.objects.remove(original, do_unlink=True)
    vault = sculpt_vault(spine, bark)
    objects.append(vault)
    clear_arch(objects)
    root = tree_for([vault])
    randomizer = random.Random(191314)
    tubes = [([], [], []), ([], [], [])]
    for strand in range(224):
        start = randomizer.uniform(.05, 12.2)
        span = randomizer.uniform(.30, 2.2)
        angle = randomizer.uniform(0, math.tau)
        radius = randomizer.uniform(.003, .011)
        points = []
        for index in range(15):
            t = min(len(spine) - 1.0001, start + span * index / 14)
            tangent = (interpolate_spine(spine, min(len(spine) - 1, t + .025))
                       - interpolate_spine(spine, max(0, t - .025))).normalized()
            u = tangent.cross(Vector((0, 1, 0))).normalized()
            v = tangent.cross(u)
            phase = angle + .16 * math.sin(t * .9 + strand) + .065 * math.sin(t * 6.4 + strand)
            direction = u * math.cos(phase) + v * math.sin(phase)
            origin = interpolate_spine(spine, t)
            point, normal, _, _ = root.ray_cast(origin, direction, .46)
            if point is None:
                continue
            point += normal * radius * (.23 + .72 * math.sin(math.pi * index / 14))
            if abs(point.x) - radius < .816 and point.z - radius < 2.718:
                continue
            points.append((point, normal))
        if len(points) > 5:
            add_fiber(tubes[strand % 2], points, radius, strand * .033)
    for index, (vertices, faces, uv) in enumerate(tubes):
        faces = [face for face in faces if not intersects_bounds((vertices[i] for i in face), PORTAL)]
        if faces:
            pieces = build_mesh(f"Frayed longitudinal root fibers {index + 1}", vertices, faces,
                                bark if index == 0 else splinter, uv)
            for polygon in pieces.data.polygons:
                polygon.use_smooth = True

    feet = [obj for obj in objects if "foot" in obj.name.lower() or "upright" in obj.name.lower()]
    add_chips(feet, slate, chip, count=183, seed=74167, arch=True)


def add_chips(objects, rock, highlight, count, seed, arch=False):
    rng = random.Random(seed)
    surface = tree_for(objects)
    batches = [([], []), ([], [])]
    for index in range(count):
        x = rng.uniform(.94, 1.55) * rng.choice((-1, 1)) if arch else rng.uniform(-2.65, 2.65)
        z = rng.uniform(.10, 1.13) if arch else rng.uniform(.025, .89)
        point, normal, _, _ = surface.ray_cast(Vector((x, -3.0, z)), Vector((0, 1, 0)), 4)
        if point is None or abs(normal.z) >= .68:
            continue
        tangent = Vector((1, 0, 0)) - normal.x * normal
        if tangent.length < .1:
            continue
        tangent.normalize()
        vertical = normal.cross(tangent).normalized()
        length = rng.uniform(.055, .18 if arch else .32)
        breadth = rng.uniform(.011, .040 if arch else .065)
        thickness = rng.uniform(.004, .021)
        if arch and abs(point.x) - length < .816:
            continue
        vertices, faces = batches[index % 5 == 0]
        offset = len(vertices)
        segments = rng.randint(5, 8)
        perimeter = []
        for side in range(segments):
            phase = math.tau * side / segments
            perimeter.append(point + tangent * (math.cos(phase) * length * rng.uniform(.67, 1))
                             + vertical * (math.sin(phase) * breadth * rng.uniform(.58, 1)))
        vertices.extend(p - normal * .012 for p in perimeter)
        vertices.extend(point + (p - point) * .82 + normal * thickness for p in perimeter)
        faces.append(tuple(range(offset + segments, offset + 2 * segments)))
        for side in range(segments):
            a, b = offset + side, offset + (side + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    for index, (vertices, faces) in enumerate(batches):
        if faces:
            obj = build_mesh(f"Fractured laminae and edge spalls {index + 1}", vertices, faces,
                             rock if index == 0 else highlight)
            project_uv(obj, .73)


def apply_surfaces(objects, bark, slate, dry_mineral, tread):
    for obj in objects:
        names = " ".join(mat.name.lower() for mat in obj.data.materials)
        is_bark = any(word in names for word in ("bark", "roots retreating"))
        surface = bark if is_bark else dry_mineral if obj.name.startswith("Quarry scar") else slate
        if not is_bark or not obj.data.uv_layers:
            project_uv(obj, .74 if not is_bark else 1.2)
        obj.data.materials.clear()
        obj.data.materials.append(surface)
        if tread and obj.name.startswith(("Quarry rock course 4", "Carved lookout seat", "Guard cap")):
            obj.data.materials.append(tread)
            rotation = obj.matrix_world.to_3x3()
            for polygon in obj.data.polygons:
                polygon.material_index = int((rotation @ polygon.normal).z > .66)


def prepare_scene(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    return [obj for obj in scene.objects if obj.type == "MESH"]


def views(asset):
    if asset == "buried_forest_root_arch":
        return (((2.62, -9.2, 4.08), (0, 0, 2.02), 5.25),
                ((1.78, -5.8, 3.82), (.85, -.1, 2.67), 1.98))
    return (((3.98, -8.36, 6.46), (0, -.16, .76), 7.28),
            ((.28, -6.25, 3.46), (.23, -1.69, .9), 2.82))


def render(asset, path, output, detail, suffix, samples, resolution):
    objects = prepare_scene(path)
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Consistent studio fill")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.24, .29, .35, 1)
    background.inputs[1].default_value = .34
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, min(
        p.z for obj in objects for face in world_triangles(obj) for p in face) - .005))
    bpy.context.object.data.materials.append(material("Matte studio floor", color=(.043, .047, .051)))
    location, target, scale = views(asset)[detail]
    camera = bpy.data.objects.new("Matched comparison camera", bpy.data.cameras.new("Comparison"))
    bpy.context.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    scene.camera = camera
    focus = Vector((0, 0, 1.6 if asset == "buried_forest_root_arch" else .5))
    for name, position, energy, size, color in (
        ("Soft neutral key", (1.5, -4.2, 6.5), 1450, 3.5, (1, .93, .84)),
        ("Cold edge", (-3.7, 2.1, 5.6), 1130, 2.3, (.68, .79, 1)),
        ("Raking fill", (-3.9, -2.1, 2.6), 385, 1.5, (.89, .95, 1)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size, data.color = energy, size, color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = position
        light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.samples, scene.cycles.use_denoising = samples, False
    scene.render.threads_mode, scene.render.threads = "FIXED", 4
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / f"{asset}_{suffix}{'_detail' if detail else ''}.png")
    bpy.ops.render.render(write_still=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clearance(asset, objects):
    bounds = PORTAL if asset.endswith("root_arch") else (
        (-1.50, 1.50), (-1.50, 1.58), (.963, 2.95))
    bad = [obj.name for obj in objects if any(intersects_bounds(face, bounds) for face in world_triangles(obj))]
    if bad:
        raise ValueError(f"{asset}: solid geometry invades requested opening {bad}")
    return bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument("--samples", type=int, default=18)
    parser.add_argument("--resolution", type=int, default=720)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    textures = output / "textures"
    textures.mkdir(exist_ok=True)
    report = {}
    for asset, source in ASSETS.items():
        objects = prepare_scene(source)
        original_triangles = sum(len(world_triangles(obj)) for obj in objects)
        surfaces = {}
        kinds = ("bark", "slate") if asset.endswith("root_arch") else ("bark", "slate", "tread")
        for kind in kinds:
            maps = {name: packed_image(f"{kind}_{name}", pixels, textures, name == "Albedo")
                    for name, pixels in texture_maps(kind).items()}
            surfaces[kind] = material(f"EIDOLON {kind} microfractures", maps)
        hue = material("Weathered slate split faces", color=(.095, .104, .104), roughness=.91)
        splinter = material("Exposed splintered woody fibers", color=(.118, .057, .027), roughness=.89)
        apply_surfaces(objects, surfaces["bark"], surfaces["slate"], hue, surfaces.get("tread"))
        if asset.endswith("root_arch"):
            refine_arch(objects, surfaces["bark"], surfaces["slate"], splinter, hue)
        else:
            courses = [obj for obj in objects if obj.name.startswith("Quarry rock course")]
            add_chips(courses, surfaces["slate"], hue, count=404, seed=8147)

        pieces = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        bpy.context.view_layer.update()
        bounds = clearance(asset, pieces)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in pieces:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = pieces[0]
        path = output / f"{asset}_refined.glb"
        bpy.ops.wm.save_as_mainfile(filepath=str(output / f"{asset}_refined.blend"))
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True)
        restored = prepare_scene(path)
        clearance(asset, restored)
        triangles = sum(len(world_triangles(obj)) for obj in restored)
        image_count = len([image for image in bpy.data.images if image.size[0] >= 768])
        if triangles <= original_triangles * 2 or image_count != 3 * len(kinds):
            raise ValueError(f"{asset}: expected detail geometry and embedded textures to survive GLB export")
        report[asset] = {"source_sha256": digest(source), "output_sha256": digest(path),
                         "source_triangles": original_triangles, "reimport_triangles": triangles,
                         "reimport_objects": len(restored), "reimport_embedded_images": image_count,
                         "clearance_prism_metres": bounds,
                         "validation": "Blender glTF round trip and authored route prism",
                         "provenance": "Original EIDOLON art and deterministic in-house texture synthesis"}
        print(f"VERIFIED {asset}: {original_triangles} -> {triangles} triangles; {image_count} packed PBR maps", flush=True)
    (output / "forest_landmarks_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not args.skip_renders:
        for asset, source in ASSETS.items():
            path = output / f"{asset}_refined.glb"
            render(asset, source, output, 0, "before", args.samples, args.resolution)
            render(asset, path, output, 0, "after", args.samples, args.resolution)
            render(asset, path, output, 1, "after", args.samples, args.resolution)


if __name__ == "__main__":
    main()
