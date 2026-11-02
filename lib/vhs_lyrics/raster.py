"""Word rasteriser: each word becomes an RGBA PNG stretched into its measured box.

Edge treatments, pen lettering, baked scanlines, camo texture and RGB-glitch channel
splits all live here. Deterministic: every random field is seeded from the word index.
"""
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .styles import STYLES, color, font_path

SIZE = 400
SCAN_PERIOD = 8.0   # px before the lens (~9.4px after it, as on the reference)
SCAN_DEPTH = 0.14
PAD = 24

_fonts = {}


def font(style):
    if style not in _fonts:
        st = STYLES[style]
        f = ImageFont.truetype(str(font_path(st["font"])), SIZE)
        if st["var"]:
            f.set_variation_by_name(st["var"])
        _fonts[style] = f
    return _fonts[style]


def ink(text, style, dil=0):
    """L mask of a word on a big canvas + its ink bbox."""
    f = font(style)
    spacing = STYLES[style]["track"] * SIZE
    img = Image.new("L", (SIZE * (len(text) + 2), SIZE * 2), 0)
    d = ImageDraw.Draw(img)
    x = SIZE // 2
    for ch in text:
        d.text((x, SIZE // 2), ch, font=f, fill=255)
        x += f.getlength(ch) + spacing
    if dil:
        img = img.filter(ImageFilter.MaxFilter(dil))
    return img, img.getbbox()


# ------------------------------------------------------------------ pen lettering
# Bad Script with Latin look-alikes (Е->E, У->Y, П->n stretched to cap height), every glyph
# drawn twice with a small rotate/shift (second pen pass) + low-frequency contour jitter.
def _hand_parts():
    f = font("hand")
    cap_n = (lambda a, b: (a[3] - a[1]) / (b[3] - b[1]))(f.getbbox("Н"), f.getbbox("n"))
    return f, {"Е": ("E", 1.0), "У": ("Y", 1.0), "П": ("n", cap_n)}


def _glyph(f, sub, ch):
    rep = sub.get(ch)
    c = rep[0] if rep else ch
    asc, desc = f.getmetrics()
    pad = SIZE // 2
    w, h = int(f.getlength(c)) + 2 * pad, asc + desc + 2 * pad
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text((pad, pad), c, font=f, fill=255)
    base = pad + asc
    if rep and rep[1] != 1.0:
        im = im.resize((w, int(h * rep[1])), Image.LANCZOS)
        base = int(base * rep[1])
    return im, base, f.getlength(c), pad


def _retrace(im, rng, amp, rot=3.0, scale=0.04):
    w, h = im.size
    t = im.rotate(rng.uniform(-rot, rot), resample=Image.BICUBIC,
                  translate=(rng.uniform(-amp, amp), rng.uniform(-amp, amp)))
    s = 1 + rng.uniform(-scale, scale)
    t = t.resize((int(w * s), int(h * s)), Image.BICUBIC)
    out = Image.new("L", (w, h), 0)
    out.paste(t, ((w - t.width) // 2, (h - t.height) // 2))
    return ImageChops.lighter(im, out)


def _jitter(img, amp, cell, seed):
    a = np.asarray(img).astype(np.float32)
    h, w = a.shape
    rng = np.random.default_rng(seed)

    def field():
        n = rng.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
        return np.asarray(Image.fromarray(n).resize((w, h), Image.BICUBIC)) * amp

    dx, dy = field(), field()
    yy, xx = np.mgrid[0:h, 0:w]
    return Image.fromarray(a[np.clip((yy + dy).round().astype(int), 0, h - 1),
                             np.clip((xx + dx).round().astype(int), 0, w - 1)].astype(np.uint8))


def hand_mask(text, track_em=0.18, seed=1):
    f, sub = _hand_parts()
    rng = np.random.default_rng(seed)
    cap = f.getbbox("Н")
    cap = cap[3] - cap[1]
    track = track_em * SIZE
    parts = [_glyph(f, sub, c) for c in text]
    w = int(sum(p[2] for p in parts) + track * len(text) + SIZE * 2)
    h = max(p[0].height for p in parts) + 40
    b = max(p[1] for p in parts) + 20
    canvas = Image.new("L", (w, h), 0)
    x = SIZE * 0.5
    for im, base, adv, pad in parts:
        im = _retrace(im, rng, 0.05 * cap)
        canvas.paste(im, (int(x - pad), b - base), im)
        x += adv + track
    canvas = canvas.crop(canvas.getbbox())
    canvas = _jitter(canvas, 0.006 * cap, cell=40, seed=seed + 2)
    return canvas.crop(canvas.getbbox())


# ------------------------------------------------------------------ edges
def edges(mask, mode, amp, seed):
    """spiky  — outline true to the font + dense fringe of thin short hairs (30–45° lean);
    torn   — paper-tear outline, no hairs, ragged dark holes inside;
    wobble — smooth low-frequency brush wobble only."""
    if mode == "none" or amp <= 0:
        return mask
    rng = np.random.default_rng(seed)
    h, w = mask.shape

    def field(sigma):
        n = Image.fromarray((rng.random((h, w)) * 255).astype(np.uint8))
        n = np.asarray(n.filter(ImageFilter.GaussianBlur(sigma)), dtype=np.float32)
        return (n - n.mean()) / (n.std() + 1e-6)

    yy, xx = np.mgrid[0:h, 0:w]

    def displace(sig, k):
        dx, dy = field(sig) * k, field(sig) * k
        o = mask[np.clip((yy + dy).astype(int), 0, h - 1), np.clip((xx + dx).astype(int), 0, w - 1)]
        return np.where(o > 110, 255, 0).astype(np.uint8)

    if mode == "wobble":
        return displace(8, amp)
    if mode == "torn":
        out = displace(4, amp * 0.6)
        return np.where(field(6) > 2.1, 0, out).astype(np.uint8)

    out = displace(3, amp * 0.12)
    img = Image.fromarray(out)
    soft = np.asarray(img.filter(ImageFilter.GaussianBlur(3)), dtype=np.float32)
    gy, gx = np.gradient(soft)
    edge = (out > 0) & (np.asarray(img.filter(ImageFilter.MinFilter(3))) == 0)
    ys, xs = np.nonzero(edge)
    if len(ys):
        pick = rng.choice(len(ys), size=max(int(len(ys) * 0.07), 1), replace=False)
        d = ImageDraw.Draw(img)
        for k in pick:
            y, x = ys[k], xs[k]
            nx, ny = -gx[y, x], -gy[y, x]
            norm = (nx * nx + ny * ny) ** 0.5
            if norm < 1e-3:
                continue
            nx, ny = nx / norm, ny / norm
            long = rng.random() < 0.1
            ln = (rng.uniform(1.5, 2.5) if long else rng.uniform(0.3, 1.0)) * amp
            jit = rng.uniform(-1.0, 1.0)
            bw = rng.uniform(0.5, 1.3)
            if long:  # bent hair: two segments
                mx, my = x + (nx - ny * jit) * ln * .5, y + (ny + nx * jit) * ln * .5
                bend = jit + rng.uniform(-0.35, 0.35)
                tx, ty = mx + (nx - ny * bend) * ln * .5, my + (ny + nx * bend) * ln * .5
                d.polygon([(x - ny * bw, y + nx * bw), (x + ny * bw, y - nx * bw), (mx, my)], fill=255)
                d.line([(mx, my), (tx, ty)], fill=255, width=1)
            else:
                tx, ty = x + (nx - ny * jit) * ln, y + (ny + nx * jit) * ln
                d.polygon([(x - ny * bw, y + nx * bw), (x + ny * bw, y - nx * bw), (tx, ty)], fill=255)
    return np.asarray(img)


def _star(d, cx, cy, r, fill):
    pts = []
    for k in range(8):
        rr = r if k % 2 == 0 else r * 0.28
        a = k * np.pi / 4
        pts.append((cx + rr * np.sin(a), cy - rr * np.cos(a)))
    d.polygon(pts, fill=fill)


# ------------------------------------------------------------------ word -> PNG(s)
def raster_word(e, i, out_dir, w, h, remap_box):
    """e: normalised item (see timeline.py). Returns (png names, left, top, width, height) in px."""
    x0, x1, y0, y1 = remap_box(e["box"])
    bw, bh = (x1 - x0) / 100 * w, (y1 - y0) / 100 * h
    if e["style"] == "hand":
        mask = hand_mask(e["text"], e.get("track", 0.18), seed=i + 1)
        bb = (0, 0, mask.width, mask.height)
    else:
        mask, bb = ink(e["text"], e["style"], e.get("dil", 0))
    if e.get("yref"):  # partial state of a growing line: keep its scale, centre on its box
        _, fb = ink(e["yref"], e["style"])
        sx = bw / (fb[2] - fb[0])
        bb = (bb[0], fb[1], bb[2], fb[3])
        pw = (bb[2] - bb[0]) * sx
        cx = (x0 + x1) / 2 / 100 * w
        left, width = cx - pw / 2, pw
    else:
        left, width = x0 / 100 * w, bw
    crop = mask.crop(bb).resize((max(1, round(width)), max(1, round(bh))), Image.LANCZOS)
    st = STYLES[e["style"]]
    mode, amp = st["edge"], st["amp"]
    if e.get("amp") is not None:
        amp = e["amp"]
    elif mode == "spiky":  # smaller words get finer spikes
        amp = max(3, amp * min(1.0, bh / 260))
    m = Image.new("L", (crop.width + 2 * PAD, crop.height + 2 * PAD), 0)
    m.paste(crop, (PAD, PAD))
    a = edges(np.asarray(m), mode, amp, seed=i * 7 + 1)
    rgba = np.zeros((m.height, m.width, 4), np.float32)
    rgba[..., :3] = color(e["color"])
    top = y0 / 100 * h - PAD
    if e.get("fx") == "camo":  # mottled dark texture
        rng = np.random.default_rng(21)
        n = Image.fromarray((rng.random((m.height, m.width)) * 255).astype(np.uint8))
        bl = np.asarray(n.filter(ImageFilter.GaussianBlur(9)), np.float32)
        bl = (bl - bl.mean()) / (bl.std() + 1e-6)
        rgba[..., :3] *= (1 - 0.45 * np.clip(bl - 0.3, 0, 1.5) / 1.5)[..., None]
    yy = np.arange(m.height) + top  # scanlines phase-locked to the frame
    rgba[..., :3] *= (1 - SCAN_DEPTH * (0.5 + 0.5 * np.cos(2 * np.pi * yy / SCAN_PERIOD)))[:, None, None]
    rgba[..., 3] = a
    img = Image.fromarray(rgba.clip(0, 255).astype(np.uint8), "RGBA")
    if e.get("fx") == "camo":
        d = ImageDraw.Draw(img)
        rng = np.random.default_rng(5)
        for _ in range(10):
            _star(d, rng.uniform(PAD, img.width - PAD), rng.uniform(img.height * .4, img.height * .8),
                  rng.uniform(8, 12), (150, 15, 20, 255))
    names = []
    if e.get("fx") == "glitch":  # pure R / G / B copies, screened together with offsets
        arr = np.asarray(img).copy()
        for ch in range(3):
            c = arr.copy()
            for k in range(3):
                if k != ch:
                    c[..., k] = 0
            nm = f"w{i:02d}_{'rgb'[ch]}.png"
            Image.fromarray(c, "RGBA").save(out_dir / nm)
            names.append(nm)
    else:
        nm = f"w{i:02d}.png"
        img.save(out_dir / nm)
        names.append(nm)
    return names, left - PAD, top, img.width, img.height
