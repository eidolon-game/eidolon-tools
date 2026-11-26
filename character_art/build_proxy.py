"""Generate a deliberately non-production proportion proxy in Blender.
Usage: blender -b --python build_proxy.py -- catalog.json char.kael output.blend
"""
import bpy
import json
import sys
from pathlib import Path

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise ValueError("Expected catalog, character ID, output.blend")
    catalog, ident, output = args
    row = next(x for x in json.loads(Path(catalog).read_text())["characters"] if x["id"] == ident)
    h = row["proposed_height_m"]
    if not h or row["role"] in ("child", "deity"):
        raise ValueError("Adult human proxy only; child/deity require custom proportions")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def ellipsoid(name, center, scale):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=tuple(v*h for v in center))
        ob = bpy.context.object
        ob.name = name
        ob.scale = tuple(v*h for v in scale)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return ob
    ellipsoid("Head", (0,0,.935), (.055,.065,.065))
    ellipsoid("Torso", (0,0,.70), (.125,.075,.18))
    ellipsoid("Pelvis", (0,0,.51), (.10,.07,.075))
    for sign, label in ((-1,"L"),(1,"R")):
        ellipsoid("Arm_"+label,(sign*.19,0,.67),(.045,.045,.15))
        ellipsoid("Forearm_"+label,(sign*.23,0,.45),(.032,.035,.12))
        ellipsoid("Thigh_"+label,(sign*.055,0,.39),(.052,.055,.14))
        ellipsoid("Shin_"+label,(sign*.055,0,.15),(.037,.04,.13))
        ellipsoid("Foot_"+label,(sign*.055,.035,.035),(.04,.075,.035))
    bpy.context.scene["character_id"] = ident
    bpy.context.scene["asset_status"] = "graybox_unrigged"
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(output).resolve()))

if __name__ == "__main__":
    main()
