"""Post pass over the HyperFrames render: CRT lens -> frame holds -> VHS row wave.

- lens: zoom + lenscorrection (k1=0.17 effective) + crop — see lens.py;
- holds: every 4th frame repeats the previous one (reference is ~22 unique fps in 30),
  except frames where something appears (noholds from compose.build);
- wave: gaussian bumps of horizontal row shift (±2–5px, sometimes 7, sigma 40–52px,
  180–550px apart) crawling upward 40px/frame over the whole frame.
"""
import subprocess

import numpy as np

from .lens import ffmpeg_chain


def wave_profile(p=16384, seed=7):
    rng = np.random.default_rng(seed)
    prof, u, c = np.zeros(p), np.arange(p), 0.0
    while c < p:
        c += rng.uniform(180, 550)
        a = rng.choice([-1, 1]) * (rng.uniform(2.0, 5.0) if rng.random() > .1 else 7.0)
        prof += a * np.exp(-0.5 * ((u - c) / rng.uniform(40, 52)) ** 2)
    return prof


def shift_rows(img, dx, w):
    """out[y, x] = img[y, x - dx[y]] with linear interpolation, edge clamp."""
    xs = np.arange(w)[None, :] - dx[:, None]
    x0 = np.floor(xs).astype(np.int32)
    fr = (xs - x0)[..., None].astype(np.float32)
    a = np.take_along_axis(img, np.clip(x0, 0, w - 1)[..., None].repeat(3, 2), 1).astype(np.float32)
    b = np.take_along_axis(img, np.clip(x0 + 1, 0, w - 1)[..., None].repeat(3, 2), 1).astype(np.float32)
    return (a * (1 - fr) + b * fr).round().astype(np.uint8)


def run(src, dst, w, h, fps, noholds, lens=True, holds=True, wave=True, k1=0.17, zoom=1.17):
    prof = wave_profile()
    P, rows = len(prof), np.arange(h)
    vf = ["-vf", ffmpeg_chain(w, h, k1, zoom)] if lens else []
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), *vf, "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-i", str(src), "-map", "0:v",
                            "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", str(dst)],
                           stdin=subprocess.PIPE)
    noholds = set(noholds)
    size, prev, f = w * h * 3, None, 0
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        if holds and f % 4 == 3 and prev is not None and f not in noholds:
            frame = prev
        prev = frame
        if wave:
            frame = shift_rows(frame, prof[(rows + 40 * f) % P], w)
        enc.stdin.write(frame.tobytes())
        f += 1
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print(f"post: {f} frames -> {dst}")
