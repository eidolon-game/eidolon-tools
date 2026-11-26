"""Generate reproducible OBJ terrain, road ribbons and city block grayboxes.
All geometry uses metres, Z up; no external dependencies.
"""
import argparse
import json
import math
import random
from pathlib import Path

def reachable(world, chapter):
    nodes = {n["id"]: n for n in world["nodes"]}
    seen = {"valdris"}
    while True:
        before = len(seen)
        for e in world["edges"]:
            a,b = e["a"],e["b"]
            if e["chapter"] <= chapter and max(nodes[a]["chapter"],nodes[b]["chapter"]) <= chapter:
                if a in seen or b in seen:
                    seen.update((a,b))
        if len(seen)==before:
            return seen

def validate(w):
    ids=[n["id"] for n in w["nodes"]]
    if len(ids)!=len(set(ids)): raise ValueError("Duplicate IDs")
    for e in w["edges"]:
        if e["a"] not in ids or e["b"] not in ids: raise ValueError("Unknown endpoint")
    for c in range(1,27):
        expected={n["id"] for n in w["nodes"] if n["chapter"]<=c}
        if reachable(w,c)!=expected: raise ValueError(f"Gate mismatch at {c}")
    for n in w["nodes"]:
        if "inner_radius" in n and not 0<n["inner_radius"]<n["outer_radius"]:
            raise ValueError("Invalid walls")

def generate(w, seed=1701, step=250):
    validate(w)
    rng=random.Random(seed)
    phase=rng.random()*math.tau
    cities=[n for n in w["nodes"] if "inner_radius" in n]
    def h(x,y):
        d=min(math.hypot(x-n["x"],y-n["y"]) for n in cities)
        return min(1,max(0,(d-1500)/1500))*(75+45*math.sin(x/1200+phase)*math.cos(y/1500))
    vertices=[]; faces=[]
    def quad(points):
        i=len(vertices)+1; vertices.extend(points); faces.append((i,i+1,i+2,i+3))
    def box(x,y,z,a,b,c):
        p=[(x,y,z),(x+a,y,z),(x+a,y+b,z),(x,y+b,z),(x,y,z+c),(x+a,y,z+c),(x+a,y+b,z+c),(x,y+b,z+c)]
        for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            quad([p[i] for i in f])
    for x in range(-12500,12500,step):
        for y in range(-12500,12500,step):
            quad([(a,b,h(a,b)) for a,b in [(x,y),(x+step,y),(x+step,y+step),(x,y+step)]])
    nodes={n["id"]:n for n in w["nodes"]}
    for e in w["edges"]:
        a,b=nodes[e["a"]],nodes[e["b"]]
        dx,dy=b["x"]-a["x"],b["y"]-a["y"]
        length=math.hypot(dx,dy)
        if not length: continue
        nx,ny=-dy/length*3,dx/length*3
        segments=math.ceil(length/25)
        for i in range(segments):
            p=[]
            for t,s in [(i/segments,-1),((i+1)/segments,-1),((i+1)/segments,1),(i/segments,1)]:
                x,y=a["x"]+dx*t+nx*s,a["y"]+dy*t+ny*s
                p.append((x,y,h(x,y)+0.2))
            quad(p)
    for n in cities:
        x,y=n["x"],n["y"]
        for radius in (n["inner_radius"],n["outer_radius"]):
            for i in range(64):
                if i in (0,63): continue
                a,b=math.tau*i/64,math.tau*(i+1)/64
                p=[(x+rr*math.cos(t),y+rr*math.sin(t),z) for rr,t,z in [(radius,a,0),(radius,b,0),(radius,b,30),(radius,a,30)]]
                quad(p)
        for dx in range(-300,301,60):
            for dy in range(-300,301,60):
                if abs(dx)<60 or abs(dy)<60: continue
                box(x+dx,y+dy,0,20,25,rng.randint(6,18))
    return "\n".join(["# EIDOLON graybox; metres; Z up"]+["v %.4f %.4f %.4f"%v for v in vertices]+["f %d %d %d %d"%f for f in faces])+"\n"

def main():
    p=argparse.ArgumentParser(); p.add_argument("world",type=Path); p.add_argument("output",type=Path); p.add_argument("--seed",type=int,default=1701)
    a=p.parse_args(); w=json.loads(a.world.read_text(encoding="utf-8")); a.output.write_text(generate(w,a.seed),encoding="utf-8")
if __name__=="__main__": main()
