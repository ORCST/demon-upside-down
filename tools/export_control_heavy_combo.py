"""Blender: evaluate the exact animation and a proportion-retargeted proxy.

Only exports one actor per variant. A separate CPU rasterizer produces depth,
lineart and beauty, avoiding changes to the user's Blender/Comfy installation.
"""
import argparse,bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser()
ap.add_argument('--output',default='art_source/control/heavy_combo_v01')
ap.add_argument('--frames',type=int,default=24)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=(ROOT/args.output).resolve()
if not OUT.is_relative_to(ROOT):raise ValueError('Output must stay inside project')
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'outputs/motion_reference_20261015/ual2_review.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
arm=bpy.data.objects['Armature'];body=bpy.data.objects['Mannequin'];socket=bpy.data.objects['Reference_sword_0']
action=bpy.data.actions['Sword_Heavy_Combo']
arm.animation_data.action=action
arm.animation_data.action_slot=action.slots[0]
for track in arm.animation_data.nla_tracks:track.mute=True
FRAMES=list(range(args.frames))
NAMES=[b.name for b in arm.pose.bones]
PARENTS={b.name:b.parent.name if b.parent else None for b in arm.pose.bones}
GROUPS={g.index:g.name for g in body.vertex_groups}
weights={name:np.zeros(len(body.data.vertices),np.float64) for name in NAMES}
for v in body.data.vertices:
    for g in v.groups:
        name=GROUPS.get(g.group)
        if name in weights:weights[name][v.index]=g.weight

def local_scale(name):
    n=name.lower()
    if n=='root':return np.array([1.,.55,1.])
    if n=='head' or 'leaf' in n and 'head' in n:return np.array([2.2,1.8,2.2])
    if n.startswith('spine') or n=='pelvis':return np.array([1.45,.67,1.40])
    if n.startswith('neck'):return np.array([1.05,.65,1.05])
    if n.startswith(('thigh','calf')):return np.array([1.20,.55,1.20])
    if n.startswith(('upperarm','lowerarm')):return np.array([1.20,.66,1.20])
    if n.startswith('clavicle'):return np.array([1.10,.85,1.10])
    if n.startswith(('foot','ball')):return np.array([1.10,.85,1.10])
    return np.array([1.,.90,1.])

def get_frame(f):
    scene.frame_set(f);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg);mesh=ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        coords=np.array([v.co[:] for v in mesh.vertices],np.float64)
        xform=np.array(arm.matrix_world.inverted()@ev.matrix_world)
        coords=coords@xform[:3,:3].T+xform[:3,3]
        tri=np.array([t.vertices[:] for t in mesh.loop_triangles],np.int32)
    finally:ev.to_mesh_clear()
    matrices={b.name:np.array(b.matrix,np.float64) for b in arm.pose.bones}
    sw=np.array(arm.matrix_world.inverted()@socket.matrix_world,np.float64)
    return coords,tri,matrices,sw

def proxy(coords,mats):
    transforms={};joints={}
    # Blender bone order is hierarchical for this rig; use explicit recursion.
    def build(name):
        if name in transforms:return
        old=mats[name];parent=PARENTS[name]
        if parent:
            build(parent);pm=transforms[parent]
            joint=pm[:3,:3]@old[:3,3]+pm[:3,3]
        else:joint=old[:3,3].copy()
        r=old[:3,:3];r=r/np.maximum(np.linalg.norm(r,axis=0),1e-8)
        linear=np.diag([1.,1.,.55]) if name=='root' else r@np.diag(local_scale(name))@np.linalg.inv(r)
        m=np.eye(4);m[:3,:3]=linear;m[:3,3]=joint-linear@old[:3,3]
        transforms[name]=m;joints[name]=joint
    for name in NAMES:build(name)
    result=np.zeros_like(coords);total=np.zeros(len(coords))
    for name,w in weights.items():
        ids=np.flatnonzero(w>0)
        if not ids.size:continue
        m=transforms[name];result[ids]+=(coords[ids]@m[:3,:3].T+m[:3,3])*w[ids,None];total[ids]+=w[ids]
    result/=np.maximum(total[:,None],1e-8)
    result[total<1e-8]=coords[total<1e-8]
    return result,transforms,joints

def prism(profile,thickness):
    n=len(profile);verts=np.array([(x,y,z) for z in [-thickness/2,thickness/2] for x,y in profile],float)
    tris=[]
    for i in range(1,n-1):tris.extend([(0,i+1,i),(n,n+i,n+i+1)])
    for i in range(n):j=(i+1)%n;tris.extend([(i,j,n+j),(i,n+j,n+i)])
    return verts,np.array(tris,np.int32)

def sword(ppu):
    # Physical lengths are calibrated in canvas pixels, independent of body retargeting.
    parts=[];faces=[];mats=[];offset=0
    profiles=[([(-15,16),(-15,196),(0,214),(15,196),(15,16)],6,1),([(-21,10),(-21,16),(21,16),(21,10)],10,2),([(-4,-18),(-4,10),(4,10),(4,-18)],8,3)]
    for profile,thick,mat in profiles:
        v,t=prism([(x/ppu,y/ppu) for x,y in profile],thick/ppu)
        parts.append(v);faces.append(t+offset);mats.extend([mat]*len(t));offset+=len(v)
    return np.vstack(parts),np.vstack(faces),np.array(mats,np.uint8)

base_verts,base_tri,base_mats,base_socket=get_frame(0)
pverts,ptrans,pjoints=proxy(base_verts,base_mats)
variants={}
for name,v in [('original',base_verts),('proxy',pverts)]:
    height=float(v[:,2].max()-v[:,2].min());ppu=192./height
    pelvis=base_mats['pelvis'][:3,3] if name=='original' else pjoints['pelvis']
    variants[name]={'ppu':ppu,'floor_z':float(v[:,2].min()),'pelvis_y':float(pelvis[1]),'frame0_body_height_units':height,'target_standing_height_px':192,'target_pelvis_x':336,'target_ground_y':624,'ground_corrections':{}}

metadata={'source_blend':str(SOURCE.relative_to(ROOT)),'source_action':'Sword_Heavy_Combo','fps':24,'size':[768,768],'frames':FRAMES,'frame_count':24,'included_range':'R000-R017 plus R018-R023 context; not an independent recovery animation','projection':'orthographic: screen right = -Y, up = +Z, camera looks along +X','variants':variants,'proxy_method':'Pose-space weighted skeletal retarget; shorten torso/legs/arms, enlarge head; retain source bone rotations and timing. Not a cow mesh.','proxy_scales':{n:local_scale(n).tolist() for n in NAMES},'sword_dimensions_px':{'blade_length':198,'blade_width':30,'blade_thickness':6,'guard_width':42,'grip_length':28},'depth_normalization':'One global camera-depth interval across both variants and all frames; near white, far dark, background black.','calibration':'Frame0 body height192px, pelvisX336, lowest foot boundaryY624. Camera fixed for the entire clip; no per-frame recentering or autoscaling.'}
metadata.update(frame_count=len(FRAMES),included_range=f'R000-R{FRAMES[-1]:03d}; source-speed consecutive frames, no padding/interpolation/retiming; includes the following cut, not an independent recovery',blender_version=bpy.app.version_string,source_scene_fps=scene.render.fps/scene.render.fps_base)
metadata['ground_contact_method']='Both variants receive a uniform body+sword vertical root correction per frame, keeping the lowest body vertex at frame0 ground. Bone angles and horizontal movement are retained. This is suitable for this grounded cut only; do not apply blindly to jumps.'
for name in variants:(OUT/name/'geometry').mkdir(parents=True,exist_ok=True)
for f in FRAMES:
    verts,tri,mats,sw=get_frame(f);pv,trans,joints=proxy(verts,mats)
    for name,v in [('original',verts),('proxy',pv)]:
        config=variants[name];ppu=config['ppu'];sv,st,sm=sword(ppu)
        origin=sw[:3,3].copy();rot=sw[:3,:3].copy();rot/=np.maximum(np.linalg.norm(rot,axis=0),1e-8)
        if name=='proxy':origin=trans['hand_r'][:3,:3]@origin+trans['hand_r'][:3,3]
        sword_vertices=sv@rot.T+origin
        # Keep this grounded attack in contact, including source foot penetration.
        # Move the whole actor and sword, never the camera or individual limbs.
        dz=config['floor_z']-float(v[:,2].min())
        v=v.copy();v[:,2]+=dz;sword_vertices[:,2]+=dz;origin[2]+=dz
        config['ground_corrections'][str(f)]={'units':dz,'screen_y_translation_px':-dz*ppu}
        allv=np.vstack([v,sword_vertices]);allt=np.vstack([tri,st+len(v)]);materials=np.concatenate([np.zeros(len(tri),np.uint8),sm])
        # The frame0-calibrated projection stays fixed for every frame.
        projected=np.empty_like(allv)
        projected[:,0]=336+(config['pelvis_y']-allv[:,1])*ppu
        projected[:,1]=624-(allv[:,2]-config['floor_z'])*ppu
        projected[:,2]=allv[:,0]*ppu
        np.savez_compressed(OUT/name/'geometry'/f'R{f:03d}.npz',vertices=projected.astype(np.float32),triangles=allt,materials=materials)
        if f==0:
            config['frame0_body_bbox']=[float(projected[:len(v),0].min()),float(projected[:len(v),1].min()),float(projected[:len(v),0].max()),float(projected[:len(v),1].max())]
            wrist=origin
            config['frame0_wrist_px']=[float(336+(config['pelvis_y']-wrist[1])*ppu),float(624-(wrist[2]-config['floor_z'])*ppu)]
    print('EXPORTED',f,flush=True)
(OUT/'render_manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
print('EXPORT_DONE',flush=True)
