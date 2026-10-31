"""Blender: assemble KayKit Dungeon pieces into side-view castle-interior layers and render them.

    blender --background --python tools/scene3d_render.py -- [layer ...]

Scale: 1 KayKit unit = 32 native px (a 4x4 wall = 128x128 px, ~2x Niulai's height).
Each layer is rendered orthographic from the front (camera at -Y looking +Y), 4x supersampled,
toon-shaded (texture x 2-step light ramp, light from the upper left like the player).
Output: art_source/3d/scene/castle_v01/<layer>.png (+ <layer>.json with size info)
Pixelize with tools/scene3d_pixelize.py.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "outputs/scene_sources/kaykit_dungeon/KayKit_Dungeon_Pack_1.1_FREE/Assets/gltf"
OUT = ROOT / "art_source/3d/scene/castle_v01"
PX = 32          # native px per unit
SS = 4           # supersampling


def wall_row(pattern, z=0.0):
    return [(name, 2.0 + 4.0 * i, 0.0, z, 0.0) for i, name in enumerate(pattern)]


# layer -> (width units, height units, [(model, x, y_depth, z, rot_z_deg[, scale, rot_x_deg])])
# x/z are the model origin; y > 0 pushes away from the camera.
LOWER = ["wall_archedwindow_open", "wall", "wall_doorway", "wall", "wall_archedwindow_gated", "wall_cracked"]
GALLERY = ["wall_arched", "wall_window_open", "wall_arched", "wall_arched", "wall_window_open", "wall_arched"]
LAYERS = {
    # great-hall back wall: 6 walls wide (768 px, tiles horizontally), 3 rows high (384 px)
    "back_wall": (24.0, 12.0,
                  wall_row(LOWER) + wall_row(GALLERY, 4.0) + wall_row(["wall"] * 6, 8.0)
                  + [("banner_patternA_red", 6.0, 0.0, 4.0, 0), ("banner_thin_red", 14.0, 0.0, 4.0, 0),
                     ("banner_patternA_red", 22.0, 0.0, 4.0, 0),
                     ("torch_mounted", 4.5, 0.0, 2.5, 0), ("torch_mounted", 7.5, 0.0, 2.5, 0),
                     ("torch_mounted", 12.5, 0.0, 2.5, 0), ("torch_mounted", 15.5, 0.0, 2.5, 0),
                     ("torch_mounted", 20.5, 0.0, 2.5, 0), ("torch_mounted", 23.5, 0.0, 2.5, 0),
                     ("sword_shield", 10.0, 0.0, 9.6, 0), ("sword_shield", 18.0, 0.0, 9.6, 0),
                     ("barrel_large", 8.6, -1.2, 0.0, 15, 0.7), ("barrel_small_stack", 9.8, -1.0, 0.0, 0, 0.7),
                     ("crates_stacked", 17.2, -1.3, 0.0, 20, 0.7), ("candle_triple", 16.2, -1.0, 0.0, 0, 0.8)]),
    # free-standing pillar in front of the back wall (two pillar pieces stacked = 256 px)
    "pillar": (4.0, 8.0, [("pillar", 2.0, 0.0, 0.0, 0), ("pillar", 2.0, 0.0, 4.0, 0)]),
    # ground blocks: wall front (cap + stone bricks); one-way platforms: wooden floor seen from above
    "ground_face": (8.0, 4.0, wall_row(["wall", "wall"])),
    # rot_x +90 turns the floor's top face toward the camera (-Y); -90 shows the back-face-culled side
    "wood_plank": (8.0, 4.0, [("floor_wood_large", 2.0, 0.0, 2.0, 0, 1.0, 90), ("floor_wood_large", 6.0, 0.0, 2.0, 0, 1.0, 90)]),
}
TORCHES = [(x, z) for name, x, y, z, *_ in LAYERS["back_wall"][2] if name == "torch_mounted"]


def toon(mat):
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    if bsdf is None:
        return
    link = bsdf.inputs["Base Color"].links
    col_socket = link[0].from_socket if link else None
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (0.55, 0.55, 0.62, 1)   # cool shadow
    ramp.color_ramp.elements[1].position = 0.18
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if col_socket:
        nt.links.new(col_socket, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(dif.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["B"]); nt.links.new(mix.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])


def render_layer(name):
    w, h, items = LAYERS[name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for model, x, y, z, rot, *extra in items:
        scale = extra[0] if extra else 1.0
        rot_x = extra[1] if len(extra) > 1 else 0.0
        before = set(scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(KIT / f"{model}.gltf"))
        for o in set(scene.objects) - before:
            if o.parent is None:
                o.rotation_mode = "XYZ"   # glTF imports use quaternions; euler edits would be ignored
                o.location = (x + o.location.x, y + o.location.y, z + o.location.z)
                o.rotation_euler.x += math.radians(rot_x)
                o.rotation_euler.z += math.radians(rot)
                o.scale = o.scale * scale
    for m in bpy.data.materials:
        if m.use_nodes:
            toon(m)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(w, h)
    cam.data.shift_x = 0.0
    cam.rotation_euler = (math.radians(90), 0, 0)          # looks along +Y
    cam.location = Vector((w / 2, -30.0, h / 2))
    cam.data.clip_end = 100
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.45, 0.75, -0.55)).to_track_quat("-Z", "Y").to_euler()
    sun.data.energy = 3.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(w * PX * SS)
    scene.render.resolution_y = int(h * PX * SS)
    scene.render.film_transparent = True
    scene.render.filter_size = 0.0
    scene.view_settings.view_transform = "Standard"
    OUT.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    info = {"width_px": int(w * PX), "height_px": int(h * PX), "ss": SS, "items": items}
    if name == "back_wall":  # torch flame positions in layer pixels (origin top-left), for glow sprites
        info["torches_px"] = [[round(x * PX), round((h - z - 0.55) * PX)] for x, z in TORCHES]
    (OUT / f"{name}.json").write_text(json.dumps(info, indent=1))
    print("RENDERED", name)


args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for layer in args or LAYERS:
    render_layer(layer)
