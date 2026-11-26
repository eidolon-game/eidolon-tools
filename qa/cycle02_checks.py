"""Standalone structural checks; no engine or physical traversal claim."""
import argparse
import json
from pathlib import Path
from campaign_checks import unreachable

def floors(data):
    rows = data["floors"]
    errors = []
    ids = [r["id"] for r in rows]
    if len(ids) != 200 or len(set(ids)) != 200:
        errors.append("floor count or identity")
    for dungeon in ("abyss", "stair"):
        group = sorted((r for r in rows if r["dungeon"] == dungeon), key=lambda r:r["index"])
        if [r["index"] for r in group] != list(range(1,101)):
            errors.append(dungeon + ": sequence")
        for i,r in enumerate(group):
            if r["previous"] != (group[i-1]["id"] if i else None):
                errors.append(r["id"] + ": predecessor")
            n,e = r["nodes"],r["edges"]
            if unreachable(n,e,r["entry"],[r["exit"],r["checkpoint"],r["objective"]]):
                errors.append(r["id"] + ": unreachable")
            if unreachable(n,e,r["checkpoint"],[r["exit"]]):
                errors.append(r["id"] + ": checkpoint")
            o = r["objective"]
            if o not in (r["entry"],r["exit"]) and not unreachable([x for x in n if x!=o],[x for x in e if o not in x],r["entry"],[r["exit"]]):
                errors.append(r["id"] + ": bypass")
    return errors

def quests(data):
    rows=data["quests"]
    ids={r["id"] for r in rows}
    errors=[]
    if len(rows)!=29 or len(ids)!=29:
        errors.append("quest count or identity")
    seen=set()
    for _ in rows:
        seen.update(r["id"] for r in rows if set(r["prerequisites"])<=seen)
    if seen!=ids:
        errors.append("missing or cyclic prerequisites")
    endings={r["id"]:set(r["requires"]) for r in data["endings"]}
    expected={k:{"mq_26"} for k in ("custodian","origin","guild")}
    expected["freedom"]={"mq_26","mem_lost","sq_eidolon_aid","sec_origin"}
    if endings!=expected or len(data["endings"])!=4:
        errors.append("ending prerequisites")
    return errors

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("kind",choices=["floors","quests"])
    p.add_argument("path",type=Path)
    a=p.parse_args()
    errors={"floors":floors,"quests":quests}[a.kind](json.loads(a.path.read_text(encoding="utf-8")))
    print(json.dumps({"scope":a.kind,"status":"FAIL" if errors else "PASS","errors":errors}))
    raise SystemExit(bool(errors))
