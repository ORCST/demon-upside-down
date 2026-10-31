"""MiniMax H3 绿底视频帧 → 牛来的像素精灵表 + Godot SpriteFrames。

用法（在项目根目录）：
    py tools/prep_sprites.py            # 处理 clips.json 里的全部动画
    py tools/prep_sprites.py idle run   # 只处理指定的动画

动画清单在 art_source/minimax/clips.json，每段动画：
    "frames": 帧目录（tools/comfy_minimax.py 生成的 *_frames），或几段首尾相接的目录列表
    "kind":   loop_all（整段循环，首尾帧相同）/ loop_cycle（从中间找一个完整循环）/ action（一次性动作）
    "align":  feet（按脚底对齐，原地动作）/ torso（按躯干对齐，跑步）/ none（不对齐，相信固定机位）
    "step":   每隔几帧取一帧，默认 2（24fps → 12fps）
    "start":  loop_cycle 从第几帧开始找循环

处理流程：抠绿幕 → 去掉和身体不连着的杂物 → 按首帧对齐到标准画布（256×256，脚底在 y=208）
→ 缩到原生像素 → 吸附到定稿的 17 色调色板 → 去孤立噪点 → 统一 1 像素描边 → 裁切打包。

输出：
    assets/sprites/niulai/<名字>.png      精灵表
    assets/sprites/niulai/niulai.tres     所有动画的 SpriteFrames（每帧都还原成 256×256，锚点一致）
    art_source/minimax/preview/<名字>.gif 预览（放大 4 倍）
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art_source" / "minimax"
REF = ROOT / "art_source" / "reference" / "poses" / "niulai_idle_tail_native.png"
OUT = ROOT / "assets" / "sprites" / "niulai"
PREVIEW = SRC / "preview"

CANVAS = 256
GROUND_Y = 208       # 脚底所在行的下一行（脚踩在 y=207）
SRC_FPS = 24
MAX_COLS = 8


# ---------------------------------------------------------------- 调色板

def load_palette() -> np.ndarray:
    ref = np.array(Image.open(REF).convert("RGBA"))
    cols = np.unique(ref[ref[..., 3] > 0][:, :3], axis=0)
    return cols.astype(np.int32)


PALETTE = load_palette()
OUTLINE = np.array([0x28, 0x1B, 0x21])


def snap(rgb: np.ndarray) -> np.ndarray:
    """每个像素换成调色板里最接近的颜色（按人眼敏感度加权）。"""
    w = np.array([2.0, 4.0, 3.0])
    d = ((rgb[:, :, None, :].astype(np.float32) - PALETTE[None, None, :, :]) ** 2 * w).sum(-1)
    return PALETTE[np.argmin(d, axis=-1)].astype(np.uint8)


# ---------------------------------------------------------------- 抠图

def key_green(rgb: np.ndarray) -> np.ndarray:
    """绿得越纯越透明。返回 0..1 的 alpha。"""
    f = rgb.astype(np.float32) / 255
    spill = f[..., 1] - np.maximum(f[..., 0], f[..., 2])
    return 1.0 - np.clip((spill - 0.12) / 0.18, 0, 1)


def drop_fx(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """去掉 H3 自己加的剑光：偏蓝的亮白色。角色调色板里没有这种颜色
    （剑的亮边 #BCC3CA 亮度不够，不会被误删）。"""
    f = rgb.astype(np.int32)
    lum = (f[..., 0] * 3 + f[..., 1] * 6 + f[..., 2]) / 10
    fx = ((lum > 215) & (f[..., 2] >= f[..., 0] - 4)).astype(np.uint8)
    # 只删大块的（剑光动辄几千像素）；眼白这种小块要留着
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fx, 8)
    big = np.isin(lab, [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 400])
    fx = cv2.dilate(big.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    out = alpha.copy()
    out[fx] = 0
    return out


def keep_body(alpha: np.ndarray) -> np.ndarray:
    """只留最大的那块和贴着它的部分（去掉 MiniMax 偶尔画出来的字幕、杂点）。"""
    solid = (alpha > 0.5).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(solid, 8)
    if n <= 2:
        return alpha
    body = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    near = cv2.dilate((lab == body).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    keep = np.isin(lab, np.unique(lab[near & (solid > 0)]))
    out = alpha.copy()
    out[~cv2.dilate(keep.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)] = 0
    return out


def feet_anchor(mask: np.ndarray) -> tuple[float, float]:
    """脚底：最下面一截的水平中心 + 最低点。"""
    ys, xs = np.nonzero(mask)
    bottom = ys.max()
    sel = ys > bottom - 6
    return float(np.median(xs[sel])), float(bottom)


def torso_x(mask: np.ndarray) -> float:
    """躯干中心：身体中段（排除剑：只看左边主体）。"""
    ys, xs = np.nonzero(mask)
    top, bottom = ys.min(), ys.max()
    sel = (ys > top + (bottom - top) * 0.45) & (ys < top + (bottom - top) * 0.8)
    return float(np.median(xs[sel]))


# ---------------------------------------------------------------- 像素化

def to_native(rgb: np.ndarray, alpha: np.ndarray, origin: tuple[float, float], scale: float) -> np.ndarray:
    """把视频帧里对应标准画布的区域缩到 256×256 原生像素，返回 RGBA。"""
    ox, oy = origin
    size = CANVAS * scale
    premul = np.dstack([rgb.astype(np.float32) * alpha[..., None], alpha])
    # 先平移到画布原点，再用面积平均缩到原生像素
    shifted = cv2.warpAffine(premul, np.float32([[1, 0, -ox], [0, 1, -oy]]), (int(np.ceil(size)), int(np.ceil(size))),
                             flags=cv2.INTER_LINEAR, borderValue=0)
    small = cv2.resize(shifted, (CANVAS, CANVAS), interpolation=cv2.INTER_AREA)
    a = small[..., 3]
    rgb_n = np.where(a[..., None] > 1e-3, small[..., :3] / np.maximum(a[..., None], 1e-3), 0)
    out = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    solid = a > 0.5
    out[..., :3] = snap(np.clip(rgb_n, 0, 255))
    out[..., 3] = solid * 255
    return out


def denoise(img: np.ndarray) -> np.ndarray:
    """去掉孤立的单个杂色像素：四邻都和它不同、且邻居里有一种颜色占多数时，换成那种颜色。"""
    out = img.copy()
    h, w = img.shape[:2]
    key = img[..., 0].astype(np.int32) << 16 | img[..., 1].astype(np.int32) << 8 | img[..., 2]
    key[img[..., 3] == 0] = -1
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            k = key[y, x]
            if k < 0:
                continue
            nb = [key[y - 1, x], key[y + 1, x], key[y, x - 1], key[y, x + 1]]
            if k in nb:
                continue
            vals, counts = np.unique(nb, return_counts=True)
            if counts.max() >= 3 and vals[np.argmax(counts)] >= 0:
                v = vals[np.argmax(counts)]
                out[y, x, :3] = [(v >> 16) & 255, (v >> 8) & 255, v & 255]
    return out


def outline(img: np.ndarray) -> np.ndarray:
    """剪影边缘统一成 1 像素深色描边（8 邻域，和定稿图的做法一致）。"""
    solid = img[..., 3] > 0
    inner = cv2.erode(solid.astype(np.uint8), np.ones((3, 3), np.uint8), borderValue=0).astype(bool)
    out = img.copy()
    out[solid & ~inner, :3] = OUTLINE
    return out


# ---------------------------------------------------------------- 选帧

def find_cycle(masks: list, start: int) -> int:
    best, best_p = 1e9, 0
    for p in range(10, min(40, len(masks) - start)):
        d = np.mean(masks[start] ^ masks[start + p])
        if d < best:
            best, best_p = d, p
    return best_p


def pick_frames(cfg: dict, masks: list) -> list[int]:
    step = cfg.get("step", 2)
    n = len(masks)
    if cfg["kind"] == "loop_cycle":
        start = cfg.get("start", 0)
        return list(range(start, start + find_cycle(masks, start), step))
    if cfg["kind"] == "loop_all":
        return list(range(0, n - 1, step))
    return list(range(0, n, step))


# ---------------------------------------------------------------- 主流程

def build(name: str, cfg: dict) -> dict | None:
    # frames 可以是一个目录，也可以是几段首尾相接的目录（关键姿势拆成的多段），接缝处的重复帧去掉
    dirs = cfg["frames"] if isinstance(cfg["frames"], list) else [cfg["frames"]]
    files = []
    for k, d in enumerate(dirs):
        seg = sorted((SRC / d).glob("*.png"))
        if not seg:
            print(f"skip {name}: 没有帧 {d}")
            return None
        files += seg[1:] if k > 0 else seg
    rgbs = [np.array(Image.open(f).convert("RGB")) for f in files]
    alphas = [keep_body(drop_fx(r, key_green(r))) for r in rgbs]
    masks = [a > 0.5 for a in alphas]
    # 背景闪成别的颜色时抠不掉，整帧都是"实心"的，提醒一下
    bad = [i for i, m in enumerate(masks) if m.mean() > 0.4]
    if bad:
        print(f"  警告 {name}: {len(bad)} 帧背景不是绿色（{bad[0]}..{bad[-1]}），这段建议重新生成")
    picks = pick_frames(cfg, masks)

    # 送进 H3 的首帧就是标准画布整张放大（256 → 视频宽度），机位固定，所以映射是已知的：
    # 原点在左上角，比例 = 视频宽度 / 256。对齐只修正之后各帧相对首帧的漂移。
    scale = rgbs[0].shape[1] / CANVAS
    base_origin = (0.0, 0.0)
    fx0, fy0 = feet_anchor(masks[0])
    tx0 = torso_x(masks[0])

    natives = []
    for i in picks:
        ox, oy = base_origin
        if cfg.get("align", "none") == "feet":
            fx, fy = feet_anchor(masks[i])
            ox += fx - fx0
            oy += fy - fy0
        elif cfg["align"] == "torso":
            ox += torso_x(masks[i]) - tx0
        img = to_native(rgbs[i], alphas[i], (ox, oy), scale)
        natives.append(outline(denoise(img)))

    # 按所有帧的并集裁切，打包成精灵表
    union = np.zeros((CANVAS, CANVAS), bool)
    for img in natives:
        union |= img[..., 3] > 0
    ys, xs = np.nonzero(union)
    bx, by, bw, bh = xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    cols = min(MAX_COLS, len(natives))
    rows = (len(natives) + cols - 1) // cols
    sheet = Image.new("RGBA", (bw * cols, bh * rows))
    for k, img in enumerate(natives):
        sheet.paste(Image.fromarray(img[by:by + bh, bx:bx + bw], "RGBA"), ((k % cols) * bw, (k // cols) * bh))
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / f"{name}.png")

    hold = None
    if cfg["kind"] == "action":
        diffs = [np.mean(natives[0][..., 3] != n[..., 3]) for n in natives]
        hold = int(np.argmax(diffs))

    fps = SRC_FPS / cfg.get("step", 2)
    _save_preview(name, natives, fps)
    info = {"file": f"{name}.png", "frames": len(natives), "cols": cols, "w": int(bw), "h": int(bh),
            "x": int(bx), "y": int(by), "fps": fps, "loop": cfg["kind"] != "action", "hold": hold,
            "scale": round(float(scale), 3)}
    print(name, info)
    return info


def _save_preview(name: str, natives: list, fps: float) -> None:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    frames = []
    for img in natives:
        bg = Image.new("RGBA", (CANVAS, CANVAS), (36, 28, 52, 255))
        bg.alpha_composite(Image.fromarray(img, "RGBA"))
        frames.append(bg.convert("RGB").resize((CANVAS * 3, CANVAS * 3), Image.NEAREST))
    frames[0].save(PREVIEW / f"{name}.gif", save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0)


def write_sprite_frames(clips: dict) -> None:
    """生成 Godot 的 SpriteFrames。每帧是 AtlasTexture：region 是精灵表里的格子，
    margin 把它还原到 256×256 画布上的原位置，所以所有动画锚点一致（脚底在 (112, 208)）。"""
    lines = []
    ext, sub, anims = [], [], []
    for idx, (name, c) in enumerate(clips.items(), 1):
        ext.append(f'[ext_resource type="Texture2D" path="res://assets/sprites/niulai/{c["file"]}" id="{idx}_{name}"]')
        frame_refs = []
        for k in range(c["frames"]):
            sid = f"AtlasTexture_{name}_{k}"
            col, row = k % c["cols"], k // c["cols"]
            sub.append(
                f'[sub_resource type="AtlasTexture" id="{sid}"]\n'
                f'atlas = ExtResource("{idx}_{name}")\n'
                f'region = Rect2({col * c["w"]}, {row * c["h"]}, {c["w"]}, {c["h"]})\n'
                f'margin = Rect2({c["x"]}, {c["y"]}, {CANVAS - c["w"]}, {CANVAS - c["h"]})\n'
                f'filter_clip = true\n')
            frame_refs.append('{\n"duration": 1.0,\n"texture": SubResource("%s")\n}' % sid)
        anims.append('{\n"frames": [%s],\n"loop": %s,\n"name": &"%s",\n"speed": %s\n}'
                     % (", ".join(frame_refs), "true" if c["loop"] else "false", name, c["fps"]))
    lines.append("[gd_resource type=\"SpriteFrames\" format=3]\n")
    lines += ext
    lines.append("")
    lines += sub
    lines.append("[resource]")
    lines.append("animations = [%s]" % ", ".join(anims))
    (OUT / "niulai.tres").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    cfg_path = SRC / "clips.json"
    all_clips = json.loads(cfg_path.read_text(encoding="utf-8"))
    wanted = sys.argv[1:] or list(all_clips)
    info_path = OUT / "anims.json"
    infos = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    for name in wanted:
        info = build(name, all_clips[name])
        if info:
            infos[name] = info
    infos = {k: v for k, v in infos.items() if k in all_clips}
    info_path.write_text(json.dumps(infos, ensure_ascii=False, indent=1), encoding="utf-8")
    write_sprite_frames(infos)
    print("->", OUT)


if __name__ == "__main__":
    main()
