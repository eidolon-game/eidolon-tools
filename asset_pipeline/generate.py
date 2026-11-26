"""Original procedural static-mesh calibration asset; run in Blender."""
import bpy
import sys, json, hashlib
from pathlib import Path
from mathutils import Vector
out = Path(sys.argv[sys.argv.index("--")+1]).resolve()
out.mkdir(parents=True, exist_ok=True)
if any(out.iterdir()):
    raise RuntimeError('Output directory must be empty')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.5))
obj = bpy.context.object
obj.name = "SM_Pipeline_Calibration"
obj.scale = (1,0.5,1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bevel = obj.modifiers.new("Edge treatment", 'BEVEL')
bevel.width = 0.025
bevel.segments = 3
bpy.ops.object.modifier_apply(modifier=bevel.name)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=0.03)
bpy.ops.object.mode_set(mode='OBJECT')
mat = bpy.data.materials.new("M_Calibration_Stone")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.24,0.21,0.18,1)
bsdf.inputs["Roughness"].default_value = 0.82
bsdf.inputs["Metallic"].default_value = 0
obj.data.materials.append(mat)
obj.data.calc_loop_triangles()
assert len(obj.data.uv_layers) > 0
assert all(abs(a-b)<1e-5 for a,b in zip(obj.dimensions,(1,0.5,1)))
assert all(p.area > 1e-8 for p in obj.data.polygons)
assert all(0 <= v <= 1 for loop in obj.data.uv_layers.active.data for v in loop.uv)
mesh = out / "SM_Pipeline_Calibration.glb"
bpy.ops.export_scene.gltf(filepath=str(mesh), export_format='GLB', use_selection=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / "SM_Pipeline_Calibration.blend"))
bpy.ops.object.camera_add(location=(3,-4,2.6))
camera = bpy.context.object
camera.rotation_euler = (Vector((0,0,0.5))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera = camera
for pos,power in [((2,-3,4),700),((-2,1,3),450)]:
    bpy.ops.object.light_add(type='AREA', location=pos)
    light = bpy.context.object
    light.data.energy = power
    light.data.shape = 'DISK'
    light.data.size = 3
    light.rotation_euler = (Vector((0,0,0.5))-light.location).to_track_quat('-Z','Y').to_euler()
scene.world = bpy.data.worlds.new("Studio")
scene.world.use_nodes = True
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(out / "preview.png")
bpy.ops.render.render(write_still=True)
# Round-trip the actual exported mesh.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(mesh))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert len(meshes) == 1 and meshes[0].data.uv_layers
assert all(abs(a-b)<1e-5 for a,b in zip(meshes[0].dimensions,(1,0.5,1)))
report = {"id":"pipeline_calibration_v1","status":"generated","blender":bpy.app.version_string,"dimensions_m":[1,0.5,1],"files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}}
(out / "report.json").write_text(json.dumps(report,indent=2)+"\n")
