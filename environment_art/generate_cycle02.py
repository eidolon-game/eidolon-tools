import json, hashlib, struct, sys
from pathlib import Path
import numpy as np
import trimesh
from trimesh.visual.texture import TextureVisuals
from trimesh.visual.material import PBRMaterial
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Dimensions in metres, Z-up authoring, bottom-center pivot. Original graybox.
SPECS = {
'wall_stone':(4,.5,3),'floor_stone':(2,2,.18),'door_frame':(1.5,.25,2.4),
 'table_oak':(1.6,.8,.8),'chair_oak':(.45,.45,.9),'bed_child':(1.5,.75,.65),
 'storage_crate':(.6,.45,.45),'toy_wood':(.2,.1,.15),'forge_anvil':(.65,.28,.85),
 'dorm_bunk':(2,.9,1.9),'catacomb_pier':(.8,.8,3)}
MATS={'stone':([115,108,96,255],.85,0),'oak':([110,72,42,255],.72,0),'iron':([80,84,88,255],.48,1),'linen':([180,168,140,255],.92,0)}
def parts(k):
 x,y,z=SPECS[k]; a=[]
 def box(s,c,m): a.append((s,c,m))
 def legs(h,m='oak'):
  for i in (-1,1):
   for j in (-1,1): box((.08,.08,h),(i*(x/2-.04),j*(y/2-.04),h/2),m)
 if k=='door_frame':
  for i in (-1,1): box((.15,y,2.2),(i*.675,0,1.1),'stone')
  box((x,y,.2),(0,0,2.3),'stone')
 elif k=='table_oak': legs(.72);box((x,y,.08),(0,0,.76),'oak')
 elif k=='chair_oak':
  legs(.42);box((x,y,.05),(0,0,.445),'oak');box((x,.07,.43),(0,y/2-.035,.685),'oak')
 elif k in ('bed_child','dorm_bunk'):
  legs(z); heights=[.35] if k=='bed_child' else [.35,1.4]
  for h in heights:
   box((x,y,.12),(0,0,h),'oak');box((x-.1,y-.1,.12),(0,0,h+.12),'linen')
  if k=='bed_child': box((.08,y,.65),(-x/2+.04,0,.325),'oak')
 elif k=='forge_anvil':
  box((.45,.28,.55),(0,0,.275),'oak');box((.3,.2,.15),(0,0,.625),'iron');box((x,y,.15),(0,0,.775),'iron')
 elif k=='toy_wood':
  box((x,y,.08),(0,0,.04),'oak');box((.09,.08,.07),(0,0,.115),'oak')
 elif k=='storage_crate':
  box((x,y,z),(0,0,z/2),'oak')
 elif k=='catacomb_pier':
  box((x,y,.2),(0,0,.1),'stone');box((.6,.6,2.6),(0,0,1.5),'stone');box((x,y,.2),(0,0,2.9),'stone')
 else: box((x,y,z),(0,0,z/2),'stone')
 return a

def mesh(s,c,m):
 # Split triangle vertices for per-face planar UVs; one UV island per triangle.
 q=trimesh.creation.box(extents=s); v=q.vertices[q.faces].reshape(-1,3)+c
 f=np.arange(len(v)).reshape(-1,3); uv=np.tile([[0,0],[1,0],[1,1]],(len(f),1))
 rgba,rough,metal=MATS[m]
 return trimesh.Trimesh(vertices=v,faces=f,process=False,visual=TextureVisuals(uv=uv,material=PBRMaterial(name=m,baseColorFactor=rgba,roughnessFactor=rough,metallicFactor=metal)))

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main(out):
 out.mkdir(parents=True,exist_ok=True); records=[]
 for k,dim in SPECS.items():
  a=parts(k); scene=trimesh.Scene(); fig=plt.figure(figsize=(4,3)); ax=fig.add_subplot(111,projection='3d')
  for i,(s,c,m) in enumerate(a):
   q=mesh(s,c,m); scene.add_geometry(q,node_name=f'{k}_{i}',geom_name=f'{k}_{i}')
   rgba=MATS[m][0]; ax.add_collection3d(Poly3DCollection(q.vertices[q.faces],facecolor=np.array(rgba[:3])/255,edgecolor='#333333',linewidth=.25))
  assert np.allclose(scene.extents,dim), (k,scene.extents,dim)
  assert np.allclose(scene.bounds[0],[-dim[0]/2,-dim[1]/2,0])
  # glTF Y-up conversion: Z-up authoring -> Y-up (right-handed).
  scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))
  glb=out/(k+'.glb'); glb.write_bytes(scene.export(file_type='glb'))
  data=glb.read_bytes(); magic,version,total=struct.unpack_from('<4sII',data); assert (magic,version,total)==(b'glTF',2,len(data))
  length,typ=struct.unpack_from('<I4s',data,12); g=json.loads(data[20:20+length]); assert typ==b'JSON' and all('TEXCOORD_0' in p['attributes'] for m in g['meshes'] for p in m['primitives'])
  loaded=trimesh.load(glb,force='scene'); assert np.allclose(loaded.extents,[dim[0],dim[2],dim[1]],atol=1e-6)
  lim=max(dim)*.65; ax.set(xlim=(-lim,lim),ylim=(-lim,lim),zlim=(dim[2]/2-lim,dim[2]/2+lim)); ax.set_box_aspect((1,1,1)); ax.view_init(25,-55); ax.set_axis_off(); ax.set_title(k+' | GRAYBOX'); fig.tight_layout(); png=out/(k+'.png'); fig.savefig(png,dpi=120); plt.close(fig)
  records.append(dict(id='env_asset_'+k,status='graybox',size_m=dim,glb=glb.name,png=png.name,sha256={glb.name:digest(glb),png.name:digest(png)},collision_boxes=[dict(size_m=s,center_m=c) for s,c,m in a],triangles=12*len(a),uv='per-triangle overlapping planar prototype',provenance='original procedural geometry; all rights reserved'))
 (out/'manifest.json').write_text(json.dumps(dict(schema_version=1,authoring_axes='Z-up',glb_axes='Y-up',units='m',assets=records),indent=2))
 print('PASS',len(records),'GLB headers, UV attributes, round-trip extents, pivots and PNG exports')
if __name__=='__main__': main(Path(sys.argv[1]))
