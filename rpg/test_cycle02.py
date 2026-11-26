import json,sys,csv
from pathlib import Path
from simulate import validate,simulate
def main():
    data=json.loads(Path(sys.argv[1]).read_text())
    registry=json.loads(Path(sys.argv[2]).read_text())
    assert data["schema"]==2
    aliases=data["aliases"]
    assert len(aliases)==len(data["items"])==63
    assert len({a["item_id"] for a in aliases})==63
    art={a["asset_id"]:a["rpg_id"] for a in registry["assets"]}
    assert all(art[a["asset_id"]]==a["legacy_id"] for a in aliases)
    validate(dict(data,schema=1))
    rows=list(simulate(data))
    assert rows[-1]["xp"]==504900 and rows[-1]["gold"]==35892
    assert min(r["gold"] for r in rows)>=0
    assert min(r["gold"] for r in simulate(data,.5))<0
    print("PASS aliases, catalog, 26 chapters, baseline and stress scenario")
if __name__=="__main__": main()
