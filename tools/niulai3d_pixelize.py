"""Renders of the rigged 3D Niulai -> native 256x256 pixel frames + previews.

    py tools/niulai3d_pixelize.py [render_dir]     (system Python 3.11: numpy / Pillow / cv2)

Input : art_source/3d/render/<dir>/{color,depth}/Fnnn.png (4x supersampled; default heavy_combo_v01)
Output: <dir>/native/Fnnn.png, preview GIF; for heavy_combo_v01 also the keyframe comparison sheet
Steps : area downscale -> 17-colour snap -> denoise -> 1px silhouette outline
        -> inner contour lines where body depth jumps (arm in front of torso etc.).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from prep_sprites import CANVAS, OUTLINE, denoise, outline, snap

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art_source/3d/render" / (sys.argv[1] if len(sys.argv) > 1 else "heavy_combo_v01")
OUT = SRC / "native"
KEYS = ROOT / "art_source/reference/poses/heavy_combo_v02"
SS = 4
DEPTH_JUMP = 0.012       # in normalised depth (range 4 units) -> ~0.05 units
LINE_MIN_SUB = 3         # supersampled edge pixels needed inside a native pixel
BG = (36, 28, 52, 255)


def native_frame(f: int) -> np.ndarray:
    col = np.array(Image.open(SRC / "color" / f"F{f:03d}.png").convert("RGBA")).astype(np.float32)
    a = col[..., 3:] / 255
    pre = np.dstack([col[..., :3] * a, a[..., 0]])
    small = cv2.resize(pre, (CANVAS, CANVAS), interpolation=cv2.INTER_AREA)
    alpha = small[..., 3]
    rgb = np.where(alpha[..., None] > 1e-3, small[..., :3] / np.maximum(alpha[..., None], 1e-3), 0)
    img = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    img[..., :3] = snap(np.clip(rgb, 0, 255))
    img[..., 3] = (alpha > 0.5) * 255
    img = outline(denoise(img))

    dep = np.array(Image.open(SRC / "depth" / f"F{f:03d}.png"))
    d = dep[..., 0].astype(np.float32) / 65535 if dep.dtype == np.uint16 else dep[..., 0].astype(np.float32) / 255
    body = dep[..., 3] > 0 if dep.ndim == 3 and dep.shape[2] == 4 else d > 0
    edge = np.zeros_like(body)
    for dy, dx in ((0, 1), (1, 0)):
        a1 = d[: d.shape[0] - dy, : d.shape[1] - dx]
        a2 = d[dy:, dx:]
        b1 = body[: d.shape[0] - dy, : d.shape[1] - dx] & body[dy:, dx:]
        jump = b1 & (np.abs(a1 - a2) > DEPTH_JUMP)
        # mark the farther side so the line sits on the occluded surface
        far1 = jump & (a1 > a2)
        far2 = jump & (a2 > a1)
        edge[: d.shape[0] - dy, : d.shape[1] - dx] |= far1
        edge[dy:, dx:] |= far2
    count = edge.reshape(CANVAS, SS, CANVAS, SS).sum(axis=(1, 3))
    inner = (count >= LINE_MIN_SUB) & (img[..., 3] > 0)
    img[inner, :3] = OUTLINE
    return img


def show(img: np.ndarray, scale: int, crop=None) -> Image.Image:
    bg = Image.new("RGBA", (CANVAS, CANVAS), BG)
    bg.alpha_composite(Image.fromarray(img, "RGBA"))
    if crop:
        bg = bg.crop(crop)
    return bg.convert("RGB").resize((bg.width * scale, bg.height * scale), Image.NEAREST)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = sorted(int(p.stem[1:]) for p in (SRC / "color").glob("F*.png"))
    natives = {}
    stats = {}
    for f in frames:
        img = native_frame(f)
        natives[f] = img
        Image.fromarray(img, "RGBA").save(OUT / f"F{f:03d}.png")
        ys, xs = np.nonzero(img[..., 3])
        stats[f] = {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], "opaque": int(len(xs))}
    crop = (8, 96, 248, 216)
    (SRC / "native_stats.json").write_text(json.dumps(stats, indent=1))
    ims = [show(natives[f], 3, crop) for f in frames]
    ims[0].save(SRC / "preview_all_24fps.gif", save_all=True, append_images=ims[1:], duration=42, loop=0)
    print("frames", len(frames), "->", OUT)
    if SRC.name != "heavy_combo_v01":
        return
    ims = [show(natives[f], 3, crop) for f in frames if f <= 16 and f % 2 == 0]
    ims[0].save(SRC / "preview_cut1_12fps.gif", save_all=True, append_images=ims[1:], duration=83, loop=0)
    # contact sheet: 3D native vs keyframe v02 at matching reference frames
    pairs = [(0, "niulai_idle_tail_native"), (4, None), (6, None), (8, "niulai_hc1_k4_native"),
             (10, "niulai_hc1_k5_native"), (12, "niulai_hc1_k6_native"), (14, None), (16, None)]
    cw, ch = (crop[2] - crop[0]) * 2, (crop[3] - crop[1]) * 2
    sheet = Image.new("RGB", (cw * len(pairs), ch * 2 + 20), BG[:3])
    for k, (f, key) in enumerate(pairs):
        if f in natives:
            t = show(natives[f], 2, crop); ImageDraw.Draw(t).text((4, 4), f"3D R{f:03d}", fill="white")
            sheet.paste(t, (k * cw, 0))
        if key:
            kimg = np.array(Image.open(KEYS / f"{key}.png").convert("RGBA"))
            if key.endswith("k5_native"):
                kimg = np.roll(kimg, 15, axis=1)
            t = show(kimg, 2, crop); ImageDraw.Draw(t).text((4, 4), key.replace("niulai_", "").replace("_native", ""), fill="white")
            sheet.paste(t, (k * cw, ch + 20))
    sheet.save(SRC / "compare_vs_keyframes.png")


if __name__ == "__main__":
    main()
