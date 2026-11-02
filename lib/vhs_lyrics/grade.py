"""Auto-grade a scene background to a target look.

A scene may give `bg.look` instead of a hand-written `bg.grade`:
  "look": {"median": 22, "p95": 90, "sat": 0.6, "tint": "colorbalance=bs=0.08"}
median / p95 are luma targets (0-255) of the cover-cropped clip over the scene's frames.
The grade is saturation + optional tint + a 4-point `curves` that maps the clip's own
median and p95 onto the targets (lows crushed, lights kept), refined over 3 passes.
Swapping a background clip therefore keeps the scene's brightness automatically.
"""
import subprocess

import numpy as np

LOOK = {"median": 22, "p95": 90, "sat": 0.6, "tint": ""}


def _measure(src, offset, frames, W, H, fps, grade):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},{grade},"
          "scale=180:135,format=gray")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(offset), "-i", str(src), "-vf", vf,
                          "-frames:v", str(frames), "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(np.float32)


def _curves(pts):
    return "curves=all='" + " ".join(f"{x:.4f}/{y:.4f}" for x, y in pts) + "'"


def fit(src, offset, frames, W, H, fps, look):
    lk = dict(LOOK, **look)
    pre = f"eq=saturation={lk['sat']}" + (f",{lk['tint']}" if lk["tint"] else "")
    m, h = lk["median"] / 255, lk["p95"] / 255
    tm, th = m, h
    base = _measure(src, offset, frames, W, H, fps, pre) / 255
    x50 = max(np.percentile(base, 50), 0.01)
    x95 = max(np.percentile(base, 95), x50 + 0.02)
    for _ in range(3):
        pts = [(0, 0), (x50, min(tm, 0.95)), (x95, min(th, 0.97)), (1, min(1, th + 0.12))]
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 0.005]
        grade = pre + "," + _curves(pts)
        r = _measure(src, offset, frames, W, H, fps, grade)
        med, p95 = np.median(r), np.percentile(r, 95)
        tm = min(tm * lk["median"] / max(med, 1), 0.9)
        th = min(max(th * lk["p95"] / max(p95, 1), tm + 0.05), 0.97)
    return grade, dict(median=float(med), p95=float(p95), mean=float(r.mean()))
