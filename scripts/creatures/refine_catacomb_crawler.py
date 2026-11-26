"""Refine the Catacomb Crawler mesh while preserving its size and six-leg silhouette.

Run: blender -b -t 4 --python-exit-code 1 --python scripts/creatures/refine_catacomb_crawler.py -- SOURCE.glb OUTPUT
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def set_surface(material, color, roughness):
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Specular IOR Level"].default_value = 0.32
    return material


def loft(name, rings, materials, bands, smooth=False):
    sides = len(rings[0])
    vertices = [vertex for ring in rings for vertex in ring]
    faces = [tuple(reversed(range(sides)))]
    for level in range(len(rings) - 1):
        for index in range(sides):
            next_index = (index + 1) % sides
            faces.append((
                level * sides + index, level * sides + next_index,
                (level + 1) * sides + next_index, (level + 1) * sides + index,
            ))
    faces.append(tuple((len(rings) - 1) * sides + index for index in range(sides)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()
    for material in materials:
        mesh.materials.append(material)

    uv = mesh.uv_layers.new(name="UVMap")
    end = len(mesh.polygons) - 1
    for polygon in mesh.polygons:
        index = polygon.index
        is_cap = index in (0, end)
        polygon.use_smooth = smooth and not is_cap
        if is_cap:
            polygon.material_index = bands[0] if index == 0 else bands[-1]
        else:
            polygon.material_index = bands[(index - 1) // sides]
        for corner in polygon.loop_indices:
            vertex_index = mesh.loops[corner].vertex_index
            ring, side = divmod(vertex_index, sides)
            if is_cap:
                angle = math.tau * side / sides
                middle = 0.80 if index == 0 else 0.93
                uv.data[corner].uv = (middle + math.cos(angle) * 0.055, 0.70 + math.sin(angle) * 0.055)
            else:
                seam = (index - 1) % sides == sides - 1
                u = 1.0 if side == 0 and seam else side / sides
                uv.data[corner].uv = (u * 0.70, ring / (len(rings) - 1) * 0.95)

    topology = bmesh.new()
    try:
        topology.from_mesh(mesh)
        bmesh.ops.triangulate(topology, faces=[face for face in topology.faces if len(face.verts) > 4])
        topology.to_mesh(mesh)
    finally:
        topology.free()
    mesh.update()

    object_ = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(object_)
    return object_


def shell(name, center, radii, phase, materials, angle_offset=0.0):
    profiles = (
        (0.16, -0.72), (0.78, -0.63), (0.99, -0.34), (1.0, -0.24),
        (0.96, -0.13), (0.99, 0.01), (0.92, 0.28), (0.73, 0.61),
        (0.43, 0.88), (0.15, 0.98),
    )
    sides = 32
    notches = ((phase * 7 + 3) % sides, (phase * 9 + 17) % sides)
    rings = []
    for level, (radius, height) in enumerate(profiles):
        ring = []
        for index in range(sides):
            angle = math.tau * index / sides
            distance = min(min((index - notch) % sides, (notch - index) % sides) for notch in notches)
            chip = (1.0 - distance * 0.5) * (0.20 if 2 <= level <= 6 else 0.04) if distance < 2 else 0.0
            ridge = 0.031 * math.sin(angle * 5 + phase) + 0.025 * math.sin(angle * 11 - phase)
            spread = radius * (1.0 + ridge - chip)
            x = math.cos(angle) * radii[0] * spread
            y = math.sin(angle) * radii[1] * spread
            yaw_x = x * math.cos(angle_offset) - y * math.sin(angle_offset)
            yaw_y = x * math.sin(angle_offset) + y * math.cos(angle_offset)
            z = (height + 0.058 * math.sin(angle * 3 + phase) - chip * 0.52) * radii[2]
            ring.append((center[0] + yaw_x, center[1] + yaw_y, center[2] + z))
        rings.append(ring)
    return loft(name, rings, materials, [1, 1, 2, 1, 2, 0, 0, 0, 0], smooth=True)


def crest_spur(index, y, keratin, fracture):
    heights = (0.39, 0.47, 0.52, 0.34, 0.465, 0.405, 0.31)
    height = heights[index]
    drift = (-0.04, 0.025, -0.025, 0.075, 0.045, -0.057, -0.024)[index]
    rings = []
    profiles = ((0.0, 0.106), (0.19, 0.109), (0.45, 0.078), (0.62, 0.064), (0.87, 0.047), (1.0, 0.024))
    for fraction, radius in profiles:
        ring = []
        for point in range(10):
            angle = math.tau * point / 10
            thickness = radius * (1.0 + 0.17 * math.sin(3 * angle + index))
            x = drift * fraction + math.cos(angle) * thickness
            local_y = y + fraction * (0.23 + index * 0.01) + math.sin(angle) * thickness * 1.2
            fracture_height = 0.027 * math.cos(angle + index) if fraction >= 0.87 else 0.0
            z = 1.455 + fraction * height + fracture_height
            ring.append((x, local_y, z))
        rings.append(ring)
    loft(f"Fractured dorsal spur {index + 1}", rings, (keratin, fracture), [0, 0, 0, 0, 1])


def sinew(name, points, radius, material, phase):
    paths = [Vector(point) for point in points]
    rings = []
    for index, point in enumerate(paths):
        axis = (paths[min(index + 1, len(paths) - 1)] - paths[max(0, index - 1)]).normalized()
        reference = Vector((0, 0, 1)) if abs(axis.z) < 0.85 else Vector((0, 1, 0))
        u = axis.cross(reference).normalized()
        v = axis.cross(u)
        thickness = radius * (0.82 + 0.18 * math.sin(index + phase))
        rings.append([
            tuple(point + thickness * (u * math.cos(math.tau * n / 8) + v * math.sin(math.tau * n / 8)))
            for n in range(8)
        ])
    loft(name, rings, (material,), [0] * (len(rings) - 1), smooth=True)


def refine_geometry():
    surfaces = bpy.data.materials
    for name, color, roughness in (
        ("Wet fascia", (0.024, 0.014, 0.012), 0.62),
        ("Exposed throat", (0.136, 0.021, 0.016), 0.53),
        ("Aged bone", (0.29, 0.22, 0.14), 0.75),
        ("Dark bone", (0.18, 0.12, 0.072), 0.81),
        ("Pale weathered bone", (0.42, 0.32, 0.20), 0.78),
        ("Blue-black keratin", (0.025, 0.036, 0.039), 0.59),
        ("Worn tooth enamel", (0.47, 0.35, 0.19), 0.62),
        ("Clouded amber eyes", (0.46, 0.19, 0.031), 0.38),
    ):
        set_surface(surfaces[name], color, roughness)

    chalk = set_surface(surfaces.new("Calcified chalk edge"), (0.355, 0.269, 0.164), 0.84)
    stratum = set_surface(surfaces.new("Lamellar dark fracture"), (0.114, 0.076, 0.047), 0.88)
    damaged_keratin = set_surface(surfaces.new("Fractured keratin crest"), (0.105, 0.100, 0.081), 0.79)
    fascia = set_surface(surfaces.new("Stretched fascia"), (0.092, 0.029, 0.021), 0.62)
    bone = [surfaces[name] for name in ("Aged bone", "Dark bone", "Pale weathered bone")]
    keratin = surfaces["Blue-black keratin"]

    original = bpy.data.objects
    for index in range(7):
        bpy.data.objects.remove(original[f"Dorsal plate {index + 1}"], do_unlink=True)
        bpy.data.objects.remove(original[f"Dorsal spur {index + 1}"], do_unlink=True)
        y = -0.54 + index * 0.27
        width = 0.51 - max(index - 3, 0) * 0.052
        center = (0.012 * math.sin(2.0 * index), y, 1.315 - max(index - 5, 0) * 0.024)
        shell(f"Chipped dorsal lamella {index + 1}", center, (width, 0.213, 0.214),
              index + 1, (bone[index % 3], stratum, chalk), (-1) ** index * 0.094)
        crest_spur(index, y, keratin, damaged_keratin)

    skull = original["Skull"]
    for vertex in skull.data.vertices:
        x, y, z = vertex.co
        soften = 0.013 * math.sin(x * 37 + y * 17) * math.cos(z * 31)
        vertex.co.x = x * (1.0 + 0.032 * math.sin(y * 17))
        vertex.co.z = z * (1.0 + 0.047 * math.sin(x * 19)) + soften
    for side in (-1, 1):
        brow = (side * 0.165, -1.126, 1.245)
        shell(f"Cleaved cranial lamella {side}", brow, (0.207, 0.29, 0.188), 13 + side,
              (bone[0], stratum, chalk), side * 0.24)
        for index in range(3):
            name = f"Knee plate {side} {index}"
            knee = tuple(original[name].location)
            bpy.data.objects.remove(original[name], do_unlink=True)
            center = (knee[0], knee[1] - 0.012, knee[2] + 0.018)
            shell(f"Overlapping knee lamella {side} {index}", center, (0.177, 0.183, 0.159),
                  17 + index * 3 + side, (bone[0], stratum, chalk), side * 0.38)
            for strand in range(4):
                x, y, z = knee
                gap = (strand - 1.5) * 0.027
                sinew(f"Joint fibre {side} {index} {strand}", (
                    (x - side * 0.21, y - 0.088 + gap, z - 0.05),
                    (x - side * 0.12, y - 0.122 + gap, z - 0.085),
                    (x - side * 0.055, y - 0.136 + gap, z - 0.126),
                    (x + side * 0.044, y - 0.085 + gap, z - 0.25),
                ), 0.011 + (strand % 2) * 0.002, fascia, strand)

        for strand in range(5):
            displace = strand * 0.026
            sinew(f"Exposed throat fibre {side} {strand}", (
                (side * (0.18 + displace), -1.19, 0.84 + displace * 0.28),
                (side * (0.23 + displace), -1.105, 0.75),
                (side * (0.28 + displace), -0.97, 0.78),
                (side * (0.30 + displace), -0.78, 0.89 + displace * 0.17),
            ), 0.010 + (strand % 2) * 0.004, fascia, strand)


def aim(object_, target):
    object_.rotation_euler = (Vector(target) - object_.location).to_track_quat("-Z", "Y").to_euler()


def area(name, location, power, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.shape, data.size = power, color, "DISK", size
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = location
    aim(light, (0, 0, 1.0))


def build(source, output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    refine_geometry()

    bpy.ops.object.select_all(action="DESELECT")
    for object_ in scene.objects:
        if object_.type == "MESH":
            object_.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output / "CatacombCrawler.glb"), export_format="GLB",
                              use_selection=True, export_normals=True, export_texcoords=True, export_tangents=True)

    slate = set_surface(bpy.data.materials.new("Preview damp slate"), (0.061, 0.064, 0.060), 0.87)
    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.object.name = "Preview floor"
    bpy.context.object.data.materials.append(slate)
    area("Broad warm key", (-3, -3, 4), 585, (1, 0.82, 0.64), 3.1)
    area("Cool vault rim", (2, 3, 4), 800, (0.58, 0.74, 1.0), 2.7)
    area("Detail fill", (3, -4, 2), 225, (0.81, 0.85, 1.0), 2.1)
    scene.world = bpy.data.worlds.new("Catacomb atmosphere")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.136, 0.15, 0.17, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.26
    bpy.ops.object.camera_add(location=(4.25, -5.85, 3.0))
    scene.camera = bpy.context.object
    scene.camera.data.lens = 53
    aim(scene.camera, (0, -0.065, 0.95))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1120
    scene.render.resolution_y = 840
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "CatacombCrawler.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "CatacombCrawler.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    first = sys.argv.index("--") + 1
    source_glb, output_dir = (Path(argument).resolve() for argument in sys.argv[first:])
    output_dir.mkdir(parents=True, exist_ok=True)
    build(source_glb, output_dir)
