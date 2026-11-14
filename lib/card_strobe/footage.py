"""Footage I/O: every clip window is precut ONCE into a small square intermediate, then workers read
exact frame numbers from it, so any split of the render across processes gives the same frames.

A clip window = {"src": video, "t0": s, "dur": s, "ax": 0..1, "ay": 0..1}. It is cover-scaled to the
CANVAS (the square plus a margin on every side, 1210 px for a 1080 square), cropped at (ax, ay), and
resampled to the timeline fps. The margin is headroom for zoom, sway, bounce and whips.
"""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                                  capture_output=True, check=True).stdout)
    s = j["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(a) / float(b), float(j["format"]["duration"])


def precut(src, t0, dur, out, fps, size, margin=1.0, ax=0.5, ay=0.5, crf=12):
    """cut + cover-crop + resample a source span into `out` (frame n = t0 + n / fps)"""
    mw, mh = int(round(size[0] * margin / 2) * 2), int(round(size[1] * margin / 2) * 2)
    vf = (f"fps={fps},scale={mw}:{mh}:force_original_aspect_ratio=increase:flags=bicubic,"
          f"crop={mw}:{mh}:(iw-{mw})*{ax}:(ih-{mh})*{ay}")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t0:.4f}", "-i", str(src), "-t", f"{dur:.4f}",
                    "-vf", vf, "-an", "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-g", "15",
                    "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def read_range(path, a, b):
    """frames a..b-1 (by frame number, exact) of a precut clip -> uint8 (n, h, w, 3)"""
    w, h, _, _ = probe(path)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf", f"select='between(n,{a},{b - 1})'",
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def square_crop_ax(x, src_w, src_h, canvas, square=1080):
    """kit crop anchor for a curated square crop whose LEFT edge is at source px x (CURATED.json
    `square_crop` on a 1920x1080 source, square = source height): its centre becomes the canvas centre"""
    return subject_ax(src_w, src_h, (x + square / 2) / src_w, canvas)


def subject_ax(src_w, src_h, subject_x, canvas):
    """crop anchor ax that centres a subject at subject_x (0..1 of the source width) in the canvas"""
    scale = canvas / min(src_w, src_h)
    sw = src_w * scale
    if sw <= canvas + 1:
        return 0.5
    return float(np.clip((subject_x * sw - canvas / 2) / (sw - canvas), 0, 1))


def subject_in_canvas(src_w, src_h, subject_x, subject_y, ax, ay, canvas):
    """where a source point (fractions) lands in the precut canvas (px)"""
    scale = canvas / min(src_w, src_h)
    sw, sh = src_w * scale, src_h * scale
    return subject_x * sw - (sw - canvas) * ax, subject_y * sh - (sh - canvas) * ay


def precut_all(clips, cache_dir, fps, square, margin, log=print):
    """precut every clip window (cached by content hash) -> {name: precut path}"""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, c in clips.items():
        cf = c.get("fps") or fps         # a clip may be precut at its source rate (e.g. 60 for slow speeds)
        key = json.dumps([str(c["src"]), c["t0"], c["dur"], c.get("ax", 0.5), c.get("ay", 0.5), cf, square, margin],
                         sort_keys=True)
        h = hashlib.sha1(key.encode()).hexdigest()[:10]
        p = cache_dir / f"{name}_{h}.mp4"
        if not p.exists():
            log(f"precut {name}: {Path(c['src']).name} {c['t0']:.2f}+{c['dur']:.2f}s ax {c.get('ax', 0.5):.2f}")
            precut(c["src"], c["t0"], c["dur"], p.with_suffix(".tmp.mp4"), cf, (square, square), margin,
                   c.get("ax", 0.5), c.get("ay", 0.5))
            p.with_suffix(".tmp.mp4").replace(p)
        out[name] = str(p)
    return out
