"""Text: thin Cormorant Garamond with a lavender glow, a split chroma and a dirty scanline tear.

Intro text (lowercase, one centred line that grows word by word):
- Font and size: wght 430, x-height 35 px@480. The ink width is squeezed so that the calibration
  line LOWER_REF measures 527 px@480.
- Core: near-white (244,246,255).
- Glow: 3 gaussians r = 3/8/20 px@480.
- Chroma: R +2.35 / B -2.10 px@480 on the text layer only, with low-res chroma (Cb/Cr at 1/6.75)
  like a 480p yuv420 capture.
- Tear: ONE fixed per-scanline displacement profile D(y) times a signed per-frame amplitude a(f).
  It comes from the texture `tear.amp` and is scaled by look.text.tear_scale. There is also a
  bell-shaped baseline tear band at rows ~250-253 (`tear.band`, px@480, negative = left). Both apply
  to the finished text layer, never to the background.
- Onset dim: the line dims to look.text.onset_dim on the frame before a new word and on the onset.

Drop text (CAPS, per-frame position from the glitch schedule, motion smears by text tokens):
- Font: wght 560, cap height about 58 px@480, dim lavender (196,210,232).
- Red accent: crimson (205,30,62), 1.28x wider and 1.27x taller.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .util import FONT, H, S, W, hblur, mask_blur, place, vblur

# ---------------------------------------------------------------- intro text
LOWER_XH, LOWER_REF = 35.0, ("на улице хочется сдохнуть", 527.0)
CAPS_CH, CAPS_REF = 55.0, ("ЕСЛИ ПРЯМО СЕЙЧАС", 530.0)
RED_CH, RED_REF, RED_WGHT = 85.0, ("МАРШРУТКА", 390.0), 700

STYLE = {
    "lower": dict(core=(244, 246, 255), op=1.0, core_blur=0.90, core_gain=1.25, chroma_div=6.75,
                  glows=[((44, 42, 112), 3.0), ((106, 106, 210), 8.0), ((210, 210, 330), 20.0)],
                  ca_r=2.35, ca_b=-2.10),
}

# fixed scanline displacement profile D(y), px@480 at amplitude 1 (rows 218..257 measured, the rest
# synthetic runs with the same statistics)
D_MEAS_Y0 = 218
D_MEAS = [1.55, 1.61, 1.54, 2.14, 2.32, 1.60, 0.33, 0.10, 0.48, 1.14, 3.00, 2.06, -0.77, -1.08, -0.02,
          -0.35, -1.68, -2.41, -1.80, -1.55, -2.37, -2.76, -0.14, 0.50, 1.04, 0.98, -0.34, -0.00, 0.94,
          0.59, -1.31, -1.70, -1.51, -1.18, 0.12, 1.57, 0.34, -2.16, -2.26, 0.04]
BAND_PROFILE = ([248.3, 249.3, 250.3, 251.3, 252.3, 253.3, 254.3, 255.3],
                [0.0, 0.22, 0.78, 1.0, 0.95, 0.38, 0.06, 0.0])


def _build_D480():
    rng = np.random.default_rng(2446)
    D = np.zeros(480, np.float32)
    y = 0
    while y < 480:
        n = int(rng.integers(2, 6))
        D[y:y + n] = float(np.clip(rng.normal(0, 1.5), -3.2, 3.2))
        y += n
    D = np.convolve(np.pad(D, 1, mode="edge"), [0.15, 0.7, 0.15], "valid").astype(np.float32)
    D[D_MEAS_Y0:D_MEAS_Y0 + len(D_MEAS)] = np.array(D_MEAS, np.float32)
    return D


D480 = _build_D480()


def _font(size, wght):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([wght])
    return f


class IntroText:
    def __init__(self, look, tex):
        t = look["text"]
        self.wght = t["weight"]
        self.style = dict(STYLE["lower"], **t.get("style", {}))
        self.tear_scale, self.onset_dim_v = t["tear_scale"], t["onset_dim"]
        self.tear = tex["tear"] if t["tear"] else dict(amp={}, band={}, band_s={})
        self.period = tex["period"]
        self._cal = None
        self._cache = {}

    def mask(self, txt):
        """-> (mask, anchor_x = ink centre, anchor_y = x-height centre)"""
        if txt in self._cache:
            return self._cache[txt]
        if self._cal is None:
            f = _font(400, self.wght)
            b = f.getbbox("x")
            size = int(round(400 * LOWER_XH * S / (b[3] - b[1])))
            fs = _font(size, self.wght)
            bb = fs.getbbox(LOWER_REF[0])
            self._cal = (fs, LOWER_REF[1] * S / (bb[2] - bb[0]), size)
        f, sx, size = self._cal
        pad = int(size * 0.25)
        im = Image.new("L", (int(f.getlength(txt)) + 2 * pad, int(size * 1.7)), 0)
        ImageDraw.Draw(im).text((pad, pad), txt, font=f, fill=255)
        nw = max(1, int(round(im.width * sx)))
        m = np.asarray(im.resize((nw, im.height), Image.LANCZOS)).astype(np.float32) / 255
        cols = np.where(m.max(0) > 0.5)[0]
        ax = (cols[0] + cols[-1] + 1) / 2 if len(cols) else nw / 2
        b = f.getbbox("x")
        self._cache[txt] = (m, ax, pad + (b[1] + b[3]) / 2)
        return self._cache[txt]

    def onset_dim(self, f, onsets):
        if f in onsets and f != 0:
            return self.onset_dim_v[1]
        if (f + 1) in onsets:
            return self.onset_dim_v[0]
        return 1.0

    def displacement_rows(self, f):
        k = str(f % self.period)
        a = self.tear["amp"].get(k, 0.0) * self.tear_scale
        y480 = (np.arange(H) + 0.5) / S
        d = np.zeros(H, np.float32)
        if a:
            d += a * D480[np.clip(y480.astype(int), 0, 479)] * S
        b = self.tear["band"].get(k)
        if b:
            d += np.interp(y480, BAND_PROFILE[0], BAND_PROFILE[1]).astype(np.float32) * b * S
        if k in self.tear["band_s"]:
            l, r = self.tear["band_s"][k]
            d += np.where((y480 >= 250) & (y480 < 253), l * S, 0) + np.where((y480 >= 254) & (y480 < 257), r * S, 0)
        return d

    def compose(self, bg, m, f, opacity=1.0):
        """bg HxWx3, m placed text mask -> composited frame."""
        p = self.style
        out = bg.astype(np.float32).copy()
        ys, xs = np.where(m > 0.02)
        if len(ys) == 0:
            return out
        glows = p["glows"]
        d = self.displacement_rows(f)
        mg = int(max(r for _, r in glows) * S * 3.0) + 12 + int(np.abs(d).max())
        y0, y1 = max(0, ys.min() - mg), min(H, ys.max() + mg + 1)
        x0, x1 = max(0, xs.min() - mg), min(W, xs.max() + mg + 1)
        mm = m[y0:y1, x0:x1].astype(np.float32)
        a = gauss(mm, p["core_blur"] * S)
        a = np.clip(a * p["core_gain"], 0, 1) * p["op"] * opacity
        gl = np.zeros(mm.shape + (3,), np.float32)
        for col, r in glows:
            gl += gauss(mm, r * S)[..., None] * np.array(col, np.float32)[None, None]
        gl *= opacity
        dd = d[y0:y1]
        if np.any(dd):
            a = row_shift(a, dd + 0.0)
            gl = row_shift(gl, dd + 0.0)
        core = np.array(p["core"], np.float32)
        sub = out[y0:y1, x0:x1]
        for c, dx in ((0, p["ca_r"] * S), (1, 0.0), (2, p["ca_b"] * S)):
            ac = frac_shift(a, dx)
            gcn = frac_shift(gl[..., c], dx)
            sub[..., c] = sub[..., c] * (1 - ac) + ac * core[c] + gcn
        sub = chroma420(np.clip(sub, 0, 255), p["chroma_div"])
        out[y0:y1, x0:x1] = sub
        return np.clip(out, 0, 255)


def row_shift(a, dx_rows):
    """shift each row y of a by dx_rows[y] px (linear interpolation, zero outside)."""
    h, w = a.shape[:2]
    xs = np.arange(w, dtype=np.float32)[None, :] - dx_rows[:, None]
    x0 = np.floor(xs)
    t = (xs - x0).astype(np.float32)
    x0 = x0.astype(np.int64)
    i0, i1 = np.clip(x0, 0, w - 1), np.clip(x0 + 1, 0, w - 1)
    v0 = (x0 >= 0) & (x0 < w)
    v1 = (x0 + 1 >= 0) & (x0 + 1 < w)
    if a.ndim == 2:
        return (np.take_along_axis(a, i0, 1) * (1 - t) * v0 + np.take_along_axis(a, i1, 1) * t * v1).astype(np.float32)
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        out[..., c] = np.take_along_axis(a[..., c], i0, 1) * (1 - t) * v0 + np.take_along_axis(a[..., c], i1, 1) * t * v1
    return out


def gauss(a, sig):
    """float separable gaussian (no 8-bit quantisation); sigma > 6 is done at 1/4 resolution."""
    if sig <= 0:
        return a
    if sig > 6:
        h, w = a.shape
        sm = np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w // 4, h // 4), Image.BILINEAR))
        sm = gauss(sm, sig / 4)
        return np.asarray(Image.fromarray(sm, "F").resize((w, h), Image.BILINEAR)).astype(np.float32)
    r = max(1, int(np.ceil(sig * 3)))
    x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-0.5 * (x / sig) ** 2)
    k = k / k.sum()
    p = np.pad(a, ((0, 0), (r, r)), mode="constant")
    o = np.zeros_like(a)
    for i, kv in enumerate(k):
        o += kv * p[:, i:i + a.shape[1]]
    p = np.pad(o, ((r, r), (0, 0)), mode="constant")
    o2 = np.zeros_like(a)
    for i, kv in enumerate(k):
        o2 += kv * p[i:i + a.shape[0]]
    return o2


def frac_shift(a, dx):
    if dx == 0:
        return a
    i = int(np.floor(dx))
    t = dx - i

    def sh(x, n):
        o = np.zeros_like(x)
        if n > 0:
            o[:, n:] = x[:, :-n]
        elif n < 0:
            o[:, :n] = x[:, -n:]
        else:
            o[:] = x
        return o
    return sh(a, i) * (1 - t) + sh(a, i + 1) * t


def chroma420(img, div):
    h, w = img.shape[:2]
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb, cr = b - y, r - y
    sw, sh = max(1, int(round(w / div))), max(1, int(round(h / div)))

    def lp(c):
        sm = Image.fromarray(c.astype(np.float32), "F").resize((sw, sh), Image.BOX)
        return np.asarray(sm.resize((w, h), Image.BILINEAR)).astype(np.float32)
    cb, cr = lp(cb), lp(cr)
    r2, b2 = y + cr, y + cb
    g2 = (y - 0.299 * r2 - 0.114 * b2) / 0.587
    return np.stack([r2, g2, b2], -1)


# ---------------------------------------------------------------- drop text
TEXT_CORE, TEXT_GLOW = (196, 210, 232), (70, 80, 150)
RED_CORE, RED_GLOW = (205, 30, 62), (110, 10, 40)


class DropText:
    def __init__(self, look):
        t = look["drop_text"]
        self.wght, self.sx, self.sy = t["weight"], t["sx"], t["sy"]
        self.core, self.glow = tuple(t["core"]), tuple(t["glow"])
        self.red_core, self.red_glow = tuple(t["red_core"]), tuple(t["red_glow"])
        self.red_scale = t["red_scale"]
        self._cache = {}

    def mask(self, txt, red=False):
        key = (txt, red)
        if key in self._cache:
            return self._cache[key]
        size = 200
        fc = _font(size, 700)
        b = fc.getbbox("Н")
        capr = (40 * S) / (b[3] - b[1])
        xr = (520 * S) / (fc.getlength("ЕСЛИ ПРЯМО СЕЙЧАС") * capr)
        fw = _font(size, self.wght)
        im = Image.new("L", (int(fw.getlength(txt) + 40), int(size * 1.6)), 0)
        ImageDraw.Draw(im).text((20, int(size * 0.2)), txt, font=fw, fill=255)
        scale_x = (fc.getlength(txt) * capr * xr / max(1, fw.getlength(txt))) * self.sx
        scale_y = capr * self.sy
        if red:
            scale_x *= self.red_scale[0]
            scale_y *= self.red_scale[1]
        nw, nh = max(1, int(im.width * scale_x)), max(1, int(im.height * scale_y))
        m = np.asarray(im.resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255
        ys, xs = np.where(m > 0.3)
        if not len(xs):                                   # empty line (drop starts before its first word)
            self._cache[key] = (m, m.shape[1] / 2, m.shape[0] / 2)
            return self._cache[key]
        self._cache[key] = (m, (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)
        return self._cache[key]

    def canvas(self, step, txt, red, ctx):
        """text alpha canvas for one schedule step: position, smears, ghost of the previous position."""
        o = dict(tv=0, th=0, td=0, tg=0, ta=1.0, tslice=False)
        for n, a in step.tx:
            o[n] = a[0] if a else True
        m, ax, ay = self.mask(txt, red)
        cx, cy = step.pos
        can = place(m, ax, ay, cx * S, cy * S)
        if o["tslice"]:
            rng = np.random.default_rng(step.seed * 7 + 1)
            y = int(cy * S - 30 * S)
            while y < cy * S + 30 * S:
                h = int(rng.integers(5, 14) * S)
                can[y:y + h] = np.roll(can[y:y + h], int(rng.integers(-24, 24) * S), axis=1)
                y += h
        if o["tv"]:
            can = vblur(can, o["tv"] * S / 2) * 0.7 + can * 0.3
        if o["th"]:
            can = hblur(can, o["th"] * S / 2) * 0.7 + can * 0.3
        if o["td"]:
            n, acc, L = 6, np.zeros_like(can), o["td"] * S
            for i in range(n):
                t = i / (n - 1) - 0.5
                acc += np.roll(np.roll(can, int(t * L * 0.6), 1), int(-t * L), 0)
            can = acc / n * 0.75 + can * 0.25
        if o["tg"] and ctx.get("tprev") is not None:
            px, py = ctx["tprev"]
            g = hblur(place(m, ax, ay, px * S, py * S), 4 * S)
            can = np.maximum(can, g * o["tg"])
        ctx["tprev"] = (cx, cy)
        return np.clip(can * o["ta"], 0, 1)

    def compose(self, bg, can, red=False):
        m = mask_blur(can, 1.2 * S)
        core = np.array(self.red_core if red else self.core, np.float32)
        glow = np.array(self.red_glow if red else self.glow, np.float32)
        out = bg + (mask_blur(m, 6 * S) * 0.9)[..., None] * glow * 0.6
        r = np.roll(m, int(2 * S), 1)
        b = np.roll(m, -int(1.6 * S), 1)
        a = np.stack([np.maximum(m * 0.7, r), m, np.maximum(m * 0.7, b)], -1)
        out = out * (1 - a * 0.85) + a * core
        return np.clip(out, 0, 255)
