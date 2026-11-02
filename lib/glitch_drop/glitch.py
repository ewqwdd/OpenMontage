"""Drop glitch section: the operators and a data-driven schedule engine.

A drop schedule is a list of Steps, one per frame from the drop onward. A Step is one line of the
pattern language:

    <seed>: <frame fx tokens> | <text tokens> | tone=r,g,b,top,mid,bottom pos=x,y

- `seed` is the random seed of the step's operators (in the reference pattern it is the source
  frame number). Re-using a slice keeps its exact look.
- `tone` is the reference luma for this step, and it is optional. Global mean RGB plus mean luma of
  the top/mid/bottom thirds; the result is pulled 85 % toward it. Without it there is no tone match.
- `pos` is the text centre in px@480. The default is 320,228.
Tokens are `name` or `name=a,b,c`. Numbers are px@480 unless noted. Colours are W (white), C (cyan),
R (red), K (dark overlay for inverted frames) or r,g,b.

Frame fx tokens run in order on the composited frame (background + text):

    inv                       invert the frame
    expo=g                    over-expose: x*g + 18*(g-1)
    botw=y,feather            content-following blow-out to white from row y down (feather 1 = 70 px, 0 = 30 px)
    hs=r                      horizontal box smear r px (85 % smear + 15 % sharp)
    vs=r,y0,y1                vertical smear r px of rows y0..y1
    soft=k                    downsample by k and back up
    wash=a,b                  linear wash x*a + b (grey flash)
    tint=r,g,b                per-channel gain
    teal / teal2              teal luma recolour (full / 45 %)
    cyaninv                   inverted + exposed cyan-white frame
    palecyan=y                inverted blown pale cyan with a teal band above row y
    whitetop=y                lamp band on top, white from row y down
    black                     near-black olive frame
    flash=col,a               blend toward a colour by a
    fill=r,g,b                solid frame (white strobe)
    mosh=y0,y1,dens           macroblock datamosh in rows y0..y1, dens = covered fraction (uses the previous frame)
    box                       top-left frozen/posterised box with a light border (cyan if cyaninv is in the step)
    lowblk / lowblk2          displaced rectangles in the lower half + smear lines (strong / weak)
    ht=y0,y1,col,mode         halftone field in rows y0..y1, mode holes (dark dots) | stripes (vertical beads)
    dust=y0,y1,col,n|grid     n grid-snapped specks in rows y0..y1, or the full 21x16 grid
    row=y,col                 one row of dashes at y
    barA=y0,y1,col            solid bar y0..y1 with a scalloped top edge, dark below
    barB=y,col                thin line at y and a row of dash teeth below it
    hl=col                    thin partial-width lines + slice tears around the text row
    line=y,col                2-px line at y
    iri=s                     oil-slick rainbow on the highlights, strength s
    tre_=a,r,g,b / tre=...    text showing through a wash: the text mask blended in colour r,g,b by a
                              (tre_ runs before the tone match, tre after it)

The tone match then runs if `tone` is given and the step has no `fill`. After it come `tre`, and the
JPEG dirt (q=38, 720x540) unless the step has `fill`.

Text tokens act on the text alpha before compositing:

    tv=r  th=r                vertical / horizontal motion smear (r/2 px box, 70 % + 30 % sharp)
    td=r                      diagonal smear of length r
    tg=a                      ghost of the previous step's text position, opacity a
    ta=a                      text opacity
    tslice                    horizontal slice displacement of the text rows
"""
import re
from dataclasses import dataclass, field, replace

import numpy as np
from PIL import Image, ImageFilter

from .util import ASSETS, H, S, W, Y, hblur, img_blur, jpeg_dirt, lum, mask_blur, resample_soft, vblur

COL = {
    "W": (240, 240, 245),
    "C": (30, 208, 245),
    "R": (232, 62, 36),
    "K": (40, 52, 50),
}
DEFAULT_POS = (320.0, 228.0)


def colv(c):
    if isinstance(c, str):
        return np.array(COL[c], np.float32)
    return np.array(c, np.float32)


# ================================================================ operators (f = the step's seed)
# ---------------------------------------------------------------- glitch operators
def op_expo(img, g):
    return np.clip(img * g + 18 * (g - 1), 0, 255)

def op_botw(img, y0, feather=1):
    """blown-out white from about row y0 (480p) downward; the edge follows the image content
    (bright areas blow first) like an over-cranked exposure, smeared along x"""
    l = mask_blur(lum(img) / 255, 6 * S)
    ramp = (np.arange(H)[:, None] - Y(y0)) / (Y(70) if feather else Y(30))
    t = np.clip(ramp + (l - 0.35) * 1.6, 0, 1)
    t = hblur(t * t * (3 - 2 * t), 24 * S)[..., None]
    return img * (1 - t) + 253 * t

def op_vsmear(img, r, y0, y1):
    a, b = Y(y0), Y(y1)
    img = img.copy()
    img[a:b] = vblur(img[a:b], r * S) * 0.85 + img[a:b] * 0.15
    return img

def _grid_masks(region_h, px=21, py=16, rx=5.2, ry=5.6, gw=4.2, ox=0, oy=0):
    yy, xx = np.mgrid[0:region_h, 0:W].astype(np.float32)
    PX, PY = px * S, py * S
    fx = ((xx - ox) % PX) - PX / 2; fy = ((yy - oy) % PY) - PY / 2
    hole = np.clip(1.6 - np.sqrt((fx / (rx * S)) ** 2 + (fy / (ry * S)) ** 2) * 1.6, 0, 1)   # soft dots
    gap = np.clip(1 - np.abs(np.abs(fx) - PX / 2) / (gw * S), 0, 1)                         # column gaps
    return hole, gap

def op_halftone(img, y0, y1, col, mode, f):
    """ref 522: bright field, dark holes on a 21x16 px grid;  503/533/593: bright vertical stripes with
    dark gaps and beads.  brightness follows the (blurred) image luminance."""
    a, b = Y(y0), Y(y1)
    reg = img[a:b]
    l = mask_blur(lum(reg) / 255, 5 * S)
    hole, gap = _grid_masks(b - a, oy=(f * 3) % 7)
    c = colv(col)
    if mode == 'holes':
        v = 0.8 + 0.2 * np.clip(l * 2.2, 0, 1)
        hole, gap = _grid_masks(b - a, rx=7.0, ry=6.2, oy=(f * 3) % 7)
        hole2 = np.clip(hole * 1.8, 0, 1)
        gapw = np.clip((np.abs(((np.arange(W) % Y(21)) - Y(10.5))) < Y(3.2))[None, :] * 1.0, 0, 1)
        pat = v * (1 - 0.92 * hole2) * (1 - 0.55 * np.maximum(gap, gapw))
        dark = np.array([30, 32, 40], np.float32) if col != 'C' else np.array([20, 50, 70], np.float32)
    else:
        v = 0.45 + 0.55 * np.clip(l * 2.0, 0, 1)
        gap2 = np.clip(gap * 1.0 + (np.abs(((np.arange(W) % Y(21)) - Y(10.5))) > Y(5.5))[None, :] * 0.9, 0, 1)
        pat = v * (1 - 0.9 * gap2) * (1 - 0.35 * hole)
        dark = np.array([20, 20, 22], np.float32) if col != 'C' else np.array([70, 80, 120], np.float32)
        if col == 'K':      # inverted frame: dark stripes on light, light beads
            c = np.array([235, 232, 226], np.float32); dark = np.array([15, 22, 18], np.float32)
    pat = mask_blur(np.clip(pat, 0, 1), 1.0 * S)
    pat = vblur(pat, 2 * S)
    out = img.copy()
    out[a:b] = dark + pat[..., None] * (c - dark)
    return out

def op_dust(img, y0, y1, col, dens, f):
    """specks (4-7 x 3-4 px @480) snapped to the 21-px grid columns, like the ref p7/p26 frames"""
    rng = np.random.default_rng(f * 13 + int(y0))
    out = img.copy(); c = colv(col)
    a, b = Y(y0), Y(y1)
    if dens == 'grid':
        for yy in np.arange(a + Y(4), b, Y(16)):
            for xx in np.arange(Y(8), W, Y(21)):
                if rng.random() < 0.36:
                    w = int(rng.integers(4, 10) * S); h = int(rng.integers(3, 5) * S)
                    xj = int(xx + rng.integers(-3, 4) * S)
                    out[int(yy):int(yy) + h, xj:xj + w] = c * 0.9 + out[int(yy):int(yy) + h, xj:xj + w] * 0.1
        return out
    n = int(dens)
    for _ in range(n):
        xx = int(rng.integers(0, W // Y(21)) * Y(21) + rng.integers(-4, 5) * S)
        yy = int(rng.integers(a, max(a + 1, b)))
        w = int(rng.integers(3, 8) * S); h = int(rng.integers(2, 5) * S)
        out[yy:yy + h, max(0, xx):xx + w] = c
    return out

def op_row(img, y, col, f):
    """single row of dashes (503/533/593 at y~425)"""
    rng = np.random.default_rng(f * 17)
    out = img.copy(); c = colv(col); yy = Y(y)
    for xx in range(Y(8), Y(440), Y(21)):
        if rng.random() < 0.55:
            w = int(rng.integers(4, 16) * S); h = int(rng.integers(2, 4) * S)
            out[yy:yy + h, xx:xx + w] = c
    return out

def op_barA(img, y0, y1, col, f):
    """p9 bar: solid band 211-240 px@480 with scalloped top edge, dark below, thin lines"""
    a, b = Y(y0), Y(y1)
    out = img.copy()
    band = np.s_[max(0, a - Y(60)):min(H, b + Y(60))]
    out[band] = hblur(out[band], 14 * S)
    c = colv(col)
    out[b:b + Y(40)] *= 0.35
    for yy in (b + Y(13), b + Y(27)):
        x0 = int(np.random.default_rng(f + yy).integers(0, W // 4)); x1 = W - int(np.random.default_rng(f + 2 * yy).integers(0, W // 3))
        out[yy:yy + Y(1.5), x0:x1] = out[yy:yy + Y(1.5), x0:x1] * 0.3 + 0.7 * np.array([150, 150, 160], np.float32)
    yy, xx = np.mgrid[a - Y(8):b, 0:W].astype(np.float32)
    teeth = ((xx % Y(16)) - Y(8)) ** 2 + ((yy - (a + Y(2))) * 1.3) ** 2 < Y(4.5) ** 2
    solid = (yy >= a + Y(4))
    msk = mask_blur((teeth | solid).astype(np.float32), 0.8 * S)
    sl = np.s_[a - Y(8):b]
    out[sl] = out[sl] * (1 - msk[..., None]) + c * msk[..., None]
    return np.clip(out, 0, 255)

def op_barB(img, y, col, f):
    """p28 bar: thin line at y then a row of dash-teeth below (523/553/583: rows 240-265)"""
    a = Y(y); out = img.copy(); c = colv(col)
    band = np.s_[max(0, a - Y(40)):min(H, a + Y(50))]
    out[band] = hblur(out[band], 10 * S)
    out[a + Y(24):a + Y(70)] *= 0.35
    out[a:a + Y(5)] = c
    yy, xx = np.mgrid[a + Y(7):a + Y(22), 0:W].astype(np.float32)
    teeth = (((xx % Y(16)) < Y(11)) & (np.abs(yy - (a + Y(14))) < Y(5))).astype(np.float32)
    teeth = mask_blur(teeth, 1.2 * S) * 0.9
    sl = np.s_[a + Y(7):a + Y(22)]
    out[sl] = out[sl] * (1 - teeth[..., None]) + c * teeth[..., None]
    return np.clip(out, 0, 255)

def op_hlines(img, col, f, cy):
    """thin partial-width lines crossing the text band + horizontal slice tears (505/535/595/655)"""
    rng = np.random.default_rng(f * 5 + 3)
    out = img.copy(); c = colv(col)
    for _ in range(3):
        y = Y(cy - 28 + rng.integers(0, 56)); h = int(rng.integers(5, 16) * S)
        out[y:y + h] = np.roll(out[y:y + h], int(rng.integers(-12, 12) * S), axis=1)
    ln = np.zeros((H, W), np.float32)
    for _ in range(4):
        y = Y(cy - 20 + rng.integers(0, 52)); x0 = int(rng.integers(0, W // 3)); x1 = int(rng.integers(W // 2, W))
        ln[y:y + Y(1.4), x0:x1] = rng.uniform(0.35, 0.7)
    ln = mask_blur(ln, 0.8 * S)[..., None]
    return out * (1 - ln) + c * ln

def op_line(img, y, col):
    out = img.copy(); out[Y(y):Y(y) + Y(2)] = out[Y(y):Y(y) + Y(2)] * 0.3 + colv(col) * 0.7
    return out

def _hsv2rgb(h, s, v):
    i = np.floor(h * 6).astype(int) % 6; fr = h * 6 - np.floor(h * 6)
    p = v * (1 - s); q = v * (1 - fr * s); t = v * (1 - (1 - fr) * s)
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)

def op_iri(img, s, f):
    """oil-slick rainbow on the glare (506/509/599/687): hue cycles slowly with luminance and x,
    spread over the whole highlight area, smeared"""
    l = img_blur(lum(img), 10 * S)
    small = l[::8, ::8]
    hue = (small / 255 * 1.6 + np.arange(small.shape[1])[None, :] / small.shape[1] * 0.8 + f * 0.13) % 1
    rb = _hsv2rgb(hue, 0.6, 1.0) * 255
    rb = np.asarray(Image.fromarray(rb.astype(np.uint8)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4 * S))).astype(np.float32)
    w = (np.clip((l - 95) / 70, 0, 1) * (1 - np.clip((l - 242) / 12, 0, 1)))[..., None] * min(1, 0.7 * s)
    tgt = rb * (np.maximum(l, 140)[..., None] / 255)
    return img * (1 - w) + tgt * w

def op_mosh(img, y0, y1, dens, f, ctx=None):
    """macroblock datamosh (510/513/540/570/600/660/690): rectangles snapped to an 8-px (480p) grid,
    8-64 px wide, 16-96 px tall, filled with the vertical pixel-stretch of their top row (the ref's
    columns of vertical streaks), stale copies of the previous frame (same polarity only),
    sideways copies and smoothed flat blocks.  dens = fraction of the region covered."""
    rng = np.random.default_rng(f * 31 + 5)
    g = Y(8)
    prev = ctx.get('prev') if ctx else None
    if prev is not None and ctx.get('prev_mean') is not None and abs(ctx['prev_mean'] - img.mean()) > 60:
        prev = None                                   # previous frame had the other polarity / a flash
    out = img.copy()
    a, b = Y(y0), Y(y1)
    area = (b - a) * W; done = 0
    while done < area * dens:
        w = int(rng.integers(1, 9)) * g; h = int(rng.integers(2, 13)) * g
        x = int(rng.integers(0, W // g)) * g; y = a + int(rng.integers(0, max(1, (b - a) // g))) * g
        hh = min(h, H - y); ww = min(w, W - x)
        if hh <= 0 or ww <= 0: continue
        r = rng.random()
        if r < 0.55:
            ry = max(0, y - int(rng.integers(0, 3)) * g)
            out[y:y + hh, x:x + ww] = out[ry, x:x + ww][None]
        elif r < 0.72 and prev is not None:
            sy = int(np.clip(y + rng.integers(-3, 4) * g, 0, H - hh)); sx = int(np.clip(x + rng.integers(-4, 5) * g, 0, W - ww))
            out[y:y + hh, x:x + ww] = prev[sy:sy + hh, sx:sx + ww]
        elif r < 0.88:
            sx = int(np.clip(x + rng.integers(-6, 7) * g, 0, W - ww))
            out[y:y + hh, x:x + ww] = img[y:y + hh, sx:sx + ww]
        else:
            blk = out[y:y + hh, x:x + ww]
            out[y:y + hh, x:x + ww] = blk * 0.4 + blk.mean((0, 1)) * 0.6
        done += hh * ww
    out[a:b] = out[a:b] * 0.7 + vblur(out[a:b], 6 * S) * 0.3
    return out

def op_box(img, f, cyan=False):
    """top-left frozen/posterised box (511/541/571/601/631/661/691): x 0-490, y 0-195 at 480p,
    sharp blocky posterised copy, light border on bottom+right, inner box at x 335-480, y 32-150"""
    out = img.copy()
    def poster(reg, lv):
        sm = Image.fromarray(np.clip(reg, 0, 255).astype(np.uint8))
        sm = sm.resize((max(1, reg.shape[1] // Y(4)), max(1, reg.shape[0] // Y(4))), Image.BILINEAR).resize((reg.shape[1], reg.shape[0]), Image.NEAREST)
        x = np.asarray(sm).astype(np.float32)
        x = x + (x - img_blur(x, 4 * S)) * 1.8                      # edge-enhanced
        x = np.round(x / (255 / lv)) * (255 / lv)
        return vblur(x, 3 * S) * 0.5 + x * 0.5
    x1, y1 = Y(490), Y(195)
    out[:y1, :x1] = np.clip(poster(out[:y1, :x1], 4) * 1.2 + 25, 0, 255)
    ix0, ix1, iy0, iy1 = Y(335), Y(480), Y(32), Y(150)
    out[iy0:iy1, ix0:ix1] = np.clip(poster(img[iy0:iy1, ix0:ix1], 3) * 1.25 + 20, 0, 255)
    bc = np.array([40, 215, 250], np.float32) if cyan else np.array([225, 225, 232], np.float32)
    for (ys, xs) in [((y1 - Y(2), y1), (0, x1)), ((0, y1), (x1 - Y(2), x1)), ((iy1 - Y(1.5), iy1), (ix0, ix1)), ((iy0, iy1), (ix1 - Y(1.5), ix1)), ((iy0, iy1), (ix0, ix0 + Y(1.5)))]:
        out[ys[0]:ys[1], xs[0]:xs[1]] = bc
    out[y1:y1 + Y(10), :x1] *= 0.5
    return out

def op_lowblk(img, f, strong=True):
    """p25 lower displaced rectangles (520/550/580/610/640/670) + horizontal smear lines"""
    rng = np.random.default_rng(f * 11 + 7)
    out = img.copy()
    n = 4 if strong else 2
    for _ in range(n):
        w = int(rng.integers(90, 450) * S); h = int(rng.integers(30, 110) * S)
        x = int(rng.integers(0, W - w)); y = int(rng.integers(Y(262), H - h // 2))
        sy = int(np.clip(y + rng.integers(-80, 40) * S, 0, H - h)); sx = int(np.clip(x + rng.integers(-60, 60) * S, 0, W - w))
        h2 = min(h, H - y)
        out[y:y + h2, x:x + w] = img[sy:sy + h2, sx:sx + w] * rng.uniform(0.35, 0.8)
    for _ in range(3 if strong else 1):
        y = int(rng.integers(Y(265), H - Y(4))); h = Y(rng.integers(2, 6))
        out[y:y + h] = out[y][None]
    return out

def op_cyaninv(img):
    """540-543/630-633: inverted, exposure +, cyan-white tint (ref mean 210,233,248)"""
    x = 255 - img
    x = np.clip(x * 1.25 + 30, 0, 255)
    return x * np.array([0.84, 0.95, 1.0], np.float32) + np.array([0, 8, 10], np.float32)

def op_palecyan(img, band):
    """557/558/647/648: inverted+blown pale cyan (200,235,245) with a darker teal band at top"""
    x = 255 - img
    x = np.clip(x * 1.5 + 195, 0, 255) * np.array([0.8, 0.94, 0.98], np.float32)
    top = np.clip((Y(band) - np.arange(H)) / Y(30), 0, 1)[:, None, None]
    t = (255 - img) * 0.6 * np.array([0.45, 0.85, 0.95], np.float32) + np.array([15, 45, 60], np.float32)
    return x * (1 - top) + t * top

def op_whitetop(img, band):
    """559/649: dark band with the lamp on top, everything below ~150 px blown white"""
    return op_botw(np.clip(img * 1.2, 0, 255), band, 1)

def op_teal(img, strength=1.0):
    l = lum(img)[..., None]
    t = l * np.array([0.45, 1.25, 1.45], np.float32) + np.array([5, 20, 25], np.float32)
    return img * (1 - strength) + t * strength


# ================================================================ schedule
@dataclass
class Step:
    fx: list = field(default_factory=list)       # [(name, [args])]
    tx: list = field(default_factory=list)
    tone: tuple = None                           # (r, g, b, top, mid, bottom) or None
    pos: tuple = DEFAULT_POS                     # text centre px@480
    seed: int = None                             # None = assigned by build (1000 + step index)

    @property
    def names(self):
        return [n for n, _ in self.fx]


def _toks(s):
    out = []
    for t in s.split():
        n, _, a = t.partition("=")
        args = []
        for v in (a.split(",") if a else []):
            try:
                args.append(float(v))
            except ValueError:
                args.append(v)
        out.append((n, args))
    return out


def parse_step(line, seed=None):
    """'[seed:] fx | tx | meta' -> Step"""
    m = re.match(r"\s*(-?\d+)\s*:(.*)$", line)
    if m:
        seed, line = int(m.group(1)), m.group(2)
    parts = (line.split("|") + ["", ""])[:3]
    st = Step(_toks(parts[0]), _toks(parts[1]), seed=seed)
    for n, a in _toks(parts[2]):
        if n == "tone":
            st.tone = tuple(a)
        elif n == "pos":
            st.pos = tuple(a)
        elif n == "seed":
            st.seed = int(a[0])
    return st


def parse(text):
    return [parse_step(l) for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def load_pattern(name):
    """a pattern from assets/patterns/<name>.txt (or a path) -> list of Steps (time order)."""
    name = "reference_drop" if name == "reference" else name
    p = ASSETS / "patterns" / f"{name}.txt"
    if not p.exists():
        p = name
    return parse(open(p, encoding="utf-8").read())


def slice(pattern, a, b):
    """steps a..b-1 (relative to the pattern start) of a pattern name or list."""
    if isinstance(pattern, str):
        pattern = load_pattern(pattern)
    return list(pattern[a:b])


def fit(pattern, n):
    """cycle/truncate a pattern to exactly n steps."""
    return [pattern[i % len(pattern)] for i in range(n)]


def build(spec, n):
    """drop.schedule from the timeline -> n Steps.

    spec = "reference" | "<pattern name>"          the pattern, cycled/truncated to n
         | [item, ...]                            concatenated, then cycled/truncated to n; an item is
             "fx | tx | meta" or "seed: fx | tx | meta"         one step
             {"pattern": name, "from": a, "to": b, "repeat": k} a slice of a pattern (k times)
             {"step": "...", "repeat": k}                       one step held k frames
    """
    out = load_pattern(spec) if isinstance(spec, str) else []
    for it in ([] if isinstance(spec, str) else spec):
        if isinstance(it, str):
            out.append(parse_step(it))
        elif "pattern" in it:
            p = load_pattern(it["pattern"])
            out += slice(p, it.get("from", 0), it.get("to", len(p))) * int(it.get("repeat", 1))
        else:
            out += [parse_step(it["step"], it.get("seed"))] * int(it.get("repeat", 1))
    return [st if st.seed is not None else replace(st, seed=1000 + i) for i, st in enumerate(fit(out, n))]


# ================================================================ per-frame application
def tone_match(img, tone, strength=0.85):
    """pull top/mid/bottom luma and the channel balance toward the step's tone target."""
    if tone is None or strength <= 0:
        return img
    rgb, bands = tone[:3], tone[3:6]
    l = lum(img)
    o = [l[:H // 3].mean(), l[H // 3:2 * H // 3].mean(), l[2 * H // 3:].mean()]
    g = [np.clip((t + 6) / (oo + 6), 0.3, 3.0) ** strength for t, oo in zip(bands, o)]
    rows = np.interp(np.arange(H), [H / 6, H / 2, 5 * H / 6], g).astype(np.float32)[:, None, None]
    x = img * rows
    wl = np.interp(np.arange(H), [H / 6, H / 2, 5 * H / 6], [max(0, (t - 215) / 40) for t in bands]).astype(np.float32)
    if wl.max() > 0:
        tl = np.interp(np.arange(H), [H / 6, H / 2, 5 * H / 6], bands).astype(np.float32)
        x = x + ((tl[:, None] - lum(x)).clip(0) * np.clip(wl, 0, 1)[:, None] * 0.8 * strength)[..., None]
    m = x.reshape(-1, 3).mean(0) + 1
    tr = np.array(rgb, np.float32) + 1
    cm = np.clip((tr / tr.mean()) / (m / m.mean()), 0.4, 2.5) ** strength
    return np.clip(x * cm, 0, 255)


def _text_through(img, tmask, a):
    m = mask_blur(tmask, 3 * S)[..., None] * a[0]
    tc = np.array(a[1:4], np.float32) if len(a) >= 4 else np.array([150, 160, 235], np.float32)
    return img * (1 - m) + tc * m


def apply(base, step, tmask=None, ctx=None, tone=0.85, jpeg=38):
    """run one Step on the composited frame (float32 HxWx3). ctx keeps 'prev' for the datamosh."""
    if ctx is None:
        ctx = {}
    img = base.astype(np.float32)
    names, f = step.names, step.seed
    for n, a in step.fx:
        if n == "inv": img = 255 - img
        elif n == "expo": img = op_expo(img, a[0])
        elif n == "botw": img = op_botw(img, a[0], a[1] if len(a) > 1 else 1)
        elif n == "hs": img = img * 0.15 + hblur(img, a[0] * S) * 0.85
        elif n == "vs": img = op_vsmear(img, a[0], a[1], a[2])
        elif n == "soft": img = resample_soft(img, a[0])
        elif n == "wash": img = img * a[0] + a[1]
        elif n == "tint": img = img * np.array(a[:3], np.float32)
        elif n == "teal": img = op_teal(img)
        elif n == "teal2": img = op_teal(img, 0.45)
        elif n == "cyaninv": img = op_cyaninv(img)
        elif n == "palecyan": img = op_palecyan(img, a[0])
        elif n == "whitetop": img = op_whitetop(img, a[0])
        elif n == "black": img = img * 0.07 * np.array([1.0, 0.9, 0.25], np.float32)
        elif n == "flash": img = img * (1 - a[1]) + colv(a[0]) * a[1]
        elif n == "fill": img = np.zeros_like(img) + np.array(a[:3], np.float32)
        elif n == "mosh": img = op_mosh(img, a[0], a[1], a[2], f, None if "cyaninv" in names else ctx)
        elif n == "box": img = op_box(img, f, cyan="cyaninv" in names)
        elif n == "lowblk": img = op_lowblk(img, f, True)
        elif n == "lowblk2": img = op_lowblk(img, f, False)
        elif n == "ht": img = op_halftone(img, a[0], a[1], a[2], a[3], f)
        elif n == "dust": img = op_dust(img, a[0], a[1], a[2], a[3], f)
        elif n == "row": img = op_row(img, a[0], a[1], f)
        elif n == "barA": img = op_barA(img, a[0], a[1], a[2], f)
        elif n == "barB": img = op_barB(img, a[0], a[1], f)
        elif n == "hl": img = op_hlines(img, a[0], f, step.pos[1])
        elif n == "line": img = op_line(img, a[0], a[1])
        elif n == "iri": img = op_iri(img, a[0], f)
        elif n == "tre_" and tmask is not None: img = _text_through(img, tmask, a)
        img = np.clip(img, 0, 255)
    img = tone_match(img, step.tone, tone if "fill" not in names else 0)
    for n, a in step.fx:
        if n == "tre" and tmask is not None:
            img = _text_through(img, tmask, a)
    if jpeg and "fill" not in names:
        img = jpeg_dirt(img, jpeg)
    ctx["prev"] = img
    ctx["prev_mean"] = float(img.mean())
    return np.clip(img, 0, 255)

