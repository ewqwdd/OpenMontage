"""Effect operators for segment A (frames 0..234), measured in spec/segA.md."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

import kit

W, H = kit.W, kit.H
MARK_SOFT, MARK_K = 0.7, 1.5


def scale_about(a, s, cx, cy, sy=None):
    """scale a full-frame 2-D map by (s, sy) about (cx, cy)."""
    sy = s if sy is None else sy
    im = Image.fromarray(a.astype(np.float32), "F")
    # inverse affine: src = (dst - c)/s + c
    coef = (1 / s, 0, cx - cx / s, 0, 1 / sy, cy - cy / sy)
    return np.asarray(im.transform((W, H), Image.AFFINE, coef, Image.BILINEAR), np.float32)


@lru_cache(maxsize=4)
def cross_tile(pitch=6):
    """small grey ticks on an axis-aligned grid (pitch 6 px): random X, '/', '\\' or dot per cell,
    ~3 px big - the 'dot ghost' screen measured on frames 76-82 / 165-171."""
    r = kit.rng(4242)
    shapes = [
        np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], np.float32),          # X
        np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], np.float32),          # /
        np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.float32),          # \
        np.array([[0, 0, 0], [0, 1, 1], [0, 1, 0]], np.float32) * 0.8,    # blob
    ]
    ny, nx = H // pitch + 1, W // pitch + 1
    out = np.zeros((ny * pitch, nx * pitch), np.float32)
    pick = r.integers(0, 4, (ny, nx))
    amp = 0.6 + 0.4 * r.random((ny, nx))
    for j in range(ny):
        for i in range(nx):
            out[j * pitch + 1:j * pitch + 4, i * pitch + 1:i * pitch + 4] = shapes[pick[j, i]] * amp[j, i]
    return kit.blur(out[:H, :W], 0.35).clip(0, 1) * 1.25


def dot_ghost(img, glyph, seed, scale=1.2, sy=None, centre=(510, 357), grey=0.5, region=None, under=None):
    """grey X-dot copy of the text, scaled about `centre`, screened over the frame."""
    g = scale_about(glyph, scale, centre[0], centre[1], sy)
    g = np.clip(g, 0, 1)
    if region is not None:
        x0, x1 = region
        xx = np.arange(W)[None, :]
        g = g * ((xx >= x0) & (xx <= x1))
    t = cross_tile(6)
    r = kit.rng(seed)
    # dots flicker in brightness a bit
    jit = 0.75 + 0.5 * r.random((H // 6 + 2, W // 6 + 2)).astype(np.float32)
    jit = np.repeat(np.repeat(jit, 6, 0), 6, 1)[:H, :W]
    a = np.clip(g * 1.4, 0, 1) * np.clip(t, 0, 1) * grey * jit
    if under is not None:      # over the red text the dots are fainter (the red still reads)
        a = a * (1 - 0.55 * np.clip(under, 0, 1))
    col = np.array([0.80, 0.80, 0.84], np.float32)
    return np.clip(img * (1 - a[..., None]) + col * a[..., None], 0, 1)


def dotted_text(rgb, glyph, k=0.35):
    """red text under a dot ghost: darkened between the dots."""
    t = cross_tile(6)
    f = 1 - k * glyph * (1 - t)
    return rgb * f[..., None]


def stripes(period=12.8, phase=0.0, duty=0.5):
    y = np.arange(H, dtype=np.float32)
    s = ((y / period + phase) % 1.0) < duty
    return s.astype(np.float32)[:, None] * np.ones((1, W), np.float32)


def scan_ghost(img, glyph, seed, scale=1.2, sy=None, centre=(480, 350), dx=0, grey=0.45, smear=10, period=12.8):
    """grey horizontally smeared + striped copy of the text (interlace ghost), behind/over the frame."""
    g = scale_about(glyph, scale, centre[0], centre[1], sy) if scale != 1 or sy else glyph
    if dx:
        g = kit.shift(g, dx)
    g = kit.box_blur_h(np.clip(g, 0, 1), smear)
    r = kit.rng(seed)
    st = 0.35 + 0.65 * stripes(period, r.random())
    a = np.clip(g * 1.3, 0, 1) * st * grey
    col = np.array([0.72, 0.72, 0.75], np.float32)
    return img * (1 - a[..., None]) + col * a[..., None]


def row_shift(layer, y0, bands):
    """shift rows of a text layer: bands = [(dy_from_y0, height, dx), ...]."""
    rgb, a, g = layer
    rgb, a, g = rgb.copy(), a.copy(), g.copy()
    for dy, h, dx in bands:
        ya, yb = max(0, y0 + dy), min(H, y0 + dy + h)
        for arr in (rgb, a, g):
            arr[ya:yb] = np.roll(arr[ya:yb], int(dx), axis=1)
    return rgb, a, g


def dim(layer, k, blur=0.0):
    rgb, a, g = layer
    if blur:
        rgb = kit.blur(rgb, blur); a = kit.blur(a, blur); g = kit.blur(g, blur)
    return rgb * k, a, g


def scratch(img, pts, col, width=2, alpha=0.8, dashed=False, seed=0):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    if dashed:
        r = kit.rng(seed)
        # dash along the polyline
        P = np.array(pts, np.float32)
        seg = np.diff(P, axis=0)
        L = np.hypot(seg[:, 0], seg[:, 1])
        s = 0.0
        on = True
        tot = L.sum()
        while s < tot:
            ln = float(r.uniform(10, 20)) if on else float(r.uniform(4, 9))
            a0, a1 = s, min(tot, s + ln)
            if on:
                q = [_at(P, L, a0), _at(P, L, (a0 + a1) / 2), _at(P, L, a1)]
                d.line(q, fill=255, width=width)
            s = a1
            on = not on
    else:
        d.line(pts, fill=255, width=width)
    a = kit.blur(np.asarray(m, np.float32) / 255, 0.7) * alpha
    return kit.over(img, col, a)


def _at(P, L, s):
    c = np.cumsum(L)
    k = int(np.searchsorted(c, s))
    k = min(k, len(L) - 1)
    s0 = c[k] - L[k]
    f = (s - s0) / max(L[k], 1e-6)
    p = P[k] + (P[k + 1] - P[k]) * f
    return (float(p[0]), float(p[1]))


def dirt(img, seed, box, n=6, col=(8, 6, 8), alpha=0.7, rmax=10):
    """dark specks/blotches inside box."""
    r = kit.rng(seed)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    x0, y0, x1, y1 = box
    for _ in range(n):
        cx, cy = r.uniform(x0, x1), r.uniform(y0, y1)
        rx, ry = r.uniform(2, rmax), r.uniform(2, rmax * 1.6)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=int(255 * r.uniform(0.5, 1)))
    a = kit.blur(np.asarray(m, np.float32) / 255, 1.5) * alpha
    return kit.over(img, col, a)


def dither_patch(img, box, seed, grey=0.55):
    x0, y0, x1, y1 = box
    m = np.zeros((H, W), np.float32)
    m[y0:y1, x0:x1] = 1
    m = kit.blur(m, 12)
    t = cross_tile(6)
    a = m * t * grey
    return img * (1 - a[..., None]) + np.array([0.78, 0.86, 0.86], np.float32) * a[..., None]


def fade(img, k):
    return img * k


# ---------------------------------------------------------------- text layer (look2 variant with embolden)
import look2  # noqa: E402


def text_layer(text, bbox, col, seed, weight=700, kind="white", tracking=6.0, name="oswald",
               bold=1, streak=(0.08, 0.04), grain_h=0.03, grain_f=0.015, soft=0.2, steps=True,
               halo=None, red_ring=False, sharp=1.4, step_amax=1, step_p=0.5, bold_gain=1.0, glow=None, vwarp=None):
    """look2.text_layer + `bold` px dilation of the glyph (the reference stems are ~2-4 px fatter than Oswald
    Bold boxed into the same bbox), separate half-res / full-res grain."""
    m, _ = kit.text_box(text, bbox, weight, tracking, name)
    if vwarp is not None:
        m = baseline_warp(m, *vwarp)
    if bold:
        m = np.clip(kit.blur(kit.dilate(m, bold), 0.4 if bold_gain == 1.0 else 0.9) * bold_gain, 0, 1)
    h = look2.down(m)
    if steps:
        h = look2.band_steps(h, seed, amax=step_amax, p=step_p)
    h = kit.gblur(h, soft)
    if glow is not None:   # wide soft glow (white words, ref rings: ~0.63 at 3 px .. 0.15 at 20 px outside)
        hc, gs, ggain, ha = glow
        g = np.clip(kit.gblur(h, gs / 2) * ggain, 0, 1) * ha
    else:
        hc, hr, ha = halo or look2.HALO[kind]
        g = kit.blur(kit.dilate(h, max(1, int(hr / 2.5))), hr / 6)
        g = np.clip(g * 1.6, 0, 1) * ha
    if red_ring:
        g = g * (1 - 0.5 * h)
    r = kit.rng(seed + 1)
    x = np.arange(look2.HW, dtype=np.float32)
    phase = r.random() < 0.5
    st = 1 - streak[0] * (((x.astype(int) + phase) % 2))[None, :]
    st = st * kit.streaks(look2.HH, look2.HW, seed + 2, amp=streak[1], ylen=30, xsoft=0.0)
    gr = r.normal(0, grain_h, (look2.HH * 2, look2.HW)).astype(np.float32).reshape(look2.HH, 2, look2.HW).mean(1)
    fill = np.asarray(col, np.float32)[None, None] / 255 * (st * (1 + gr))[..., None]
    rgb = np.asarray(hc, np.float32)[None, None] / 255 * np.ones((look2.HH, look2.HW, 1), np.float32)
    rgb = rgb * (1 - h[..., None]) + fill * h[..., None]
    alpha = np.maximum(g, h)
    rgb_f, a_f, h_f = look2.up(np.clip(rgb, 0, 1)), np.clip(look2.up(alpha), 0, 1), np.clip(look2.up(h), 0, 1)
    if sharp:
        h_f = np.clip(h_f + sharp * (h_f - kit.blur(h_f, 2.0)), 0, 1)
        rgb_f = np.clip(rgb_f + sharp * (rgb_f - kit.blur(rgb_f, 2.0)), 0, 1)
    fg = kit.rng(seed + 3).normal(0, grain_f, (kit.H, kit.W)).astype(np.float32)
    rgb_f = np.clip(rgb_f * (1 + fg[..., None] * h_f[..., None]), 0, 1)
    return rgb_f, a_f, h_f


def baseline_warp(m, base_dst, bottom_dst):
    """Oswald's Д / У descenders are longer than the reference font's: move the baseline down to base_dst and
    squeeze the descender into [base_dst, bottom_dst] (ref: КОГДА body 467 / Д 494, ХОЛОДНО 524 / 565,
    ПУЗА У sits on the baseline)."""
    ink = m > 0.5
    cols = np.nonzero(ink.any(0))[0]
    bottoms = np.array([np.nonzero(ink[:, x])[0][-1] for x in cols])
    top = int(np.nonzero(ink.any(1))[0][0]); base_src = float(np.median(bottoms)); bot_src = float(bottoms.max())
    y = np.arange(H, dtype=np.float32)
    src = np.interp(y, [top, base_dst, bottom_dst], [top, base_src, bot_src])
    src[y < top] = y[y < top]
    i0 = np.clip(np.floor(src).astype(int), 0, H - 1); i1 = np.clip(i0 + 1, 0, H - 1); f = (src - np.floor(src))[:, None]
    out = m[i0] * (1 - f) + m[i1] * f
    out[y > bottom_dst + 1] = 0
    return out


def layer_echo(img, layer, scale=1.08, sy=None, centre=(480, 340), dx=0, k=0.5, period=8.0, depth=0.6, seed=0,
               tint=1.0):
    """double exposure: the whole text layer (fill + halo) scaled about centre and composited over again,
    its alpha striped horizontally (frames 100, 107-108)."""
    rgb, a, _ = layer
    sr = np.stack([scale_about(rgb[..., c], scale, centre[0], centre[1], sy) for c in range(3)], -1)
    sa = scale_about(a, scale, centre[0], centre[1], sy)
    if dx:
        sr = np.stack([kit.shift(sr[..., c], dx) for c in range(3)], -1); sa = kit.shift(sa, dx)
    st = 1 - depth * (1 - stripes(period, kit.rng(seed).random()))
    al = np.clip(sa * st * k, 0, 1)
    return img * (1 - al[..., None]) + sr * tint * al[..., None]


def smear_layer(layer, r, mix=0.65, vblur=0.0):
    """entry-frame horizontal motion smear of a text layer: mix of the sharp and the box-smeared layer."""
    rgb, a, g = layer
    sr = kit.box_blur_h(rgb, r); sa = kit.box_blur_h(a, r); sg = kit.box_blur_h(g, r)
    if vblur:
        sr = kit.blur(sr, vblur); sa = kit.blur(sa, vblur); sg = kit.blur(sg, vblur)
    return (rgb * (1 - mix) + sr * mix, a * (1 - mix) + sa * mix, g * (1 - mix) + sg * mix)


def small_text_layer(text, bbox, col, seed, weight=650, tracking=4.0, name="oswald", bold=1,
                     shadow=((8, 6, 10), 1.6, 0.85, (3, 4)), grain=0.02, sharp=0.8):
    """the small front line is crisp (full res, edge ~4 px) with a soft dark shadow, low grain."""
    m, _ = kit.text_box(text, bbox, weight, tracking, name)
    if bold:
        m = np.clip(kit.blur(kit.dilate(m, bold), 0.5) * 0.95, 0, 1)
    m = np.clip(m + sharp * (m - kit.blur(m, 1.5)), 0, 1)
    sc, sr, so, (sx, sy) = shadow
    sh = kit.shift(kit.blur(kit.dilate(m, 2), sr), sx, sy)
    sh = np.clip(sh * 1.4, 0, 1) * so
    n = kit.rng(seed).normal(0, grain, (kit.H, kit.W)).astype(np.float32)
    fill = np.asarray(col, np.float32)[None, None] / 255 * (1 + n[..., None])
    rgb = np.asarray(sc, np.float32)[None, None] / 255 * (1 - m[..., None]) + fill * m[..., None]
    a = np.maximum(sh, m)
    return np.clip(rgb, 0, 1), a, m


# ---------------------------------------------------------------- crisp dot ghost (post-codec), measured 76-82 / 165-171 / 190
@lru_cache(maxsize=2)
def crisp_dots(pitch=7, seed=777):
    """lattice of sharp ~5 px X / + / ring marks with a bright centre, one per 6 px cell (ref zoom f79-80)."""
    X = np.array([[1, 0, 0, 0, 1], [0, .8, 0, .8, 0], [0, 0, 1, 0, 0], [0, .8, 0, .8, 0], [1, 0, 0, 0, 1]], np.float32) * .8
    P = np.array([[0, 0, .7, 0, 0], [0, 0, .9, 0, 0], [.7, .9, 1, .9, .7], [0, 0, .9, 0, 0], [0, 0, .7, 0, 0]], np.float32)
    R = np.array([[0, .6, .8, .6, 0], [.6, .3, 0, .3, .6], [.8, 0, .4, 0, .8], [.6, .3, 0, .3, .6], [0, .6, .8, .6, 0]], np.float32)
    D = np.array([[0, 0, 0, 0, 0], [0, .5, .8, .5, 0], [0, .8, 1, .8, 0], [0, .5, .8, .5, 0], [0, 0, 0, 0, 0]], np.float32)
    shapes = [X, X, P, D]
    r = kit.rng(seed)
    ny, nx = H // pitch + 2, W // pitch + 2
    out = np.zeros((ny * pitch + 8, nx * pitch + 8), np.float32)
    pick = r.integers(0, 4, (ny, nx)); amp = 0.45 + 0.55 * r.random((ny, nx))
    for j in range(ny):
        o = (pitch // 2) * (j % 2)          # 45-degree lattice: every other row offset by half a pitch
        for i in range(nx):
            y, x = j * pitch, i * pitch + o
            out[y:y + 5, x:x + 5] = np.maximum(out[y:y + 5, x:x + 5], shapes[pick[j, i]] * amp[j, i])
    return out[:H, :W]


@lru_cache(maxsize=2)
def small_marks(pitch=6, seed=4243):
    """ref zoom f79-80 (8x): ~3 px grey ticks (X, /, \\, diamond) one per 6 px cell, black gaps, slightly soft."""
    r = kit.rng(seed)
    shapes = [
        np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], np.float32),
        np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], np.float32),
        np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.float32),
        np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.float32) * 0.85,
        np.array([[0, 0, 0], [0, 1, 1], [0, 1, 1]], np.float32) * 0.9,
    ]
    ny, nx = H // pitch + 2, W // pitch + 2
    out = np.zeros((ny * pitch, nx * pitch), np.float32)
    pick = r.integers(0, len(shapes), (ny, nx)); amp = 0.55 + 0.45 * r.random((ny, nx))
    for j in range(ny):
        for i in range(nx):
            y, x = j * pitch + 1 + int(r.integers(0, 2)), i * pitch + 1 + int(r.integers(0, 2))
            out[y:y + 3, x:x + 3] = shapes[pick[j, i]] * amp[j, i]
    return np.clip(kit.gblur(out[:H, :W], MARK_SOFT) * MARK_K, 0, 1)


def crisp_dot_ghost(img, glyph, seed, scale, sy, centre, region=None, under=None, gain=0.55, flick=0.45,
                    vis=None, tile="crisp"):
    g = scale_about(glyph, scale, centre[0], centre[1], sy) > 0.5
    if region is not None:
        xx = np.arange(W)[None, :]
        g = g & (xx >= region[0]) & (xx <= region[1])
    t = crisp_dots() if tile == "crisp" else small_marks()
    if vis is not None:       # measured visibility mask of the ghost (transparent in the middle, ref 76-82)
        g = g * vis
    r = kit.rng(seed)
    jit = 1 - flick + 2 * flick * r.random((H // 6 + 2, W // 6 + 2)).astype(np.float32)
    jit = np.repeat(np.repeat(jit, 6, 0), 6, 1)[:H, :W]
    a = g * t * jit * gain
    if under is not None:
        a = a * (1 - 0.5 * np.clip(under, 0, 1))
    a = np.clip(a, 0, 1)
    col = np.array([0.86, 0.86, 0.88], np.float32)
    return np.clip(img * (1 - a[..., None]) + col * a[..., None], 0, 1)


def stroke_mask(pts, width):
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).line(pts, fill=255, width=int(width), joint="curve")
    return np.asarray(im, np.float32) / 255


def checker(cell=3, phase=0):
    y, x = np.mgrid[0:H, 0:W]
    return (((x + phase) // cell + y // cell) % 2).astype(np.float32)


def checker_stroke(img, pts, width=14, col=(232, 232, 240), alpha=0.95, cell=3, soft=1.0):
    """bright diagonal film-burn stroke with a checker / dither texture (ref frame 28)."""
    m = kit.gblur(stroke_mask(pts, width), soft)
    t = 0.45 + 0.55 * checker(cell)
    return kit.over(img, col, np.clip(m * t * alpha, 0, 1))


def dither_rect(img, box, col=(20, 18, 34), alpha=0.55, edge_dither=10, seed=0):
    """translucent dark column over the text, its left edge broken into a checker dither."""
    x0, y0, x1, y1 = box
    m = np.zeros((H, W), np.float32); m[y0:y1, x0:x1] = 1
    xx = np.arange(W, dtype=np.float32)[None, :]
    ed = np.clip((xx - x0) / max(1, edge_dither), 0, 1)
    ch = checker(2)
    m = m * np.where(ed < 1, ch * (1 - ed) + ed, 1)
    return kit.over(img, col, kit.gblur(m, 0.6) * alpha)
