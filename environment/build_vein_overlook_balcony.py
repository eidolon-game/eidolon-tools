"""Generate the original Vein Overlook quarry balcony with Blender."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def surface(name, rgb, roughness, grain):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    tree = material.node_tree
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = grain
    noise.inputs["Detail"].default_value = 4
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .32
    bump.inputs["Distance"].default_value = .040
    tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def mesh(name, vertices, faces, materials):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        data.materials.append(material)
    return obj


def layer(name, outline, bottom, top, surfaces, seed):
    randomizer = random.Random(seed)
    centroid = Vector((sum(point[0] for point in outline), sum(point[1] for point in outline))) / len(outline)
    count = len(outline)
    vertices = []
    rings = ((.90, bottom), (1.0, bottom + .070), (1.0, top - .050), (.97, top))
    for row, (scale, z) in enumerate(rings):
        for point in outline:
            x, y = centroid + (Vector(point) - centroid) * scale
            level = z + (randomizer.uniform(-.020, .020) if row in (1, 2) else 0)
            vertices.append((x, y, level))
    faces = [tuple(reversed(range(count)))]
    for row in range(3):
        for index in range(count):
            a = row * count + index
            b = row * count + (index + 1) % count
            faces.append((a, b, b + count, a + count))
    faces.append(tuple(range(3 * count, 4 * count)))
    obj = mesh(name, vertices, faces, surfaces)
    uv = obj.data.uv_layers.new(name="Open quarry UV")
    for polygon in obj.data.polygons:
        horizontal = abs(polygon.normal.z) > .65
        polygon.material_index = 0 if horizontal else randomizer.choices((0, 1, 2), (2, 5, 1))[0]
        for index in polygon.loop_indices:
            point = obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv = (.16 * point.x + .50, .18 * (point.y if horizontal else point.z) + .46)
    return obj


def cut_stone(name, center, dimensions, material, width=.028, seed=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if seed is not None:
        rng = random.Random(seed)
        for vertex in obj.data.vertices:
            vertex.co.x *= rng.uniform(.96, 1.03)
            vertex.co.y *= rng.uniform(.95, 1.04)
            vertex.co.z *= rng.uniform(.97, 1.03)
    obj.data.materials.append(material)
    edge = obj.modifiers.new("Rounded quarry breaks", "BEVEL")
    edge.width = width
    edge.segments = 2
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def stone_bar(name, start, end, sections, material, bevel):
    start, end = Vector(start), Vector(end)
    obj = cut_stone(name, (start + end) / 2, (*sections, (end - start).length), material, bevel)
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def root(name, positions, sizes, material):
    centers = [Vector(point) for point in positions]
    vertices = []
    sides = 8
    for row, (center, radius) in enumerate(zip(centers, sizes)):
        tangent = (centers[min(row + 1, len(centers) - 1)] - centers[max(0, row - 1)]).normalized()
        reference = Vector((0, 1, 0)) if abs(tangent.y) < .95 else Vector((1, 0, 0))
        edge = tangent.cross(reference).normalized()
        cross = tangent.cross(edge)
        for index in range(sides):
            angle = math.tau * index / sides
            vertices.append(center + radius * (edge * math.cos(angle) + cross * math.sin(angle)))
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(centers) - 1):
        for index in range(sides):
            a = row * sides + index
            b = row * sides + (index + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    obj = mesh(name, vertices, faces, (material,))
    for polygon in obj.data.polygons[1:-1]:
        polygon.use_smooth = True
    return obj


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_light(name, center, rgb, energy, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = energy, rgb, size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    aim(obj, (0, 0, .64))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    stone = surface("Dry fissured blue-black rock", (.066, .092, .110), .88, 16)
    vein = surface("Dusk slate seam", (.032, .047, .062), .92, 19)
    dust = surface("Dry ochre quarry traces", (.142, .111, .069), .93, 22)
    tread = surface("Dry worked tread", (.145, .170, .175), .91, 29)
    guard = surface("Dark dressed guard stone", (.107, .130, .137), .86, 27)
    seat = surface("Polished wear on stone seat", (.159, .176, .172), .78, 24)
    bark = surface("Roots retreating into seam", (.067, .044, .030), .92, 18)

    outline = [(-2.66,-1.95),(-2.05,-2.33),(-.93,-2.50),(.20,-2.43),(1.82,-2.39),
               (2.66,-1.90),(2.73,-.33),(2.65,1.66),(1.98,1.98),(.25,2.04),
               (-1.21,1.99),(-2.39,1.80),(-2.71,.64)]
    parts = []
    ranges = ((.84, -.119, .194), (.91, .16, .432), (.97, .408, .682), (1, .641, .950))
    for index, (factor, low, high) in enumerate(ranges):
        shift_x = -.04 * (3 - index)
        outline_scaled = [(x * factor + shift_x, y * factor + .03 * (3 - index)) for x, y in outline]
        layer_materials = (tread if index == 3 else stone, vein, dust)
        parts.append(layer(f"Quarry rock course {index + 1}", outline_scaled, low, high, layer_materials, 80 + index))

    # Low cut-stone guard along the drop. Clear upper travel is behind it.
    parapet = [
        (-2.16,-1.86,-1.40,-2.025),
        (-1.40,-2.025,-.45,-2.092),
        (-.45,-2.092,.59,-2.075),
        (.59,-2.075,1.54,-2.016),
        (1.54,-2.016,2.14,-1.84),
    ]
    for index, (x, y, next_x, next_y) in enumerate(parapet):
        parts.append(stone_bar(f"Cut guard base {index + 1}", (x,y,1.103),(next_x,next_y,1.103),
                              (.28,.33), guard, .038))
        parts.append(stone_bar(f"Guard cap {index + 1}", (x,y,1.312),(next_x,next_y,1.312),
                              (.117,.39), seat, .025))
    for x, y in ((-2.16,-1.86), (-1.40,-2.025), (.59,-2.075), (2.14,-1.84)):
        parts.append(cut_stone(f"Cut parapet post {x}", (x,y,1.183), (.29,.34,.47), guard, .033))

    # The carved bench and residual spine sit outside the three-metre route.
    for y in (-.39, .54):
        parts.append(cut_stone(f"Bench lobe {y}", (2.083,y,1.131), (.45,.33,.40), stone, .074, 77))
    bench = [ (1.781,-.712), (2.330,-.703), (2.466,-.475), (2.455,.683),
              (2.285,.873), (1.799,.819), (1.736,.690), (1.745,-.562) ]
    parts.append(layer("Carved lookout seat", bench, 1.270, 1.485, (seat, stone, dust), 91))
    parts.append(cut_stone("Bench rough back", (2.390,.10,1.617), (.37,1.70,.46), stone, .075, 96))
    for index, center, dimensions in (
        (1,(-2.43,.85,1.212),(.46,1.72,.55)), (2,(-2.32,1.25,1.539),(.55,.78,.48)),
        (3,(-2.42,1.47,1.827),(.45,.55,.37)), (4,(-2.30,.51,1.096),(.54,.71,.31)),
    ):
        parts.append(cut_stone(f"Remaining quarry spine {index}", center, dimensions, stone, .067, 180 + index))
    for name, points, radii in [
        ("Root drawing into left seam", [(-2.30,1.64,1.91),(-2.43,1.30,1.59),(-2.59,.79,1.38),
                                          (-2.63,.57,.98),(-2.69,.26,.69),(-2.59,-.03,.43)],
         (.049,.057,.051,.038,.028,.008)),
        ("Root fork in seam", [(-2.62,.60,1.03),(-2.56,.26,.81),(-2.62,-.10,.54),(-2.64,-.42,.29)],
         (.036,.031,.022,.008)),
        ("Receding ravine root", [(2.58,.98,1.24),(2.72,.76,1.10),(2.69,.36,.87),
                                   (2.75,.16,.59),(2.61,-.31,.33)],
         (.034,.050,.039,.033,.010)),
    ]:
        parts.append(root(name, points, radii, bark))
    # Dark ochre chips under the parapet mark quarrying without entering the tread.
    for index in range(8):
        x = -1.77 + index * .422
        start = (x,-1.755+(.035 if index%2 else 0),.956)
        end = (x+.047,-1.719+(.035 if index%2 else 0),.957)
        parts.append(stone_bar(f"Quarry scar {index + 1}", start, end, (.013,.013), dust, .003))

    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[3]
    bpy.ops.export_scene.gltf(filepath=str(output / "vein_overlook_balcony.glb"), export_format="GLB",
                              use_selection=True, export_apply=True)
    bpy.ops.mesh.primitive_plane_add(size=150, location=(0, 0, -.136))
    bpy.context.object.data.materials.append(surface("Matte preview earth", (.027, .039, .047), .88, 20))
    world = bpy.data.worlds.new("Dim cavern air")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.15, .23, .32, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .29
    camera = bpy.data.objects.new("Balcony preview camera", bpy.data.cameras.new("Balcony preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (3.98, -8.36, 6.46)
    aim(camera, (0, -.16, .76))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 7.28
    scene.camera = camera
    add_light("Light from shaft", (-2.9, -3.1, 5.3), (.64, .82, 1), 1020, 2.9)
    add_light("Pale mineral rim", (3.7, 2.2, 4.5), (1, .72, .48), 1180, 2.5)
    add_light("Lower cavern fill", (2.1, -4.0, 1.46), (.66, .81, .93), 230, 2.7)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 38
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 900
    scene.render.resolution_y = 680
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / "vein_overlook_balcony.png")
    scene["asset_status"] = "prototype_pending_unreal_import_and_route_collision"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "vein_overlook_balcony.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
