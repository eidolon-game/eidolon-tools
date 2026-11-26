"""Generate EIDOLON's original Riftroot Tangle floor-20 prototype in Blender."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def surface(name, color, roughness, grain=None):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    tree = material.node_tree
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    if grain is not None:
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = grain
        noise.inputs["Detail"].default_value = 4
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .41
        bump.inputs["Distance"].default_value = .059
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


def rock(name, center, size, rotation, materials, seed, layers=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=layers, radius=1, location=center)
    obj = bpy.context.object
    obj.name = name
    rng = random.Random(seed)
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        periodic = .11 * math.sin(5.4*x - 5.9*y + 4.7*z)
        factor = 1 + periodic + rng.uniform(-.074, .074)
        vertex.co.x *= factor
        vertex.co.y *= factor
        vertex.co.z = min(.86, max(-.88, vertex.co.z * factor))
    obj.data.update()
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = rotation
    for material in materials:
        obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        choice = rng.random()
        polygon.material_index = 0
        if len(materials) > 1 and choice < .19:
            polygon.material_index = 1
        if len(materials) > 2 and choice > .92:
            polygon.material_index = 2
    return obj


def root(name, path, radii, materials, phase=0, sides=10):
    centers = [Vector(point) for point in path]
    vertices = []
    for row, (center, radius) in enumerate(zip(centers, radii)):
        tangent = (centers[min(row + 1, len(centers) - 1)] - centers[max(0, row - 1)]).normalized()
        reference = Vector((1, 0, 0)) if abs(tangent.x) < .92 else Vector((0, 1, 0))
        edge = tangent.cross(reference).normalized()
        fore = tangent.cross(edge)
        for spoke in range(sides):
            angle = math.tau * spoke / sides
            ridge = 1 + .14 * math.cos(3 * angle + .7 * row + phase)
            vertices.append(center + radius * ridge * (edge * math.cos(angle) + .84 * fore * math.sin(angle)))
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(centers) - 1):
        for spoke in range(sides):
            start = row * sides + spoke
            following = row * sides + (spoke + 1) % sides
            faces.append((start, following, following + sides, start + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    obj = mesh(name, vertices, faces, materials)
    uv = obj.data.uv_layers.new(name="Root grain UV")
    for polygon in obj.data.polygons[1:-1]:
        row, spoke = divmod(polygon.index - 1, sides)
        polygon.use_smooth = True
        polygon.material_index = int(len(materials) > 1 and (spoke + int(phase)) % 5 == 1)
        left, right = spoke / sides, (spoke + 1) / sides
        bottom, top = row / (len(centers) - 1), (row + 1) / (len(centers) - 1)
        for loop, coordinates in zip(polygon.loop_indices, ((left,bottom),(right,bottom),(right,top),(left,top))):
            uv.data[loop].uv = coordinates
    return obj


def cavity(dark, fissure):
    center_x, center_z = -.43, 1.80
    rim = [(-.48,-.27),(-.52,.05),(-.30,.32),(-.07,.33),(.21,.21),(.33,-.02),
           (.22,-.24),(.02,-.32),(-.24,-.36)]
    vertices = [(center_x + x, -1.44 + .15 * math.sin(index * 2.0), center_z + z)
                for index, (x,z) in enumerate(rim)]
    vertices.extend((center_x + x*.62, -1.19, center_z + z*.62) for x,z in rim)
    vertices.append((center_x + .018, -1.148, center_z - .021))
    faces = []
    count = len(rim)
    for index in range(count):
        following = (index + 1) % count
        faces.append((following,index,index+count,following+count))
        faces.append((following+count,index+count,count*2))
    obj = mesh("Asymmetric exposed cavity", vertices, faces, (dark, fissure))
    for polygon in obj.data.polygons:
        polygon.material_index = int(polygon.index % 7 in (2, 4))
    return obj


def attach(obj, parent):
    bpy.context.view_layer.update()
    transform = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = transform


def group(name, location, parts):
    parent = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(parent)
    parent.location = location
    for obj in parts:
        attach(obj, parent)
    return parent


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z","Y").to_euler()


def light(name, position, color, power, radius):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = power, radius, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, 0, 1.16))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    slate = surface("Abyss dark shale", (.058,.083,.104), .83, 19)
    stratum = surface("Blue fissure stratum", (.095,.130,.145), .84, 28)
    quartz = surface("Pale mineral fracture", (.175,.192,.158), .89, 22)
    bark = surface("Living dark root", (.115,.050,.025), .88, 17)
    sap = surface("Fresh root fracture", (.229,.111,.051), .82, 24)
    fissure = surface("Cavity inner scar", (.130,.055,.029), .87, 25)
    void = surface("Recessed slate shadow", (.013,.022,.025), .95)
    rocks = (slate,stratum,quartz)
    roots = (bark,sap)

    core_rocks = [
        ("Main fused shale carapace",(0,.24,1.88),(2.59,2.67,1.45),(.13,-.19,.21)),
        ("Crown shear slab",(-.23,.37,2.62),(2.12,1.38,.78),(-.24,.18,.28)),
        ("Rear shell mass",(.58,1.38,1.73),(1.78,1.51,1.32),(-.14,.28,.21)),
        ("Rear dragged stone",(-.48,1.78,1.01),(1.43,1.25,.89),(.24,.11,-.34)),
        ("Left cavity jaw",(-.99,-.80,1.54),(.93,1.01,.81),(.16,-.20,.31)),
        ("Right broken breast slab",(.53,-.90,1.45),(1.00,1.22,1.05),(-.19,.30,-.24)),
        ("Cavity crooked brow",(-.53,-.99,2.22),(1.33,.93,.62),(-.18,.19,-.22)),
        ("Submerged underside keel",(.10,.19,.94),(1.73,1.93,.62),(.02,-.18,-.13)),
        ("Right shell spur",(1.05,.65,2.25),(.96,1.35,.72),(.24,.22,.15)),
        ("Left shell spur",(-1.10,.33,2.08),(.84,1.48,.75),(-.17,.25,-.20)),
    ]
    carapace = [rock(name, center, dimensions, rotation, rocks, 49 + index)
                for index,(name,center,dimensions,rotation) in enumerate(core_rocks)]
    carapace.append(cavity(void,fissure))
    straps = [
        ("Main scar root", [(-1.0,-1.32,1.59),(-1.07,-1.24,1.99),(-.92,-.88,2.47),(-.60,-.40,2.76),
                           (-.37,.10,2.95),(-.18,.69,2.84),(.09,1.37,2.28),(.22,2.03,1.71)],
         (.11,.126,.13,.15,.153,.131,.105,.036)),
        ("Crossing braid",[(1.05,-1.30,1.33),(.89,-1.26,1.94),(.56,-1.10,2.42),(.12,-.42,2.93),
                           (-.36,.24,3.00),(-.83,.72,2.64),(-1.16,1.15,2.11),(-.71,1.63,1.38)],
         (.076,.108,.117,.13,.13,.12,.093,.039)),
        ("Left low bloodroot",[(-.99,-1.38,1.48),(-.68,-1.42,1.45),(-.48,-1.44,1.39),(-.25,-1.42,1.44),
                                (.24,-1.29,1.60),(.74,-.94,1.82),(1.18,-.27,1.68),(1.28,.47,1.48)],
         (.063,.072,.07,.065,.09,.098,.11,.044)),
        ("Rear girdle root",[(1.03,-.28,1.87),(1.19,.36,2.36),(1.18,.98,2.37),(.95,1.53,2.10),
                             (.64,1.89,1.77),(.02,2.12,1.48),(-.54,2.22,1.24),(-1.03,1.79,1.11)],
         (.065,.102,.113,.113,.105,.10,.081,.031)),
        ("Fissure edge root",[(-.90,-1.36,2.16),(-.74,-1.50,2.06),(-.53,-1.51,2.10),(-.34,-1.49,2.05),
                               (-.15,-1.46,1.91),(-.09,-1.39,1.66),(.14,-1.35,1.40)],
         (.049,.054,.056,.062,.054,.052,.021)),
        ("Right braid underside",[(.21,-.77,1.10),(.63,-.81,.94),(1.00,-.40,.98),(1.25,.30,1.09),
                                  (1.18,.87,1.24),(.77,1.24,1.43),(.50,1.51,1.92)],
         (.048,.08,.11,.098,.094,.08,.036)),
        ("Left narrow cross seam",[(-.25,-.36,2.83),(-.61,-.28,2.84),(-.98,.05,2.53),(-1.29,.40,2.21),
                                   (-1.41,.44,1.87),(-1.14,.40,1.50),(-.86,.39,1.22)],
         (.044,.068,.092,.106,.087,.068,.027)),
    ]
    for index,(name,path,radii) in enumerate(straps):
        carapace.append(root(name,path,radii,roots,index*.84))
    for index,(x,y,z) in enumerate(((-.85,-.40,2.78),(-.42,.73,2.85),(.36,.58,2.88),(.83,1.08,2.58))):
        carapace.append(root(f"Crown snag {index+1}", [(x,y,z-.12),(x-.05,y+.05,z+.035),(x+.08,y+.18,z+.18)],
                             (.071,.049,.012), roots,index))

    body = group("Rig_Shale_Root_Core",(0,0,1.72),carapace)
    movable_groups = [body]
    limb_parts = []
    legs = [
        ("Front_Left",(-1.01,-.78,1.51),(-1.66,-1.04,.89),(-1.65,-1.58,.28),(-1.51,-1.88,.18),.17),
        ("Front_Right",(1.05,-.65,1.48),(1.55,-.79,.91),(1.66,-1.41,.26),(1.60,-1.63,.18),-.11),
        ("Rear_Left",(-.91,1.02,1.53),(-1.64,1.12,.90),(-1.76,1.56,.27),(-1.61,1.87,.18),-.16),
        ("Rear_Right",(1.02,.98,1.53),(1.53,.97,.83),(1.72,1.50,.28),(1.83,1.78,.18),.20),
    ]
    for index,(name,hip,knee,ankle,toe,phase) in enumerate(legs):
        pieces = [root(f"{name} primary tendon", [hip,knee,ankle,toe], (.23,.24,.20,.099), roots, index),
                  rock(f"{name} shoulder shale",Vector(hip).lerp(Vector(knee),.28),(.85,.85,.72),
                       (.20,.25,phase),rocks,113+index),
                  rock(f"{name} low knee shell",knee,(.78,.82,.53),(.24,phase,-phase),rocks,123+index),
                  rock(f"{name} foot stone",ankle,(.68,.79,.37),(.09,.16,phase),rocks,141+index)]
        side = -1 if "Left" in name else 1
        for offset in (-1,1):
            flow = [Vector(hip)+Vector((offset*.12,-.13,.17)),
                    Vector(knee)+Vector((side*.15,offset*.12,.17)),
                    Vector(ankle)+Vector((offset*.18,offset*.16,.10)),
                    Vector(toe)+Vector((offset*.12,offset*.14,-.04))]
            pieces.append(root(f"{name} binding root {offset}",flow,(.093,.103,.085,.031),roots,index+offset))
            x,y,z = Vector(toe)+Vector((offset*.132,0,.018))
            pieces.append(rock(f"{name} {offset} toe claw",(x,y,z),(.25,.38,.225),
                               (.23,phase+offset*.14,offset*.13),rocks,159+index+offset,1))
        limb = group(f"Rig_Limb_{name}",hip,pieces)
        movable_groups.append(limb)
        limb_parts.extend(pieces)

    wedge_parts = [
        rock("Lifting wedge central face",(.46,-1.65,2.04),(1.28,1.37,.817),(-.12,.20,-.34),rocks,231),
        rock("Wedge pointed outer lamina",(.54,-2.16,1.83),(1.04,.91,.531),(-.29,.11,-.21),rocks,242),
        rock("Wedge worn side fragment",(.31,-1.63,1.78),(.53,1.23,.57),(.18,-.19,.16),rocks,251),
        root("Movable wedge binding",[(-.09,-1.02,2.15),(-.20,-1.37,2.23),(-.17,-1.78,2.15),
                                     (.16,-2.11,1.91),(.57,-2.28,1.69),(.83,-2.09,1.57)],
             (.084,.091,.094,.086,.079,.035),roots,1.4),
        root("Wedge hinge braid",[(.71,-1.02,2.30),(.98,-1.40,2.22),(1.07,-1.65,2.12),
                                 (1.03,-1.93,1.93),(.84,-2.26,1.75),(.66,-2.34,1.66)],
             (.086,.092,.088,.076,.063,.026),roots,3.6),
    ]
    wedge = group("Rig_Lifting_Rock_Wedge",(.42,-1.10,2.18),wedge_parts)
    wedge["lift_axis_blender"] = "local -X"
    wedge["preview_lift_degrees"] = 30
    asset = group("Riftroot_Tangle_Preview",(0,0,0),[*movable_groups,wedge])
    asset["front_direction_blender"] = "local -Y"
    asset["prototype_use"] = "Design and rig planning; not an Unreal enemy asset"
    bpy.context.view_layer.update()
    floor = min((obj.matrix_world @ vertex.co).z for obj in limb_parts for vertex in obj.data.vertices)
    for part in asset.children:
        part.location.z -= floor

    bpy.ops.object.select_all(action="DESELECT")
    for obj in [asset,*movable_groups,wedge,*carapace,*limb_parts,*wedge_parts]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = asset
    bpy.ops.export_scene.gltf(filepath=str(output / "riftroot_tangle.glb"), export_format="GLB",
                              use_selection=True, export_extras=True)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.006))
    bpy.context.object.data.materials.append(surface("Preview cavern floor",(.026,.045,.061),.79,22))
    world = bpy.data.worlds.new("Riftroot ambient")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.13,.24,.34,1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .26
    camera = bpy.data.objects.new("Creature preview camera",bpy.data.cameras.new("Creature preview camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (-6.6,-9.3,5.05)
    aim(camera,(0,-.13,1.24))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 6.68
    scene.camera = camera
    light("Cool fissure opening",(-3.0,-3.5,5.8),(.59,.75,1),1080,2.4)
    light("Light through roots",(2.4,2.4,5.0),(1,.65,.36),1370,2.7)
    light("Low side silhouette",(3.8,-3.7,2.1),(.63,.79,.84),225,2.7)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 920
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene["asset_status"] = "prototype_pending_rig_collision_unreal_import_and_art_review"
    scene.render.filepath = str(output / "riftroot_tangle.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "riftroot_tangle.blend"))
    bpy.ops.render.render(write_still=True)
    wedge.rotation_euler.x = math.radians(-30)
    camera.location = (-4.0,-10.5,4.12)
    aim(camera,(0,-.31,1.43))
    scene.render.filepath = str(output / "riftroot_tangle_wedge_raised.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
