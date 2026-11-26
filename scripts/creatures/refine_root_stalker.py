"""Rebuild the original Root Stalker surface and silhouette details in Blender 4.3.

Run: blender -b -t 4 --python-exit-code 1 --python refine_root_stalker.py -- INPUT.glb OUTPUT
The output is a detailed static art prototype with baked texture maps.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import zlib

import bpy
from mathutils import Vector
from mathutils.noise import noise_vector
import numpy as np


def png(path, pixels):
    """Write an RGB PNG in the color space of the supplied pixels."""
    height, width, channels = pixels.shape

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    if channels != 3:
        raise ValueError("The texture needs three channels.")
    scanlines = b"".join(b"\x00" + row.tobytes() for row in pixels)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 8))
        + chunk(b"IEND", b"")
    )


def materials(texture_dir):
    """Bake directional grain and tangent-space normal maps into embeddable images."""
    texture_dir.mkdir(exist_ok=True)
    count = 1024
    v, u = np.mgrid[:count, :count].astype(np.float32) * (math.tau / count)
    stripes = u + .03*np.sin(v*3 + u*2) + .016*np.sin(v*7 - u*8)
    grain = .49 + .12*np.sin(stripes*39 + np.sin(v*3)*.7) + .10*np.sin(stripes*83 + np.cos(v*9)*.69)
    grain += .053*np.sin((stripes + .006*np.sin(v*11))*191 + v*3)
    grain += .034*np.sin(u*257 + .51*np.cos(v*15))
    grain += .051*np.sin(u*14 + v*2) * np.sin(u*31 - v*4)
    pits = np.maximum(0, np.sin(u*87 + v*117) * np.cos(u*143 - v*79) - .55)**2
    seams = np.maximum(0, np.cos(stripes*23 + .60*np.sin(v*5)) - .77)**2 * 4
    fibers = .014*np.sin(u*323 - v*11) + .022*np.sin(u*351 + v*24)
    height = grain + fibers - pits*.36 - seams
    dx = 1.18*(np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1))
    dy = 1.18*(np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0))
    nz = np.ones_like(dx)
    normal = np.stack((-dx, dy, nz), axis=-1)
    normal /= np.sqrt(np.sum(normal*normal, axis=-1, keepdims=True))
    normal_path = texture_dir / "ironwood_directional_normal.png"
    png(normal_path, np.rint((normal*.5+.5)*255).astype(np.uint8))
    normal_image = bpy.data.images.load(str(normal_path), check_existing=True)
    normal_image.colorspace_settings.name = "Non-Color"

    parameters = {
        "heart": ("Dark ironwood heart", (26,20,17), (93,66,49), .82, .37),
        "bark": ("Oxidized longitudinal bark", (35,24,17), (150,105,73), .78, .68),
        "scar": ("Torn copper fibers", (33,17,12), (159,80,47), .67, .65),
        "bone": ("Weathered ivory fracture", (62,44,32), (186,162,117), .76, .58),
        "moss": ("Dried lichen traces", (30,30,18), (106,113,67), .86, .48),
        "horn": ("Black worn root hooks", (23,20,13), (79,62,43), .57, .47),
    }
    signal = np.clip((grain + fibers - seams*.76 - pits*.53 - .24)*1.6, 0, 1)
    signal += .04*np.sin(v*3+u*5) - .06*np.sin(v*7-u*3)*np.sin(u*53 + v*11)
    mats = {}
    for key, (name, dark, bright, roughness, strength) in parameters.items():
        filename = texture_dir / f"{key}_ironwood_basecolor.png"
        shade = np.array(dark, dtype=np.float32) + signal[..., None] * (np.array(bright) - dark)
        png(filename, np.rint(np.clip(shade, 0, 255)).astype(np.uint8))
        image = bpy.data.images.load(str(filename), check_existing=True)
        material = bpy.data.materials.new(name)
        material.diffuse_color = (*(np.asarray(bright)/255*.52), 1)
        material.use_nodes = True
        tree = material.node_tree
        shader = tree.nodes["Principled BSDF"]
        shader.inputs["Roughness"].default_value = roughness
        base_texture = tree.nodes.new("ShaderNodeTexImage")
        base_texture.image = image
        tree.links.new(base_texture.outputs["Color"], shader.inputs["Base Color"])
        normal_texture = tree.nodes.new("ShaderNodeTexImage")
        normal_texture.image = normal_image
        normal_map = tree.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = strength
        tree.links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
        tree.links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
        mats[key] = material

    eyes = bpy.data.materials.new("Deep amber through split resin")
    eyes.use_nodes = True
    bsdf = eyes.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (.105,.031,.006,1)
    bsdf.inputs["Roughness"].default_value = .50
    bsdf.inputs["Emission Color"].default_value = (.55,.147,.022,1)
    bsdf.inputs["Emission Strength"].default_value = .27
    mats["iris"] = eyes
    return mats


def mesh(name, vertices, faces, mats, material_indices, uv_coordinates, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    for material in mats:
        data.materials.append(material)
    uv = data.uv_layers.new(name="Directional grain")
    for polygon, material_index, coords in zip(data.polygons, material_indices, uv_coordinates):
        polygon.material_index = material_index
        polygon.use_smooth = smooth
        for index, coord in zip(polygon.loop_indices, coords):
            uv.data[index].uv = coord
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def spline(points, values, t):
    segment = min(int(t * (len(points)-1)), len(points)-2)
    fraction = t*(len(points)-1) - segment
    first, second = points[segment], points[segment+1]
    beginning = points[max(0, segment-1)]
    end = points[min(len(points)-1, segment+2)]
    center = .5*((2*first) + (-beginning + second)*fraction
                 + (2*beginning - 5*first + 4*second - end)*fraction**2
                 + (-beginning + 3*first - 3*second + end)*fraction**3)
    radius = values[segment] + (values[segment+1]-values[segment]) * fraction
    return center, radius


def radial_axes(points, radii, t, reference):
    center, radius = spline(points, radii, t)
    before = spline(points, radii, max(0, t-.003))[0]
    after = spline(points, radii, min(1, t+.003))[0]
    direction = (after-before).normalized()
    first = direction.cross(reference)
    if first.length < .12:
        first = direction.cross(Vector((1,0,0)))
    first.normalize()
    return center, radius, first, direction.cross(first)


def root(name, controls, radii, mat, seed, *, strands=11, extent=1.0, secondary=None):
    points = [Vector(point) for point in controls]
    reference = Vector((0,1,0)) if abs((points[-1]-points[0]).normalized().y) < .90 else Vector((0,0,1))
    rng = random.Random(seed)
    phase = rng.random()*math.tau
    vertices = []
    rings = 3 + 4*(len(points)-1)
    for ring in range(rings):
        t = ring/(rings-1)
        center, radius, right, across = radial_axes(points,radii,t,reference)
        for side in range(strands):
            a = math.tau*side/strands
            crest = 1 + .12*math.sin(a*3 + phase + 2.1*t) + .05*math.cos(a*5 - 4.2*t + phase)
            ridge = 1 + rng.uniform(-.042,.042)
            vertices.append(center + radius*crest*ridge*(math.cos(a)*right + math.sin(a)*across*extent))
    faces = [tuple(reversed(range(strands)))]
    uv = [tuple((.5+.40*math.cos(math.tau*k/strands),.5+.40*math.sin(math.tau*k/strands))
                for k in reversed(range(strands)))]
    indices = [0]
    for ring in range(rings-1):
        for side in range(strands):
            a = ring*strands+side
            b = ring*strands+(side+1)%strands
            faces.append((a,b,b+strands,a+strands))
            u0,u1 = side/strands,(side+1)/strands
            v0,v1 = ring/(rings-1),(ring+1)/(rings-1)
            uv.append(((u0,v0),(u1,v0),(u1,v1),(u0,v1)))
            indices.append(int(secondary is not None and (side+int(phase))%5 == 1))
    faces.append(tuple(range(len(vertices)-strands,len(vertices))))
    uv.append(tuple((.5+.4*math.cos(math.tau*k/strands),.5+.4*math.sin(math.tau*k/strands))
                    for k in range(strands)))
    indices.append(0)
    return mesh(name, vertices, faces,(mat,) if secondary is None else (mat,secondary),indices,uv,True)


def solid_plate(name, rows, normals, mats, thickness, seed):
    """Give a raised split plate a back, chipped lip and real edge thickness."""
    rng = random.Random(seed)
    length, width = len(rows), len(rows[0])
    vertices = [point for row in rows for point in row]
    front_count = len(vertices)
    for row, normal in zip(rows,normals):
        vertices.extend(point - normal*(thickness*rng.uniform(.66,1.28)) for point in row)

    def index(j,i):
        return j*width+i

    faces, indices, uv = [], [], []

    def add(corners, slot):
        faces.append(corners)
        indices.append(slot)
        uv.append(tuple(((corner%front_count)%width/(width-1),
                         ((corner%front_count)//width)/(length-1)) for corner in corners))

    for j in range(length-1):
        for i in range(width-1):
            corners = (index(j,i),index(j,i+1),index(j+1,i+1),index(j+1,i))
            slot = 2 if i == width-2 and rng.random() < .56 else int(i%3 == 1)
            if rng.random() < .40:
                add((corners[0],corners[1],corners[2]),slot)
                add((corners[0],corners[2],corners[3]),slot)
            else:
                add(corners,slot)
            add(tuple(corner+front_count for corner in reversed(corners)),0)
    edges = []
    edges.extend((index(0,i+1),index(0,i)) for i in range(width-1))
    edges.extend((index(j+1,width-1),index(j,width-1)) for j in range(length-1))
    edges.extend((index(length-1,i),index(length-1,i+1)) for i in range(width-1))
    edges.extend((index(j,0),index(j+1,0)) for j in range(length-1))
    for a,b in edges:
        add((a,b,b+front_count,a+front_count),2 if rng.random()<.68 else 1)
    # Custom strip endpoints can be parametrized in either direction. Orient the closed
    # shell consistently using signed volume before export.
    def volume(corners):
        origin = vertices[corners[0]]
        return sum(origin.dot(vertices[a].cross(vertices[b]))
                   for a,b in zip(corners[1:],corners[2:]))
    if sum(volume(corners) for corners in faces) < 0:
        faces = [tuple(reversed(corners)) for corners in faces]
        uv = [tuple(reversed(coords)) for coords in uv]
    return mesh(name,vertices,faces,mats,indices,uv)


def laminate(name, controls, radii, stage, angle, span, mats, seed, height=.018, curl=0, extent=.93):
    points = [Vector(point) for point in controls]
    reference = Vector((0,1,0)) if abs((points[-1]-points[0]).normalized().y)<.90 else Vector((0,0,1))
    rng = random.Random(seed)
    phase = rng.uniform(-1,1)
    rows, normals = [], []
    for j in range(12):
        progress = j/11
        t = stage[0]+(stage[1]-stage[0])*progress
        center, radius, right, across = radial_axes(points,radii,t,reference)
        offset = phase*.11 + math.sin(progress*3.4+phase)*.088
        width = span*(.62+.38*math.sin(math.pi*progress)**.7)*rng.uniform(.85,1.13)
        row = []
        for i in range(8):
            fraction = i/7
            theta = angle + offset + (fraction-.5)*width
            radial = right*math.cos(theta) + across*math.sin(theta)*extent
            ridge = height*(math.sin(fraction*math.pi)**.64 + .34*math.sin(fraction*math.pi*5+phase))
            breakage = rng.uniform(-.012,.012) if i in (0,7) else rng.uniform(-.004,.004)
            curl_height = curl * math.exp(-progress*7) * math.sin(fraction*math.pi)
            row.append(center + (radius+.009+ridge+breakage+curl_height)*radial)
        rows.append(row)
        normals.append((right*math.cos(angle)+across*math.sin(angle)).normalized())
    return solid_plate(name,rows,normals,mats,thickness=.010,seed=seed+700)


def face_plate(name, controls, materials, seed):
    rng = random.Random(seed)
    rows = []
    points = [Vector(control[:3]) for control in controls]
    widths = [control[3] for control in controls]
    for index in range(15):
        progress = index/14
        center, width = spline(points,widths,progress)
        row = []
        for j in range(9):
            fraction = j/8
            torn = rng.uniform(-.017,.016) if j in (0,8) else rng.uniform(-.006,.006)
            ridge = .023*math.sin(math.pi*fraction)**.92 + .008*math.sin(18*fraction + 3.0*progress)
            row.append(center+Vector(((fraction-.50)*width*(1+rng.uniform(-.13,.13)), -ridge+torn, torn*.61)))
        rows.append(row)
    return solid_plate(name,rows,[Vector((0,-1,0))]*len(rows),materials,.013,seed+384)


def roughen(obj, material, strength, seed):
    for vertex in obj.data.vertices:
        x,y,z = vertex.co
        normal = vertex.normal.copy()
        grain = noise_vector(Vector((31*x+seed,14*y-seed,37*z+seed*.14)))[0]
        splits = math.sin(43*x-19*z + 1.8*math.sin(31*y-z))
        vertex.co += normal * strength * (.57*grain+.43*splits)
    obj.data.update()
    obj.data.materials.clear()
    obj.data.materials.append(material)


def sculpt(mats):
    ash = (mats["bark"],mats["heart"],mats["bone"])
    blood = (mats["scar"],mats["heart"],mats["bone"])
    ivory = (mats["bone"],mats["bark"],mats["scar"])
    moss = (mats["bark"],mats["moss"],mats["bone"])
    meshes = []
    for index,obj in enumerate(tuple(bpy.context.scene.objects)):
        if obj.name == "Sloped stalking torso":
            roughen(obj,mats["heart"],.019,index)
            meshes.append(obj)
        else:
            bpy.data.objects.remove(obj,do_unlink=True)

    trunk = [(0,-.73,1.96),(-.023,-.55,2.017),(-.034,-.291,2.069),
             (-.016,.041,1.992),(.017,.344,1.754),(.021,.677,1.57),(.039,.86,1.48)]
    for index in range(11):
        start = .012 + index*.078
        end = min(1,start+.225)
        for side in (-1,1):
            for row, angle in enumerate((side*.33,side*.94,side*1.44)):
                stage = (start+.019*row,end-.006*row)
                if stage[1]-stage[0]<.029:
                    continue
                if index%3 == 0 and row == 2:
                    continue
                meshes.append(laminate(f"Thorax fractured lamina {side} {index+1:02}.{row+1}",
                                       trunk,(.22,.36,.465,.42,.34,.32,.19),stage,
                                       angle-math.pi/2,.53,ash if row < 2 else moss,181+index*32+side+row*7,
                                       height=.032,curl=.027+(row==1)*.010,extent=.87))
    for side in (-1,1):
        for index in range(7):
            y=-.41+index*.183
            z=2.24-max(index-2,0)*.133
            path=[
                (side*(.18-.006*index),y-.051,z+.106),
                (side*(.365-.017*index),y-.019,z+.030),
                (side*(.469-.027*index),y+.044,z-.164),
                (side*(.304-.019*index),y+.101,z-.37),
                (side*(.17-.012*index),y+.06,z-.402),
            ]
            meshes.append(root(f"Interwoven exposed flank binding {side} {index+1}",path,
                               (.027,.052,.046,.030,.006),mats["bark"],246+index*8+side,secondary=mats["scar"]))
        for index in range(5):
            y=-.28+index*.21
            z=2.42-max(index-2,0)*.16
            path=[(side*.070,y,z),(side*.102,y+.091,z+.049),
                  (side*.166,y+.147,z+.090+index%2*.025),(side*.215,y+.164,z+.085)]
            meshes.append(root(f"Broken spine fiber {side} {index+1}",path,
                               (.011,.015,.012,.002),mats["bone"],297+index*8+side,strands=7))

    head_core=[(-.013,-1.26,1.86),(-.016,-1.176,1.962),(-.016,-1.043,2.059),(-.019,-.86,2.096),(-.016,-.69,2.119)]
    meshes.append(root("Dark disrupted head core",head_core,(.072,.133,.189,.207,.122),mats["heart"],314,
                       strands=22, extent=.88,secondary=mats["scar"]))
    for side in (-1, 1):
        for index in range(5):
            x = side * (.10 + index*.026)
            z = 2.17 + .035*index
            path = [(x, -.91, z), (x*1.30, -.75, z + .055),
                    (x*1.32, -.58, z + .043), (x*1.20, -.40, z - .036)]
            meshes.append(root(f"{'Left' if side < 0 else 'Right'} neck weave {index+1}",
                               path, (.022, .047, .034, .010), mats["bark"],
                               351+index*7+side, secondary=mats["scar"]))
    faces = [
        ("Split crown central ivory left",[(-.081,-1.108,2.255,.101),(-.074,-1.137,2.174,.104),
                                          (-.071,-1.204,2.077,.096),(-.078,-1.232,1.993,.080),
                                          (-.069,-1.259,1.876,.049)],ivory),
        ("Split crown central dark right",[(.049,-1.081,2.240,.108),(.040,-1.141,2.182,.102),
                                            (.035,-1.204,2.083,.087),(.026,-1.233,1.989,.091),
                                            (.024,-1.261,1.860,.038)],ash),
        ("Fractured left cheek horn",[(-.191,-1.038,2.267,.092),(-.221,-1.097,2.169,.082),
                                     (-.236,-1.116,2.082,.094),(-.173,-1.154,1.983,.111),
                                     (-.104,-1.230,1.847,.052)],ash),
        ("Fractured right cheek horn",[(.177,-1.048,2.221,.092),(.202,-1.105,2.138,.092),
                                      (.188,-1.145,2.049,.087),(.150,-1.178,1.963,.082),
                                      (.079,-1.227,1.827,.047)],ivory),
        ("Distressed lower jaw segment",[(-.068,-1.253,1.905,.069),(-.057,-1.263,1.857,.082),
                                         (-.048,-1.245,1.810,.066),(-.019,-1.224,1.784,.039)],blood),
        ("Broken right muzzle lamina",[(.115,-1.231,1.947,.046),(.097,-1.242,1.903,.049),
                                        (.087,-1.242,1.844,.039),(.062,-1.234,1.795,.021)],ivory),
    ]
    for index,(name,controls,materials_) in enumerate(faces):
        meshes.append(face_plate(name,controls,materials_,442+index*26))
    for side in (-1,1):
        x=side*.149-.016
        z=2.106+(.006 if side<0 else -.006)
        brow=[(x-side*.061,-1.127,z+.008),(x-side*.036,-1.176,z+.040),
              (x+side*.012,-1.178,z+.046),(x+side*.043,-1.151,z+.030),(x+side*.062,-1.115,z-.023)]
        meshes.append(root(f"Torn eye canopy {side}",brow,(.019,.026,.023,.019,.006),
                           mats["bark"],490+side,secondary=mats["bone"]))
        meshes.append(root(f"Socket shadow {side}",[(x-.044,-1.119,z-.010),(x-.015,-1.154,z),
                                                     (x+.028,-1.151,z-.008),(x+.046,-1.126,z-.022)],
                           (.013,.028,.025,.008),mats["heart"],512+side,extent=.61))
        meshes.append(root(f"Amber resin trapped in socket {side}",[(x-.015,-1.177,z-.010),
                         (x,-1.184,z+.004),(x+.020,-1.170,z-.008)],(.005,.012,.003),
                         mats["iris"],528+side,strands=7,extent=.65))
        jaw=[(side*.095,-1.137,1.792),(side*.180,-1.289,1.755),
             (side*.190,-1.377,1.781),(side*.205,-1.427,1.843+side*.014)]
        meshes.append(root(f"Worn jaw hook {side}",jaw,(.063,.043,.031,.003),
                           mats["horn"],550+side,strands=12,secondary=mats["bone"]))
        crests=[(side*.155,-.985,2.151),(side*.226,-.941,2.370),
                (side*.313,-.788,2.503),(side*.357,-.634,2.563)]
        meshes.append(root(f"Jagged facial crest {side}",crests,(.073,.058,.032,.003),
                           mats["bark"],571+side,secondary=mats["bone"]))
        for index in range(4):
            point = Vector(crests[1]).lerp(Vector(crests[2]),index*.19)
            meshes.append(root(f"Split facial crest strand {side}.{index+1}",
                               [point,point+Vector((side*.048,-.012,.034)),point+Vector((side*.078,.026,.072))],
                               (.012,.011,.002),mats["bone"],597+index+side,strands=7))

    for side in (-1,1):
        front=[(side*.346,-.295,2.025),(side*(.759+side*.041),-.371+side*.064,1.427),
               (side*(.801+side*.052),-.612+side*.182,.286),(side*(.829+side*.051),-.792+side*.182,.126)]
        rear=[(side*.268,.620,1.553),(side*(.613-side*.033),.427,.930+side*.045),
              (side*(.650-side*.025),.966+side*.122,.487),(side*(.735-side*.020),.992+side*.147,.121)]
        for front_leg, controls in ((True,front),(False,rear)):
            prefix = f"{'Fore' if front_leg else 'Hind'} {'left' if side<0 else 'right'}"
            radii = (.201,.148,.075,.060) if front_leg else (.181,.138,.090,.057)
            seed = 736 + side*21 + front_leg*431
            meshes.append(root(f"{prefix} torn load-bearing core",controls,radii,mats["heart"],seed,
                               strands=19,extent=.91,secondary=mats["scar"]))
            for index in range(9):
                angle = index*math.tau/9 + side*.06
                for row,stage in enumerate(((.021,.360),(.301,.715),(.662,.965))):
                    stage = (stage[0]+(index%3)*.019,min(.986,stage[1]-(index%4)*.014))
                    materials_ = blood if row==0 and index in (3,4) else ash
                    meshes.append(laminate(f"{prefix} split lamination {index+1}.{row+1}",controls,
                                           radii,stage,angle+.13*row,.65,materials_,
                                           seed+31*index+row,height=.019+(index%2)*.006,curl=.018))
            hip,elbow,wrist,foot=map(Vector,controls)
            scar_elbow= (hip.lerp(elbow,.89),elbow+Vector((side*.092,-.085,.045)),
                         elbow.lerp(wrist,.15)+Vector((side*.083,-.039,0)))
            meshes.append(root(f"{prefix} exposed diagonal muscle",scar_elbow,(.033,.037,.011),
                               mats["scar"],seed+40,strands=9))
            for index in range(5):
                t = .15 + .15*index
                points=[Vector(p) for p in controls]
                center,radius,right,across = radial_axes(points,radii,t,Vector((0,1,0)))
                theta=.84*index+side*.57
                radial=right*math.cos(theta)+across*math.sin(theta)
                tip=center+radial*(radius+.058)+Vector((side*.028,0,-.08))
                start=center+radial*(radius-.010)+Vector((0,0,.065))
                meshes.append(root(f"{prefix} fraying fiber {index+1}",[start,center+radial*(radius+.031),tip],
                                   (.018,.014,.002),mats["bone"],seed+71+index,strands=7))
            for digit in range(3):
                x=foot.x+.074*(digit-1)
                y=foot.y+.042*abs(digit-1)
                claw=[(x,y+.022,foot.z+.006),(x+side*.016,y-.135,.121),
                      (x+side*.036,y-.220,.069),(x+side*.053,y-.260,.013+(.009 if digit==1 else 0))]
                meshes.append(root(f"{prefix} grounded split claw {digit+1}",claw,
                                   (.052,.043,.028,.003),mats["horn"],seed+103+digit,strands=11,
                                   extent=.87,secondary=mats["bone"]))
                meshes.append(root(f"{prefix} torn claw fibre {digit+1}",
                                   [claw[1],(x+side*.043,y-.202,.071),(x+side*.060,y-.244,.033)],
                                   (.015,.012,.002),mats["bone"],seed+115+digit,strands=7))
        horn=[(side*.264,-.405,2.220),(side*.397,-.257,2.576),
              (side*.498,-.155,2.815),(side*.573,-.001,2.950)]
        meshes.append(root(f"Split scapular spike {side}",horn,(.114,.083,.042,.003),
                           mats["bark"],932+side,secondary=mats["bone"]))
        for index in range(4):
            base=Vector(horn[0]).lerp(Vector(horn[2]),.31+index*.18)+Vector((side*.03,-.03,.00))
            meshes.append(root(f"Scapular spike wood tear {side}.{index+1}",
                               [base,base+Vector((side*.028,-.036,.084)),base+Vector((side*.045,-.019,.148))],
                               (.030,.018,.003),mats["bone"],946+index+side,strands=7))

    tail=[(.044,.795,1.465),(.167,1.132,1.235),(.473,1.446,1.121),
          (.656,1.786,1.093),(.711,2.039,1.163),(.662,2.238,1.080)]
    tail_radii=(.133,.110,.083,.055,.033,.003)
    meshes.append(root("Continuous trailing broken root",tail,tail_radii,mats["bark"],1190,
                       strands=14,secondary=mats["scar"]))
    meshes.append(root("Trailing root offset fork",[(.473,1.446,1.121),(.318,1.756,1.004),(.284,1.922,.925)],
                       (.065,.039,.003),mats["horn"],1191,secondary=mats["bone"]))
    for i in range(5):
        meshes.append(laminate(f"Unfolding tail bark {i+1}",tail,tail_radii,(.13+i*.125,.37+i*.125),
                               .77*i,.88,ash,1220+i,height=.011,curl=.017))
    return meshes


def aim(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def light(name, position, hsv, power, size, target):
    output=bpy.data.lights.new(name,"AREA")
    output.energy,output.color,output.size=power,hsv,size
    obj=bpy.data.objects.new(name,output)
    bpy.context.collection.objects.link(obj)
    obj.location=position
    aim(obj,target)


def studio():
    scene=bpy.context.scene
    scene.unit_settings.system="METRIC"
    bpy.ops.mesh.primitive_plane_add(size=80,location=(0,0,-.006))
    base=bpy.data.materials.new("Dark compressed forest litter")
    base.use_nodes=True
    nodes=base.node_tree.nodes
    shader=nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value=(.023,.034,.028,1)
    shader.inputs["Roughness"].default_value=.90
    variation=nodes.new("ShaderNodeTexNoise")
    variation.inputs["Scale"].default_value=34
    variation.inputs["Detail"].default_value=3
    bump=nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.38
    bump.inputs["Distance"].default_value=.026
    base.node_tree.links.new(variation.outputs["Fac"],bump.inputs["Height"])
    base.node_tree.links.new(bump.outputs["Normal"],shader.inputs["Normal"])
    bpy.context.object.data.materials.append(base)
    world=bpy.data.worlds.new("Buried forest light")
    scene.world=world
    world.use_nodes=True
    background=world.node_tree.nodes["Background"]
    background.inputs[0].default_value=(.113,.179,.157,1)
    background.inputs[1].default_value=.26
    light("Warm direction",(-2.5,-3.8,4.9),(1,.78,.53),820,1.73,(0,-.35,1.35))
    light("Cool grain rim",(3.9,2.8,4.25),(.52,.76,.79),1490,1.75,(0,.12,1.54))
    light("Face bounce",(3.0,-4.55,2.6),(.79,.86,1),260,1.75,(0,-.82,2.0))
    camera=bpy.data.objects.new("Matched studio camera",bpy.data.cameras.new("Matched studio camera"))
    bpy.context.collection.objects.link(camera)
    scene.camera=camera
    scene.render.engine="CYCLES"
    scene.cycles.samples=32
    scene.cycles.use_denoising=False
    scene.render.threads_mode="FIXED"
    scene.render.threads=4
    scene.render.resolution_x=1100
    scene.render.resolution_y=850
    scene.render.resolution_percentage=100
    return camera


def render(output,camera,composition):
    scene=bpy.context.scene
    if composition == "wide":
        camera.location=(5.88,-7.15,3.86)
        camera.data.lens=65
        aim(camera,(.13,.18,1.44))
    else:
        camera.location=(2.14,-4.64,2.98)
        camera.data.lens=103
        aim(camera,(.062,-.815,2.121))
    scene.render.filepath=str(output)
    bpy.ops.render.render(write_still=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--matched-reference",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=True)
    source=args.source.resolve()
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if args.matched_reference:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        camera=studio()
        for frame in ("wide","close"):
            render(args.output/f"RootStalker_reference_{frame}.png",camera,frame)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    mats=materials(args.output/"textures")
    asset_meshes=sculpt(mats)
    asset=bpy.data.objects.new("RootStalker_Abyss_Forest_Stalker",None)
    bpy.context.collection.objects.link(asset)
    asset["asset_id"]="abyss_forest_stalker"
    asset["source_glb_sha256"]=source_hash
    asset["asset_status"]="static creature detail prototype; pending rig, LODs, collision and Unreal review"
    asset["physical_scale_m"]=1.0
    bpy.context.view_layer.update()
    prior_floor=min((obj.matrix_world@vertex.co).z for obj in asset_meshes for vertex in obj.data.vertices)
    for obj in asset_meshes:
        world=obj.matrix_world.copy()
        world.translation.z -= prior_floor
        obj.parent=asset
        obj.matrix_world=world
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [asset,*asset_meshes]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=asset
    glb=args.output/"RootStalker_reworked.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",use_selection=True,export_extras=True)

    for image in bpy.data.images:
        if image.source=="FILE" and not image.packed_file:
            image.pack()
    camera=studio()
    render(args.output/"RootStalker_reworked_wide.png",camera,"wide")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/"RootStalker_reworked.blend"))
    render(args.output/"RootStalker_reworked_close.png",camera,"close")
    (args.output/"provenance.json").write_text(json.dumps({
        "asset_id":asset["asset_id"],"source_glb_sha256":source_hash,
        "export_glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
        "blender_version":bpy.app.version_string,"status":asset["asset_status"],
        "method":"original torso silhouette; modeled split bark, shell plates and roots; deterministic directional texture maps"
    },indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
