"""Department 12 modular placement studies; not playable maps. All rights reserved."""
import json, sys
from pathlib import Path
import numpy as np
import trimesh
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import generate_cycle02 as base
from generate_textured import mesh

# local m, Z-up, yaw degrees. POI references are from department 16 proposals.
ROOMS={
 'home_before':('valdris_home',[('table_oak',0,0,0),('chair_oak',0,-.85,0),('chair_oak',0,.85,180),('storage_crate',-2.8,2.8,0)]),
 'home_present':('valdris_home',[('table_oak',0,0,0),('chair_oak',0,-.85,0),('chair_oak',0,.85,180),('bed_child',-2.3,2.5,0),('toy_wood',-2.3,1.7,0)]),
 'home_erased':('valdris_home',[('table_oak',0,0,0),('chair_oak',0,-.85,0),('chair_oak',0,.85,180),('storage_crate',-2.8,2.8,0)]),
 'forge':('valdris_forge',[('forge_anvil',0,0,0),('table_oak',-2.6,2.7,0),('storage_crate',2.6,2.7,0)]),
 'guild':('valdris_guild',[('table_oak',0,2,0),('chair_oak',0,2.9,180),('catacomb_pier',-2.8,1.5,0),('catacomb_pier',2.8,1.5,0)]),
 'dormitory':('valdris_dormitory',[('dorm_bunk',-2.7,1.9,90),('dorm_bunk',2.7,1.9,90),('storage_crate',-2.7,-.1,0),('storage_crate',2.7,-.1,0)]),
 'abyss_trial':('valdris_abyss',[('catacomb_pier',-2.7,2.5,0),('catacomb_pier',2.7,2.5,0),('catacomb_pier',-2.7,-2.5,0),('catacomb_pier',2.7,-2.5,0)])}


def main(out):
 out.mkdir(parents=True,exist_ok=True); records=[]
 for name,(poi,props) in ROOMS.items():
  layout=[('floor_stone',x,y,0) for x in (-3,-1,1,3) for y in (-3,-1,1,3)]
  layout += [('wall_stone',x,3.75,0) for x in (-2,2)]
  # Front and right are deliberately open for the cutaway.
  layout += [('wall_stone',-3.75,y,90) for y in (-2,2)] + [('door_frame',0,-3.85,0)] + props
  scene=trimesh.Scene(); fig=plt.figure(figsize=(8,6)); ax=fig.add_subplot(111,projection='3d'); placements=[]
  for i,(k,x,y,yaw) in enumerate(layout):
   z=-.18 if k=='floor_stone' else 0.; transform=trimesh.transformations.rotation_matrix(np.radians(yaw),[0,0,1]); transform[:3,3]=[x,y,z]
   placements.append(dict(asset_id='env_asset_'+k,position_cm=[round(x*100),round(y*100),round(z*100)],yaw_deg=yaw))
   for j,(s,c,m) in enumerate(base.parts(k)):
    q=mesh(s,c,m); q.apply_transform(transform); scene.add_geometry(q,node_name=f'{k}_{i}_{j}',geom_name=f'{k}_{i}_{j}')
    ax.add_collection3d(Poly3DCollection(q.vertices[q.faces],facecolor=np.asarray(base.MATS[m][0][:3])/255,edgecolor='#353535',linewidth=.2))
  scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0])); p=out/(name+'.glb'); p.write_bytes(scene.export(file_type='glb'))
  loaded=trimesh.load(p,force='scene'); assert np.allclose(loaded.extents,scene.extents,atol=1e-6)
  ax.set(xlim=(-4.5,4.5),ylim=(-4.5,4.5),zlim=(-.2,4.5)); ax.set_box_aspect((9,9,4.7)); ax.view_init(36,-55); ax.set_axis_off(); ax.set_title(name+' | CUTAWAY GRAYBOX'); fig.tight_layout(); img=out/(name+'.png'); fig.savefig(img,dpi=120); plt.close(fig)
  records.append(dict(id='env_study_'+name,poi=poi,status='graybox_cutaway',floor_id='abyss_001' if name=='abyss_trial' else None,placements=placements,sha256={p.name:base.digest(p),img.name:base.digest(img)}))
 assert not any(p['asset_id'] in ('env_asset_bed_child','env_asset_toy_wood') for r in records if r['id'] in ('env_study_home_before','env_study_home_erased') for p in r['placements'])
 (out/'assembly-manifest.json').write_text(json.dumps(dict(schema_version=1,units='cm',notes='Local placement studies, no runtime access, navigation or collision integration. Save/Quest own variant selection.',assemblies=records),indent=2))
 print('PASS',len(records),'cutaway GLBs and PNGs; extents round-trip; Noah props absent in before/erased')
if __name__=='__main__': main(Path(sys.argv[1]))
