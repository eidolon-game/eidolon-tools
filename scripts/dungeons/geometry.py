import json, random, hashlib, pathlib, sys

# 200 cm grid, Z up, local floor datum; original project graybox.
FAMILIES = 'catacombs buried_forest lost_mines sunken_kingdom crystal_lands necropolis infernal_forges inverted_citadel silent_sanctuary abyss_heart time memory life death matter will destiny'.split()

def layout(family, seed, tutorial=False):
    rng = random.Random(seed)
    width = 5 if tutorial else 5 + FAMILIES.index(family) % 4
    length = 14 if tutorial else 12 + rng.randrange(8)
    cells = {(x,y) for x in range(length) for y in range(width)}
    gate = length//2
    # A full transverse gate, with no walkable alternative around it.
    for x in range(2,gate-1):
        cells.add((x,width))
    if not tutorial:
        for x in range(gate+2,length-1):
            cells.add((x,-1-rng.randrange(1)))
    return dict(family=family,seed=seed,cell_cm=200,height_cm=300,cells=sorted(cells),entry=[0,width//2],checkpoint=[1,width//2],exit=[length-1,width//2],gate_x=gate,encounter=[gate-2,width//2],anomaly=[gate+2,width//2],secret=[2,width])

def validate(d):
    cells={tuple(p) for p in d['cells']}; gate=d['gate_x']
    def reach(start, locked):
        seen={tuple(start)}; todo=list(seen)
        while todo:
            x,y=todo.pop()
            for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if p not in cells or p in seen or (locked and min(x,p[0])==gate-1 and max(x,p[0])==gate): continue
                seen.add(p); todo.append(p)
        return seen
    assert d['cell_cm']>=150 and d['height_cm']>=240
    assert all(tuple(d[k]) in cells for k in ('entry','checkpoint','exit','encounter','anomaly','secret'))
    assert reach(d['entry'],False)==cells
    assert tuple(d['exit']) not in reach(d['entry'],True)
    assert tuple(d['encounter']) in reach(d['checkpoint'],True)
    assert tuple(d['exit']) in reach(d['checkpoint'],False)
    assert tuple(d['anomaly']) not in reach(d['entry'],True)

def obj(d):
    cells={tuple(p) for p in d['cells']}; lines=['# Original EIDOLON graybox; metres, Z up']; count=0
    def box(name,x,y,z,a,b,c):
        nonlocal count
        lines.append('o '+name)
        for X,Y,Z in ((x,y,z),(x+a,y,z),(x+a,y+b,z),(x,y+b,z),(x,y,z+c),(x+a,y,z+c),(x+a,y+b,z+c),(x,y+b,z+c)):
            lines.append(f'v {X/100:.3f} {Y/100:.3f} {Z/100:.3f}')
        for face in ((1,4,3,2),(5,6,7,8),(1,2,6,5),(2,3,7,6),(3,4,8,7),(4,1,5,8)):
            lines.append('f '+' '.join(str(count+i) for i in face))
        count+=8
    for x,y in sorted(cells):
        X,Y=x*200,y*200
        box(f'floor_{x}_{y}',X,Y,-18,200,200,18)
        for dx,dy,xx,yy,a,b in ((-1,0,X-25,Y,25,200),(1,0,X+200,Y,25,200),(0,-1,X,Y-25,200,25),(0,1,X,Y+200,200,25)):
            if (x+dx,y+dy) not in cells:
                box(f'wall_{x}_{y}_{dx}_{dy}',xx,yy,0,a,b,300)
        if x==d['gate_x'] and (x-1,y) in cells:
            box(f'gate_{y}',X-10,Y,0,20,200,300)
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
    for i in range(200):
        f=FAMILIES[i//10] if i<100 else FAMILIES[10+(i-100)%7]
        d=layout(f,10001+i if i<100 else 20001+i-100,i==0); validate(d)
        assert d==layout(f,d['seed'],i==0)
    d=layout('catacombs',10001,True)
    (out/'abyss_001_layout.json').write_text(json.dumps(d,indent=2)+'\n')
    mesh=obj(d); (out/'abyss_001_graybox.obj').write_text(mesh)
    print('PASS 200 geometry layouts, deterministic replay, reachability, locked gate, checkpoint and anomaly')
    print('OBJ SHA256',hashlib.sha256(mesh.encode()).hexdigest())
