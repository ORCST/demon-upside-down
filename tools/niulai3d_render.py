"""Blender: render the rigged Niulai for pixelization (side view, facing right).

    blender --background --python tools/niulai3d_render.py -- [clip] [first last]

clip is a baked clip from niulai3d_build_rig.py (default heavy_combo); frames default to the whole clip.
For each frame writes, at 4x the native 256 canvas (1024x1024):
  color/Fnnn.png  toon-shaded colour (texture x 2-step light ramp, flat-emission sword)
  depth/Fnnn.png  16-bit camera depth of the body only (for inner contour lines)
Output: art_source/3d/render/<clip>/ (heavy_combo keeps its original folder heavy_combo_v01)
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
BLEND = ROOT / "art_source/3d/model/niulai_rig_v01.blend"
RENDER_ROOT = ROOT / "art_source/3d/render"
H = 1.078
SS = 4                      # supersampling factor over the native canvas
CANVAS = 256
FEET_Y, BODY_X = 207, 112   # native pixel rows/cols
DEPTH_RANGE = (3.0, 7.0)    # camera distance mapped to 0..1 in the depth pass

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
clip = args.pop(0) if args and not args[0].isdigit() else "heavy_combo"
OUT = RENDER_ROOT / ("heavy_combo_v01" if clip == "heavy_combo" else clip)

INFLATE = 0.010  # push the surface out ~0.6 native px so limbs read chunkier, like the hand-drawn sprite

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
body = bpy.data.objects["Niulai"]
rig_act = bpy.data.actions[f"NL_{clip}"]
bpy.data.objects["NiulaiRig"].animation_data.action = rig_act
bpy.data.objects["Sword"].animation_data.action = bpy.data.actions[f"SW_{clip}"]
first, last = (int(args[0]), int(args[1])) if len(args) >= 2 else (0, int(rig_act.frame_range[1]))
if INFLATE:
    disp = body.modifiers.new("Inflate", "DISPLACE")
    disp.strength = INFLATE
    disp.mid_level = 0.0
sword_parts = [o for o in scene.objects if o.name.startswith("Sword") and o.type == "MESH"]

# camera: orthographic, looking along +X so the calf (facing -Y) faces screen right
cam = bpy.data.objects.new("PixelCam", bpy.data.cameras.new("PixelCam"))
scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = H * CANVAS / 64
upp = cam.data.ortho_scale / CANVAS
cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
# screen column c <-> y = cam.y - (c - 128) * upp ; ground z=0 on the lower edge of row FEET_Y
cam.location = Vector((-5.0, -0.03 + (BODY_X - CANVAS / 2) * upp, (FEET_Y + 1 - CANVAS / 2) * upp))
cam.data.clip_start, cam.data.clip_end = 0.1, 20

# light from the upper left of the screen (+Y, +Z), slightly from the camera side
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); scene.collection.objects.link(sun)
sun.rotation_euler = Vector((0.35, -0.6, -0.72)).to_track_quat("-Z", "Y").to_euler()
sun.data.energy = 3.0

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = CANVAS * SS
scene.render.film_transparent = True
scene.render.filter_size = 0.0
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"

# ---------------------------------------------------------------- materials
mat = body.data.materials[0]
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
tex_socket = bsdf.inputs["Base Color"].links[0].from_socket
out_node = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
s2r = nt.nodes.new("ShaderNodeShaderToRGB")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "CONSTANT"
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1)
ramp.color_ramp.elements[1].position = 0.18
ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
mix.inputs["Factor"].default_value = 1.0
toon = nt.nodes.new("ShaderNodeEmission")
nt.links.new(dif.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
nt.links.new(tex_socket, mix.inputs["A"]); nt.links.new(ramp.outputs["Color"], mix.inputs["B"])
nt.links.new(mix.outputs["Result"], toon.inputs["Color"])
camdata = nt.nodes.new("ShaderNodeCameraData")
mrange = nt.nodes.new("ShaderNodeMapRange")
mrange.inputs["From Min"].default_value, mrange.inputs["From Max"].default_value = DEPTH_RANGE
depth_em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(camdata.outputs["View Z Depth"], mrange.inputs["Value"]); nt.links.new(mrange.outputs["Result"], depth_em.inputs["Color"])

def body_mode(mode):
    nt.links.new((toon if mode == "color" else depth_em).outputs[0], out_node.inputs["Surface"])
    for p in sword_parts:
        p.hide_render = mode == "depth"

(OUT / "color").mkdir(parents=True, exist_ok=True)
(OUT / "depth").mkdir(parents=True, exist_ok=True)
for f in range(first, last + 1):
    scene.frame_set(f)
    for mode in ("color", "depth"):
        body_mode(mode)
        scene.render.image_settings.color_depth = "16" if mode == "depth" else "8"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.filepath = str(OUT / mode / f"F{f:03d}.png")
        bpy.ops.render.render(write_still=True)
print("DONE", first, last)
