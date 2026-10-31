"""Blender: author Niulai's guard idle (sword held forward, tip up-right) on top of Sword_Idle,
and give the locomotion clips the same sword grip.

    blender --background --python tools/niulai3d_guard_idle.py      (after niulai3d_build_rig.py)

UAL Sword_Idle rests the sword across the chest with the torso turned to the camera and the
head looking down: at 64 px the blade covers the face. This keeps its legs and pelvis bob, but
  - torso chain: pure profile with a forward guard lean (+ a small breathing sway)
  - head: level, turned slightly toward the camera so brow / eye / snout read
  - arms: IK to hand targets in front of the belly (relative to the chest, so they follow the bob)
  - sword: fixed angle in the right hand, tip up-forward
Locomotion (jog / sprint / jump_*): legs and torso stay as baked, both arms IK to the same grip
relative to the chest -> actions NL_<clip>_carry / SW_<clip>_carry.
Adds the actions to art_source/3d/model/niulai_rig_v01.blend.
Render with: blender --background --python tools/niulai3d_render.py -- guard_idle
"""
import bpy, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parent.parent
BLEND = ROOT / "art_source/3d/model/niulai_rig_v01.blend"
SRC = "sword_idle"
OUT = "guard_idle"
# locomotion clips get the same sword grip relative to the chest, so idle -> run/jump keeps the sword
CARRY = {"jog": "jog_carry", "sprint": "sprint_carry", "jump_start": "jump_start_carry",
         "jump_loop": "jump_loop_carry", "jump_land": "jump_land_carry"}

# pose parameters (world: forward = -Y = screen right, camera at -X, up = +Z)
LEAN = {"spine_01": 4, "spine_02": 8, "spine_03": 12, "neck_01": 6, "Head": 0}   # forward lean, deg
HEAD_YAW = -12            # turn toward the camera, deg
BREATH = 1.5              # extra chest lean amplitude over the loop, deg
SWORD_FOLLOW = 0.25        # share of the chest rotation the sword follows (running lean, landing dip)
SWORD_ANGLE = 38          # blade above horizontal, deg
HAND_R = Vector((-0.10, -0.13, 0.35))   # right (camera-side) hand, relative to standing pose
STANCE = (("thigh_r", "foot_r", 18), ("thigh_l", "foot_l", -18))   # widen the source stance: near leg back, far leg forward, deg
HAND_L = Vector((0.06, -0.12, 0.34))    # left hand reaches toward the grip from the far side


def norm(m):
    return Matrix.Translation(m.to_translation()) @ m.to_3x3().normalized().to_4x4()


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
arm = bpy.data.objects["NiulaiRig"]
sword = bpy.data.objects["Sword"]
mesh = bpy.data.objects["Niulai"]
arm.animation_data.action = bpy.data.actions[f"NL_{SRC}"]
sword.animation_data.action = bpy.data.actions[f"SW_{SRC}"]

# hand -> sword offset, constant in every baked clip
scene.frame_set(0)
hand_w = norm(arm.matrix_world @ arm.pose.bones["hand_r"].matrix)
sock_rel = hand_w.inverted() @ norm(sword.matrix_world)

# desired sword orientation: blade (local +Y) up-forward, bright edge (local +X) up-back
a = math.radians(SWORD_ANGLE)
d = Vector((0, -math.cos(a), math.sin(a)))
w = Vector((0, math.sin(a), math.cos(a)))
sword_rot = Matrix((w, d, w.cross(d))).transposed()           # columns X, Y, Z
hand_rot = sword_rot @ sock_rel.to_3x3().inverted()

rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}


def empty(name):
    e = bpy.data.objects.new(name, None)
    scene.collection.objects.link(e)
    return e


# ---------------------------------------------------------------- constraints
rot_targets, rot_cons = {}, []
for name in LEAN:
    e = empty(f"tgt_{name}")
    rot_targets[name] = e
    c = arm.pose.bones[name].constraints.new("COPY_ROTATION")
    c.target = e
    rot_cons.append((name, c))
ik_targets, pole_targets = {}, {}
for s in ("r", "l"):
    t, p = empty(f"ik_{s}"), empty(f"pole_{s}")
    ik_targets[s], pole_targets[s] = t, p
    c = arm.pose.bones[f"lowerarm_{s}"].constraints.new("IK")
    c.target, c.pole_target, c.chain_count = t, p, 2
    c.pole_angle = math.radians(-90)
hand_tgt = empty("tgt_hand_r")
c = arm.pose.bones["hand_r"].constraints.new("COPY_ROTATION")
c.target = hand_tgt
pole_off = {"r": Vector((-0.12, 0.10, -0.15)), "l": Vector((0.12, 0.10, -0.15))}
parents = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}


def lean_rot(name, deg):
    yaw = HEAD_YAW if name == "Head" else HEAD_YAW / 2 if name == "neck_01" else 0
    r = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(deg), 3, "X")
    return r @ rest[name].to_3x3()


def chest_w():
    return arm.matrix_world @ arm.pose.bones["spine_03"].matrix


def sample(src, guard):
    """Evaluate src with the constraints; returns {frame: armature-space bone matrices}."""
    act = bpy.data.actions[f"NL_{src}"]
    arm.animation_data.action = act
    first, last = int(act.frame_range[0]), int(act.frame_range[1])
    n = last - first + 1
    for name, c in rot_cons:   # locomotion keeps its torso but gets the level, face-readable head
        c.influence = 1.0 if guard or name in ("neck_01", "Head") else 0.0

    def place(f):
        breath = BREATH * math.sin(2 * math.pi * (f - first) / n)
        for name, e in rot_targets.items():
            extra = breath * (LEAN[name] / 12) if name.startswith("spine") else 0
            e.matrix_world = lean_rot(name, LEAN[name] + extra).to_4x4()
        scene.frame_set(f)
        bpy.context.view_layer.update()

    posed = {}
    for f in range(first, last + 1):
        place(f)
        chest = chest_w()
        for s in ("r", "l"):
            h = chest @ GRIP["rel"][s]
            ik_targets[s].location = h
            pole_targets[s].location = h + pole_off[s]
        # sword angle mostly fixed in the world; it only follows a fraction of the chest's turn
        delta = (chest.to_3x3().normalized() @ GRIP["chest"].inverted()).to_quaternion()
        follow = Quaternion().slerp(delta, SWORD_FOLLOW)
        hand_tgt.matrix_world = (follow.to_matrix() @ hand_rot).to_4x4()
        bpy.context.view_layer.update()
        pm = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
        for thigh, foot, deg in (STANCE if guard else ()):   # swing each leg subtree about the hip, keep the foot flat
            for top, ang in ((thigh, deg), (foot, -deg)):
                joint = pm[top].to_translation()
                pivot = Matrix.Translation(joint) @ Matrix.Rotation(math.radians(ang), 4, "X") @ Matrix.Translation(-joint)
                for b in [top, *(c.name for c in arm.pose.bones[top].children_recursive)]:
                    pm[b] = pivot @ pm[b]
        posed[f] = pm
    return posed


# grip relative to the chest, defined on the guard pose at frame 0 (no breathing)
arm.animation_data.action = bpy.data.actions[f"NL_{SRC}"]
for _, c in rot_cons:
    c.influence = 1.0
for name, e in rot_targets.items():
    e.matrix_world = lean_rot(name, LEAN[name]).to_4x4()
scene.frame_set(0)
bpy.context.view_layer.update()
chest0 = chest_w()
GRIP = {"rel": {"r": chest0.inverted() @ HAND_R, "l": chest0.inverted() @ HAND_L},
        "chest": chest0.to_3x3().normalized()}

jobs = {OUT: sample(SRC, True)}
jobs.update({out: sample(src, False) for src, out in CARRY.items()})

# ---------------------------------------------------------------- bake to plain keyframes
for pb in arm.pose.bones:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
for e in [*rot_targets.values(), *ik_targets.values(), *pole_targets.values(), hand_tgt]:
    bpy.data.objects.remove(e, do_unlink=True)


def bake(out, posed):
    for old in (f"NL_{out}", f"SW_{out}"):
        if old in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[old])
    rig_act = bpy.data.actions.new(f"NL_{out}"); rig_act.use_fake_user = True
    sw_act = bpy.data.actions.new(f"SW_{out}"); sw_act.use_fake_user = True
    arm.animation_data.action = rig_act
    sword.animation_data.action = sw_act
    arm.location = (0, 0, 0)
    for f, pm in posed.items():
        for name, m in pm.items():
            p = parents[name]
            pb = arm.pose.bones[name]
            if p:
                pb.matrix_basis = (rest[p].inverted() @ rest[name]).inverted() @ pm[p].inverted() @ m
            else:
                pb.matrix_basis = rest[name].inverted() @ m
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_quaternion", frame=f)
    # ground contact, then sword in the hand
    ground = {}
    for f in posed:
        scene.frame_set(f)
        ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        ground[f] = -min((ev.matrix_world @ v.co).z for v in me.vertices)
        ev.to_mesh_clear()
    for f, dz in ground.items():
        arm.location.z = dz
        arm.keyframe_insert("location", index=2, frame=f)
    for f in posed:
        scene.frame_set(f)
        sword.matrix_world = norm(arm.matrix_world @ arm.pose.bones["hand_r"].matrix) @ sock_rel
        sword.keyframe_insert("location", frame=f)
        sword.keyframe_insert("rotation_quaternion", frame=f)
    print("DONE", out, min(posed), max(posed))


for out, posed in jobs.items():
    bake(out, posed)
arm.animation_data.action = bpy.data.actions[f"NL_{SRC}"]
sword.animation_data.action = bpy.data.actions[f"SW_{SRC}"]
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
