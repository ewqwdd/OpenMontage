"""Geometry and glitch helpers: camera affine, keyframe curves, 20 fps conform, mosaic, band,
zoom-blur + macroblock clip entry, 9:16 letterbox."""
import numpy as np
from PIL import Image


# ---------------------------------------------------------------- camera
def _affine(src, zoom, dx, dy, rot, size):
    """PIL affine: output pixel -> source pixel. zoom 1 = the source's central `size` crop."""
    w, h = size
    sh, sw = src.shape[:2]
    c, s = np.cos(np.radians(rot)) / zoom, np.sin(np.radians(rot)) / zoom
    ox, oy = w / 2 + dx, h / 2 + dy
    a, b, d, e = c, s, -s, c
    cc = sw / 2 - a * ox - b * oy
    ff = sh / 2 - d * ox - e * oy
    return (a, b, cc, d, e, ff)


def camera(src, zoom=1.0, dx=0.0, dy=0.0, rot=0.0, size=None):
    size = size or (src.shape[1], src.shape[0])
    return np.asarray(Image.fromarray(src).transform(size, Image.AFFINE, _affine(src, zoom, dx, dy, rot, size),
                                                     Image.BILINEAR))


# ---------------------------------------------------------------- curves
def keyframes(i, keys, ease="cosine"):
    """interpolate through [(frame, value), ...], clamped at both ends; cosine-eased or linear"""
    if i <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if a <= i <= b:
            u = (i - a) / (b - a)
            if ease == "cosine":
                u = 0.5 - 0.5 * np.cos(np.pi * u)
            return va + (vb - va) * u
    return keys[-1][1]


def conform(j, fps=30, to=20):
    """output frame j -> source frame index when the footage is conformed to `to` fps inside `fps`
    (20 in 30: every 3rd frame repeats, the stuttery texture of ref3)"""
    if not to or to >= fps:
        return j
    return int(np.floor(j * to / fps) * (fps / to))


def pingpong(j, span, hold=1):
    """source frame index that runs 0..span..0 and repeats, each source frame held `hold` frames"""
    q = j // hold
    n = q % (2 * span)
    return n if n <= span else 2 * span - n


# ---------------------------------------------------------------- pixel glitches
def mosaic(img, block=36):
    h, w = img.shape[:2]
    sm = Image.fromarray(img).resize((max(1, w // block), max(1, h // block)), Image.BOX)
    return np.asarray(sm.resize((w, h), Image.NEAREST))


def band(img, y0, y1, k=0.35):
    """translucent black strip (the 'subtitle bar'): multiply rows y0..y1 by k (in place)"""
    img[y0:y1] = (img[y0:y1].astype(np.float32) * k).astype(np.uint8)
    return img


def zoom_blur(img, z0, z1, n=4):
    """average of n centre zooms between z0 and z1 (radial smear)"""
    h, w = img.shape[:2]
    im = Image.fromarray(img)
    acc = np.zeros(img.shape, np.float32)
    for k in range(n):
        z = z0 + (z1 - z0) * k / max(1, n - 1)
        cw, ch = w / z, h / z
        box = ((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2)
        acc += np.asarray(im.resize((w, h), Image.BILINEAR, box=box), np.float32)
    return (acc / n).astype(np.uint8)


def macroblock(img, seed, strength=1.0, n=14):
    """displaced blocky macroblocks + small white glitch rectangles"""
    rng = np.random.default_rng(seed)
    out = img.copy()
    h, w = img.shape[:2]
    for _ in range(int(n * strength)):
        bw, bh = int(rng.integers(40, 160)), int(rng.integers(24, 96))
        x, y = int(rng.integers(0, w - bw)), int(rng.integers(0, h - bh))
        sx = int(np.clip(x + rng.integers(-90, 90), 0, w - bw))
        sy = int(np.clip(y + rng.integers(-40, 40), 0, h - bh))
        blk = img[sy:sy + bh, sx:sx + bw]
        k = 16
        blk = np.asarray(Image.fromarray(blk).resize((max(1, bw // k), max(1, bh // k)), Image.BOX)
                         .resize((bw, bh), Image.NEAREST))
        out[y:y + bh, x:x + bw] = blk
    for _ in range(int(2 + 3 * strength)):
        x, y = int(rng.integers(60, w - 120)), int(rng.integers(60, h - 60))
        out[y:y + 10, x:x + int(rng.integers(30, 60))] = 245
    return out


def glitch_entry(img, i, e0, frames=4):
    """first `frames` frames of a clip: zoom-blur x1.25 -> 1 + macroblocks, ease-out (ref3 #6)"""
    u = (i - e0) / frames
    s = (1 - u) ** 2
    img = zoom_blur(img, 1.0 + 0.25 * s, 1.0 + 0.25 * s + 0.12 * s, 5)
    return macroblock(img, seed=i, strength=s * 1.4 + 0.2)


# ---------------------------------------------------------------- layout
def letterbox(square, size, y0, bar):
    """square picture into the 9:16 frame; `bar` = colour of the bars (they follow the polarity)"""
    out = np.empty((size[1], size[0], 3), np.uint8)
    out[:] = bar
    out[y0:y0 + square.shape[0]] = square
    return out
