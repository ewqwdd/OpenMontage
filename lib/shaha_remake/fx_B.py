"""Effect operators for segment B (frames 235-436). numpy + PIL, built on kit.py."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

import kit

H, W = kit.H, kit.W


# ------------------------------------------------------------------ glyphs
@lru_cache(maxsize=64)
def _strip(text, cap, width, weight, tracking, ss=2):
    """per-character masks of one text line, squeezed to `width` px of ink, cap height `cap` px.
    -> (list of (char, mask_strip HxW)), cap_top offset in strip px."""
    probe = kit.font("oswald", 200, weight)
    bb = probe.getbbox("Н")
    capr = (bb[3] - bb[1]) / 200
    size = max(6, int(round(cap * ss / capr)))
    f = kit.font("oswald", size, weight)
    hb = f.getbbox("Н")
    adv = [f.getlength(c) for c in text]
    total = sum(adv) + tracking * size * (len(text) - 1) + 2 * size
    hh = int(size * 1.8)
    oy = int(size * 0.3)
    x = size
    ims = []
    for c, a in zip(text, adv):
        im = Image.new("L", (int(total), hh), 0)
        if c.strip():
            ImageDraw.Draw(im).text((x, oy), c, font=f, fill=255)
        ims.append(np.asarray(im, np.float32) / 255)
        x += a + tracking * size
    allm = np.max(np.stack(ims), 0)
    xs = np.where(allm.max(0) > 0.1)[0]
    x0, x1 = xs[0], xs[-1] + 1
    sx = width / (x1 - x0)
    nh = int(round(hh / ss))
    out = []
    for c, m in zip(text, ims):
        m = m[:, x0:x1]
        r = Image.fromarray((m * 255).astype(np.uint8)).resize((int(width), nh), Image.LANCZOS)
        out.append((c, np.asarray(r, np.float32) / 255))
    cap_top = (oy + hb[1]) / ss
    return out, cap_top


def line(text, cap, x0, x1, top, weight=700, tracking=0.0, vis=None, sy=1.0):
    """full-frame mask of a text line; vis = string like 'МН_ К·Ж...' (letter=on, '·'=0.5, '_'=off)."""
    chars, ct = _strip(text, int(cap), int(round(x1 - x0)), int(weight), float(tracking))
    out = np.zeros((H, W), np.float32)
    acc = None
    for k, (c, m) in enumerate(chars):
        if not c.strip():
            continue
        a = 1.0
        if vis is not None and k < len(vis):
            v = vis[k]
            a = 0.0 if v == "_" else (0.45 if v == "·" else 1.0)
        if a <= 0:
            continue
        acc = m * a if acc is None else np.maximum(acc, m * a)
    if acc is None:
        return out
    if sy != 1.0:
        acc = np.asarray(Image.fromarray(acc, "F").resize((acc.shape[1], max(1, int(acc.shape[0] * sy))), Image.BILINEAR))
    oy = int(round(top - ct * sy)); ox = int(round(x0))
    h, w = acc.shape
    ya, xa = max(0, oy), max(0, ox)
    yb, xb = min(H, oy + h), min(W, ox + w)
    if yb > ya and xb > xa:
        out[ya:yb, xa:xb] = acc[ya - oy:yb - oy, xa - ox:xb - ox]
    return out


# ------------------------------------------------------------------ filters
def blur_hv(a, sx, sy):
    out = a.astype(np.float32)
    for ax, s in ((1, sx), (0, sy)):
        if s <= 0:
            continue
        b = max(1, int(round(s * 0.95)))
        for _ in range(3):
            out = kit._box(out, b, ax)
    return out


def scale_about(a, sx, sy, cx, top):
    """scale a full-frame mask about (cx, top)."""
    h, w = a.shape[:2]
    nw, nh = int(round(w * sx)), int(round(h * sy))
    if a.ndim == 2:
        r = np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((nw, nh), Image.BILINEAR))
    else:
        r = np.stack([np.asarray(Image.fromarray(a[..., c].astype(np.float32), "F").resize((nw, nh), Image.BILINEAR))
                      for c in range(a.shape[2])], -1)
    out = np.zeros_like(a)
    ox = int(round(cx - cx * sx)); oy = int(round(top - top * sy))
    ya, xa = max(0, oy), max(0, ox)
    yb, xb = min(h, oy + nh), min(w, ox + nw)
    out[ya:yb, xa:xb] = r[ya - oy:yb - oy, xa - ox:xb - ox]
    return out


def vstreak_field(seed, amp=0.11, ylen=(8, 40)):
    """multiplicative vertical streak field, 1-2 px wide, 10-40 px long (random per frame)."""
    r = kit.rng(seed)
    ny = H // 6 + 2
    n = r.normal(0, 1, (ny, W)).astype(np.float32)
    n = 0.6 * n + 0.4 * np.roll(n, 1, 1)
    yi = np.linspace(0, ny - 1.001, H)
    i0 = yi.astype(int); f = (yi - i0)[:, None]
    n = n[i0] * (1 - f) + n[i0 + 1] * f
    return 1 + amp * n


def grain_field(seed, elong=0.5):
    """1 px mono noise, slightly vertically elongated (lag-1 vertical corr ~0.3)."""
    n = kit.rng(seed).normal(0, 1, (H + 1, W)).astype(np.float32)
    n = (n[:-1] + elong * n[1:]) / np.sqrt(1 + elong ** 2)
    return n


def quincunx(m, pitch=6.0, gain=1.0):
    """dot screen with dots on a 6 px square grid + centre dot (= 45deg lattice of 4.24 px)."""
    return kit.halftone(m, pitch=pitch / np.sqrt(2), angle=np.pi / 4, gain=gain)


def hslices(img, seed, region, n=5, hmin=8, hmax=30, amp=50, xr=None):
    r = kit.rng(seed)
    out = img.copy()
    y0, y1 = region
    for _ in range(n):
        bh = int(r.integers(hmin, hmax + 1))
        y = int(r.integers(y0, max(y0 + 1, y1 - bh)))
        dx = int(r.integers(-amp, amp + 1))
        if xr is None:
            out[y:y + bh] = np.roll(img[y:y + bh], dx, axis=1)
        else:
            a, b = xr
            out[y:y + bh, a:b] = np.roll(img[y:y + bh, a:b], dx, axis=1)
    return out


def scanlines(h, w, period=12.0, duty=0.5, depth=0.7, phase=0.0):
    y = np.arange(h, dtype=np.float32)
    on = (((y + phase) % period) < period * duty).astype(np.float32)
    return np.broadcast_to((1 - depth * (1 - on))[:, None], (h, w))


# ------------------------------------------------------------------ prism
PRISM_TINTS = [  # (dx, rgb weights): red/orange copies left, cyan/blue copies right
    (-8, (0.55, 0.10, 0.02)), (-5, (0.45, 0.30, 0.08)), (-2, (0.20, 0.30, 0.18)),
    (2, (0.08, 0.25, 0.30)), (5, (0.02, 0.15, 0.30)), (8, (0.0, 0.05, 0.22)),
]


def prism(m, spread=1.0, tints=PRISM_TINTS):
    """per-channel alpha (H,W,3) of a white glyph split into tinted copies (sum ~1 per channel)."""
    out = np.zeros((H, W, 3), np.float32)
    for dx, wts in tints:
        s = kit.shift(m, dx * spread, 0)
        for c in range(3):
            out[..., c] += wts[c] * s
    tot = np.asarray([sum(t[1][c] for t in tints) for c in range(3)], np.float32)
    return np.clip(out / tot, 0, 1)


RAINBOW = [  # ~6 copies spread ~30 px (ЗА УПОКОЙ)
    (-15, (0.50, 0.05, 0.00)), (-9, (0.45, 0.35, 0.00)), (-4, (0.30, 0.45, 0.05)),
    (2, (0.05, 0.45, 0.25)), (8, (0.00, 0.25, 0.45)), (14, (0.10, 0.00, 0.40)),
]


def comp_rgb_alpha(img, col_rgb, a3):
    """composite colour (3,) through per-channel alpha (H,W,3)."""
    c = np.asarray(col_rgb, np.float32)[None, None] / 255
    return img * (1 - a3) + c * a3


def over(img, col, a):
    return kit.over(img, col, a)


def screen_col(img, col, a):
    c = np.asarray(col, np.float32)[None, None] / 255
    return 1 - (1 - img) * (1 - c * np.clip(a, 0, 1)[..., None])
