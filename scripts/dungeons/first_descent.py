"""Authored First Descent layout, using the shared graybox exporter."""
import hashlib
import json
import pathlib
import sys
from geometry import obj, validate


def authored():
    cells=set()
    for x0,x1,y0,y1 in [(0,2,2,3),(3,4,2,2),(5,9,0,5),(6,7,6,6),(10,10,2,2),(11,13,1,3),(14,15,2,2)]:
        cells.update((x,y) for x in range(x0,x1+1) for y in range(y0,y1+1))
    return dict(family='catacombs',seed=10001,cell_cm=200,height_cm=300,cells=sorted(cells),entry=[0,2],checkpoint=[2,2],exit=[15,2],gate_x=10,encounter=[7,2],anomaly=[12,2],secret=[6,6])


def verify(d):
    validate(d)
    cells={tuple(p) for p in d['cells']}
    gate=d['gate_x']
    assert [(x,y) for x,y in sorted(cells) if x==gate and (x-1,y) in cells]==[(10,2)]
    assert len(cells)==52
    assert d['entry']!=d['exit']
    # Secret is optional; removing it must not affect the mandatory route.
    reduced=dict(d,cells=[p for p in d['cells'] if p[1]!=6],secret=d['checkpoint'])
    validate(reduced)
    mesh=obj(d)
    vertices=[tuple(map(float,l.split()[1:])) for l in mesh.splitlines() if l.startswith('v ')]
    faces=[list(map(int,l.split()[1:])) for l in mesh.splitlines() if l.startswith('f ')]
    assert all(len(set(f))==4 and all(1<=i<=len(vertices) for i in f) for f in faces)
    return mesh,len(vertices),len(faces)


if __name__=='__main__':
    out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
    d=authored(); mesh,nv,nf=verify(d)
    (out/'abyss_001_authored.json').write_text(json.dumps(d,indent=2)+'\n')
    (out/'abyss_001_authored.obj').write_text(mesh)
    print('PASS authored layout, gate cut, optional secret, OBJ indices',nv,nf)
    print('OBJ SHA256',hashlib.sha256(mesh.encode()).hexdigest())
