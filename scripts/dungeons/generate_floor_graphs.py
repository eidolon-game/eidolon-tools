"""Deterministic floor graph generator; standard library only."""
import json
import argparse
FAMILIES = "catacombs buried_forest lost_mines sunken_kingdom crystal_lands necropolis infernal_forges inverted_citadel silent_sanctuary abyss_heart".split()
LAWS = "time memory life death matter will destiny".split()
LAYOUTS = "linear fork loop hub switchback".split()
ANCHORS = {"abyss.001":"tutorial_perception","abyss.070":"statue","abyss.090":"remember","abyss.100":"guardian_and_sealed_door","eternity.100":"empyrea_threshold"}
def generate():
    floors = []
    for d in ("abyss","eternity"):
        for n in range(1,101):
            id = f"{d}.{n:03}"
            family = FAMILIES[(n-1)//10] if d == "abyss" else LAWS[(n-1)%7]
            layout = LAYOUTS[(n-1+(n-1)//10)%5]
            nodes = ["entry","checkpoint","trial","exit","secret"]
            edges = [["entry","checkpoint"],["checkpoint","trial"],["trial","exit"],["checkpoint","secret"]]
            if layout == "fork": edges.append(["entry","secret"])
            if layout == "loop": edges.append(["secret","trial"])
            if layout == "hub":
                nodes.append("annex")
                edges.extend([["checkpoint","annex"],["annex","trial"]])
            if layout == "switchback":
                nodes.append("landing")
                edges[1] = ["checkpoint","landing"]
                edges.append(["landing","trial"])
            floors.append(dict(id=id,index=n,dungeon=d,family=family,layout=layout,seed=(10000 if d=="abyss" else 20000)+n,nodes=nodes,edges=edges,entry="entry",exit="exit",objective="trial",checkpoint="checkpoint",secret="secret",mechanic=family+"."+layout,encounter="boss_slot" if n%10==0 else "elite_slot" if n%3==0 else "standard_slot",difficulty=(n+9)//10,duration_minutes=12 if n%10==0 else 6,accessibility=["no_color_only","timing_assist"],reward_slot=id+".reward",narrative_anchor=ANCHORS.get(id),previous=None if n==1 else f"{d}.{n-1:03}",status="graph_prototype"))
    return dict(schema_version=1,status="graph_prototype",floors=floors)
def validate(data):
    floors=data["floors"]
    expected={f"{d}.{n:03}" for d in ("abyss","eternity") for n in range(1,101)}
    if len(floors)!=200 or {f["id"] for f in floors}!=expected:
        raise ValueError("floor IDs")
    for f in floors:
        nodes=set(f["nodes"])
        if len(nodes)!=len(f["nodes"]): raise ValueError("duplicate node")
        if any(a not in nodes or b not in nodes for a,b in f["edges"]): raise ValueError("invalid edge")
        def reachable(start, blocked=None):
            seen={start}
            for _ in nodes:
                for a,b in f["edges"]:
                    if a in seen and b!=blocked: seen.add(b)
            return seen
        if reachable(f["entry"])!=nodes: raise ValueError("unreachable node")
        if f["exit"] in reachable(f["entry"],f["objective"]): raise ValueError("objective bypass")
        if f["exit"] not in reachable(f["checkpoint"]): raise ValueError("checkpoint deadlock")
        if f["narrative_anchor"]!=ANCHORS.get(f["id"]): raise ValueError("anchor mismatch")
    return True
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--verify")
    args=p.parse_args()
    data=generate()
    validate(data)
    if args.verify:
        with open(args.verify,encoding="utf-8") as stream:
            other=json.load(stream)
        validate(other)
        if other!=data: raise ValueError("catalog drift")
        print("200 floors verified")
    else:
        print(json.dumps(data,indent=1))
