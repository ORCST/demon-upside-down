"""把 Godot Movie Maker 录下的 PNG 序列 + WAV 合成 MP4（像素放大，带声音）。

需要 PyAV，用 ComfyUI 自带的 Python 跑：
  D:/Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/Scripts/python.exe tools/encode_movie.py <帧目录> <输出.mp4> [放大倍数=3]

录制命令示例（在项目目录）：
  Godot_v4.6.2-stable_win64_console.exe --path . --write-movie rec/f.png --fixed-fps 60 -- --autopilot=demo
"""
import glob
import os
import sys
import wave

import av
import numpy as np
from PIL import Image

FPS = 60


def main():
    frames_dir, out_path = sys.argv[1], sys.argv[2]
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    frames = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    if not frames:
        sys.exit("没有找到 PNG 帧: " + frames_dir)
    w, h = Image.open(frames[0]).size

    out = av.open(out_path, "w")
    vs = out.add_stream("libx264", rate=FPS)
    vs.width, vs.height = w * scale, h * scale
    vs.pix_fmt = "yuv420p"
    vs.options = {"crf": "18", "preset": "medium"}

    wavs = glob.glob(os.path.join(frames_dir, "*.wav"))
    audio = None
    if wavs:
        with wave.open(wavs[0], "rb") as wf:
            rate, ch, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())
        dtype = {2: np.int16, 4: np.int32}[width]
        pcm = np.frombuffer(raw, dtype=dtype).reshape(-1, ch)
        if width == 4:
            pcm = (pcm >> 16).astype(np.int16)
        aus = out.add_stream("aac", rate=rate)
        aus.layout = "stereo" if ch == 2 else "mono"
        audio = (aus, pcm, rate)

    for i, path in enumerate(frames):
        img = Image.open(path).convert("RGB").resize((w * scale, h * scale), Image.NEAREST)
        vf = av.VideoFrame.from_image(img)
        vf.pts = i
        for pkt in vs.encode(vf):
            out.mux(pkt)
    for pkt in vs.encode():
        out.mux(pkt)

    if audio:
        aus, pcm, rate = audio
        chunk = 1024
        layout = "stereo" if pcm.shape[1] == 2 else "mono"
        for start in range(0, len(pcm), chunk):
            block = np.ascontiguousarray(pcm[start:start + chunk].reshape(1, -1))  # s16 打包格式 = 交错排列
            af = av.AudioFrame.from_ndarray(block, format="s16", layout=layout)
            af.sample_rate = rate
            af.pts = start
            for pkt in aus.encode(af):
                out.mux(pkt)
        for pkt in aus.encode():
            out.mux(pkt)
    out.close()
    print("wrote", out_path, f"{len(frames)} frames", "with audio" if audio else "no audio")


if __name__ == "__main__":
    main()
