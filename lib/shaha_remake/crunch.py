"""Compression look of the reference: 8x8-block edge jitter (per frame) + real MPEG-2 re-encode pass."""
import subprocess
from pathlib import Path

import numpy as np

import kit


def edge_map(img):
    L = img.mean(-1)
    gx = np.abs(np.diff(L, axis=1, prepend=L[:, :1]))
    return kit.blur(np.clip(gx * 6, 0, 1), 1.5)


def block_jitter(img, seed, p=0.35, amax=2, bs=8, region=None, hmul=(1, 2)):
    """blocks (bs wide, bs*k tall) that contain an edge get their content shifted dx px horizontally."""
    r = kit.rng(seed)
    e = edge_map(img)
    out = img.copy()
    h, w = img.shape[:2]
    y = 0
    if region is not None:
        x0, y0, x1, y1 = region
    else:
        x0, y0, x1, y1 = 0, 0, w, h
    for by in range(0, h, bs):
        if by + bs <= y0 or by >= y1:
            continue
        for bx in range(0, w, bs):
            if bx + bs <= x0 or bx >= x1:
                continue
            if e[by:by + bs, bx:bx + bs].max() < 0.15 or r.random() > p:
                continue
            dx = int(r.integers(1, amax + 1)) * (1 if r.random() < 0.5 else -1)
            bh = bs * int(r.integers(hmul[0], hmul[1] + 1))
            ys = slice(by, min(h, by + bh))
            sx = np.clip(np.arange(bx, min(w, bx + bs)) - dx, 0, w - 1)
            out[ys, bx:bx + bs] = img[ys][:, sx]
    return out


def codec_pass(src_dir, dst_dir, f0, f1, q=9, pattern="%04d.png"):
    """re-encode frames through MPEG-2 at a fixed quantiser and decode back (mosquito noise, block edges)."""
    dst = Path(dst_dir); dst.mkdir(parents=True, exist_ok=True)
    tmp = dst / "_crunch.mpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-start_number", str(f0), "-i", str(Path(src_dir) / pattern),
                    "-frames:v", str(f1 - f0), "-c:v", "mpeg2video", "-qscale:v", str(q), "-g", "12", "-bf", "2",
                    "-pix_fmt", "yuv420p", str(tmp)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-start_number", str(f0), str(dst / pattern)], check=True)
    tmp.unlink()


def _hblur(a, s):
    if s <= 0:
        return a
    r = int(3 * s + 0.5); x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-x * x / (2 * s * s)); k /= k.sum()
    p = np.pad(a, ((0, 0), (r, r)), mode="edge")
    return sum(k[j] * p[:, j:j + a.shape[1]] for j in range(2 * r + 1))


def edge_jitter(img, seed, p=0.25, amax=3, cell=16, hmul=(2, 8), bs=8, xsoft=2.5):
    """compression tearing as a displacement field: tall row bands (bs*k, on the 8 px grid) split into
    `cell` px wide cells, some displaced +-1..amax px horizontally; the field is softened in x only, so an
    edge moves as a whole segment (no 8 px teeth) and the steps sit on the block-row boundaries (ref 29-31)."""
    r = kit.rng(seed)
    h, w = img.shape[:2]
    D = np.zeros((h, w), np.float32)
    y = 0
    while y < h:
        bh = bs * int(r.integers(hmul[0], hmul[1] + 1))
        for x0 in range(0, w, cell):
            if r.random() < p:
                D[y:y + bh, x0:x0 + cell] = int(r.integers(1, amax + 1)) * (1 if r.random() < 0.5 else -1)
        y += bh
    D = _hblur(D, xsoft)
    xs = np.arange(w, dtype=np.float32)[None, :] - D
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1); x1 = np.clip(x0 + 1, 0, w - 1)
    f = np.clip(xs - np.floor(xs), 0, 1)[..., None]
    rows = np.arange(h)[:, None]
    return img[rows, x0] * (1 - f) + img[rows, x1] * f
