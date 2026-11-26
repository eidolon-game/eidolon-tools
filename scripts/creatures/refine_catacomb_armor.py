"""Rebuild four Catacombs creatures using the checked PBR catalog as input.

Run Blender 4.3 in background with this script, then the PBR catalog and
output directory after --. The originals and their dimensions remain available
for fixed-camera review. Each of the four forms has an anatomy-specific pass.
"""

import argparse
from hashlib import sha256
import json
from math import cos, pi, sin, sqrt
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector, noise


ORIGINALS = Path(__file__).resolve().parents[2] / "previews/catacombs"
ASSETS = ("OssuaryTick", "LintelMantis", "MarrowRam", "VaultPincer")


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    if 'FINISHED' not in bpy.ops.import_scene.gltf(filepath=str(path)):
        raise RuntimeError(f"Could not import {path}")
    bpy.context.view_layer.update()
    return {obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"}


def bounds(objects):
    corners = [obj.matrix_world @ Vector(point) for obj in objects for point in obj.bound_box]
    return tuple(Vector(tuple(component(point[axis] for point in corners) for axis in range(3)))
                 for component in (min, max))


def mesh_object(name, vertices, faces, uvs, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    uv = mesh.uv_layers.new(name="Surface")
    for loop in mesh.loops:
        uv.data[loop.index].uv = uvs[loop.vertex_index]
    return obj


def replace_plate(obj, normal, phase, serration):
    """A thick chitin or calcite shell with worn, irregular laminar margins."""
    low, high = bounds((obj,))
    mid, half = (high + low) / 2, (high - low) / 2
    side_axis = abs(normal.x) > .5
    u = Vector((0, 1, 0)) if side_axis else Vector((1, 0, 0))
    v = normal.cross(u)
    ru = sum(abs(u[i]) * half[i] for i in range(3))
    rv = sum(abs(v[i]) * half[i] for i in range(3))
    height = sum(abs(normal[i]) * half[i] for i in range(3))
    material = obj.data.materials[0]
    name = obj.name
    count, rings = 40, 12
    verts, faces, uvs = [mid + normal * height], [], [(.5, .5)]
    for ring in range(1, rings + 1):
        radius = ring / rings
        for index in range(count):
            a = index * 2 * pi / count
            irregular = 1 - serration * (.5 + .5 * sin(a * 9 + phase)) * radius ** 4
            across = radius * cos(a) * irregular
            along = radius * sin(a) * irregular
            shoulder = sqrt(max(0.0, 1 - radius ** 1.62))
            grain = .10 * sin(a * 11 + radius * 4 + phase) * radius * (1 - radius)
            contour = height * (shoulder + grain + .08 * sin(radius * 38 + phase) * radius)
            verts.append(mid + u * ru * across + v * rv * along + normal * contour)
            uvs.append(((across + 1) / 2, (along + 1) / 2))
            next_index = (index + 1) % count
            here = 1 + (ring - 1) * count + index
            following = 1 + (ring - 1) * count + next_index
            if ring == 1:
                faces.append((0, here, following))
            else:
                faces.append((here - count, here, following, following - count))
    edge = 1 + (rings - 1) * count
    underside = len(verts)
    for index in range(count):
        radial = verts[edge + index] - mid
        radial -= normal * radial.dot(normal)
        verts.append(mid + radial * .91 - normal * height * .40)
        uvs.append(uvs[edge + index])
    bottom = len(verts)
    verts.append(mid - normal * height * .62)
    uvs.append((.5, .5))
    for index in range(count):
        other = (index + 1) % count
        faces.append((edge + other, edge + index, underside + index, underside + other))
        faces.append((bottom, underside + other, underside + index))
    bpy.data.objects.remove(obj, do_unlink=True)
    plate = mesh_object(f"Laminar {name}", verts, faces, uvs, material)
    for polygon in plate.data.polygons:
        polygon.use_smooth = polygon.index < rings * count
    return plate


def shell_weathering(obj, amplitude, seed, cuts=2):
    """Add real dents and chips to the existing mesh and retain its UV seams."""
    model = obj.data
    bm = bmesh.new()
    bm.from_mesh(model)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=cuts, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    world = obj.matrix_world
    inverse = world.inverted().to_3x3()
    normal_matrix = inverse.transposed()
    shift = Vector((seed * .24, seed * .074, seed * .31))
    for vertex in bm.verts:
        point = world @ vertex.co
        if point.z < .024:
            continue
        direction = (normal_matrix @ vertex.normal).normalized()
        shape = noise.noise(point * 24 + shift)
        chips = max(0.0, noise.noise(point * 63 + shift) - .25)
        vertex.co += inverse @ (direction * amplitude * (shape - 1.8 * chips))
    bm.to_mesh(model)
    bm.free()
    model.update()


def add_ligament(name, points, radius, material):
    vertices, faces, uvs = [], [], []
    sides = 8
    for index, point in enumerate(points):
        t = index / (len(points) - 1)
        direction = (points[min(index + 1, len(points) - 1)] - points[max(0, index - 1)]).normalized()
        side = direction.cross(Vector((0, 0, 1)))
        if side.length < .01:
            side = direction.cross(Vector((0, 1, 0)))
        side.normalize()
        up = direction.cross(side)
        thickness = radius * (.74 + .26 * sin(t * pi))
        for digit in range(sides):
            angle = digit / sides * 2 * pi
            vertices.append(point + (side * cos(angle) + up * sin(angle)) * thickness)
            uvs.append((digit / sides, t))
            if index:
                current = index * sides + digit
                next_vertex = index * sides + (digit + 1) % sides
                faces.append((current - sides, next_vertex - sides, next_vertex, current))
    side_face_count = len(faces)
    last_ring = len(vertices) - sides
    for end, ring in ((0, 0), (len(points) - 1, last_ring)):
        cap = len(vertices)
        vertices.append(points[end])
        uvs.append((.5, .5))
        for digit in range(sides):
            edge = (ring + digit, ring + (digit + 1) % sides)
            faces.append((cap, *edge) if end else (cap, *reversed(edge)))
    obj = mesh_object(name, vertices, faces, uvs, material)
    mesh = obj.data
    surface = mesh.uv_layers[0].data
    for face in obj.data.polygons:
        if face.index < side_face_count:
            face.use_smooth = True
            if face.index % sides == sides - 1:
                for loop_id in face.loop_indices:
                    if mesh.loops[loop_id].vertex_index % sides == 0:
                        surface[loop_id].uv.x = 1.0
            continue
        for loop_id in face.loop_indices:
            vertex_id = mesh.loops[loop_id].vertex_index
            if vertex_id < last_ring + sides:
                angle = (vertex_id % sides) * 2 * pi / sides
                surface[loop_id].uv = (.5 + .45 * cos(angle), .5 + .45 * sin(angle))
    return obj


def tendon_groups(center, across, length, width, count, material, name):
    for i in range(count):
        offset = (i / (count - 1) - .5) * width
        points = []
        for j in range(7):
            t = j / 6
            points.append(center + across * offset + Vector((0, length * (t - .5),
                          width * .16 * sin(t * pi) + .003 * sin(t * 5 + i))))
        add_ligament(f"{name} fiber {i + 1}", points, width / count * .21, material)


def shape_limb(obj, start, end, radii, bend):
    """Rebuild a straight proxy around the original attachment points."""
    start, end = Vector(start), Vector(end)
    travel = end - start
    axis = travel.normalized()
    side = axis.cross(Vector((0, 0, 1))).normalized()
    up = axis.cross(side)
    rings, sides = 19, 20
    vertices, faces, uv = [], [], []
    for ring in range(rings):
        t = ring / (rings - 1)
        center = start.lerp(end, t) + side * bend * sin(pi * t)
        core = radii[0] + (radii[1] - radii[0]) * t
        section = core * (.77 + .24 * sin(2 * pi * t + .22) + .15 * sin(pi * t))
        if ring in (0, rings - 1):
            section *= .79
        for index in range(sides):
            a = index * 2 * pi / sides
            ribs = (1 + .10 * sin(a * 5 + t * 3) * sin(pi * t))
            vertices.append(center + (side * cos(a) + up * sin(a) * .79) * section * ribs)
            uv.append((index / sides, t))
            if ring:
                here = ring * sides + index
                following = ring * sides + (index + 1) % sides
                faces.append((here - sides, following - sides, following, here))
    faces.extend((tuple(reversed(range(sides))), tuple(range(len(vertices) - sides, len(vertices)))))
    name, material = obj.name, obj.data.materials[0]
    bpy.data.objects.remove(obj, do_unlink=True)
    new = mesh_object(name, vertices, faces, uv, material)
    for face in new.data.polygons:
        face.use_smooth = len(face.vertices) == 4


def eye_facets(obj, sign):
    lo, hi = bounds((obj,))
    center, r = (hi + lo) / 2, (hi - lo) / 2
    verts, faces, uv = [], [], []
    spacing = .021
    material = obj.data.materials[0]
    for row in range(-3, 4):
        for column in range(-4, 5):
            x = (column + .5 * (row % 2)) * spacing
            z = row * spacing * .88
            f = (x / r.x) ** 2 + (z / r.z) ** 2
            if f > .87:
                continue
            y = center.y - r.y * sqrt(1 - f) + sign * x * .09
            origin = len(verts)
            verts.append(center + Vector((x, y - center.y - .0045, z)))
            uv.append((.5, .5))
            for i in range(6):
                a = i * pi / 3
                local_x = x + spacing * .53 * cos(a)
                local_z = z + spacing * .53 * sin(a)
                f_edge = min(.98, (local_x / r.x) ** 2 + (local_z / r.z) ** 2)
                verts.append(center + Vector((local_x,
                             -r.y * sqrt(1 - f_edge) - .0008 + sign * local_x * .09, local_z)))
                uv.append((.5 + .5 * cos(a), .5 + .5 * sin(a)))
            for i in range(6):
                faces.append((origin, origin + 1 + i, origin + 1 + (i + 1) % 6))
    if not faces:
        raise ValueError(f"No facet geometry fits {obj.name}")
    mesh_object(f"Beveled ommatidia {sign}", verts, faces, uv, material)


def tick_form(objects):
    for index in range(1, 6):
        replace_plate(objects[f"Scute {index}"], Vector((0, 0, 1)), index * .77, .14)
    shell_weathering(objects["Head wedge"], .008, 11)
    shell_weathering(objects["Ossuary seed back"], .006, 38, 1)
    skin = objects["Flattened abdomen"].data.materials[0]
    for side in (-1, 1):
        for row in range(4):
            lo, hi = bounds((objects[f"Hinge {side} {row}"],))
            mid = (lo + hi) / 2 + Vector((side * .007, 0, .026))
            tendon_groups(mid, Vector((1, 0, 0)), .053, .024, 4, skin, f"Tick leg {side} {row}")


def mantis_form(objects):
    shell_weathering(objects["Vertical thorax"], .017, 11, 1)
    shell_weathering(objects["Head"], .012, 27, 1)
    for side in (-1, 1):
        eye = objects[f"Compound eye {side}"]
        shader = eye.data.materials[0].node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (.22, .075, .017, 1)
        shader.inputs['Roughness'].default_value = .45
        eye_facets(eye, side)
        shell_weathering(objects[f"Curved raptorial blade {side}"], .012, 28 + side, 3)
        for row in range(4):
            replace_plate(objects[f"Thoracic rib {side} {row}"], Vector((side, 0, 0)), row * 1.1 + side, .12)
        thorax = objects['Vertical thorax'].data.materials[0]
        for index in range(3):
            origin = (side * .146, .091 + index * .161, .814 - index * .126)
            knee = (side * (.55 + index * .018), .007 + index * .155, .613 - index * .072)
            foot = (side * (.705 - index * .042), -.410 + index * .535, .051)
            shape_limb(objects[f'Femur {side} {index}'], origin, knee, (.081, .046), .021 * side)
            shape_limb(objects[f'Shin {side} {index}'], knee, foot, (.051, .024), -.023 * side)
            hinge = objects[f'Leg hinge {side} {index}']
            hinge.data.materials[0] = thorax
            shell_weathering(hinge, .007, 44 + 8 * index + side, 1)
        elbow = objects[f'Raptorial elbow {side}']
        elbow.data.materials[0] = thorax
        shell_weathering(elbow, .009, 17 + side, 1)
        lo, hi = bounds((objects[f"Raptorial elbow {side}"],))
        tendon_groups((lo + hi) / 2 + Vector((side * .022, 0, .055)), Vector((1, 0, 0)),
                      .092, .046, 5, objects["Abdominal taper"].data.materials[0], f"Blade hinge {side}")


def ram_form(objects):
    shell_weathering(objects["Cranial wedge shield"], .036, 37, 4)
    shell_weathering(objects["Forehead median ridge"], .019, 29, 2)
    for side in (-1, 1):
        for i in range(5):
            replace_plate(objects[f"Flank plate {side} {i}"], Vector((side, 0, 0)), i * .92 + side, .19)
        for i in range(4):
            shell_weathering(objects[f"Dorsal collar {side} {i}"], .012, 17 * i + side, 1)
        for end in (0, 1):
            shoulder = objects[f'Shoulder muscle {side} {end}']
            shoulder.data.materials[0] = objects['Low barrel body'].data.materials[0]
            shell_weathering(shoulder, .016, 10 + end * 102 + side, 1)
            lo, hi = bounds((objects[f"Kneecap {side} {end}"],))
            tendon_groups((lo + hi) / 2 + Vector((side * .077, 0, .079)), Vector((1, 0, 0)),
                          .156, .095, 6, objects["Low barrel body"].data.materials[0], f"Knee strain {side} {end}")
            for toe in (-1, 1):
                shell_weathering(objects[f"Cloven hoof {side} {end} {toe}"], .007, 17 * end + toe, 1)


def pincer_form(objects):
    shell_weathering(objects["Slab carapace"], .025, 33, 3)
    for index in range(1, 5):
        replace_plate(objects[f"Carapace buttress {index}"], Vector((0, 0, 1)), index * .61, .21)
    for index, part in enumerate(("impact palm", "fixed sweeping finger", "mobile counterfinger")):
        shell_weathering(objects[f"Large chela {part}"], .017 + index * .004, 52 + index * 19, 4)
    for part in ("Large chela shoulder", "Light appendage exposed hinge"):
        obj = objects[part]
        lo, hi = bounds((obj,))
        center = (lo + hi) / 2 + Vector((0, 0, (hi.z - lo.z) * .42))
        tendon_groups(center, Vector((1, 0, 0)), .18, .09, 6, obj.data.materials[0], part)


RECIPES = dict(zip(ASSETS, (tick_form, mantis_form, ram_form, pincer_form)))


def export_asset(path):
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and any(len(face.vertices) > 4 for face in obj.data.polygons):
            triangulate = obj.modifiers.new('Tangent export triangles', 'TRIANGULATE')
            triangulate.keep_custom_normals = True
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_apply=True,
                              export_tangents=True, use_selection=True)


def check_tangent_channels(path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    scene = json.loads(raw[20:20 + length])
    checked = 0
    for mesh in scene['meshes']:
        for primitive in mesh['primitives']:
            if 'normalTexture' not in scene['materials'][primitive['material']]:
                continue
            assert {'TEXCOORD_0', 'TANGENT'} <= primitive['attributes'].keys(), mesh.get('name')
            checked += 1
    return checked


def statistics(objects):
    for obj in objects:
        obj.data.calc_loop_triangles()
    lo, hi = bounds(objects)
    return {"mesh_objects": len(objects), "triangles": sum(len(obj.data.loop_triangles) for obj in objects),
            "bounds_m": list(hi - lo), "floor_m": float(lo.z)}


def render(path, objects, original_bounds, detail, samples, detail_focus=None,
           camera_direction=(1.32, -1.72, .91)):
    lo, hi = original_bounds
    center = (lo + hi) * .5
    height = (hi - lo).z
    extent = (hi - lo).length
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 820, 625
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("Diffuse neutral fill")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.14, .17, .19, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .25
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, lo.z - .004))
    floor = bpy.data.materials.new("Studio slate")
    floor.diffuse_color = (.067, .076, .072, 1)
    bpy.context.object.data.materials.append(floor)
    for name, direction, factor, color, radius in (
            ("Raking warm key", (-1.6, -1.9, 2.4), 229, (1, .85, .69), .85),
            ("Cool back edge", (1.8, 1.1, 1.9), 222, (.61, .77, 1), .81),
            ("Soft frontal fill", (1.2, -1.3, 1.6), 78, (.88, .93, 1), .95)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.color, light.size = factor * extent ** 2, color, radius * extent
        obj = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(obj)
        obj.location = center + extent * Vector(direction)
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
    target = center
    camera_location = center + extent * Vector(camera_direction)
    if detail:
        target = center + Vector((0, -.18 * extent, .05 * height))
    if detail and detail_focus is not None:
        target = Vector(detail_focus)
        camera_location += target - center
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = extent * (.56 if detail else 1.02)
    scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    for obj in list(bpy.context.scene.objects):
        if obj not in objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def build(name, input_catalog, output, render_samples, refine=None):
    reset()
    original = ORIGINALS / f"{name}.glb"
    reference = list(import_glb(original).values())
    reference_bounds = bounds(reference)
    source_stats = statistics(reference)
    detail_focus = None
    if name == 'MortarLeech':
        lo, hi = reference_bounds
        # Include the upper hooks and feeding collar in the detail view.
        detail_focus = (lo + hi) * .5 + Vector((0, 0, .24 * (hi.z - lo.z)))
    destination = output / name
    destination.mkdir(parents=True, exist_ok=True)
    if render_samples:
        render(destination / 'before.png', reference, reference_bounds, False, render_samples)
        render(destination / 'before_detail.png', reference, reference_bounds, True, render_samples,
               detail_focus=detail_focus)
    reset()
    objects = import_glb(input_catalog / 'catacombs' / original.name)
    (refine or RECIPES[name])(objects)
    path = destination / original.name
    export_asset(path)
    tangent_count = check_tangent_channels(path)
    reset()
    exported = list(import_glb(path).values())
    stats = statistics(exported)
    assert stats['triangles'] > source_stats['triangles'], name
    assert all(abs(new - old) <= max(.016, .045 * old)
               for old, new in zip(source_stats['bounds_m'], stats['bounds_m'])), (name, source_stats, stats)
    assert abs(stats['floor_m'] - source_stats['floor_m']) < .014, name
    if not any(node.type == 'NORMAL_MAP' for mat in bpy.data.materials if mat.use_nodes for node in mat.node_tree.nodes):
        raise RuntimeError(f"Verified source textures did not round-trip for {name}")
    stats['embedded_images'] = len(bpy.data.images)
    stats['textured_primitives_with_tangents'] = tangent_count
    if render_samples:
        render(destination / 'after.png', exported, reference_bounds, False, render_samples)
        render(destination / 'after_detail.png', exported, reference_bounds, True, render_samples,
               detail_focus=detail_focus)
    report = {'asset': name, 'source_sha256': sha256(original.read_bytes()).hexdigest(),
              'result_sha256': sha256(path.read_bytes()).hexdigest(), 'original': source_stats,
              'reimport': stats, 'blender': bpy.app.version_string}
    (destination / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('VERIFIED', report, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_catalog', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--asset', choices=ASSETS, action='append')
    parser.add_argument('--samples', type=int, default=24, help="Use 0 to export and verify geometry only")
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    for name in args.asset or ASSETS:
        build(name, args.input_catalog.resolve(), args.output.resolve(), args.samples)


if __name__ == '__main__':
    main()
