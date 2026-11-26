"""Original garment shell prototypes, not fitted or rigged characters.
Run: python character_art/generate_garments.py OUTPUT_DIR
Dependencies: numpy, trimesh, matplotlib. All rights reserved.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

# height, bottom/top elevation, elliptical radii (width, depth), RGB
PROFILES = {
 "kael_recruit_vest": (1.79, .51, .81, (.145,.082),(.195,.105),(83,62,43)),
 "darius_forge_apron": (1.84,.35,.79,(.19,.105),(.18,.12),(89,53,33)),
 "elara_healer_tunic": (1.66,.34,.81,(.21,.10),(.16,.09),(109,123,94)),
 "lyra_civilian_tunic": (1.63,.39,.80,(.18,.086),(.15,.083),(134,74,50)),
 "noah_civilian_vest": (.96,.49,.77,(.115,.072),(.125,.078),(65,91,117)),
}
def mesh_for(key):
    h,lo,hi,base,top,rgb=PROFILES[key]
    # Elliptical open shell, duplicated UV seam. Apron is a front panel.
    n=48
    angle=np.linspace(-np.pi/2,np.pi/2,n+1) if "apron" in key else np.linspace(-np.pi,np.pi,n+1)
    v=[]; uv=[]; faces=[]
    for j,t in enumerate(np.linspace(0,1,9)):
        rx=(1-t)*base[0]+t*top[0]
        ry=(1-t)*base[1]+t*top[1]
        for i,a in enumerate(angle):
            # glTF axes: Y up, Z forward; small fabric waviness
            wave=1+.018*np.sin(8*a)*np.sin(np.pi*t)
            v.append([rx*np.sin(a)*wave,h*(lo+(hi-lo)*t),ry*np.cos(a)*wave])
            uv.append([i/n,t])
    for j in range(8):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;c=a+n+1;d=c+1
            faces.extend([(a,b,c),(b,d,c)])
    mat=PBRMaterial(name=key,baseColorFactor=[*rgb,255],metallicFactor=0.,roughnessFactor=.85,doubleSided=True)
    return trimesh.Trimesh(vertices=v,faces=faces,visual=trimesh.visual.TextureVisuals(uv=uv,material=mat),process=False)
def main(out):
    out.mkdir(parents=True,exist_ok=True)
    records=[]
    fig,axes=plt.subplots(5,3,figsize=(8,13))
    for row,key in enumerate(PROFILES):
        mesh=mesh_for(key)
        assert np.isfinite(mesh.vertices).all() and (mesh.area_faces>1e-10).all()
        assert len(mesh.visual.uv)==len(mesh.vertices)
        assert np.min(mesh.visual.uv)>=0 and np.max(mesh.visual.uv)<=1
        assert mesh.faces.max()<len(mesh.vertices)
        path=out/(key+".glb")
        path.write_bytes(mesh.export(file_type="glb"))
        loaded=trimesh.load(path,force="scene",process=False)
        assert len(loaded.geometry)==1
        m=next(iter(loaded.geometry.values()))
        assert len(m.faces)==len(mesh.faces) and len(m.visual.uv)==len(mesh.vertices)
        assert np.allclose(m.bounds,mesh.bounds,atol=1e-6)
        records.append(dict(id=key,path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),vertices=len(mesh.vertices),triangles=len(mesh.faces),dimensions_m=mesh.extents.tolist(),status="generated_prototype",license="All rights reserved"))
        for col,(label,axis,depth) in enumerate([("Front",0,2),("Right",2,0),("Back",0,2)]):
            ax=axes[row,col]; pts=mesh.vertices.copy()
            if label=="Back": pts[:,0]*=-1
            order=np.argsort(pts[mesh.faces,depth].mean(axis=1))
            if label=="Back": order=order[::-1]
            rgb=np.array(PROFILES[key][-1])/255.
            poly=PolyCollection(pts[mesh.faces[order]][:,:,[axis,1]],facecolors=[rgb],edgecolors="none")
            ax.add_collection(poly);ax.set_xlim(-.3,.3);ax.set_ylim(0,1.95);ax.set_aspect("equal")
            ax.set_title((key+" | " if col==0 else "")+label,fontsize=8);ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(out/"garment_orthographic.png",dpi=160);plt.close(fig)
    records.append(dict(path="garment_orthographic.png",sha256=hashlib.sha256((out/"garment_orthographic.png").read_bytes()).hexdigest(),status="orthographic_projection_not_photoreal_render"))
    (out/"manifest.json").write_text(json.dumps(records,indent=2)+"\n")
if __name__=="__main__":
    main(Path(sys.argv[1]))
