"""Cycle 02 original prototype textures, UVs and separate collision proxies.
Run: python generate_textured.py OUTPUT_DIRECTORY
All rights reserved. Not Blender/UE or production photorealism.
"""
import json, sys, struct
from pathlib import Path
import numpy as np
from PIL import Image
import trimesh
from trimesh.visual.texture import TextureVisuals
from trimesh.visual.material import PBRMaterial
import generate_cycle02 as base


def images(name):
    rgb, rough, metal = base.MATS[name]
    rng = np.random.default_rng(120 + list(base.MATS).index(name))
    n = 128
    y, x = np.mgrid[0:n, 0:n] * (2*np.pi/n)
    noise = rng.normal(0, .08, (n,n))
    if name == 'oak':
        h = .20*np.sin(9*x + .35*np.sin(3*y)) + noise*.25
    elif name == 'stone':
        h = .13*np.sin(4*x)*np.sin(3*y) + noise
    elif name == 'linen':
        h = .08*(np.sin(24*x)+np.sin(24*y)) + noise*.2
    else:
        h = .04*np.sin(19*x) + noise*.15
    col = np.clip(np.asarray(rgb[:3])[None,None,:]*(1+h[:,:,None]),0,255).astype('uint8')
    mr = np.zeros((n,n,3), dtype='uint8')
    mr[:,:,0]=255; mr[:,:,1]=np.clip((rough+h*.15)*255,0,255).astype('uint8'); mr[:,:,2]=round(metal*255)
    dy, dx = np.gradient(h); normals = np.stack((-dx,-dy,np.ones_like(h)),axis=-1)
    normals /= np.linalg.norm(normals,axis=-1,keepdims=True)
    normal = ((normals*.5+.5)*255).astype('uint8')
    return [Image.fromarray(a) for a in (col,mr,normal)]


def mesh(s,c,m):
    q = trimesh.creation.box(extents=s)
    verts = q.vertices[q.faces].reshape(-1,3)
    uv=[]
    # Pack six planar face islands in a 3x2 grid; 5% padding per cell.
    for tri, norm in zip(q.vertices[q.faces],q.face_normals):
        axis=int(np.argmax(np.abs(norm))); side=int(norm[axis]>0)
        idx=axis*2+side; u,v=[j for j in range(3) if j!=axis]
        coords=tri[:,[u,v]]/np.asarray(s)[[u,v]]+.5
        coords=.05+.9*coords
        uv.extend((coords+[idx%3,idx//3])/[3,2])
    albedo,mr,normal=images(m)
    mat=PBRMaterial(name=m,baseColorFactor=[255,255,255,255],roughnessFactor=1.,metallicFactor=1.,baseColorTexture=albedo,metallicRoughnessTexture=mr,normalTexture=normal)
    return trimesh.Trimesh(vertices=verts+c,faces=np.arange(len(verts)).reshape(-1,3),vertex_normals=np.repeat(q.face_normals,3,axis=0),process=False,visual=TextureVisuals(uv=np.array(uv),material=mat))


def main(out):
    base.mesh=mesh
    base.main(out)
    path=out/'manifest.json'; data=json.loads(path.read_text())
    for name in base.MATS:
        for image,suffix in zip(images(name),('basecolor','metalrough','normal')):
            image.save(out/f'mat_{name}_{suffix}.png')
    textures={p.name:base.digest(p) for p in sorted(out.glob('mat_*.png'))}
    for rec in data['assets']:
        k=rec['id'].removeprefix('env_asset_'); coll=trimesh.Scene()
        for i,(s,c,m) in enumerate(base.parts(k)):
            q=trimesh.creation.box(extents=s); q.apply_translation(c)
            coll.add_geometry(q,node_name=f'UCX_{k}_{i:02d}',geom_name=f'UCX_{k}_{i:02d}')
        coll.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))
        cp=out/(k+'_collision.glb'); cp.write_bytes(coll.export(file_type='glb'))
        loaded=trimesh.load(cp,force='scene'); assert len(loaded.geometry)==len(rec['collision_boxes'])
        assert np.allclose(loaded.extents,[rec['size_m'][0],rec['size_m'][2],rec['size_m'][1]])
        raw=(out/rec['glb']).read_bytes(); n=struct.unpack_from('<I',raw,12)[0]; g=json.loads(raw[20:20+n])
        assert all('NORMAL' in p['attributes'] and 'TEXCOORD_0' in p['attributes'] for m in g['meshes'] for p in m['primitives'])
        assert all('baseColorTexture' in m['pbrMetallicRoughness'] and 'metallicRoughnessTexture' in m['pbrMetallicRoughness'] and 'normalTexture' in m for m in g['materials'])
        rec.update(uv='six padded planar islands per box; shared material UVs across parts',collision_glb=cp.name,material_status='original procedural prototype textures; PNG preview is flat diagnostic')
        rec['sha256'][cp.name]=base.digest(cp)
    data.update(textures=textures,source='generate_cycle02.py + generate_textured.py',status='graybox',texture_channels='sRGB base color; linear metalrough G=roughness B=metalness; tangent-space normal RGB')
    path.write_text(json.dumps(data,indent=2))
    print('PASS',len(data['assets']),'normal/UV/PBR texture attributes and collision round-trip checks;',len(textures),'texture files')


if __name__=='__main__': main(Path(sys.argv[1]))
