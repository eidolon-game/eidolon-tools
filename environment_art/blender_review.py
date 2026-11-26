"""Import generated GLBs into Blender and render each as a separate review scene.
Blender 4.x command: blender -b -t 2 -P blender_review.py -- INPUT_DIR OUTPUT_DIR
Authoring and collision data remain separate. All rights reserved.
"""
import sys
from pathlib import Path
import bpy
from mathutils import Vector


def main(src, dst):
    dst.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.glob('*.glb')):
        if path.stem.endswith('_collision'):
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
        meshes = [o for o in scene.objects if o.type == 'MESH']
        if not meshes or any(not o.data.uv_layers or not o.data.materials for o in meshes):
            raise ValueError(f'Missing mesh, UV or material: {path}')
        corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        low = Vector(tuple(min(p[i] for p in corners) for i in range(3)))
        high = Vector(tuple(max(p[i] for p in corners) for i in range(3)))
        center = (low+high)/2
        span = max(high-low)
        if span <= 0:
            raise ValueError(f'Empty bounds: {path}')
        camera_data = bpy.data.cameras.new('ReviewCamera')
        camera = bpy.data.objects.new('ReviewCamera', camera_data)
        scene.collection.objects.link(camera)
        camera.location = center + Vector((.85,-1,.75)).normalized()*span*3
        camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = span*1.75
        scene.camera = camera
        light_data = bpy.data.lights.new('ReviewKey','AREA')
        light = bpy.data.objects.new('ReviewKey',light_data)
        scene.collection.objects.link(light)
        light.location = center+Vector((-1,-1,2))*span
        light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
        light_data.energy = 700*span*span
        light_data.shape = 'DISK'
        light_data.size = span
        world = bpy.data.worlds.new('ReviewWorld')
        world.use_nodes = True
        world.node_tree.nodes.get('Background').inputs[0].default_value = (.16,.16,.16,1)
        world.node_tree.nodes.get('Background').inputs[1].default_value = .5
        scene.world = world
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 32
        scene.render.resolution_x = 960
        scene.render.resolution_y = 720
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str((dst/(path.stem+'_blender.png')).resolve())
        bpy.ops.wm.save_as_mainfile(filepath=str((dst/(path.stem+'.blend')).resolve()))
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    if len(args) != 2:
        raise SystemExit('Expected INPUT_DIR OUTPUT_DIR')
    main(Path(args[0]), Path(args[1]))
