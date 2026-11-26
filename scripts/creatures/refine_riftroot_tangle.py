"""Fracture and texture the original Riftroot prototype.

Run with Blender: blender -b --python-exit-code 1 --python this_script -- output_dir
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_riftroot_tangle import aim, light, surface

SOURCE = (Path(__file__).resolve().parents[2] /
          "previews/buried-forest/riftroot/riftroot_tangle.glb")
PIVOTS = ("Rig_Shale_Root_Core", "Rig_Lifting_Rock_Wedge",
          "Rig_Limb_Front_Left", "Rig_Limb_Front_Right", "Rig_Limb_Rear_Left", "Rig_Limb_Rear_Right")
TEXTURE_SIZE = 768


def image(name, pixels, color=False):
    size = TEXTURE_SIZE
    result = bpy.data.images.new(name, width=size, height=size, alpha=True)
    if not color:
        result.colorspace_settings.name = "Non-Color"
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(pixels, 0., 1.)
    result.pixels.foreach_set(rgba.ravel())
    result.pack()
    return result


def tile_noise(rng, x, y, nx, ny):
    grid = rng.random((ny, nx))
    px, py = x * nx, y * ny
    ix, iy = np.floor(px).astype(int), np.floor(py).astype(int)
    fx, fy = px - ix, py - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = grid[iy % ny, ix % nx] * (1 - fx) + grid[iy % ny, (ix + 1) % nx] * fx
    b = grid[(iy + 1) % ny, ix % nx] * (1 - fx) + grid[(iy + 1) % ny, (ix + 1) % nx] * fx
    return a * (1 - fy) + b * fy


def texture_triplet(name, root, cap=False):
    rng = np.random.default_rng(77 if root else 63)
    x, y = np.meshgrid(np.arange(TEXTURE_SIZE) / TEXTURE_SIZE, np.arange(TEXTURE_SIZE) / TEXTURE_SIZE)
    broad = tile_noise(rng, x, y, 9, 11)
    middle = tile_noise(rng, x, y, 37, 33)
    grain = tile_noise(rng, x, y, 173, 149)
    if root:
        warp = x + .042 * tile_noise(rng, x, y, 13, 8) + .021 * np.sin(2 * math.tau * y)
        grain_long = tile_noise(rng, warp, y, 121, 10)
        fine_fiber = tile_noise(rng, warp, y, 245, 29)
        split = np.clip((.33 - grain_long) * 4., 0., 1.)
        height = .51 * grain_long + .25 * fine_fiber + .22 * middle - .35 * split
        value = .46 + .24 * broad + .20 * grain_long + .13 * middle - .30 * split
        color = value[..., None] * np.array([.39, .253, .155])
        color += np.clip((broad - .56) * .8, 0., .27)[..., None] * np.array([.25, .122, .036])
        roughness = .77 + .21 * fine_fiber
    else:
        warp = y + .045 * tile_noise(rng, x, y, 8, 8) + .03 * np.sin(math.tau * x)
        bands = tile_noise(rng, x, warp, 5, 98)
        hairlines = np.clip((.14 - abs(np.sin(math.tau * (10 * warp + .63 * broad)))) * 5.6, 0., 1.)
        chips = np.clip((middle - .72) * 2., 0., 1.)
        height = .44 * bands + .20 * middle + .12 * grain - .21 * hairlines
        value = .59 + .30 * broad + .21 * bands + .13 * middle + .045 * grain - .39 * hairlines
        color = value[..., None] * np.array([.264, .265, .249] if cap else [.205, .218, .227])
        oxidized = np.clip((broad * .60 + middle * .35 - .46) * 1.75, 0., .38)
        color += oxidized[..., None] * np.array([.17, .085, .023])
        color += chips[..., None] * np.array([.12, .116, .085])
        roughness = .76 + .24 * bands

    dx = (np.roll(height, 1, 1) - np.roll(height, -1, 1)) * (2.5 if root else 2.1)
    dy = (np.roll(height, 1, 0) - np.roll(height, -1, 0)) * 2.1
    normal = np.stack((dx, dy, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return (image(name + " base color", color, color=True),
            image(name + " roughness", roughness[..., None]),
            image(name + " detail normal", normal * .5 + .5))


def pbr(name, fallback, *, root=False, cap=False):
    material = surface(name, fallback, .88)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes["Principled BSDF"]
    assign = ((-560, 250), (-560, -20), (-560, -300))
    maps = []
    for pixels, location in zip(texture_triplet(name, root, cap), assign):
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = pixels
        texture.location = location
        maps.append(texture)
    links.new(maps[0].outputs["Color"], shader.inputs["Base Color"])
    links.new(maps[1].outputs["Color"], shader.inputs["Roughness"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.location = (-260, -280)
    normal.inputs["Strength"].default_value = .83
    links.new(maps[2].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return material


def clip_slab(source, axis, lower, upper):
    slab = source.copy()
    for plane, remove_inner in ((lower, True), (upper, False)):
        result = bmesh.ops.bisect_plane(slab, geom=list(slab.verts) + list(slab.edges) + list(slab.faces),
                                      dist=1e-6, plane_co=axis * plane, plane_no=axis,
                                      clear_inner=remove_inner, clear_outer=not remove_inner)
        boundary = [edge for edge in result["geom_cut"] if isinstance(edge, bmesh.types.BMEdge)
                    and edge.is_valid and edge.is_boundary]
        if boundary:
            cap = bmesh.ops.holes_fill(slab, edges=boundary, sides=0)
            for face in cap["faces"]:
                face.material_index = 1
    bmesh.ops.recalc_face_normals(slab, faces=list(slab.faces))
    return slab


def fracture(obj, exterior, fresh, shadow, rng):
    original = bmesh.new()
    original.from_mesh(obj.data)
    bmesh.ops.remove_doubles(original, verts=list(original.verts), dist=1e-5)
    for face in original.faces:
        face.material_index = 0
    axis = Vector((rng.uniform(-.32, .32), rng.uniform(-.38, .38), 1.)).normalized()
    widths = [axis.dot(vertex.co) for vertex in original.verts]
    low, high = min(widths), max(widths)
    count = max(2, min(10, math.ceil((high - low) / .143)))
    breaks = [low - .001] + [low + (high - low) * (i + rng.uniform(-.35, .35)) / count
                              for i in range(1, count)] + [high + .001]
    vertices, polygons, indices = [], [], []
    ripple = rng.uniform(0., math.tau)

    def displaced(point):
        bend = .024 * math.sin(point.x * 5.1 + point.y * 6.3 + ripple)
        bend += .010 * math.sin(point.x * 16.9 - point.y * 12.7)
        return point + axis * bend

    def collect(slab, slide, shade=None):
        offset = len(vertices)
        slab.verts.index_update()
        vertices.extend(displaced(vertex.co) + slide for vertex in slab.verts)
        polygons.extend(tuple(vertex.index + offset for vertex in face.verts) for face in slab.faces)
        indices.extend(face.material_index if shade is None else shade for face in slab.faces)

    for index, (lower, upper) in enumerate(zip(breaks, breaks[1:])):
        slit = min(.014, (upper - lower) * .07) * rng.uniform(.51, 1.)
        slab = clip_slab(original, axis, lower + slit * (index != 0),
                         upper - slit * (index != count - 1))
        shift = Vector((rng.uniform(-.013, .013), rng.uniform(-.013, .013), 0))
        if count >= 4 and rng.random() < .37 and slab.verts:
            # A steep joint terminates some seams and displaces the adjacent lamina.
            joint = Vector((rng.uniform(.65, 1.0), rng.uniform(-1., 1.), rng.uniform(-.36, .36))).normalized()
            lateral = [joint.dot(vertex.co) for vertex in slab.verts]
            minimum, maximum = min(lateral), max(lateral)
            split = minimum + (maximum - minimum) * rng.uniform(.20, .66)
            for bounds, slip in (((minimum - .001, split - .007), -.009),
                                 ((split + .007, maximum + .001), .009)):
                fragment = clip_slab(slab, joint, *bounds)
                collect(fragment, shift + joint * slip)
                fragment.free()
        else:
            collect(slab, shift)
        slab.free()

    for vertex in original.verts:
        vertex.co *= .86
    collect(original, Vector(), shade=2)
    original.free()
    data = bpy.data.meshes.new(obj.name + " physical bedding")
    data.from_pydata(vertices, [], polygons)
    data.update()
    for material in (exterior, fresh, shadow):
        data.materials.append(material)
    for face, index in zip(data.polygons, indices):
        face.material_index = index
    obj.data = data
    project_uv(obj, axis, rng)


def project_uv(obj, axis, rng):
    uv = obj.data.uv_layers.new(name="Bedding UV")
    along = Vector((1., 0., 0.))
    across = axis.cross(along).normalized()
    along = across.cross(axis).normalized()
    offset_x, offset_y = rng.random(), rng.random()
    for face in obj.data.polygons:
        if abs(face.normal.dot(axis)) > .68:
            u_axis, v_axis = along, across
        else:
            u_axis, v_axis = axis.cross(face.normal).normalized(), axis
        for loop_index in face.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (vertex.dot(u_axis) * 1.29 + offset_x,
                                     vertex.dot(v_axis) * 1.53 + offset_y)


def root_sections(obj):
    uv = obj.data.uv_layers.active
    sections = {}
    for polygon in obj.data.polygons:
        coordinates = [uv.data[index].uv for index in polygon.loop_indices]
        # The source side islands use ten evenly spaced columns; the UVs
        # on the planar end caps project each ring radially instead.
        if any(abs(u * 10 - round(u * 10)) > 1e-4 for u, _ in coordinates):
            continue
        if max(v for _, v in coordinates) - min(v for _, v in coordinates) < 1e-4:
            continue
        for loop_index, (_, v) in zip(polygon.loop_indices, coordinates):
            vertex = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            sections.setdefault(round(v, 5), set()).add(tuple(vertex))
    route = []
    for key in sorted(sections):
        ring = list(map(Vector, sorted(sections[key])))
        center = sum(ring, Vector()) / len(ring)
        radius = sum((vertex - center).length for vertex in ring) / len(ring)
        route.append((center, radius))
    if len(route) < 3 or min(radius for _, radius in route) < .005:
        raise RuntimeError(f"Missing original root UV sections on {obj.name}.")
    return route


def refine_root(obj, bark, seed):
    rng = random.Random(seed)
    route = root_sections(obj)
    sections = []
    for i in range(len(route) - 1):
        point, radius = route[i]
        following, next_radius = route[i + 1]
        before = route[max(i - 1, 0)][0]
        after = route[min(i + 2, len(route) - 1)][0]
        for j in range(5):
            t = j / 5
            curve = .5 * ((2 * point) + (-before + following) * t
                          + (2 * before - 5 * point + 4 * following - after) * t * t
                          + (-before + 3 * point - 3 * following + after) * t * t * t)
            sections.append((curve, radius + (next_radius - radius) * t))
    sections.append(route[-1])
    count = 20
    vertices, faces, face_uv = [], [], []
    phase = rng.uniform(0., math.tau)
    length = sum((a[0] - b[0]).length for a, b in zip(sections, sections[1:]))
    strip = Vector((0., 0., 1.))
    for index, (center, radius) in enumerate(sections):
        tangent = (sections[min(index + 1, len(sections) - 1)][0] - sections[max(0, index - 1)][0]).normalized()
        perpendicular = strip - tangent * tangent.dot(strip)
        if perpendicular.length < .01:
            perpendicular = tangent.cross(Vector((1., 0., 0.)))
        strip = perpendicular.normalized()
        cross = tangent.cross(strip)
        u = index / (len(sections) - 1)
        for spoke in range(count):
            angle = spoke * math.tau / count
            ridges = (1. + .17 * math.cos(3 * angle + 1.3 * u + phase)
                      + .095 * math.cos(8 * angle - 4 * u)
                      + .048 * math.sin(11 * angle + 12 * u + phase))
            vertices.append(center + radius * ridges * (.98 * math.cos(angle) * strip + .92 * math.sin(angle) * cross))
    for row in range(len(sections) - 1):
        v0, v1 = row * length / (len(sections) - 1), (row + 1) * length / (len(sections) - 1)
        for spoke in range(count):
            a, b = count * row + spoke, count * row + (spoke + 1) % count
            faces.append((a, b, b + count, a + count))
            u0, u1 = phase + spoke / count, phase + (spoke + 1) / count
            face_uv.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
    faces.extend((tuple(reversed(range(count))), tuple(range(len(vertices) - count, len(vertices)))))
    for v in (0., length):
        face_uv.append(tuple((phase + .48 * math.cos(s * math.tau / count),
                              v + .04 * math.sin(s * math.tau / count)) for s in range(count)))
    data = bpy.data.meshes.new(obj.name + " fluted bark")
    data.from_pydata(vertices, [], faces)
    data.update()
    data.materials.append(bark)
    uv = data.uv_layers.new(name="Root fiber UV")
    for face, points in zip(data.polygons, face_uv):
        face.use_smooth = face.index < len(faces) - 2
        for loop_index, point in zip(face.loop_indices, points):
            uv.data[loop_index].uv = point
    obj.data = data


def bounds(meshes):
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
    return tuple((min(point[i] for point in points), max(point[i] for point in points)) for i in range(3))


def scene_preview(output, wedge, samples):
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0., 0., -.055))
    bpy.context.object.data.materials.append(surface("Preview dark earth", (.029, .027, .024), .96, 48))
    world = bpy.data.worlds.new("Subterranean ambient")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.21, .25, .29, 1.)
    background.inputs[1].default_value = .33
    camera = bpy.data.objects.new("Riftroot look development", bpy.data.cameras.new("Riftroot look development"))
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    scene.camera = camera
    light("Neutral cave opening", (-3.5, -4.4, 6.2), (.87, .93, 1.), 1500, 3.5)
    light("Warm mineral edge", (3.4, 2.5, 4.6), (1., .80, .60), 1500, 2.6)
    light("Soft cavity lift", (3.5, -4.5, 2.3), (.80, .85, .89), 240, 3.0)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 832
    scene.render.image_settings.file_format = "PNG"

    angles = (("riftroot_tangle", (-6.4, -9.1, 4.7), (0, -.10, 1.35), 6.60, False),
              ("riftroot_tangle_detail", (-2.4, -6.0, 3.0), (-.56, -1.17, 1.99), 2.86, False),
              ("riftroot_tangle_wedge_raised", (-4.8, -9.1, 4.0), (0, -.27, 1.53), 6.60, True))
    for index, (name, position, target, scale, raised) in enumerate(angles):
        wedge.rotation_euler.x = math.radians(-30) if raised else 0.
        camera.location = position
        camera.data.ortho_scale = scale
        aim(camera, target)
        scene.render.filepath = str(output / (name + ".png"))
        if index == 0:
            bpy.ops.wm.save_as_mainfile(filepath=str(output / "riftroot_tangle.blend"))
        bpy.ops.render.render(write_still=True)


def verify_export(path, original_pivots, expected_bounds, expected_triangles):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    for name, (parent, transform) in original_pivots.items():
        obj = bpy.data.objects[name]
        if not obj.parent or obj.parent.name != parent or any(
                abs(a - b) > 1e-5 for actual, expected in zip(obj.matrix_local, transform)
                for a, b in zip(actual, expected)):
            raise RuntimeError(f"Changed pivot or hierarchy after reimport: {name}.")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    materials = {material for obj in meshes for material in obj.data.materials}
    textured = [material for material in materials if material.use_nodes and
                any(node.type == "TEX_IMAGE" and node.image for node in material.node_tree.nodes)]
    if len(textured) != 3 or any(not obj.data.uv_layers for obj in meshes):
        raise RuntimeError("The imported shale, cut faces and bark require their PBR textures and UVs.")
    actual = bounds(meshes)
    if any(abs(a - b) > .02 for aa, bb in zip(actual, expected_bounds) for a, b in zip(aa, bb)):
        raise RuntimeError(f"Changed envelope after reimport: {actual}.")
    triangles = sum(len(obj.data.polygons) for obj in meshes)
    if triangles != expected_triangles:
        raise RuntimeError(f"Expected {expected_triangles} triangles, got {triangles}.")
    return {"mesh_parts": len(meshes), "triangles": triangles, "textured_materials": len(textured),
            "pivots": list(original_pivots), "bounds_m": actual}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.samples < 1:
        raise ValueError("Samples must be positive.")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    bpy.context.view_layer.update()
    original_pivots = {name: (bpy.data.objects[name].parent.name,
                              bpy.data.objects[name].matrix_local.copy()) for name in PIVOTS}
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    source_bounds = bounds(meshes)
    part_bounds = {obj.name: bounds([obj]) for obj in meshes}

    exterior = pbr("Fractured graphitic shale", (.065, .071, .074))
    fresh = pbr("Split shale bedding faces", (.091, .093, .087), cap=True)
    bark = pbr("Exposed fluted roots", (.117, .060, .027), root=True)
    shadow = surface("Dark recessed fissures", (.012, .011, .010), .95)
    for i, obj in enumerate(sorted(meshes, key=lambda obj: obj.name)):
        rng = random.Random(3100 + i)
        if obj.name == "Asymmetric exposed cavity":
            obj.data.materials.clear()
            obj.data.materials.append(shadow)
            for face in obj.data.polygons:
                face.material_index = 0
            project_uv(obj, Vector((0., 0., 1.)), rng)
        elif any("Living dark root" in material.name for material in obj.data.materials):
            refine_root(obj, bark, 4200 + i)
        else:
            fracture(obj, exterior, fresh, shadow, rng)
    reworked_bounds = bounds(meshes)
    if any(abs(a - b) > .13 for aa, bb in zip(reworked_bounds, source_bounds) for a, b in zip(aa, bb)):
        for obj in meshes:
            actual = bounds([obj])
            before = part_bounds[obj.name]
            if any(abs(a - b) > .13 for aa, bb in zip(actual, before) for a, b in zip(aa, bb)):
                print(f"{obj.name}: {before} -> {actual}")
        raise RuntimeError(f"Envelope drifted more than 13 cm: {source_bounds} -> {reworked_bounds}.")

    triangle_count = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangle_count += len(obj.data.loop_triangles)
    asset = bpy.data.objects["Riftroot_Tangle_Preview"]
    asset["prototype_use"] = "Original art candidate; Unreal import, rig integration, and art approval pending"
    path = output / "riftroot_tangle.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_extras=True, export_tangents=True)
    if not args.verify_only:
        scene_preview(output, bpy.data.objects["Rig_Lifting_Rock_Wedge"], args.samples)
    results = verify_export(path, original_pivots, reworked_bounds, triangle_count)
    report = {"blender": bpy.app.version_string, "source": SOURCE.name, "source_bounds_m": source_bounds,
              "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "glb_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "reimport": results,
              "previews_rendered": not args.verify_only}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
