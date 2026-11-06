"""Effect operators for segment C (frames 437-644), from spec/segC.md.

Layers are (rgb, alpha, glyph) full-res tuples as produced by look2.text_layer. Most operators work on
"premultiplied channel layers": P (H,W,3) premultiplied colour and A (H,W,3) per-channel alpha, so a
channel split / prism can be applied and composited per channel (out_c = bg_c * (1 - A_c) + P_c).
"""
from functools import lru_cache

import numpy as np

import kit
import look2

H, W = kit.H, kit.W


# ------------------------------------------------------------------ layer <-> channel form
def to_ch(layer):
    rgb, a, _ = layer
    A = np.repeat(a[..., None], 3, -1)
    return rgb * A, A


def comp_ch(img, P, A):
    return np.clip(img * (1 - np.clip(A, 0, 1)) + P, 0, 1)


def scale_ch(P, A, k):
    """fade a channel layer (k scalar or (3,) colour multiplier on P, alpha by its mean)."""
    k = np.asarray(k, np.float32)
    ka = float(k.mean()) if k.ndim else float(k)
    return P * k, A * ka


def add_ch(a, b):
    """stack layer b over layer a -> one channel layer."""
    Pa, Aa = a
    Pb, Ab = b
    return Pb + Pa * (1 - Ab), Ab + Aa * (1 - Ab)


# ------------------------------------------------------------------ geometry
def shift2(a, dx, dy=0):
    return kit.shift(a, dx, dy) if a.ndim == 2 else np.stack([kit.shift(a[..., c], dx, dy) for c in range(a.shape[2])], -1)


def hscale(a, k, cx=480):
    """horizontal scale about x=cx (nearest-ish bilinear via index map)."""
    x = (np.arange(W, dtype=np.float32) - cx) / k + cx
    x0 = np.clip(np.floor(x).astype(int), 0, W - 1)
    x1 = np.clip(x0 + 1, 0, W - 1)
    f = (x - np.floor(x))
    valid = ((x >= 0) & (x <= W - 1)).astype(np.float32)
    if a.ndim == 2:
        return (a[:, x0] * (1 - f) + a[:, x1] * f) * valid
    return (a[:, x0] * (1 - f)[:, None] + a[:, x1] * f[:, None]) * valid[:, None]


def crop_x(a, x_max=None, x_min=None, y_min=None, y_max=None):
    out = a.copy()
    if x_max is not None:
        out[:, int(x_max):] = 0
    if x_min is not None:
        out[:, :int(x_min)] = 0
    if y_min is not None:
        out[:int(y_min)] = 0
    if y_max is not None:
        out[int(y_max):] = 0
    return out


def bands(a, spec):
    """spec = [(y0, y1, dx)]: horizontal band displacement (works on 2D or 3D arrays)."""
    out = a.copy()
    for y0, y1, dx in spec:
        out[y0:y1] = np.roll(a[y0:y1], int(dx), axis=1)
    return out


# ------------------------------------------------------------------ textures
def scanlines(h=H, period=13.0, duty=0.5, phase=0.0, soft=0.25):
    """horizontal stripe pattern (1 = line on) with the reference 12-13 px period."""
    y = np.arange(h, dtype=np.float32)
    t = ((y / period + phase) % 1.0)
    on = np.clip((duty - t) / soft + 0.5, 0, 1) * np.clip((t) / soft + 0.5, 0, 1)
    return on[:, None]


def scan_ghost(mask, dx, dy=0, lum=0.55, period=13.0, phase=0.0, smear=3):
    """striped (scanline) offset copy of a glyph mask -> alpha (H,W) to paint in grey."""
    g = shift2(mask, dx, dy)
    if smear:
        g = kit.box_blur_h(g, smear)
    return np.clip(g * scanlines(period=period, phase=phase) * lum, 0, 1)


def noise_block(shape_mask, seed, rect, std=0.3):
    """coarse 1 px mono dither noise multiplier inside rect (x0, y0, x1, y1) -> (H,W) multiplier."""
    r = kit.rng(seed)
    m = np.ones((H, W), np.float32)
    x0, y0, x1, y1 = rect
    n = r.random((y1 - y0, x1 - x0)).astype(np.float32)
    m[y0:y1, x0:x1] = np.clip(1 - std * 2.2 * (n - 0.35), 0.15, 1.3)
    return m


def halftone_ch(P, A, pitch=4.0, angle=np.pi / 4, gain=1.25):
    """replace the layer's coverage by a dot screen (dark dots on the lit areas)."""
    lum = A.mean(-1)
    dots = kit.halftone(np.clip(lum, 0, 1), pitch, angle, gain)
    k = (dots / np.maximum(lum, 1e-3))[..., None]
    k = np.clip(k, 0, 1)
    return P * k, A * k


def dot_dither(seed, pitch=3.5, density=0.35):
    """sparse dot/cross dither multiplier (ghost copies of 619/631/644)."""
    r = kit.rng(seed)
    y, x = np.mgrid[0:H, 0:W]
    grid = ((x % int(round(pitch))) == 0) | ((y % int(round(pitch))) == 0)
    holes = r.random((H, W)) < density
    return np.where(grid & holes, 0.25, 1.0).astype(np.float32)


def checker(seed, rect, pitch=2, depth=0.45):
    m = np.ones((H, W), np.float32)
    x0, y0, x1, y1 = rect
    y, x = np.mgrid[y0:y1, x0:x1]
    c = (((x // pitch) + (y // pitch)) % 2).astype(np.float32)
    r = kit.rng(seed).random(c.shape) < 0.7
    m[y0:y1, x0:x1] = 1 - depth * c * r
    return m


def drips(mask, seed, n=70, wmin=1, wmax=2, lmin=16, lmax=32, depth=0.13):
    """dark vertical streaks hanging from the top edge of each glyph stem (ДЕВЧАТА)."""
    r = kit.rng(seed)
    out = np.ones((H, W), np.float32)
    ys, xs = np.where(mask > 0.6)
    if not len(xs):
        return out
    top = {}
    for x in np.unique(xs):
        top[x] = ys[xs == x].min()
    cols = list(top.keys())
    for _ in range(n):
        x = int(r.choice(cols))
        w = int(r.integers(wmin, wmax + 1))
        L = int(r.integers(lmin, lmax + 1))
        y0 = top[x] + int(r.integers(0, 6))
        prof = np.linspace(1, 0, L, dtype=np.float32) ** 0.7
        d = depth * float(r.uniform(0.6, 1.4))
        out[y0:y0 + L, x:x + w] *= (1 - d * prof[: max(0, min(L, H - y0))])[:, None]
    return out


def speck(seed, n=12, mask=None, dark=True, rmax=2):
    """small dust specks (multiplier map)."""
    r = kit.rng(seed)
    out = np.ones((H, W), np.float32)
    if mask is not None:
        ys, xs = np.where(mask > 0.8)
        if not len(xs):
            return out
        idx = r.integers(0, len(xs), n)
        pts = zip(xs[idx], ys[idx])
    else:
        pts = zip(r.integers(0, W, n), r.integers(0, H, n))
    for x, y in pts:
        rr = int(r.integers(1, rmax + 1))
        out[max(0, y - rr):y + rr, max(0, x - rr // 2):x + rr // 2 + 1] = 0.35 if dark else 1.6
    return out


# ------------------------------------------------------------------ colour
def prism(P, A, dx_r=7, dx_b=-10, blur=7.0, dx_g=0):
    """spectral split: each channel shifted horizontally and smeared -> continuous rainbow fringes."""
    outP, outA = np.empty_like(P), np.empty_like(A)
    for c, dx in enumerate((dx_r, dx_g, dx_b)):
        p = kit.shift(P[..., c], dx)
        a = kit.shift(A[..., c], dx)
        if blur:
            p = kit.box_blur_h(p, blur)
            a = kit.box_blur_h(a, blur)
        outP[..., c], outA[..., c] = p, a
    return outP, outA


@lru_cache(maxsize=1)
def text_vignette():
    """the reference vignette also darkens the text near the frame edges: 1 - 1.43 d^4."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((x - 480) / 480, (y - 360) / 360)
    return np.clip(1 - 1.43 * d ** 4, 0.12, 1)[..., None].astype(np.float32)


def scratch(seed, p0, p1, width=1.2, lum=0.9):
    """thin bright diagonal scratch line from p0 to p1 -> alpha (H,W)."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = np.hypot(dx, dy)
    t = np.clip(((x - x0) * dx + (y - y0) * dy) / (L * L), 0, 1)
    d = np.hypot(x - (x0 + t * dx), y - (y0 + t * dy))
    wob = 1 + 0.4 * np.sin(t * 25 + seed)
    return np.clip((width * wob - d), 0, 1) * lum


# ------------------------------------------------------------------ text layers (cached; the reference text
# texture is static while a word is held: frame diffs 0.2-1 luma)
_cache = {}


def layer(key, text, bbox, col, seed, **kw):
    k = (key, text, tuple(bbox), tuple(col), seed, tuple(sorted((a, str(b)) for a, b in kw.items())))
    if k not in _cache:
        if len(_cache) > 40:
            _cache.clear()
        _cache[k] = look2.text_layer(text, bbox, col, seed, **kw)
    return _cache[k]


def mask_of(text, bbox, weight=700, tracking=0.0, name="oswald"):
    return kit.text_box(text, bbox, weight, tracking, name)
