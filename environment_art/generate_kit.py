"""Generate isolated environment graybox kit in Blender; not final art.
Run: blender -b -t 2 -P generate_kit.py -- /absolute/output.blend
Original project source; all rights reserved.
"""
import bpy, sys, math
from pathlib import Path

def material(name, rgb, roughness, metallic=0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgb,1)
    p.inputs["Roughness"].default_value=roughness
    p.inputs["Metallic"].default_value=metallic
    return m

def box(name, size, center, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj=bpy.context.object
    obj.name=name
    obj.dimensions=size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    bevel=obj.modifiers.new("Edge wear proxy","BEVEL")
    bevel.width=.015
    bevel.segments=2
    obj.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    return obj

def main():
    if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:]) != 1:
        raise SystemExit("Specify one output .blend path after --")
    out=Path(sys.argv[-1]).resolve()
    if out.suffix != ".blend" or out.exists():
        raise SystemExit("Output must be a new .blend file")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    stone=material("M_ENV_Stone_Prototype",(.32,.30,.26),.85)
    oak=material("M_ENV_Oak_Prototype",(.19,.10,.05),.72)
    iron=material("M_ENV_Iron_Prototype",(.22,.23,.24),.48,1)
    box("SM_ENV_Wall_4m_P", (4,.5,3),(0,0,1.5),stone)
    box("SM_ENV_Paving_2m_P",(2,2,.18),(0,4,.09),stone)
    box("SM_ENV_Ruin_Pier_P",(.8,.8,1.75),(5,0,.875),stone)
    box("SM_ENV_TableTop_P",(1.6,.8,.1),(5,4,.8),oak)
    for x in (4.35,5.65):
        for y in (3.7,4.3):
            box("SM_ENV_TableLeg_P",(.1,.1,.75),(x,y,.375),oak)
    box("SM_ENV_ForgeAnvilProxy_P",(.65,.28,.25),(8,4,.8),iron)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(8,0,1))
    rock=bpy.context.object
    rock.name="SM_ENV_Rock_P"
    for v in rock.data.vertices:
        v.co.x*=1.2+0.13*math.sin(v.index*2.4)
        v.co.z*=.75+0.1*math.cos(v.index*1.7)
    rock.data.materials.append(stone)
    for obj in bpy.context.scene.objects:
        if obj.type=="MESH":
            assert all(d>0 for d in obj.dimensions)
            assert len(obj.data.materials)>0
    out.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
if __name__=="__main__":
    main()
