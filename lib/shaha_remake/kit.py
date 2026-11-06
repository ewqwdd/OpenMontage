"""Core primitives for the шАхА remake (960x720, 30 fps). numpy + PIL only."""
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 960, 720, 30
OSWALD = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "vhs_lyrics" / "assets" / "fonts" / "Oswald.ttf")
FONTS = {"oswald": OSWALD}


# ------------------------------------------------------------------ fonts / text masks
@lru_cache(maxsize=64)
def font(name, size, weight=700):
    f = ImageFont.truetype(FONTS.get(name, name), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


@lru_cache(maxsize=512)
def _glyph_line(text, name, cap_px, weight, xscale, tracking, ss=3):
    """mask (float32 0..1) of one line of text, tight-cropped; cap_px = cap height in output px."""
    # cap height of Oswald ~ 0.81 em at its metrics; measure it
    probe = font(name, 200 * ss, weight)
    bb = probe.getbbox("Н")
    cap = (bb[3] - bb[1]) / (200 * ss)
    size = max(4, int(round(cap_px * ss / cap)))
    f = font(name, size, weight)
    asc, desc = f.getmetrics()
    xs = [0.0]
    widths = []
    for ch in text:
        widths.append(f.getlength(ch))
    total = sum(widths) + tracking * ss * max(0, len(text) - 1)
    im = Image.new("L", (int(total + 4 * size), asc + desc + 2 * size), 0)
    d = ImageDraw.Draw(im)
    x = size
    pos = []
    for ch, w in zip(text, widths):
        d.text((x, size), ch, font=f, fill=255)
        pos.append(x)
        x += w + tracking * ss
    a = np.asarray(im, np.float32) / 255
    # squeeze horizontally, downsample
    h, w = a.shape
    nw = max(1, int(round(w * xscale / ss)))
    nh = max(1, int(round(h / ss)))
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS), np.float32) / 255
    ys, xs_ = np.where(a > 0.05)
    if not len(xs_):
        return np.zeros((1, 1), np.float32), []
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs_.min(), xs_.max() + 1
    a = a[y0:y1, x0:x1].copy()
    # per-letter x ranges (output px, relative to the crop) for letter dropout
    lp = [((p * xscale / ss) - x0, (p + wd) * xscale / ss - x0) for p, wd in zip(pos, widths)]
    return a, lp


def text_mask(text, cap_px, weight=700, xscale=1.0, tracking=0.0, name="oswald"):
    m, lp = _glyph_line(text, name, int(round(cap_px)), int(weight), round(float(xscale), 3), float(tracking))
    return m, lp


def place(mask, cx, cy, size=(H, W), anchor="c"):
    """put a mask on a full frame at centre (cx, cy) -> full frame float mask."""
    out = np.zeros(size, np.float32)
    h, w = mask.shape
    x0 = int(round(cx - w / 2)) if anchor[0] != "l" else int(round(cx))
    y0 = int(round(cy - h / 2))
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(size[1], x0 + w), min(size[0], y0 + h)
    if xb > xa and yb > ya:
        out[ya:yb, xa:xb] = mask[ya - y0:yb - y0, xa - x0:xb - x0]
    return out


# ------------------------------------------------------------------ mask effects
def rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def rough(m, seed, amp=2.0, band=(2, 7), erode=0.0):
    """jagged edges: rows displaced horizontally in small bands (VHS line jitter on the glyphs)."""
    r = rng(seed)
    h, w = m.shape
    out = np.empty_like(m)
    y = 0
    while y < h:
        b = int(r.integers(band[0], band[1] + 1))
        dx = int(round(r.normal(0, amp)))
        out[y:y + b] = np.roll(m[y:y + b], dx, axis=1)
        y += b
    if erode > 0:
        n = r.random(m.shape).astype(np.float32)
        n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
        out = np.clip(out - erode * (n > 0.55) * (out < 0.98), 0, 1)
    return out


def blur(a, r):
    if r <= 0:
        return a
    b = max(1, int(round(r * 0.95)))          # 3 box passes ~ gaussian sigma r
    out = a.astype(np.float32)
    for ax in (0, 1):
        for _ in range(3):
            out = _box(out, b, ax)
    return out


def _box(a, b, ax):
    k = 2 * b + 1
    pad = [(0, 0)] * a.ndim
    pad[ax] = (b + 1, b)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=ax)
    sl_hi = [slice(None)] * a.ndim; sl_lo = [slice(None)] * a.ndim
    sl_hi[ax] = slice(k, None); sl_lo[ax] = slice(None, -k)
    return (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / k


def box_blur_h(a, r):
    """horizontal smear (motion blur) radius r px."""
    if r < 1:
        return a
    k = int(r) * 2 + 1
    c = np.cumsum(np.pad(a, [(0, 0), (k // 2 + 1, k // 2)] + [(0, 0)] * (a.ndim - 2), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k]) / k


def dilate(m, r):
    if r <= 0:
        return m
    im = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.MaxFilter(int(r) * 2 + 1)), np.float32) / 255


def shift(a, dx, dy=0):
    dx, dy = int(round(dx)), int(round(dy))
    out = np.roll(a, (dy, dx), (0, 1))
    if dx > 0: out[:, :dx] = 0
    if dx < 0: out[:, dx:] = 0
    if dy > 0: out[:dy] = 0
    if dy < 0: out[dy:] = 0
    return out


def halftone(m, pitch=4, angle=0.0, gain=1.0):
    """dot screen modulated by m (0..1)."""
    h, w = m.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    c, s = np.cos(angle), np.sin(angle)
    u, v = (x * c + y * s) / pitch, (-x * s + y * c) / pitch
    d = np.hypot(u - np.round(u), v - np.round(v))           # 0..0.707
    rad = np.sqrt(np.clip(m * gain, 0, 1)) * 0.55
    return np.clip((rad - d) * pitch * 1.5 + 0.5, 0, 1) * (m > 0.02)


def vstripes(h, w, pitch=3.0, depth=0.18, phase=0.0):
    x = np.arange(w, dtype=np.float32)
    s = 1 - depth * (0.5 + 0.5 * np.cos(2 * np.pi * (x / pitch + phase)))
    return np.broadcast_to(s[None, :], (h, w))


# ------------------------------------------------------------------ colour layers
def over(dst, col, a):
    """composite flat colour (3,) with alpha a (H,W) over dst (H,W,3) float 0..1."""
    a = np.clip(a, 0, 1)[..., None]
    return dst * (1 - a) + np.asarray(col, np.float32)[None, None] / 255 * a


def over_img(dst, src, a):
    a = np.clip(a, 0, 1)[..., None]
    return dst * (1 - a) + src * a


def screen(dst, src):
    return 1 - (1 - dst) * (1 - src)


def rgb_split(img, dx_r=3, dx_b=-3, dy=0):
    out = img.copy()
    out[..., 0] = np.roll(img[..., 0], (dy, dx_r), (0, 1))
    out[..., 2] = np.roll(img[..., 2], (-dy, dx_b), (0, 1))
    return out


def slices(img, seed, n=6, hmin=4, hmax=40, amp=40, region=None):
    """horizontal band displacement."""
    r = rng(seed)
    out = img.copy()
    h, w = img.shape[:2]
    y0, y1 = (0, h) if region is None else region
    for _ in range(n):
        bh = int(r.integers(hmin, hmax + 1))
        y = int(r.integers(y0, max(y0 + 1, y1 - bh)))
        dx = int(r.integers(-amp, amp + 1))
        out[y:y + bh] = np.roll(img[y:y + bh], dx, axis=1)
    return out


def grain(img, seed, amt=0.04, mono=True):
    r = rng(seed)
    n = r.normal(0, amt, img.shape[:2] + ((1,) if mono else (3,))).astype(np.float32)
    return np.clip(img + n, 0, 1)


def vignette(h=H, w=W, strength=0.55, power=2.2):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((x - w / 2) / (w / 2), (y - h / 2) / (h / 2)) / np.sqrt(2)
    return (1 - strength * np.clip(d, 0, 1) ** power)[..., None]


# ------------------------------------------------------------------ clips
class Clip:
    """decodes a clip at 30 fps into a 4:3 crop (zoom, centre), cached as uint8 array on demand."""

    def __init__(self, path, t0=0.0, dur=10.0, zoom=1.0, cx=0.5, cy=0.5, hflip=False, speed=1.0):
        self.path, self.t0, self.dur, self.zoom, self.cx, self.cy = str(path), t0, dur, zoom, cx, cy
        self.hflip, self.speed = hflip, speed
        self._frames = None

    def _load(self):
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", self.path], capture_output=True, text=True)
        sw, sh = map(int, p.stdout.strip().split(",")[:2])
        # crop to 4:3 then zoom
        if sw / sh > 4 / 3:
            ch, cw = sh, sh * 4 / 3
        else:
            cw, ch = sw, sw * 3 / 4
        cw, ch = cw / self.zoom, ch / self.zoom
        x0 = (sw - cw) * self.cx
        y0 = (sh - ch) * self.cy
        vf = (f"setpts=PTS/{self.speed},fps={FPS},crop={int(cw)}:{int(ch)}:{int(x0)}:{int(y0)},"
              f"scale={W}:{H}:flags=bicubic" + (",hflip" if self.hflip else ""))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(self.t0), "-i", self.path,
                              "-t", str(self.dur / self.speed + 0.5), "-vf", vf, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                             capture_output=True, check=True).stdout
        self._frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)

    def frame(self, i):
        if self._frames is None:
            self._load()
        i = int(np.clip(i, 0, len(self._frames) - 1))
        return self._frames[i].astype(np.float32) / 255


def grade(img, gain=1.0, gamma=1.0, lift=0.0, sat=1.0, tint=(1, 1, 1)):
    x = np.clip(img, 0, 1) ** gamma * gain + lift
    g = x.mean(-1, keepdims=True)
    x = g + (x - g) * sat
    return np.clip(x * np.asarray(tint, np.float32), 0, 1)


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


@lru_cache(maxsize=512)
def _boxed(text, w, h, weight, tracking, name):
    m, lp = text_mask(text, 200, weight, 1.0, tracking, name)
    sx, sy = w / m.shape[1], h / m.shape[0]
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((max(1, w), max(1, h)), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255, [(a * sx, b * sx) for a, b in lp]


def text_box(text, bbox, weight=700, tracking=0.0, name="oswald"):
    """text mask stretched to exactly fill bbox (x0, y0, x1, y1) on a full frame -> (frame mask, letter x-ranges)."""
    x0, y0, x1, y1 = [int(round(v)) for v in bbox]
    m, lp = _boxed(text, x1 - x0, y1 - y0, int(weight), float(tracking), name)
    out = np.zeros((H, W), np.float32)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if xb > xa and yb > ya:
        out[ya:yb, xa:xb] = m[ya - y0:yb - y0, xa - x0:xb - x0]
    return out, [(x0 + a, x0 + b) for a, b in lp]


def streaks(h, w, seed, amp=0.05, ylen=40, xsoft=0.6):
    """vertical streak field (1 + noise): random per column, slowly varying in y."""
    r = rng(seed)
    ny = max(2, h // ylen + 2)
    n = r.normal(0, 1, (ny, w)).astype(np.float32)
    if xsoft > 0:
        n = (n + xsoft * np.roll(n, 1, 1)) / (1 + xsoft)
    yi = np.linspace(0, ny - 1.001, h)
    i0 = yi.astype(int); f = (yi - i0)[:, None]
    n = n[i0] * (1 - f) + n[i0 + 1] * f
    return 1 + amp * n


def block_steps(m, seed, hmin=12, hmax=60, p=0.35, amax=3):
    """glyph edges stepped by tall horizontal bands shifted a few px (compression-block look)."""
    r = rng(seed)
    out = m.copy()
    y = 0
    h = m.shape[0]
    while y < h:
        b = int(r.integers(hmin, hmax + 1))
        if r.random() < p:
            out[y:y + b] = np.roll(m[y:y + b], int(r.integers(-amax, amax + 1)), axis=1)
        y += b
    return out


def macroblocks(img, seed, mask=None, bs=16, p=0.12, amax=6, src=None):
    """compression-style rectangular glitches: some grid blocks copy content shifted by a few px
    (or from `src`, e.g. the previous frame = datamosh)."""
    r = rng(seed)
    out = img.copy()
    h, w = img.shape[:2]
    S = img if src is None else src
    for by in range(0, h, bs):
        for bx in range(0, w, bs):
            if mask is not None and mask[by:by + bs, bx:bx + bs].max() < 0.2:
                continue
            if r.random() < p:
                bw = bs * int(r.integers(1, 4))        # runs of 1-3 blocks horizontally
                dx = int(r.integers(-amax, amax + 1)); dy = int(r.integers(-amax, amax + 1))
                ys, xs = slice(by, min(h, by + bs)), slice(bx, min(w, bx + bw))
                sy = np.clip(np.arange(ys.start, ys.stop) + dy, 0, h - 1)
                sx = np.clip(np.arange(xs.start, xs.stop) + dx, 0, w - 1)
                out[ys, xs] = S[sy][:, sx]
    return out


def jpeg(img, q=35, scale=1.0):
    import io
    im = Image.fromarray(to_u8(img))
    if scale != 1.0:
        im = im.resize((int(W * scale), int(H * scale)), Image.BILINEAR)
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); b.seek(0)
    im = Image.open(b).convert("RGB")
    if scale != 1.0:
        im = im.resize((W, H), Image.BILINEAR)
    return np.asarray(im, np.float32) / 255


def gblur(a, s):
    """exact separable gaussian blur, sigma s (works for fractional s)."""
    if s <= 0.05:
        return a
    r = max(1, int(np.ceil(3 * s)))
    x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-x * x / (2 * s * s)); k /= k.sum()
    out = a.astype(np.float32)
    for ax in (0, 1):
        pad = [(0, 0)] * out.ndim; pad[ax] = (r, r)
        p = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        n = out.shape[ax]
        for j, kj in enumerate(k):
            sl = [slice(None)] * out.ndim; sl[ax] = slice(j, j + n)
            acc += kj * p[tuple(sl)]
        out = acc
    return out
