"""Blender: Hunyuan Niulai mesh -> UAL-compatible rig -> baked clips + sword.

    blender --background --python tools/niulai3d_build_rig.py

Rig: a copy of the UAL skeleton fitted into the A-pose mesh. Each fitted bone keeps the
source rest orientation rotated by the minimal rotation from source to target direction,
so copying world rotations per frame reproduces the source motion without twist.
UAL1 and UAL2 share the same skeleton, so UAL1 actions are played on the UAL2 review armature.
Each clip becomes its own action: rig "NL_<clip>", sword "SW_<clip>" (frames start at 0).
Output: art_source/3d/model/niulai_rig_v01.blend (+ niulai_rig_v01_report.json)
"""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT = Path(__file__).resolve().parent.parent
SRC_FBX = ROOT / "art_source/3d/reference/9a238c874d291ec59ea7b5bd02d0d64b.fbx"
MODEL_DIR = ROOT / "art_source/3d/model"
FBX_COPY = MODEL_DIR / "niulai_hunyuan_v01.fbx"
OUT_BLEND = MODEL_DIR / "niulai_rig_v01.blend"
SOURCE_BLEND = ROOT / "outputs/motion_reference_20261015/ual2_review.blend"
UAL1_GLB = ROOT / "outputs/motion_reference_20261015/sources/Universal Animation Library[Standard]/Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb"
# clip name -> source action (UAL2 actions live in the review blend, UAL1 ones come from the glb)
CLIPS = {
    "heavy_combo": "Sword_Heavy_Combo",
    "sword_idle": "Sword_Idle",
    "jog": "Jog_Fwd_Loop",
    "sprint": "Sprint_Loop",
    "jump_start": "Jump_Start",
    "jump_loop": "Jump_Loop",
    "jump_land": "Jump_Land",
    "roll": "Roll",
    "hit": "Hit_Chest",
    "death": "Death01",
}
H = 1.078                      # Niulai standing height (units)
NATIVE_PX = 64 / H             # native pixels per unit at 64px standing height
CX, CY = 0.01, -0.03           # body centre (mesh is offset slightly)

MODEL_DIR.mkdir(parents=True, exist_ok=True)
if not FBX_COPY.exists():
    shutil.copy2(SRC_FBX, FBX_COPY)

# ------------------------------------------------------------------ source data
bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
s_arm = bpy.data.objects["Armature"]
s_sock = bpy.data.objects["Reference_sword_0"]
for t in s_arm.animation_data.nla_tracks:
    t.mute = True
scene = bpy.context.scene
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(UAL1_GLB))
for o in set(bpy.data.objects) - before:   # keep only the imported actions
    bpy.data.objects.remove(o, do_unlink=True)

def norm(m):
    return Matrix.Translation(m.to_translation()) @ m.to_3x3().normalized().to_4x4()

src_rest = {b.name: norm(s_arm.matrix_world @ b.matrix_local) for b in s_arm.data.bones}
src_len = {b.name: b.length * s_arm.matrix_world.to_scale()[0] for b in s_arm.data.bones}
parents = {b.name: (b.parent.name if b.parent else None) for b in s_arm.data.bones}
order = [b.name for b in s_arm.data.bones]  # Blender keeps parents before children
src_pelvis_rest = src_rest["pelvis"].to_translation()

def sample(action_name):
    act = bpy.data.actions[action_name]
    s_arm.animation_data.action = act
    s_arm.animation_data.action_slot = act.slots[0]
    out = {}
    for f in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1):
        scene.frame_set(f)
        out[f - int(act.frame_range[0])] = {
            "pose": {pb.name: norm(s_arm.matrix_world @ pb.matrix) for pb in s_arm.pose.bones},
            "sock": norm(s_sock.matrix_world)}
    return out

clip_frames = {clip: sample(action) for clip, action in CLIPS.items()}

# ------------------------------------------------------------------ target joints
def L(x, y, z):  # left side helper; right side mirrors x around CX
    return Vector((CX + x, CY + y, z))

joints = {
    "root": (L(0, 0, 0), L(0, 0.5, 0)),
    "pelvis": (L(0, 0, 0.27), L(0, 0, 0.33)),
    "spine_01": (L(0, 0, 0.33), L(0, 0, 0.41)),
    "spine_02": (L(0, 0, 0.41), L(0, 0, 0.49)),
    "spine_03": (L(0, 0, 0.49), L(0, 0, 0.58)),
    "neck_01": (L(0, 0, 0.58), L(0, 0, 0.65)),
    "Head": (L(0, 0, 0.65), L(0, 0, 0.95)),
}
side = {
    "clavicle": ((0.02, 0, 0.56), (0.17, 0, 0.57)),
    "upperarm": ((0.19, 0, 0.565), (0.27, 0, 0.48)),
    "lowerarm": ((0.27, 0, 0.48), (0.33, 0, 0.42)),
    "hand": ((0.33, 0, 0.42), (0.36, 0, 0.37)),
    "thigh": ((0.10, 0.01, 0.27), (0.10, 0.02, 0.15)),
    "calf": ((0.10, 0.02, 0.15), (0.10, 0.03, 0.075)),
    "foot": ((0.10, 0.03, 0.075), (0.10, -0.06, 0.02)),
    "ball": ((0.10, -0.06, 0.02), (0.10, -0.10, 0.02)),
    "ball_leaf": ((0.10, -0.10, 0.02), (0.10, -0.14, 0.02)),
}
for base, (h, t) in side.items():
    for s, sx in (("l", 1), ("r", -1)):
        joints[f"{base}_{s}"] = (L(sx * h[0], h[1], h[2]), L(sx * t[0], t[1], t[2]))

FINGER_SCALE = 0.45
tgt_rest = {}   # armature-space (== world, armature at identity) rest matrices
tgt_len = {}
for name in order:
    sr = src_rest[name]
    s_rot = sr.to_quaternion()
    s_dir = (sr.to_3x3() @ Vector((0, 1, 0))).normalized()
    if name in joints:
        head, tail = joints[name]
        t_dir = (tail - head).normalized()
        rot = s_dir.rotation_difference(t_dir) @ s_rot
        tgt_rest[name] = Matrix.Translation(head) @ rot.to_matrix().to_4x4()
        tgt_len[name] = (tail - head).length
    else:  # fingers: follow the fitted hand, scaled into the fist
        p = parents[name]
        anc = p
        while anc not in joints:
            anc = parents[anc]
        rel = src_rest[anc].inverted() @ sr
        rel = Matrix.Translation(rel.to_translation() * FINGER_SCALE) @ rel.to_3x3().to_4x4()
        tgt_rest[name] = tgt_rest[anc] @ rel
        tgt_len[name] = src_len[name] * FINGER_SCALE

# sword socket relative to hand_r (constant in source; take frame 0)
fr0 = clip_frames["heavy_combo"][0]
sock_rel = fr0["pose"]["hand_r"].inverted() @ fr0["sock"]
K = H / 2.0  # mannequin is 2.0 units tall
sock_rel = Matrix.Translation(sock_rel.to_translation() * K) @ sock_rel.to_3x3().to_4x4()

# ------------------------------------------------------------------ build target scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24
bpy.ops.import_scene.fbx(filepath=str(FBX_COPY))
mesh = [o for o in scene.objects if o.type == "MESH"][0]
mesh.name = "Niulai"
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# remove the duplicate tail stub at the back centre of the shorts
bm = bmesh.new(); bm.from_mesh(mesh.data)
stub = [v for v in bm.verts if -0.03 < v.co.x < 0.07 and 0.30 < v.co.z < 0.43 and v.co.y > 0.165]
removed = len(stub)
bmesh.ops.delete(bm, geom=stub, context="VERTS")
boundary = [e for e in bm.edges if e.is_boundary]
if boundary:
    bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
bm.to_mesh(mesh.data); bm.free()

arm_data = bpy.data.armatures.new("NiulaiRig")
arm = bpy.data.objects.new("NiulaiRig", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
ebs = {}
for name in order:
    eb = arm_data.edit_bones.new(name)
    eb.head = (0, 0, 0); eb.tail = (0, 0.1, 0)
    eb.matrix = tgt_rest[name]
    eb.length = max(tgt_len[name], 0.005)
    ebs[name] = eb
for name in order:
    if parents[name]:
        ebs[name].parent = ebs[parents[name]]
    ebs[name].use_connect = False
    ebs[name].use_deform = name in joints and name != "root" and "leaf" not in name
bpy.ops.object.mode_set(mode="OBJECT")
tgt_rest = {b.name: b.matrix_local.copy() for b in arm_data.bones}  # exact values Blender stored

# skin
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
unweighted = sum(1 for v in mesh.data.vertices if not v.groups)

# ------------------------------------------------------------------ bake animation
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
ratio = joints["pelvis"][0].z / src_pelvis_rest.z

# The source combo spins the body up to ~180 deg. A faceless mannequin hides it in side
# view, but Niulai would show his back. Clamp the world yaw of the torso/head chain to
# near-profile (negative = turned toward the camera at -X). Arms and legs keep their exact
# world rotations so the side-view sword path stays faithful to the reference.
YAW_CHAIN = ("pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "Head")
YAW_TOWARD_CAM = math.radians(40)          # max 3/4 turn toward the camera
HEAD_PITCH = (math.radians(-15), math.radians(10))
HEAD_ROLL = math.radians(20)
fwd_local = {n: src_rest[n].to_3x3().inverted() @ Vector((0, -1, 0)) for n in YAW_CHAIN}
up_local = {n: src_rest[n].to_3x3().inverted() @ Vector((0, 0, 1)) for n in YAW_CHAIN}
yaw_log = {}

def clamp_yaw(name, rot3):
    # continuous map: facing away (yaw>0) or fully back (+-180) -> profile; turning toward the
    # camera (-90) -> at most a 3/4 view. sin() keeps it continuous through the +-180 wrap.
    f = rot3 @ fwd_local[name]
    yaw = math.atan2(f.x, -f.y)
    new = -YAW_TOWARD_CAM * math.sin(-yaw) if yaw < 0 else 0.0
    rot3 = Matrix.Rotation(new - yaw, 3, "Z") @ rot3
    if name == "Head":  # keep the face readable: limit looking down/up and sideways tilt
        f = rot3 @ fwd_local[name]
        flat = Vector((f.x, f.y, 0)).normalized()
        pitch = math.asin(max(-1.0, min(1.0, f.z)))
        tp = min(max(pitch, HEAD_PITCH[0]), HEAD_PITCH[1])
        rot3 = f.rotation_difference(flat * math.cos(tp) + Vector((0, 0, tp and math.sin(tp)))).to_matrix() @ rot3
        f = rot3 @ fwd_local[name]
        u = rot3 @ up_local[name]
        ref = (Vector((0, 0, 1)) - f * f.z).normalized()          # 'no roll' up vector
        roll = math.atan2(f.dot(ref.cross(u)), ref.dot(u))
        tr = min(max(roll, -HEAD_ROLL), HEAD_ROLL)
        rot3 = Matrix.Rotation(tr - roll, 3, f) @ rot3
    return rot3, math.degrees(yaw)

# ------------------------------------------------------------------ sword (native-pixel sized)
def hexcol(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c] + [1]

def flat_mat(name, hx):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = hexcol(hx)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])
    return m

def box(name, x0, x1, y0, y1, th, mat, tip=False):
    u = 1 / NATIVE_PX
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)] if not tip else [(x0, y0), (x1, y0), (x1, y1 - 3), ((x0 + x1) / 2, y1), (x0, y1 - 3)]
    bm = bmesh.new()
    top = [bm.verts.new((x * u, y * u, th / 2 * u)) for x, y in pts]
    bot = [bm.verts.new((x * u, y * u, -th / 2 * u)) for x, y in pts]
    bm.faces.new(top); bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([top[i], top[j], bot[j], bot[i]])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); return ob

sword = bpy.data.objects.new("Sword", None)
scene.collection.objects.link(sword)
parts = [
    # Blade/guard are as deep as they are wide: a flat blade turns edge-on (1-2 px) in side
    # view during swings; a square section always reads as a wide greatsword.
    box("SwordGrip", -1.5, 1.5, -6, 3.3, 3, flat_mat("grip", "#5B402D")),
    box("SwordGuard", -7, 7, 3.3, 5.3, 10, flat_mat("guard", "#4D515D")),
    box("SwordBlade", -5, 3, 5.3, 71.3, 8, flat_mat("blade", "#777C86"), tip=True),
    box("SwordEdge", 3, 5, 5.3, 68.3, 8, flat_mat("edge", "#BCC3CA")),
]
for p in parts:
    scene.collection.objects.link(p); p.parent = sword
sword.rotation_mode = "QUATERNION"
arm.animation_data_create(); sword.animation_data_create()


# Locomotion clips swing the sword arm wildly (the source carries nothing). Those clips hold
# the right arm in its Sword_Idle pose relative to the chest, so the sword stays carried.
CARRY_CLIPS = {"jog", "sprint", "jump_start", "jump_loop", "jump_land", "roll"}
R_ARM = ("clavicle_r", "upperarm_r", "lowerarm_r", "hand_r")


def compute_posed(sp, clip, f, carry_ref=None):
    posed = {}
    for name in order:
        p = parents[name]
        if carry_ref and name in R_ARM:
            posed[name] = posed[p] @ (carry_ref[p].inverted() @ carry_ref[name])
            continue
        rot3 = sp[name].to_3x3()
        if name in YAW_CHAIN:
            rot3, y = clamp_yaw(name, rot3)
            yaw_log.setdefault(clip, {}).setdefault(name, {})[f] = round(y)
        if name == "root":
            t = tgt_rest[name].to_translation()
        elif name == "pelvis":
            t = tgt_rest[name].to_translation() + (sp[name].to_translation() - src_pelvis_rest) * ratio
        else:
            t = posed[p] @ (tgt_rest[p].inverted() @ tgt_rest[name].to_translation())
        posed[name] = Matrix.Translation(t) @ rot3.to_4x4()
    return posed


def bake_clip(clip, frames, carry_ref=None):
    """Bake one sampled source clip into actions NL_<clip> (rig) and SW_<clip> (sword)."""
    rig_act = bpy.data.actions.new(f"NL_{clip}"); rig_act.use_fake_user = True
    sw_act = bpy.data.actions.new(f"SW_{clip}"); sw_act.use_fake_user = True
    arm.animation_data.action = rig_act
    sword.animation_data.action = sw_act
    arm.location = (0, 0, 0)
    hands = {}
    for f, data in frames.items():
        posed = compute_posed(data["pose"], clip, f, carry_ref)
        for name in order:
            pb = arm.pose.bones[name]
            p = parents[name]
            if p:
                basis = (tgt_rest[p].inverted() @ tgt_rest[name]).inverted() @ posed[p].inverted() @ posed[name]
            else:
                basis = tgt_rest[name].inverted() @ posed[name]
            pb.matrix_basis = basis
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_quaternion", frame=f)
        hands[f] = posed["hand_r"]
    # ground contact: lowest body vertex on z=0 every frame (uniform vertical shift)
    ground = {}
    for f in frames:
        scene.frame_set(f)
        ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        ground[f] = -min((ev.matrix_world @ v.co).z for v in me.vertices)
        ev.to_mesh_clear()
    for f, dz in ground.items():
        arm.location.z = dz
        arm.keyframe_insert("location", index=2, frame=f)
    for f in frames:
        scene.frame_set(f)
        sword.matrix_world = norm(arm.matrix_world @ hands[f]) @ sock_rel
        sword.keyframe_insert("location", frame=f)
        sword.keyframe_insert("rotation_quaternion", frame=f)
    return {"source_action": CLIPS[clip], "frames": [0, max(frames)],
            "ground_shift_range": [round(min(ground.values()), 4), round(max(ground.values()), 4)]}


ratio = joints["pelvis"][0].z / src_pelvis_rest.z
carry = compute_posed(clip_frames["sword_idle"][0]["pose"], "sword_idle", 0)
clips_report = {clip: bake_clip(clip, frames, carry if clip in CARRY_CLIPS else None)
                for clip, frames in clip_frames.items()}
for clip in CARRY_CLIPS:
    clips_report[clip]["sword_arm"] = "Sword_Idle frame 0 (relative to spine_03)"
arm.animation_data.action = bpy.data.actions["NL_heavy_combo"]
sword.animation_data.action = bpy.data.actions["SW_heavy_combo"]
scene.frame_start, scene.frame_end = 0, clips_report["heavy_combo"]["frames"][1]

report = {"source": str(SOURCE_BLEND.relative_to(ROOT)), "ual1": str(UAL1_GLB.relative_to(ROOT)),
          "clips": clips_report, "stub_vertices_removed": removed, "unweighted_vertices": unweighted,
          "pelvis_translation_ratio": ratio,
          "torso_yaw_map": f"away/back -> profile; toward camera -> -{math.degrees(YAW_TOWARD_CAM):.0f}*sin(-yaw)",
          "head_pitch_deg": [math.degrees(x) for x in HEAD_PITCH], "head_roll_deg": math.degrees(HEAD_ROLL),
          "source_pelvis_yaw_deg": yaw_log.get("heavy_combo", {}).get("pelvis"),
          "sword_px": {"blade": 66, "blade_width": 10, "guard_width": 14, "grip": 9.3}}
(MODEL_DIR / "niulai_rig_v01_report.json").write_text(json.dumps(report, indent=1))
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print("DONE", json.dumps(clips_report))
