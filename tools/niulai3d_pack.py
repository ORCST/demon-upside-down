"""Pack the player's sprites into one SpriteFrames, all 3D-rendered: Heavy Combo cuts, locomotion
(idle/run/jump/fall/land/dash/hurt/death) and two-frame attacks built from Heavy Combo frames.

    py tools/niulai3d_pack.py        (system Python 3.11)

Output: assets/sprites/niulai3d/<clip>.png and niulai3d.tres. Every frame is an AtlasTexture
whose margin restores the 256x256 canvas, so all clips share the feet anchor (112, 208):
use AnimatedSprite2D with centered=false, offset=(-112, -208).
Frame timing is driven by the player script (AttackData.anim_timing), not by the resource.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "art_source/3d/render/heavy_combo_v01/native"
OUT = ROOT / "assets/sprites/niulai3d"
CANVAS = 256
MAX_COLS = 8


def hc(*frames):
    return [RENDER / f"F{f:03d}.png" for f in frames]


def r3d(clip, first, last, step=1):
    """Frames of a 3D-rendered UAL clip (art_source/3d/render/<clip>/native)."""
    return [RENDER.parent.parent / clip / "native" / f"F{f:03d}.png" for f in range(first, last + 1, step)]


# Heavy Combo cuts at 12 fps (even source frames). Chosen from the full render sheet:
# hc1 下撩: wind-up R002-008, swing R010, hit R012, follow R014-016
# hc2 过肩斜劈: lift R018-022, swing R024, hit R026, back-sweep R028-030
# hc3 后仰砸地: hold R030/052, lift R056-060, overhead R062, slam R064-066, ground hold + stand up
CLIPS = {
    "hc1": hc(2, 4, 6, 8, 10, 12, 14, 16),
    "hc2": hc(18, 20, 22, 24, 26, 28, 30),
    "hc3": hc(30, 52, 56, 58, 60, 62, 64, 66, 72, 80, 88, 92, 96, 100),
    # Locomotion, all 3D-rendered from UAL clips (24 fps source). *_carry = same sword grip as the
    # guard idle (tools/niulai3d_guard_idle.py), so switching idle <-> run/jump keeps the sword in place:
    "idle": r3d("guard_idle", 0, 38, 2),       # guard stance on Sword_Idle, 12 fps loop
    "run": r3d("jog_carry", 0, 22),            # Jog_Fwd_Loop, 24 fps loop
    "jump": r3d("jump_start_carry", 4, 12, 2), # Jump_Start after take-off (F000-003 still crouch on the ground)
    "fall": r3d("jump_loop_carry", 0, 56, 4),  # Jump_Loop, nearly static
    "land": r3d("jump_land_carry", 2, 6, 2),   # Jump_Land crouch
    "dash": r3d("sprint_carry", 4, 10, 2),     # Sprint_Loop forward lean; Roll is too long for a 0.16 s dash
    "hurt": r3d("hit", 0, 8),                  # Hit_Chest
    "death": r3d("death", 0, 40, 2),           # Death01, ends lying down
    # Two-frame attacks (wind-up, strike), reusing Heavy Combo renders so they match the 3D Niulai:
    "atk_power": hc(60, 64),      # sword lifted behind -> slam forward
    "atk_uppercut": hc(8, 22),    # deep crouch, sword low behind -> sword straight up
    "atk_air": hc(20, 26),        # sword raised back -> diagonal cut down-forward
    "atk_spike": hc(62, 66),      # overhead -> sword driven down
}
LOOP = {"idle", "run", "fall"}
FPS = 12.0
CLIP_FPS = {"run": 24.0, "jump": 24.0, "land": 24.0, "dash": 30.0, "hurt": 24.0}


def pack(name: str, files: list) -> dict:
    imgs = [np.array(Image.open(f).convert("RGBA")) for f in files]
    union = np.zeros((CANVAS, CANVAS), bool)
    for im in imgs:
        union |= im[..., 3] > 0
    ys, xs = np.nonzero(union)
    x, y = int(xs.min()), int(ys.min())
    w, h = int(xs.max()) - x + 1, int(ys.max()) - y + 1
    cols = min(MAX_COLS, len(imgs))
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGBA", (w * cols, h * rows))
    for k, im in enumerate(imgs):
        sheet.paste(Image.fromarray(im[y:y + h, x:x + w], "RGBA"), ((k % cols) * w, (k // cols) * h))
    sheet.save(OUT / f"{name}.png")
    return {"path": f"res://assets/sprites/niulai3d/{name}.png", "frames": len(imgs), "cols": cols,
            "w": w, "h": h, "x": x, "y": y, "sources": [str(f.relative_to(ROOT)) for f in files]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    clips = {}
    for name, files in CLIPS.items():
        clips[name] = pack(name, files)

    ext, sub, anims = [], [], []
    for idx, (name, c) in enumerate(clips.items(), 1):
        ext.append(f'[ext_resource type="Texture2D" path="{c["path"]}" id="{idx}_{name}"]')
        refs = []
        for k in range(c["frames"]):
            sid = f"AtlasTexture_{name}_{k}"
            col, row = k % c["cols"], k // c["cols"]
            sub.append(f'[sub_resource type="AtlasTexture" id="{sid}"]\n'
                       f'atlas = ExtResource("{idx}_{name}")\n'
                       f'region = Rect2({col * c["w"]}, {row * c["h"]}, {c["w"]}, {c["h"]})\n'
                       f'margin = Rect2({c["x"]}, {c["y"]}, {CANVAS - c["w"]}, {CANVAS - c["h"]})\n'
                       f'filter_clip = true\n')
            refs.append('{\n"duration": 1.0,\n"texture": SubResource("%s")\n}' % sid)
        anims.append('{\n"frames": [%s],\n"loop": %s,\n"name": &"%s",\n"speed": %s\n}'
                     % (", ".join(refs), "true" if name in LOOP else "false", name, CLIP_FPS.get(name, FPS)))
    text = "[gd_resource type=\"SpriteFrames\" format=3]\n\n" + "\n".join(ext) + "\n\n" + "\n".join(sub) + \
           "\n[resource]\nanimations = [%s]\n" % ", ".join(anims)
    (OUT / "niulai3d.tres").write_text(text, encoding="utf-8")
    (OUT / "clips.json").write_text(json.dumps(clips, indent=1, ensure_ascii=False), encoding="utf-8")
    print({k: v["frames"] for k, v in clips.items()})


if __name__ == "__main__":
    main()
