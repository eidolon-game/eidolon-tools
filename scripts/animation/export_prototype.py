"""Original EIDOLON graybox node-animation exporter; no Blender dependency.
Usage: python scripts/animation/export_prototype.py OUTPUT.gltf
Not a skinned mesh or production rig. glTF uses meters, Y up.
"""
import base64
import json
import math
import struct
import sys
from pathlib import Path

def generate():
    blob = bytearray()
    views, accessors, animations = [], [], []
    nodes = [
        {"name":"root","children":[1]},
        {"name":"pelvis","translation":[0,0.95,0],"children":[2,3,5]},
        {"name":"spine","translation":[0,0.20,0],"children":[7,8]},
        {"name":"thigh_l","translation":[-0.10,0,0],"children":[4]},
        {"name":"shin_l","translation":[0,-0.43,0]},
        {"name":"thigh_r","translation":[0.10,0,0],"children":[6]},
        {"name":"shin_r","translation":[0,-0.43,0]},
        {"name":"arm_l","translation":[-0.22,0.25,0]},
        {"name":"arm_r","translation":[0.22,0.25,0]},
    ]
    def accessor(values, kind, count, bounds=False):
        offset=len(blob)
        blob.extend(struct.pack("<"+"f"*len(values),*values))
        views.append({"buffer":0,"byteOffset":offset,"byteLength":len(blob)-offset})
        a={"bufferView":len(views)-1,"componentType":5126,"count":count,"type":kind}
        if bounds: a.update(min=[min(values)],max=[max(values)])
        accessors.append(a)
        return len(accessors)-1
    for name,duration,amplitude in [("idle",2,3),("walk",1,25),("run",0.7,45),("sprint",0.55,60),("attack_light",0.62,75),("attack_heavy",1.32,105),("dodge",0.55,55)]:
        times=[duration*i/30 for i in range(31)]
        inp=accessor(times,"SCALAR",31,True)
        samplers,channels=[],[]
        for joint,phase,scale in [(3,0,1),(5,math.pi,1),(4,0,0.6),(6,math.pi,0.6),(7,math.pi,0.7),(8,0,0.7)]:
            values=[]
            for i in range(31):
                if name.startswith("attack"):
                    angle=amplitude*math.sin(math.pi*i/30)*scale if joint==8 else 0
                elif name=="dodge":
                    angle=amplitude*math.sin(math.pi*i/30)*scale if joint in (3,4,5,6) else 0
                else:
                    angle=amplitude*math.sin(2*math.pi*i/30+phase)*scale
                half=math.radians(angle)/2
                values.extend([math.sin(half),0,0,math.cos(half)])
            out=accessor(values,"VEC4",31)
            samplers.append({"input":inp,"output":out,"interpolation":"LINEAR"})
            channels.append({"sampler":len(samplers)-1,"target":{"node":joint,"path":"rotation"}})
        animations.append({"name":"anim_"+name,"samplers":samplers,"channels":channels})
    return {"asset":{"version":"2.0","generator":"EIDOLON original graybox exporter"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":nodes,"animations":animations,"buffers":[{"byteLength":len(blob),"uri":"data:application/octet-stream;base64,"+base64.b64encode(blob).decode("ascii")}],"bufferViews":views,"accessors":accessors}

def main():
    Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":
    main()
