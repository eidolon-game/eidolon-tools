"""Generate the Radura obliqua overlook prototype and preview in Blender."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def material(name, color, roughness):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = (*color, 1)
    shader = result.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return result


def mesh(name, vertices, faces, materials, material_indices=()):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    for surface in materials:
        data.materials.append(surface)
    for polygon, index in zip(data.polygons, material_indices):
        polygon.material_index = index
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def ledge(name, outline, bottom, top, surfaces, seed):
    rng = random.Random(seed)
    center = Vector((sum(x for x, _ in outline) / len(outline), sum(y for _, y in outline) / len(outline)))
    vertices = []
    for factor, height in ((0.94, bottom), (1.0, bottom + 0.055), (1.0, top - 0.045), (0.97, top)):
        for x, y in outline:
            point = center + (Vector((x, y)) - center) * factor
            # Keep the tread planar while letting the exposed edge break along the seam.
            offset = rng.uniform(-0.016, 0.016) if height not in (bottom, top) else 0.0
            vertices.append((*point, height + offset))
    size = len(outline)
    faces = [tuple(reversed(range(size)))]
    indices = [1]
    for row in range(3):
        for index in range(size):
            current = row * size + index
            following = row * size + (index + 1) % size
            faces.append((current, following, following + size, current + size))
            indices.append(rng.choices((0, 1, 2), (4, 5, 1))[0])
    faces.append(tuple(range(3 * size, 4 * size)))
    indices.append(0)
    obj = mesh(name, vertices, faces, surfaces, indices)
    uv = obj.data.uv_layers.new(name="Shale UV")
    for polygon in obj.data.polygons:
        horizontal = abs(polygon.normal.z) > 0.65
        for loop_index in polygon.loop_indices:
            point = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (point.x * 0.14 + 0.5, (point.y if horizontal else point.z) * 0.25 + 0.45)
    return obj


def tube_geometry(points, radii, vertices, faces, sides=7):
    offset = len(vertices)
    for index, (point, radius) in enumerate(zip(points, radii)):
        tangent = (points[min(len(points) - 1, index + 1)] - points[max(0, index - 1)]).normalized()
        axis = tangent.cross(Vector((1, 0, 0))).normalized()
        cross = tangent.cross(axis)
        for side in range(sides):
            spin = math.tau * side / sides
            vertices.append(point + radius * (axis * math.cos(spin) + cross * math.sin(spin)))
    faces.append(tuple(offset + side for side in reversed(range(sides))))
    for row in range(len(points) - 1):
        for side in range(sides):
            current = offset + row * sides + side
            following = offset + row * sides + (side + 1) % sides
            faces.append((current, following, following + sides, current + sides))
    faces.append(tuple(offset + (len(points) - 1) * sides + side for side in range(sides)))


def root_veil(surface, seeds):
    vertices, faces = [], []
    for x, y, height, length, drift in seeds:
        points = [
            Vector((x + drift * t + 0.027 * math.sin(t * 9), y - 0.08 * math.sin(t * math.pi / 2), height - length * t))
            for t in (0, 0.15, 0.3, 0.5, 0.72, 0.9, 1)
        ]
        tube_geometry(points, (0.019, 0.015, 0.013, 0.01, 0.007, 0.004, 0.0015), vertices, faces)
    obj = mesh("Hanging roots", vertices, faces, (surface,))
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def fern(name, center, size, phase, surfaces, rng):
    vertices, faces, indices = [], [], []
    for frond in range(7):
        angle = phase + frond * math.tau / 7 + rng.uniform(-0.13, 0.13)
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        transverse = Vector((-direction.y, direction.x, 0))
        reach = size * rng.uniform(0.69, 1.0)
        rise = size * rng.uniform(0.57, 0.83)

        def position(progress):
            # The last segment bends back inward and downward at the tip.
            return Vector(center) + direction * (reach * math.sin(progress * 1.94)) + Vector((
                0, 0, rise * math.sin(progress * 2.47) + 0.17 * size * progress,
            ))

        radii = (0.008, 0.007, 0.006, 0.0045, 0.0035, 0.0025, 0.0015)
        tube_geometry([position(t) for t in (0, .12, .27, .45, .64, .84, 1)], radii, vertices, faces, 5)
        indices.extend([0] * (len(faces) - len(indices)))
        for leaflet in range(9):
            progress = 0.20 + leaflet * 0.086
            attach = position(progress)
            spread = reach * (0.11 + 0.21 * math.sin(progress * math.pi)) * (1.09 - progress)
            for sign in (-1, 1):
                side = transverse * sign
                base = attach + side * 0.002
                tip = attach + side * spread + direction * (spread * 0.74) + Vector((0, 0, -spread * 0.16))
                midpoint = base.lerp(tip, 0.53)
                rib = midpoint + Vector((0, 0, spread * 0.15))
                offset = len(vertices)
                edge = direction * (spread * 0.23)
                vertices.extend((base, midpoint - edge, tip, midpoint + edge, rib))
                leaf_faces = ((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4))
                if sign > 0:
                    leaf_faces = tuple(tuple(reversed(face)) for face in leaf_faces)
                faces.extend(tuple(offset + index for index in face) for face in leaf_faces)
                indices.extend((1, 1, 2, 2))
    return mesh(name, vertices, faces, surfaces, indices)


def aim(obj, center):
    obj.rotation_euler = (Vector(center) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, location, color, energy, radius):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = energy, color, radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, (0, -0.15, 0.8))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    slate = material("Wet blue shale", (0.071, 0.094, 0.107), 0.80)
    strata = material("Exposed shale seam", (0.041, 0.055, 0.066), 0.84)
    ochre = material("Brown mineral trace", (0.12, 0.095, 0.061), 0.91)
    bark = material("Thin dark root", (0.043, 0.026, 0.013), 0.94)
    stem = material("Fern stem", (0.11, 0.11, 0.04), 0.86)
    leaves = material("Fern green", (0.062, 0.145, 0.065), 0.77)
    ribs = material("Fern folded face", (0.096, 0.193, 0.091), 0.77)
    stone = (slate, strata, ochre)

    formations = [
        ("Buried foundation", [(-2.55, -0.52), (-2.0, -1.07), (-0.76, -1.20), (.65, -1.38), (1.64, -1.21),
                               (2.22, -.45), (2.29, .60), (1.62, 1.27), (-.52, 1.36), (-2.31, .94)], 0.0, .35),
        ("Lower shale plate", [(-2.61, -.55), (-2.19, -1.23), (-1.14, -1.30), (-.42, -1.46), (.69, -1.54),
                               (1.86, -1.36), (2.48, -.64), (2.53, .61), (1.73, 1.35), (-.59, 1.45), (-2.32, .94)], .30, .64),
        ("Slanted seam", [(-2.60, -.52), (-2.26, -1.43), (-1.08, -1.49), (-.16, -1.36), (.87, -1.60),
                          (1.76, -1.30), (2.53, -.72), (2.63, .53), (1.95, 1.31), (-.58, 1.42), (-2.45, .97)], .61, .88),
        ("Walkable upper plate", [(-2.60, -.65), (-2.25, -1.47), (-1.06, -1.62), (-.05, -1.55), (.94, -1.72),
                                  (1.77, -1.43), (2.48, -.96), (2.68, .54), (1.99, 1.31), (0, 1.48),
                                  (-1.47, 1.36), (-2.54, .86)], .84, 1.10),
        ("Rear fern shelf", [(-2.0, .80), (-1.60, .58), (-.93, .64), (0, .71), (.74, .63), (1.45, .76),
                             (1.86, 1.12), (1.25, 1.42), (-.37, 1.41), (-1.65, 1.31)], 1.08, 1.22),
        ("Outer shale fragment", [(1.82, -1.18), (2.21, -1.24), (2.60, -.95), (2.62, -.51),
                                  (2.38, -.57), (1.99, -.84)], 1.04, 1.20),
    ]
    pieces = [ledge(name, outline, low, high, stone, seed + 64)
              for seed, (name, outline, low, high) in enumerate(formations)]
    root_sites = [
        (-1.74,-1.48,1.04,.69,.16), (-1.49,-1.52,1.05,.79,.11), (-1.16,-1.58,1.04,.74,-.12),
        (-.70,-1.56,1.06,.83,.15), (-.52,-1.54,1.04,.91,.09), (-.30,-1.54,1.04,.61,-.10),
        (.14,-1.59,1.04,.76,-.12), (.35,-1.63,1.04,.62,.16), (.59,-1.66,1.05,.80,.13),
        (.95,-1.67,1.04,.78,.08), (1.09,-1.64,1.04,.62,.05), (1.38,-1.54,1.06,.66,.14),
    ]
    pieces.append(root_veil(bark, root_sites))
    rng = random.Random(1247)
    fern_sites = [(-1.72, .97, 1.22, .55), (-1.23, 1.05, 1.22, .40), (-.50, 1.09, 1.22, .53),
                  (.26, 1.07, 1.22, .45), (.93, 1.02, 1.22, .51), (1.39, 1.06, 1.22, .38),
                  (2.33, -.91, 1.20, .46), (2.51, -.77, 1.20, .32), (-1.87, -1.13, 1.10, .35)]
    for index, (x, y, z, size) in enumerate(fern_sites):
        pieces.append(fern(f"Curl fern {index + 1}", (x, y, z), size, rng.random() * math.tau,
                           (stem, leaves, ribs), rng))

    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[3]
    bpy.ops.export_scene.gltf(filepath=str(output / "oblique_clearing_overlook.glb"), export_format="GLB",
                              use_selection=True)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.005))
    bpy.context.object.data.materials.append(material("Preview floor", (0.025, 0.031, 0.032), 0.91))
    world = bpy.data.worlds.new("Overcast fill")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.20, 0.27, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.33
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (3.5, -9.6, 5.2)
    aim(camera, (0.0, -.09, .76))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 6.60
    scene.camera = camera
    light("Overcast key", (-3.1, -3.0, 5.2), (0.71, 0.83, 1.0), 820, 3.2)
    light("Warm rim", (2.4, 3.2, 3.5), (1.0, 0.70, 0.41), 695, 2.1)
    light("Low blue fill", (2.6, -4.9, 1.5), (0.63, 0.78, 1.0), 124, 2.6)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 880
    scene.render.resolution_y = 580
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "oblique_clearing_overlook.png")
    scene["asset_status"] = "prototype_pending_unreal_import_collision_and_visual_review"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "oblique_clearing_overlook.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
