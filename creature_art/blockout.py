"""Run: blender -b -t 1 --python blockout.py -- /absolute/output.blend
Unverified graybox only; no production rig or collision.
"""
import bpy
import sys
from pathlib import Path

def ellipsoid(name, center, scale):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def main(output):
    if output.suffix != ".blend":
        raise ValueError("Expected .blend output")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    ellipsoid("PROXY_Torso", (0,0,125), (48,24,35))
    ellipsoid("PROXY_Crown", (30,0,160), (18,15,20))
    for x in (-30,30):
        for y in (-17,17):
            ellipsoid(f"PROXY_Leg_{x}_{y}", (x,y,55), (9,9,55))
    bpy.context.scene["asset_status"] = "graybox_unverified"
    bpy.context.scene["creature_id"] = "titan_roaming"
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))

if __name__ == "__main__":
    main(Path(sys.argv[sys.argv.index("--")+1]).resolve())
