"""Segment A of the шАхА remake: reference frames 0..234 (spec/segA.json, spec/segA.md)."""
from functools import lru_cache

import numpy as np

import kit
import look2
import fx_A as fx
from bgs import bg

RANGE = (0, 235)
TRACK = 2.0
BOLD = 1

# ---------------------------------------------------------------- colours (fill target before streak/grain loss)
WHITE = (230, 229, 237)
WHITE2 = (225, 225, 233)           # ОЧЕНЬ / ОЧЕНЬ СИЛЬНО (ref core 213-222)
RED = (170, 41, 50)
RED_DIM = (146, 40, 52)            # КИШКИ: whole word x0.78
RED_LINE = (176, 43, 55)
RED_LOVE = (165, 39, 49)           # ТОРЧАТ ИЗ ПУЗА / МОЯ ЛЮБОВЬ
CYAN1 = (119, 197, 201)            # ХОЛОДНО
CYAN2 = (53, 179, 178)             # ПОРОВНУ
SMALL = (248, 238, 236)
SMALL_CYAN = (144, 206, 196)

# big line states: (first, last, text, bbox, colour, kind, weight)
BIG = [
    (28, 32, "КОГДА", (350, 211, 613, 494), WHITE, "white", 700),
    (33, 46, "КИШКИ", (337, 216, 626, 468), RED_DIM, "red", 700),
    (47, 64, "ТОРЧАТ", (328, 212, 635, 469), RED, "red", 700),
    (65, 69, "ТОРЧАТ ИЗ", (258, 212, 699, 469), RED, "red", 700),
    (70, 82, "ТОРЧАТ ИЗ ПУЗА", (158, 215, 817, 469), RED_LINE, "red", 700),
    (83, 94, "ОЧЕНЬ", (380, 234, 582, 450), WHITE2, "white", 700),
    (95, 108, "ОЧЕНЬ СИЛЬНО", (233, 234, 727, 450), WHITE2, "white", 700),
    (109, 126, "ХОЛОДНО", (192, 134, 769, 565), CYAN1, "cyan", 700),
    (127, 137, "МОЯ", (377, 174, 587, 497), RED, "red", 650),
    (138, 215, "МОЯ ЛЮБОВЬ", (145, 174, 821, 497), RED_LOVE, "red", 650),
    (216, 234, "ПОРОВНY",  # Latin Y: the reference У has no descender
     (177, 102, 790, 545), CYAN2, "cyan", 700),
]

# small front line: (first, last, text, bbox)
SMALL_LINES = [
    (151, 154, "я", (469, 316, 489, 366)),
    (155, 176, "я разделил", (362, 316, 596, 383)),
    (177, 183, "я разделил бы", (326, 299, 631, 382)),
    (184, 196, "я разделил бы этот", (277, 299, 684, 383)),
    (197, 215, "я разделил бы этот холод", (205, 299, 756, 382)),
]

# per-frame brightness of the big line (entry ramps, dims)
BRIGHT = {28: 0.94, 70: 0.91, 71: 0.94, 72: 0.95, 73: 0.97, 83: 0.95, 95: 0.92, 107: 0.95, 108: 0.95,
          109: 0.95, 126: 0.9, 127: 0.88, 138: 0.91, 139: 0.93, 140: 0.93, 141: 0.96, 142: 0.98,
          76: 0.75, 77: 0.75, 78: 0.87, 79: 0.87, 80: 0.87, 81: 0.84, 82: 0.88,
          165: 0.81, 166: 0.81, 167: 0.91, 168: 0.91, 169: 0.91, 170: 0.89, 171: 0.92,
          181: 0.89, 182: 0.93, 190: 0.9, 191: 0.9, 192: 0.91, 193: 0.9, 194: 0.91, 195: 0.95, 196: 0.95,
          197: 0.88, 198: 0.88, 215: 0.85, 216: 0.88, 217: 0.95, 234: 0.9}
SMALL_BRIGHT = {181: 0.95, 182: 0.95, 183: 0.93, 215: 0.9}

# row-band shifts of the big line on entry / exit frames: [(dy from bbox top, rows, dx)]
ROWS = {
    28: [(0, 12, 4), (12, 10, 2), (22, 14, 1)],
    29: [(0, 10, 3), (10, 8, 2)],
    32: [(0, 10, 3), (172, 52, -1)],
    109: [(0, 8, 2), (24, 14, -2), (360, 6, -2), (380, 8, -4)],
    123: [(80, 18, 1)],
    125: [(2, 12, 2), (12, 22, 1)],
    216: [(0, 3, -4), (3, 8, -2), (27, 30, 2)],
    217: [(0, 28, -2), (41, 4, 1)],
    234: [(0, 11, -6), (11, 26, -4), (37, 30, -3)],
}


def _state(table, i):
    for row in table:
        if row[0] <= i <= row[1]:
            return row
    return None


@lru_cache(maxsize=32)
def _layer(text, bbox, col, kind, weight, seed, small=False):
    vw = VWARP.get(text)
    if small:
        return fx.small_text_layer(text, bbox, col, seed)
    if kind == "red":
        rs = RED_SOFT.get(text, 0.75)
        return fx.text_layer(text, bbox, col, seed, weight=weight, kind="red", tracking=TRACK, bold=1, bold_gain=1.5,
                             streak=(0.05, 0.03), grain_h=0.03, grain_f=0.03, soft=rs,
                             steps=True, halo=((26, 18, 44), 6, 0.85), red_ring=True, sharp=0.0, step_p=0.25, vwarp=vw)
    if kind == "cyan":
        return fx.text_layer(text, bbox, col, seed, weight=weight, kind="cyan", tracking=TRACK, bold=BOLD, bold_gain=1.3,
                             streak=(0.06, 0.03), grain_h=0.025, grain_f=0.012, soft=0.0, steps=True, sharp=0.8, step_p=WSTEP,
                         halo=WHALO, vwarp=vw)
    return fx.text_layer(text, bbox, col, seed, weight=weight, kind="white", tracking=TRACK, bold=BOLD, bold_gain=1.3,
                         streak=WSTREAK, grain_h=0.0, grain_f=0.0, soft=WSOFT_T.get(text, WSOFT), steps=True,
                         sharp=0.0 if text in WSOFT_T else WSHARP, step_p=WSTEP,
                         glow=WGLOW, vwarp=vw)


# measured 20-80 % edge rise of the red words (ref): КИШКИ 6.2 px, ТОРЧАТ.. 5.3 px
WSTEP = 0.15
WHALO = ((33, 31, 54), 8, 0.92)    # (cyan words)
# white words: wide lavender-navy glow, measured rings outside the edge (ref 29-31, 86-104)
WGLOW = ((47, 49, 106), 19.0, 1.6, 0.73)
WSTREAK = (0.03, 0.03)
WSOFT, WSHARP = 0.0, 0.6
WSOFT_T = {"ОЧЕНЬ": 0.4, "ОЧЕНЬ СИЛЬНО": 0.4}     # ref edge rise 3-4 px on these (КОГДА 2.2)
ECHO_K = {100: 0.55, 101: 0.22, 102: 0.16, 103: 0.11, 104: 0.07}
RED_GRAIN_SIZE = 1.0
RED_GRAIN = {"МОЯ": 0.03, "МОЯ ЛЮБОВЬ": 0.02, "КИШКИ": 0.045, "ТОРЧАТ ИЗ": 0.025, "ТОРЧАТ ИЗ ПУЗА": 0.022}
RED_GRAIN_DEF = 0.035
RED_SOFT = {"КИШКИ": 1.4}
RED_N = 0.02
# measured ref baseline / descender bottom (Oswald's descenders are longer and squeeze the body)
VWARP = {"КОГДА": (467, 494), "ХОЛОДНО": (524, 565), "ТОРЧАТ ИЗ ПУЗА": (469, 474)}


def big_layer(i):
    st = _state(BIG, i)
    if st is None:
        return None, None
    f0, f1, text, bbox, col, kind, wt = st
    # white / cyan band steps re-randomised every frame, red ones static per word
    seed = (i * 7919) if kind != "red" else (f0 * 104729)
    lay = _layer(text, bbox, col, kind, wt, seed)
    if kind == "red":      # the red grain is re-randomised every frame (ref temporal diff ~10 levels)
        rgb, a, g = lay
        n = kit.rng(i * 613 + 5).normal(0, RED_N, (kit.H, kit.W)).astype(np.float32)
        fl = 1 + 0.03 * kit.rng(i * 31 + 7).normal()   # per-frame brightness flicker of the red (ref ±5 %)
        lay = (np.clip(rgb * fl * (1 + n * g)[..., None], 0, 1), a, g)
    POST[i] = (lay[2], RED_GRAIN.get(text, RED_GRAIN_DEF) if kind == "red" else WGRAIN_T.get(text, WGRAIN), "fine" if kind == "red" else "col")
    return lay, st


POST_FX = {}   # frame -> [fn(img) -> img] applied after the codec pass

# red visibility per 20 px column band from x=140 (ref measurement, 9 = fully visible)
RED_VIS = {   # R-G excess per 20 px column band from x=140, relative to frames 73-74 (x/8.6)
    76: "8777655555767666655554943334644656",
    77: "8877656555757667555554943334644656",
    78: "6666666777878878688787867675855644",
    79: "5667667777878878688787867675855544",
    80: "5666666777778889688787867674844433",
    81: "5666666666565667677787977674854534",
    82: "6889888998788889988887797667686844",
}


@lru_cache(maxsize=16)
def _red_vis(i):
    v = np.array([int(c) / 8.6 for c in RED_VIS[i]], np.float32)
    x = np.arange(kit.W, dtype=np.float32)
    prof = np.interp(x, 140 + 20 * np.arange(len(v)) + 10, v, left=v[0], right=v[-1])
    prof = np.clip(prof, 0.08, 1.05)
    return kit.gblur(np.repeat(prof[None, :], kit.H, 0), 4.0)


POST = {}      # frame -> (text mask, grain sigma) for the post-codec grain (render_A.py)

import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
GHOST = _json.loads((_Path(__file__).parent / "spec" / "ghost_vis_A.json").read_text())
GHOST_GAIN = 0.7


@lru_cache(maxsize=1)
def ghost_mask():
    """dot-ghost glyph of ТОРЧАТ ИЗ ПУЗА (76-82): lighter weight, x1.21 / y1.18 about (533, 389), horizontal bars
    thinned 6 px (ref: ghost x 80-876, y 192-480, Т stem ~20 px, crossbar ~30 px)."""
    m, _ = kit.text_box("ТОРЧАТ ИЗ ПУЗА", (158, 215, 817, 469), 600, TRACK, "oswald")
    m = fx.baseline_warp(m, 469, 474)
    sx, sy, gx, gy = GHOST["geo"]
    g = fx.scale_about(m, sx, gx, gy, sy) > 0.5
    e = g.copy()
    for d in range(1, GHOST_VERO + 1):
        e &= np.roll(g, d, 0) & np.roll(g, -d, 0)
    return e.astype(np.float32)


GHOST_VERO = 6


@lru_cache(maxsize=8)
def _ghost_vis(i):
    v = np.asarray(GHOST["vis"][str(i)], np.float32)
    c = GHOST["cell"]
    v = np.repeat(np.repeat(v, c, 0), c, 1)[:kit.H, :kit.W]
    return np.clip(kit.gblur(v, c * 0.6), 0, 1)
WGRAIN = 0.05
WGRAIN_T = {"ОЧЕНЬ": 0.072, "ОЧЕНЬ СИЛЬНО": 0.072}


def small_layer(i):
    st = _state(SMALL_LINES, i)
    if st is None:
        return None, None
    f0, f1, text, bbox = st
    lay = _layer(text, bbox, SMALL, "white", 560, f0 * 31, small=True)
    if text.endswith("холод"):
        rgb, a, g = lay
        rgb = rgb.copy()
        xx = np.arange(kit.W)[None, :]
        sel = (xx >= 622)[..., None] * (g[..., None] > 0.02)
        tint = np.asarray(SMALL_CYAN, np.float32) / np.asarray(SMALL, np.float32)
        rgb = np.where(sel, rgb * tint, rgb)
        lay = (rgb, a, g)
    return lay, st


def _small_comp(img, i, sl, sst):
    f0, f1, text, bbox = sst
    k = SMALL_BRIGHT.get(i, 1.0)
    rgb, a, g = sl
    if i in (164, 165, 166):   # echo of 'я' ~19 px left, 1.1x
        ex = fx.scale_about(g * (np.arange(kit.W)[None, :] < bbox[0] + 30), 1.1, bbox[0] + 10, 341)
        ex = kit.shift(ex, -19)
        img = kit.over(img, (225, 215, 212), ex * 0.85)
    if i == 214:
        ex = kit.shift(g * (np.arange(kit.W)[None, :] < bbox[0] + 22), -47)
        img = kit.over(img, (180, 175, 175), ex * fx.cross_tile(6) * 0.9)
    if i in (170, 190):
        ex = kit.shift(g * (np.arange(kit.W)[None, :] > bbox[2] - 60), 36 if i == 190 else 20)
        img = kit.over(img, (220, 210, 208), ex * 0.6)
    return kit.over_img(img, rgb * k, a)


def _centre(bbox):
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def frame(i):
    img = bg(i).copy()
    # fade in from black over 0..14
    # (fade-in 0..14 is already in the per-frame exposure match of bgs.bg)

    # scratches over the background before the text
    if i == 27:
        img = fx.scratch(img, [(505, 140), (480, 300), (445, 470)], (4, 3, 6), width=3, alpha=0.75)

    lay, st = big_layer(i)
    if lay is not None:
        f0, f1, text, bbox, col, kind, wt = st
        if i in ROWS:
            lay = fx.row_shift(lay, bbox[1], ROWS[i])
        k = BRIGHT.get(i, 1.0)
        if i in RED_VIS:
            k = 1.0                  # the measured column profile already holds the dim
        elif kind == "red" and (165 <= i <= 171 or i == 190):
            k = min(1.0, k * 1.15)   # the measured dim already includes the dot screen
        blur = {28: 2.2, 83: 1.6, 84: 0.8}.get(i, 0.8 if i in (95, 109, 127, 138, 215, 216) else 0.0)
        lay = fx.dim(lay, k, blur)
        SM = {82: (10, 0.7, 2.5), 28: (4, 0.5, 0), 95: (6, 0.6, 1.0), 109: (14, 0.8, 0), 110: (5, 0.4, 0), 216: (8, 0.7, 2.0), 217: (4, 0.4, 0)}
        if i in SM:
            lay = fx.smear_layer(lay, *SM[i])
        cx, cy = _centre(bbox)
        g = lay[2]

        # ---- ghosts drawn behind the text (scan ghosts on white/cyan words)
        if i in (95,):
            img = fx.scan_ghost(img, g, i, scale=1.04, centre=(cx, cy), grey=0.3, smear=14, period=6.4)
        if i in (109, 110):
            img = fx.scan_ghost(img, g, i, scale=1.12, sy=1.0, centre=(cx, cy), grey=0.32 if i == 109 else 0.12, smear=18)
        if 122 <= i <= 126:
            grow = {122: 0.07, 123: 0.4, 124: 0.45, 125: 0.55, 126: 0.6}[i]
            s = {122: 1.2, 123: 1.29, 124: 1.29, 125: 1.26, 126: 1.22}[i]
            img = fx.scan_ghost(img, g, i, scale=s, sy=s * 1.0, centre=(cx, cy + 14), grey=grow, smear=8)
        if 218 <= i <= 233:     # faint persistent striped ghost at the sides of ПОРОВНУ
            img = fx.scan_ghost(img, g, i, scale=1.16, sy=1.12, centre=(cx, cy - 8), grey=0.13, smear=8)
        if i in (216, 217):
            img = fx.scan_ghost(img, g, i, scale=1.16, sy=1.12, centre=(cx, cy - 8), grey=0.5 if i == 216 else 0.42, smear=8)

        rgb, a, gg = lay
        if i in RED_VIS:
            v = _red_vis(i)
            rgb = rgb * v[..., None]; a = a * (0.25 + 0.75 * v); gg = gg * v
        if i in (216, 217):
            rgb = rgb * (0.85 + 0.15 * fx.stripes(6.4, 0.6))[..., None]
        if 125 <= i <= 126:        # stripes inside the cyan letters too
            rgb = rgb * (0.9 + 0.1 * fx.stripes(6.4, 0.3))[..., None]
        if kind == "red" and (76 <= i <= 82 or 165 <= i <= 171 or i == 190):
            rgb = fx.dotted_text(kit.blur(rgb, 1.2), gg, 0.15)
        img = kit.over_img(img, rgb, a)

        # ---- double exposure of the white line (scaled / offset copy with striped alpha)
        if i in ECHO_K:       # fine 4 px striped echo, fading tail 102-104 (ref temporal diff 101->102 ~5 %)
            img = fx.layer_echo(img, lay, 1.08, 1.06, (cx, cy), k=ECHO_K[i], period=4.0, depth=0.45, seed=i)
        if i in (107, 108):
            img = fx.layer_echo(img, lay, 1.0, None, (cx, cy), dx=-30, k={107: 0.2, 108: 0.3}[i], period=4.0, depth=0.45,
                                seed=i, tint=0.75)

        # ---- dot ghosts over red lines: crisp, composited after the codec pass (render_A.py)
        if 76 <= i <= 82:      # geometry fitted to the ref dot density, visibility map measured per 20 px cell
            POST_FX.setdefault(i, []).append(lambda im, i=i:
                fx.crisp_dot_ghost(im, ghost_mask(), i, 1.0, 1.0, (480, 360), vis=_ghost_vis(i), tile="cross",
                                   gain=GHOST_GAIN, flick=0.3))
        if 165 <= i <= 171 or i == 190:
            sc = {165: 1.1, 166: 1.11, 167: 1.17, 168: 1.17, 169: 1.17, 170: 1.17, 171: 1.17, 190: 1.17}[i]
            region = (267, 877) if i == 171 else None
            POST_FX.setdefault(i, []).append(lambda im, g=g, i=i, sc=sc, region=region, cx=cx, cy=cy:
                fx.crisp_dot_ghost(im, g, i, sc, sc * 1.06, (cx + 2, cy + 15), region=region, under=g))

        # dirt
        if i in (36, 37, 38):
            img = fx.dirt(img, 360 + i, (340, 214, 625, 232), n=8, col=(10, 4, 8), alpha=0.8, rmax=9)
        if i == 43:
            img = fx.dirt(img, 43, (465, 255, 525, 345), n=4, col=(12, 5, 8), alpha=0.75, rmax=14)
        if i == 222:
            img = fx.dither_patch(img, (516, 118, 833, 322), 222, grey=0.45)
            img = fx.dirt(img, 222, (560, 200, 720, 320), n=6, col=(14, 18, 22), alpha=0.6, rmax=7)

    # ---- small front line: crisp, composited after the codec pass, under the dot ghost (ref 160-184)
    sl, sst = small_layer(i)
    if sl is not None:
        POST_FX.setdefault(i, []).insert(0, lambda im, i=i, sl=sl, sst=sst: _small_comp(im, i, sl, sst))

    # scratch over text
    if i == 28:     # entry burn: dark column + white checker stroke + black scratch + spike (ref zoom f28)
        img = fx.dither_rect(img, (478, 226, 528, 482), alpha=0.6, seed=28)
        img = fx.checker_stroke(img, [(326, 464), (352, 440), (376, 414), (400, 386)], width=22)
        img = fx.checker_stroke(img, [(489, 222), (496, 200), (502, 192)], width=10, cell=2)
        img = fx.scratch(img, [(384, 402), (404, 376), (426, 344)], (8, 6, 10), width=4, alpha=0.8)
    if i in (116, 117):
        pts = [(140, 546), (205, 525), (265, 496), (295, 475), (325, 441), (355, 427), (385, 385),
               (415, 368), (445, 315), (475, 231), (500, 185)]
        img = fx.scratch(img, pts, (235, 240, 240), width=9, alpha=0.95, dashed=True, seed=116)
    return np.clip(img, 0, 1).astype(np.float32)
