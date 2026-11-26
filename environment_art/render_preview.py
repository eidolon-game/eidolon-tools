"""CPU depth-buffered orthographic preview of exported GLB. Not UE or Blender PBR parity.
Original code; all rights reserved. Usage: python render_preview.py INPUT_DIR
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh


def unit(v):
    return v / np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)


def sample(img,uv,default):
    if img is None: return np.broadcast_to(default,(*uv.shape[:-1],len(default)))
    a=np.asarray(img.convert('RGB'),dtype=float)/255
    h,w=a.shape[:2]; i=np.clip((uv[...,0]*(w-1)).astype(int),0,w-1); j=np.clip(((1-uv[...,1])*(h-1)).astype(int),0,h-1)
    return a[j,i]


def render(path):
    scene=trimesh.load(path,force='scene'); convert=trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]); pieces=[]
    for node in scene.graph.nodes_geometry:
        tf,gn=scene.graph[node]; q=scene.geometry[gn].copy(); q.apply_transform(convert@tf); pieces.append(q)
    vertices=np.concatenate([q.vertices for q in pieces]); view=unit(np.array([.85,-1.,.75])); right=unit(np.cross([0.,0.,1.],view)); up=np.cross(view,right); basis=np.stack((right,up,view),axis=1)
    projected=vertices@basis; lo=projected.min(axis=0); hi=projected.max(axis=0)
    W,H=960,720; scale=min((W-120)/max(hi[0]-lo[0],1e-6),(H-150)/max(hi[1]-lo[1],1e-6)); center=(hi+lo)/2
    depth=np.full((H,W),-np.inf); rgb=np.empty((H,W,3),dtype=np.uint8); rgb[:]=[28,32,38]
    light=unit(view+np.array([-.5,-.2,1.])); half=unit(light+view)
    for q in pieces:
        xyz=q.vertices@basis; xy=np.stack(((xyz[:,0]-center[0])*scale+W/2,H/2+35-(xyz[:,1]-center[1])*scale),axis=1)
        uvs=q.visual.uv; mat=q.visual.material
        for face,n in zip(q.faces,q.face_normals):
            if np.dot(n,view)<=1e-10: continue
            p=xy[face]; z=xyz[face,2]; lo2=np.maximum(np.floor(p.min(axis=0)).astype(int),[0,0]); hi2=np.minimum(np.ceil(p.max(axis=0)).astype(int),[W-1,H-1]); x0,y0=lo2; x1,y1=hi2
            if x0>x1 or y0>y1: continue
            xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5); a,b,c=p
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-10: continue
            w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den; w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den; w2=1-w0-w1
            zz=w0*z[0]+w1*z[1]+w2*z[2]; region=depth[y0:y1+1,x0:x1+1]; mask=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)&(zz>region)
            if not mask.any(): continue
            weights=np.stack((w0[mask],w1[mask],w2[mask]),axis=-1); uv=weights@uvs[face]; factor=np.asarray(mat.baseColorFactor[:3],dtype=float)/255
            color=sample(mat.baseColorTexture,uv,[1.,1.,1.])*factor; mr=sample(mat.metallicRoughnessTexture,uv,[1.,1.,1.]); rough=np.clip(mr[:,1]*mat.roughnessFactor,.06,1); metal=mr[:,2]*mat.metallicFactor
            norms=np.broadcast_to(n,(len(uv),3)); tri=q.vertices[face]; du=uvs[face][1:]-uvs[face][0]; det=du[0,0]*du[1,1]-du[1,0]*du[0,1]
            if mat.normalTexture is not None and abs(det)>1e-10:
                e=tri[1:]-tri[0]; t=unit((e[0]*du[1,1]-e[1]*du[0,1])/det); bt=unit((e[1]*du[0,0]-e[0]*du[1,0])/det); nm=sample(mat.normalTexture,uv,[.5,.5,1])*2-1; norms=unit(nm[:,0,None]*t+nm[:,1,None]*bt+nm[:,2,None]*n)
            ndl=np.maximum(norms@light,0); ndh=np.maximum(norms@half,0); spec=ndh**(2+50*(1-rough)); lin=color**2.2
            lit=lin*(.33+.75*ndl[:,None])*(1-.45*metal[:,None])+spec[:,None]*(.04*(1-metal[:,None])+.35*metal[:,None]*lin)
            rgb[y0:y1+1,x0:x1+1][mask]=(np.clip(lit,0,1)**(1/2.2)*255).astype(np.uint8); region[mask]=zz[mask]
    assert np.isfinite(depth).sum()>1000, path
    im=Image.fromarray(rgb); draw=ImageDraw.Draw(im); font=ImageFont.truetype('DejaVuSans.ttf',25); small=ImageFont.truetype('DejaVuSans.ttf',15)
    draw.text((28,20),path.stem.replace('_',' ').upper(),font=font,fill=(235,232,223)); draw.text((30,52),'EIDOLON / DEPT 12   |   GRAYBOX / CPU TEXTURED PREVIEW',font=small,fill=(168,177,187)); draw.text((30,H-32),'Orthographic depth buffer / approximate lighting / not Unreal or Blender',font=small,fill=(168,177,187))
    out=path.with_name(path.stem+'_render.png'); im.save(out); return {'glb':path.name,'render':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'covered_pixels':int(np.isfinite(depth).sum())}


if __name__=='__main__':
    root=Path(sys.argv[1]); records=[render(p) for p in sorted(root.glob('*.glb')) if not p.stem.endswith('_collision')]; (root/'render-manifest.json').write_text(json.dumps(records,indent=2)); print('PASS',len(records),'depth-buffered textured previews')
