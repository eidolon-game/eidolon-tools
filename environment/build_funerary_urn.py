"""Generate an original static funerary urn for EIDOLON in Blender."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def surface(name, color, metal, roughness):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    return material


def revolve(name, profile, material, *, closed=False, segments=64):
    vertices = []
    for radius, height in profile:
        vertices.extend(
            (radius * math.cos(math.tau * index / segments),
             radius * math.sin(math.tau * index / segments), height)
            for index in range(segments)
        )
    faces = [] if closed else [tuple(reversed(range(segments)))]
    section = profile + [profile[0]] if closed else profile
    for row in range(len(section) - 1):
        lower = row * segments
        upper = (lower + segments) % len(vertices)
        for index in range(segments):
            following = (index + 1) % segments
            faces.append((lower + index, lower + following, upper + following, upper + index))
    if not closed:
        faces.append(tuple(range(len(vertices) - segments, len(vertices))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Surface UV")
    cumulative = [0.0]
    for first, second in zip(section, section[1:]):
        cumulative.append(cumulative[-1] + math.dist(first, second))
    side_polygons = mesh.polygons[:] if closed else mesh.polygons[1:-1]
    for polygon in side_polygons:
        polygon.use_smooth = True
        row, index = divmod(polygon.index - int(not closed), segments)
        left, right = index / segments, (index + 1) / segments
        bottom = cumulative[row] / cumulative[-1] * 0.8
        top = cumulative[row + 1] / cumulative[-1] * 0.8
        for loop_index, coordinates in zip(polygon.loop_indices, ((left, bottom), (right, bottom), (right, top), (left, top))):
            uv.data[loop_index].uv = coordinates
    if not closed:
        for polygon, offset, radius in ((mesh.polygons[0], 0.25, profile[0][0]),
                                        (mesh.polygons[-1], 0.75, profile[-1][0])):
            for loop_index in polygon.loop_indices:
                vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
                uv.data[loop_index].uv = (offset + 0.08 * vertex.x / radius, 0.90 + 0.08 * vertex.y / radius)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def seal_mesh(material):
    # Individual ridges outline a fractured lozenge across the middle band.
    vertices, faces = [], []
    for sector in range(8):
        angle = math.tau * sector / 8
        for start, end in (((-0.11, 0.41), (0, 0.46)), ((0, 0.46), (0.11, 0.41)),
                           ((0.11, 0.41), (0.02, 0.36)), ((-0.02, 0.36), (-0.11, 0.41))):
            offset = len(vertices)
            for radial in (0.265, 0.276):
                for theta, height in ((start[0], start[1] - 0.004), (end[0], end[1] - 0.004),
                                      (end[0], end[1] + 0.004), (start[0], start[1] + 0.004)):
                    vertices.append((radial * math.cos(angle + theta), radial * math.sin(angle + theta), height))
            faces.extend(tuple(offset + index for index in face) for face in
                         ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                          (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)))
    mesh = bpy.data.meshes.new("Fractured seal ridges")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Fractured seal ridges", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_light(name, position, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = power, color, size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, 0, 0.37))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    stone = surface("Basalt", (0.065, 0.075, 0.086), 0.0, 0.81)
    bronze = surface("Oxidized bronze", (0.21, 0.099, 0.045), 0.72, 0.44)
    patina = surface("Seal traces", (0.089, 0.20, 0.149), 0.55, 0.56)
    body = revolve("Basalt urn body", [
        (0.145, 0.0), (0.163, 0.014), (0.164, 0.040), (0.149, 0.059),
        (0.145, 0.084), (0.176, 0.130), (0.216, 0.181), (0.248, 0.252),
        (0.266, 0.336), (0.267, 0.452), (0.250, 0.503), (0.211, 0.551),
        (0.152, 0.582), (0.142, 0.606), (0.142, 0.639), (0.159, 0.650),
        (0.159, 0.665), (0.127, 0.665), (0.127, 0.615), (0.118, 0.591),
    ], stone)
    lid = revolve("Basalt lid", [
        (0.157, 0.667), (0.162, 0.677), (0.156, 0.698), (0.123, 0.715),
        (0.082, 0.728), (0.034, 0.730), (0.033, 0.752), (0.043, 0.763),
        (0.035, 0.783), (0.021, 0.790),
    ], stone)
    lower = revolve("Lower bronze band", [(0.257, 0.325), (0.270, 0.331), (0.273, 0.343),
                                           (0.269, 0.350), (0.257, 0.349)], bronze, closed=True)
    upper = revolve("Upper bronze band", [(0.260, 0.465), (0.271, 0.469),
                                           (0.268, 0.482), (0.258, 0.488),
                                           (0.252, 0.486), (0.252, 0.465)], bronze, closed=True)
    traces = seal_mesh(patina)

    bpy.ops.object.select_all(action="DESELECT")
    for piece in (body, lid, lower, upper, traces):
        piece.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.export_scene.gltf(
        filepath=str(output / "valdris_funerary_urn.glb"), export_format="GLB", use_selection=True,
    )

    # Preview-only ground, lights and camera are excluded from the game export.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
    bpy.context.object.data.materials.append(surface("Preview floor", (0.047, 0.045, 0.047), 0.0, 0.86))
    world = bpy.data.worlds.new("Low fill")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.14, 0.18, 0.25, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.22
    camera = bpy.data.objects.new("Preview camera", bpy.data.cameras.new("Preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (1.38, -2.48, 1.27)
    aim(camera, (0, 0, 0.40))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.13
    scene.camera = camera
    add_light("Warm key", (0.4, -1.2, 1.33), (1.0, 0.76, 0.52), 115, 0.61)
    add_light("Cool rim", (-0.85, 0.47, 0.92), (0.50, 0.69, 1.0), 125, 0.51)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "valdris_funerary_urn.png")
    scene["asset_status"] = "prototype_pending_unreal_import_and_art_review"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "valdris_funerary_urn.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
