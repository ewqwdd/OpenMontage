"""Shared constants and pixel helpers.

The kit renders 1440x1080 (4:3). Every measured number in it is in reference pixels at 640x480
("px@480"), and S = 2.25 converts them to the canvas. Arrays: masks are float32 HxW in 0..1, images
float32 HxWx3 in 0..255.
"""
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

W, H, S = 1440, 1080, 2.25
BW, BH = 1520, 1140          # clips are loaded with a margin for jitter/shake
ASSETS = Path(__file__).parent / "assets"
FONT = str(ASSETS / "fonts" / "CormorantGaramond.ttf")
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def Y(v):
    """px@480 -> canvas px (int)"""
    return int(round(v * S))


def lum(x):
    return x[..., 0] * 0.299 + x[..., 1] * 0.587 + x[..., 2] * 0.114


def mask_blur(m, r):
    """PIL gaussian blur of a 0..1 mask (8-bit quantised, as measured)."""
    if r <= 0:
        return m
    im = Image.fromarray(np.clip(m * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def img_blur(a, r):
    """PIL gaussian blur of a 0..255 array (2D or HxWx3)."""
    if r <= 0:
        return a
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32)


def box1d(a, r, axis):
    """centred box of width 2*int(r) along axis, edge padded."""
    k = int(r)
    if k < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (k, k)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float32)
    hi = [np.s_[:]] * a.ndim
    lo = [np.s_[:]] * a.ndim
    hi[axis] = np.s_[2 * k:]
    lo[axis] = np.s_[:-2 * k]
    return (c[tuple(hi)] - c[tuple(lo)]) / (2 * k)


def hblur(a, r):
    return box1d(a, r, 1)


def vblur(a, r):
    return box1d(a, r, 0)


def resample_soft(img, k):
    """downsample by k and back up (the compressed softness of the reference)."""
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    sm = im.resize((max(1, W // int(k)), max(1, H // int(k))), Image.BILINEAR)
    return np.asarray(sm.resize((W, H), Image.BICUBIC)).astype(np.float32)


def jpeg_dirt(img, q=38):
    """TikTok-like compression: 720x540 JPEG round trip."""
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((720, 540), Image.BILINEAR)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("RGB").resize((W, H), Image.BICUBIC)).astype(np.float32)


def place(mask, ax, ay, cx, cy):
    """put mask so that its anchor (ax, ay) lands at (cx, cy) on a WxH canvas."""
    canvas = np.zeros((H, W), np.float32)
    x0 = int(round(cx - ax))
    y0 = int(round(cy - ay))
    h, w = mask.shape
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    w2 = min(w - sx0, W - dx0)
    h2 = min(h - sy0, H - dy0)
    if w2 > 0 and h2 > 0:
        canvas[dy0:dy0 + h2, dx0:dx0 + w2] = mask[sy0:sy0 + h2, sx0:sx0 + w2]
    return canvas


def luma_lut(img, xp, fp, strength=1.0):
    """tone-map luma through (xp, fp), keep each pixel's chroma ratio."""
    with np.errstate(all="ignore"):     # spurious Accelerate matmul warnings on macOS
        l = img @ LUMA
    ln = np.interp(l, xp, fp).astype(np.float32)
    if strength != 1.0:
        ln = l + (ln - l) * strength
    return img * ((ln + 1) / (l + 1))[..., None]
