"""Castle scene renders -> native pixel textures for Godot.

    py tools/scene3d_pixelize.py        (system Python 3.11)

Input : art_source/3d/scene/castle_v01/<layer>.png (4x supersampled, from scene3d_render.py)
Output: assets/environment/castle/*.png + castle.json (torch positions etc.)
Steps : area downscale -> per-layer grade (far = darker/cooler, so the gameplay layer and the
        player stand out) -> one shared limited palette for all scene layers (no dithering).
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art_source/3d/scene/castle_v01"
OUT = ROOT / "assets/environment/castle"
SS = 4
PALETTE_SIZE = 32
# layer: (brightness, rgb tint) — "dark purple + warm torchlight" look
GRADE = {
    "back_wall": (0.50, (0.86, 0.80, 1.00)),
    "pillar": (0.56, (0.86, 0.80, 1.00)),
    "ground_face": (0.70, (0.90, 0.86, 1.00)),
    "wood_plank": (0.95, (1.00, 0.95, 0.92)),
}


def native(name: str) -> np.ndarray:
    im = np.array(Image.open(SRC / f"{name}.png").convert("RGBA")).astype(np.float32)
    a = im[..., 3:] / 255
    pre = np.dstack([im[..., :3] * a, a[..., 0]])
    h, w = im.shape[0] // SS, im.shape[1] // SS
    small = cv2.resize(pre, (w, h), interpolation=cv2.INTER_AREA)
    alpha = small[..., 3]
    rgb = np.where(alpha[..., None] > 1e-3, small[..., :3] / np.maximum(alpha[..., None], 1e-3), 0)
    k, tint = GRADE[name]
    rgb = np.clip(rgb * k * np.array(tint), 0, 255)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = (alpha > 0.5) * 255
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    layers = {n: native(n) for n in GRADE}
    # shared palette from all opaque pixels
    pix = np.concatenate([l[l[..., 3] > 0][:, :3] for l in layers.values()])
    side = int(np.ceil(np.sqrt(len(pix))))
    pad = np.zeros((side * side, 3), np.uint8); pad[:len(pix)] = pix; pad[len(pix):] = pix[0]
    pal_img = Image.fromarray(pad.reshape(side, side, 3)).quantize(PALETTE_SIZE, method=Image.Quantize.MEDIANCUT)
    snapped = {}
    for n, l in layers.items():
        q = Image.fromarray(l[..., :3]).quantize(palette=pal_img, dither=Image.Dither.NONE).convert("RGB")
        snapped[n] = np.dstack([np.array(q), l[..., 3]])

    # back wall: full image, tiles horizontally every 768 px
    Image.fromarray(snapped["back_wall"], "RGBA").save(OUT / "back_wall.png")
    # pillar: crop to its opaque columns
    p = snapped["pillar"]; xs = np.nonzero(p[..., 3].any(0))[0]
    Image.fromarray(p[:, xs.min():xs.max() + 1], "RGBA").save(OUT / "pillar.png")
    # ground blocks from the wall front: top cap strip + repeating brick body (one wall = 128 px wide)
    g = snapped["ground_face"]
    rows = np.nonzero(g[..., 3].any(1))[0]
    top = rows.min()
    Image.fromarray(g[top:top + 14, 0:128], "RGBA").save(OUT / "block_cap.png")
    Image.fromarray(g[top + 22:top + 94, 0:128], "RGBA").save(OUT / "block_body.png")
    # one-way platform: an 8 px strip of wooden boards seen from above, darker lower edge
    wd = snapped["wood_plank"]
    rows = np.nonzero(wd[..., 3].any(1))[0]
    strip = wd[rows.min() + 40:rows.min() + 48, 0:128].copy()
    strip[-2:, :, :3] = (strip[-2:, :, :3] * 0.55).astype(np.uint8)
    Image.fromarray(strip, "RGBA").save(OUT / "plank.png")

    info = json.loads((SRC / "back_wall.json").read_text())
    meta = {"back_wall_size": [info["width_px"], info["height_px"]], "torches_px": info["torches_px"],
            "palette": [list(map(int, c)) for c in np.array(pal_img.getpalette()[:PALETTE_SIZE * 3]).reshape(-1, 3)]}
    (OUT / "castle.json").write_text(json.dumps(meta, indent=1))
    print("->", OUT, sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
