"""合成占位音效 → audio/sfx/*.wav

用法: python tools/gen_sfx.py
打击音 = 低频"咚"(音高快速下滑) + 噪声瞬态"啪" + 失真噪声"咔"，叠起来就有肉感。
以后找到/做了真实音效，直接覆盖同名 wav 即可。
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "audio", "sfx")
rng = np.random.default_rng(7)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env(dur, attack, decay_pow=1.0):
    t = t_axis(dur)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.clip(1 - (t - attack) / max(dur - attack, 1e-4), 0, 1) ** decay_pow
    return np.where(t < attack, a, d)


def lowpass(x, cutoff):
    """一阶低通，cutoff 可以是随时间变化的数组"""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def noise(dur):
    return rng.uniform(-1, 1, int(SR * dur))


def sweep_sine(dur, f0, f1, curve=3.0):
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-curve * t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def pad(x, dur):
    n = int(SR * dur)
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def thump(dur, f0, f1, decay=4.0):
    return sweep_sine(dur, f0, f1) * env(dur, 0.002, decay)


def whoosh(dur, lo, hi, gain=0.6):
    t = t_axis(dur)
    k = t / dur
    cutoff = lo + (hi - lo) * np.sin(np.pi * k) ** 2
    x = lowpass(noise(dur), cutoff)
    x = highpass(x, 200)
    return x * env(dur, dur * 0.35, 1.5) * gain * 4


def crunch(dur, drive=6.0):
    x = highpass(noise(dur), 1500) * env(dur, 0.001, 3.0)
    return np.tanh(x * drive) * 0.5


def mix(dur, *parts):
    out = np.zeros(int(SR * dur))
    for p in parts:
        out += pad(p, dur)
    return out


def finish(x, drive=1.6, gain=0.9):
    x = np.tanh(x * drive) / np.tanh(drive)
    peak = np.max(np.abs(x)) or 1
    return x / peak * gain


def save(name, x):
    os.makedirs(OUT, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("wrote", name)


def main():
    save("whoosh_light", finish(whoosh(0.12, 800, 5000), 1.2, 0.5))
    save("whoosh_heavy", finish(whoosh(0.22, 300, 2500), 1.2, 0.6))

    save("hit_light", finish(mix(0.14,
        thump(0.12, 220, 70, 3.0) * 0.9,
        highpass(noise(0.012), 3000) * env(0.012, 0.0005, 2) * 0.8,
        lowpass(noise(0.04), 1800) * env(0.04, 0.001, 2.5) * 0.7,
    ), 2.0, 0.85))

    save("hit_heavy", finish(mix(0.32,
        thump(0.3, 160, 38, 2.5) * 1.2,
        thump(0.18, 90, 30, 2.0) * 0.6,
        highpass(noise(0.02), 2500) * env(0.02, 0.0005, 2) * 0.9,
        crunch(0.09, 8.0) * 0.8,
        lowpass(noise(0.08), 900) * env(0.08, 0.001, 2) * 0.8,
    ), 2.6, 0.95))

    save("ko", finish(mix(0.7,
        thump(0.65, 140, 28, 2.0) * 1.3,
        crunch(0.14, 10.0) * 0.9,
        lowpass(noise(0.6), np.linspace(2500, 120, int(SR * 0.6))) * env(0.6, 0.002, 1.5) * 1.2,
    ), 2.8, 0.95))

    save("jump", finish(mix(0.1,
        sweep_sine(0.09, 260, 520, -2.0) * env(0.09, 0.005, 2) * 0.4,
        whoosh(0.08, 1500, 4000, 0.3),
    ), 1.2, 0.4))

    save("land", finish(mix(0.12,
        thump(0.1, 110, 45, 3.0),
        lowpass(noise(0.05), 1200) * env(0.05, 0.001, 2) * 0.6,
    ), 1.8, 0.55))

    save("dash", finish(whoosh(0.18, 1500, 7000, 0.7), 1.3, 0.5))

    save("hurt", finish(mix(0.24,
        thump(0.2, 180, 60, 2.5),
        np.sign(sweep_sine(0.2, 520, 180, 2.0)) * env(0.2, 0.002, 2) * 0.25,
        crunch(0.06, 6.0) * 0.6,
    ), 2.0, 0.85))

    save("bounce", finish(mix(0.16,
        thump(0.15, 95, 38, 3.0),
        lowpass(noise(0.07), 700) * env(0.07, 0.001, 2) * 0.8,
    ), 2.2, 0.7))

    t = t_axis(0.22)
    ting = (np.sin(2 * np.pi * 1320 * t) + 0.5 * np.sin(2 * np.pi * 1980 * t)) * env(0.22, 0.002, 2.5)
    save("warn", finish(ting, 1.0, 0.35))


if __name__ == "__main__":
    main()
