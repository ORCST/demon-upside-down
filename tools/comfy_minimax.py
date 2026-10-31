"""通过本机 ComfyUI 的 HTTP 接口跑 MiniMax H3（图生视频 / 首尾帧生视频）。

ComfyUI 要先启动（Comfy Desktop 里打开，或用命令行启动），默认端口 8189：
    D:/Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/Scripts/python.exe main.py \
        --port 8189 --models-directory D:/Comfy-Desktop/ComfyUI-Shared/models

用法（在项目根目录）：
    py tools/comfy_minimax.py --first art_source/x.png --prompt-file p.txt \
        --seconds 3 --size 512x768 --out art_source/minimax/adu_walk

输出：<out>.mp4（带音轨）和 <out>_frames/ 下逐帧 PNG。
参数和 Comfy 自带的 MiniMax H3 模板一致：turbo LoRA、8 步、res_multistep。
"""
import argparse
import json
import shutil
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

UNET = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
CLIP = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VAE_VIDEO = "minimax_h3_video_vae_fp16.safetensors"
VAE_AUDIO = "minimax_h3_audio_vae_fp32.safetensors"
TURBO_LORA = "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"


def frame_count(seconds: float) -> int:
    """24fps，对齐到模型要求的 17k+5 帧。"""
    n = max(5, round(seconds * 24))
    return n + (5 - n % 17) % 17


def api(host: str, path: str, data: bytes | None = None, headers: dict | None = None):
    req = urllib.request.Request(f"http://{host}{path}", data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def upload(host: str, path: Path) -> str:
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + path.read_bytes() + \
           f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    res = json.loads(api(host, "/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    return res["name"]


def build_graph(prompt: str, w: int, h: int, length: int, seed: int, prefix: str,
                first: str | None, last: str | None, steps: int) -> dict:
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": TURBO_LORA, "strength_model": 1.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_VIDEO}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_AUDIO}},
        "7": {"class_type": "MiniMaxH3ImageToVideo",
              "inputs": {"clip": ["3", 0], "vae": ["4", 0], "prompt": prompt,
                         "width": w, "height": h, "length": length}},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "10": {"class_type": "BasicScheduler",
               "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}},
        "11": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["7", 0]}},
        "12": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["8", 0], "guider": ["11", 0], "sampler": ["9", 0],
                          "sigmas": ["10", 0], "latent_image": ["7", 1]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["4", 0]}},
        "14": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["12", 0], "vae": ["5", 0]}},
        "15": {"class_type": "CreateVideo", "inputs": {"images": ["13", 0], "audio": ["14", 0], "fps": 24}},
        "16": {"class_type": "SaveVideo",
               "inputs": {"video": ["15", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
        "17": {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": prefix + "_f"}},
    }
    if first:
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": first}}
        g["7"]["inputs"]["first_frame"] = ["20", 0]
    if last:
        g["21"] = {"class_type": "LoadImage", "inputs": {"image": last}}
        g["7"]["inputs"]["last_frame"] = ["21", 0]
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1:8189")
    ap.add_argument("--first")
    ap.add_argument("--last")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--size", default="512x768")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--out", required=True, help="输出路径前缀（不带扩展名）")
    a = ap.parse_args()

    for _ in range(60):  # ComfyUI 刚启动时要等它加载完
        try:
            api(a.host, "/system_stats")
            break
        except OSError:
            time.sleep(3)
    else:
        raise SystemExit(f"连不上 ComfyUI（{a.host}），先启动它")

    prompt = Path(a.prompt_file).read_text(encoding="utf-8") if a.prompt_file else a.prompt
    w, h = (int(v) for v in a.size.lower().split("x"))
    out = Path(a.out)
    prefix = f"demon_unside_down/{out.name}_{int(time.time())}"
    first = upload(a.host, Path(a.first)) if a.first else None
    last = upload(a.host, Path(a.last)) if a.last else None

    graph = build_graph(prompt, w, h, frame_count(a.seconds), a.seed, prefix, first, last, a.steps)
    pid = json.loads(api(a.host, "/prompt", json.dumps({"prompt": graph}).encode(),
                         {"Content-Type": "application/json"}))["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while True:
        hist = json.loads(api(a.host, f"/history/{pid}"))
        if pid in hist:
            entry = hist[pid]
            if entry.get("status", {}).get("status_str") == "error":
                raise SystemExit("ComfyUI 报错：" + json.dumps(entry["status"], ensure_ascii=False)[:2000])
            break
        time.sleep(5)
    print(f"done in {time.time() - t0:.0f}s", flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(str(out) + "_frames")
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    n = 0
    for node in entry["outputs"].values():
        for kind in ("images", "videos", "gifs"):
            for f in node.get(kind, []):
                q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f["subfolder"], "type": f["type"]})
                data = api(a.host, f"/view?{q}")
                if f["filename"].lower().endswith(".png"):
                    n += 1
                    (frames_dir / f"{n:04d}.png").write_bytes(data)
                else:
                    (out.with_suffix(Path(f["filename"]).suffix)).write_bytes(data)
    print(f"saved {n} frames -> {frames_dir}")


if __name__ == "__main__":
    main()
