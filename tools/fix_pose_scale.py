"""把 Codex 姿势图的身体大小统一到基准待机图。

Codex 按"剑长一致"缩放了每张姿势图，结果身体大小差了 ±20%。当作 H3 的首尾帧时，角色会在动作中途变大变小。
这里用"黄色皮肤 + 奶油色鼻头"的像素面积估算每张图的身体大小，再绕脚底（空中姿势绕身体中心）缩放回来，
重新吸附调色板、去噪、描边。

用法（在项目根目录）：
    py tools/fix_pose_scale.py
输入：art_source/reference/poses/_codex/niulai_<姿势>_native.png（Codex 原图，保留不动）
输出：art_source/reference/poses/niulai_<姿势>_native.png 和 _x4.png（放大 4 倍，方便看）
"""
from pathlib import Path
import argparse

import cv2
import numpy as np
from PIL import Image

from prep_sprites import CANVAS, denoise, outline, snap

ROOT = Path(__file__).resolve().parent.parent
POSES = ROOT / "art_source" / "reference" / "poses"
SRC = POSES / "_codex"
BASE = "idle_tail"

SKIN = {(0xE8, 0xB8, 0x30), (0xF4, 0xD3, 0x6A), (0xB6, 0x8A, 0x24)}
CREAM = {(0xF6, 0xEA, 0xCB), (0xDC, 0xCC, 0xAB), (0xB6, 0xA3, 0x85)}
AIR = {"jump", "fall", "air_slash_end", "plunge"}
# 张嘴喊疼时鼻头面积会变大，只看皮肤
SKIN_ONLY = {"hurt"}
TOLERANCE = 0.07


def color_mask(img: np.ndarray, colors: set) -> np.ndarray:
    m = np.zeros(img.shape[:2], bool)
    for c in colors:
        m |= (img[..., 0] == c[0]) & (img[..., 1] == c[1]) & (img[..., 2] == c[2]) & (img[..., 3] > 0)
    return m


def body_scale(img: np.ndarray, base: np.ndarray, pose: str) -> float:
    s = np.sqrt(color_mask(img, SKIN).sum() / color_mask(base, SKIN).sum())
    if pose in SKIN_ONLY:
        return float(s)
    c = np.sqrt(color_mask(img, CREAM).sum() / color_mask(base, CREAM).sum())
    return float((s + c) / 2)


def anchor(img: np.ndarray, pose: str) -> tuple[float, float]:
    skin = color_mask(img, SKIN)
    ys, xs = np.nonzero(skin)
    cx = float(xs.mean())
    if pose in AIR:
        return cx, float(ys.mean())
    oys, _ = np.nonzero(img[..., 3] > 0)
    return cx, float(oys.max() + 1)  # 地面姿势：脚底那条线不动


def rescale(img: np.ndarray, k: float, pivot: tuple[float, float]) -> np.ndarray:
    big = cv2.resize(img, (CANVAS * 4, CANVAS * 4), interpolation=cv2.INTER_NEAREST).astype(np.float32)
    a = big[..., 3:] / 255
    premul = np.dstack([big[..., :3] * a, a[..., 0]])
    size = int(round(CANVAS * k))
    small = cv2.resize(premul, (size, size), interpolation=cv2.INTER_AREA)
    px, py = pivot
    ox, oy = int(round(px - px * k)), int(round(py - py * k))
    canvas = np.zeros((CANVAS, CANVAS, 4), np.float32)
    x0, y0 = max(ox, 0), max(oy, 0)
    x1, y1 = min(ox + size, CANVAS), min(oy + size, CANVAS)
    canvas[y0:y1, x0:x1] = small[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    alpha = canvas[..., 3]
    rgb = np.where(alpha[..., None] > 1e-3, canvas[..., :3] / np.maximum(alpha[..., None], 1e-3), 0)
    out = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    out[..., :3] = snap(np.clip(rgb, 0, 255))
    out[..., 3] = (alpha > 0.5) * 255
    return outline(denoise(out))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--poses', nargs='+', help='Only process these pose names, e.g. hc1_k1 hc1_k2; do not migrate or rewrite other poses.')
    args = ap.parse_args()
    SRC.mkdir(exist_ok=True)
    if args.poses:
        files = [SRC / f'niulai_{pose}_native.png' for pose in args.poses]
        for f in files:
            if not f.is_file():
                raise SystemExit(f'Missing selected input: {f}')
    else:
        for f in POSES.glob("niulai_*_native.png"):  # 第一次运行：把 Codex 原图挪进 _codex
            if not (SRC / f.name).exists():
                f.replace(SRC / f.name)
        files = sorted(SRC.glob("niulai_*_native.png"))
    base = np.array(Image.open(SRC / f"niulai_{BASE}_native.png").convert("RGBA"))
    for f in files:
        pose = f.name[len("niulai_"):-len("_native.png")]
        img = np.array(Image.open(f).convert("RGBA"))
        s = body_scale(img, base, pose)
        if pose == BASE or abs(1 - s) <= TOLERANCE:
            out, note = img, "不用改"
        else:
            # 重新吸色、描边会让面积有点偏差，按复测结果迭代修正（每次都从原图缩放）
            k, pivot = 1 / s, anchor(img, pose)
            for _ in range(4):
                out = rescale(img, k, pivot)
                err = body_scale(out, base, pose)
                if abs(1 - err) < 0.03:
                    break
                k /= err
            note = f"缩放 x{k:.2f} → 复测 {body_scale(out, base, pose):.2f}"
        Image.fromarray(out, "RGBA").save(POSES / f.name)
        Image.fromarray(out, "RGBA").resize((CANVAS * 4, CANVAS * 4), Image.NEAREST).save(
            POSES / f.name.replace("_native.png", "_x4.png"))
        print(f"{pose:16s} 身体大小 {s:.2f}  {note}")


if __name__ == "__main__":
    main()
