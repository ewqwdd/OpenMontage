"""Segment D: frames 645-852 (ДАВАЙ ПЕРЕВЕРНЕМ ЕЕ В СРЕДУ / надеюсь, что мой / БОГ СО МНОЙ КОГДА Я НА НЕЙ ЕДУ / ending).

Built from spec/segD.json + segD.md. frame(i) -> float32 (720, 960, 3) in 0..1.
Layer order: bg < lowercase line < БОГ < СО МНОЙ < front word (each with its navy plate) ; then the ending.
"""
from functools import lru_cache

import numpy as np

import kit
import bgs
import fx_D as fx

RANGE = (645, 853)
H, W = kit.H, kit.W

# ------------------------------------------------------------------ words (tight glyph boxes incl. breve/descender)
DAVAY = ("ДАВАЙ", (249, 136, 707, 528))
PEREV = ("ПЕРЕВЕРНЕМ", (71, 198, 894, 500))
EE = ("ЕЕ", (418, 198, 545, 500))
V = ("В", (442, 198, 521, 500))
VSREDU = ("В СРЕДУ", (212, 194, 760, 528))
NAD1 = ("надеюсь", (329, 319, 659, 425))
NAD2 = ("надеюсь, что", (244, 319, 740, 432))
NAD3 = ("надеюсь, что мой", (146, 288, 814, 432))
SO = ("СО", (438, 517, 522, 611))
SOMNOY = ("СО МНОЙ", (330, 486, 629, 611))
KOGDA = ("КОГДА", (262, 132, 708, 606))
YA = ("Я", (446, 139, 520, 566))
YANA = ("Я НА", (321, 137, 641, 566))
YANANEY = ("Я НА НЕЙ", (180, 130, 834, 596))
EDU = ("ЕДУ", (330, 139, 629, 611))
BOG1 = ("БОГ", (226, 202, 742, 538))      # 750-755, on the lowercase line
BOG2 = ("БОГ", (226, 98, 668, 426))       # 756+, moved up

NAVY = (36, 32, 74)
BIG = dict(kind="white", halo=(NAVY, 14, 0.96), streak=(0.09, 0.04), grain=0.03, soft=0.3, weight=700,
           tracking=6.0)
LOW = dict(kind="white", halo=((22, 20, 24), 5, 0.55), streak=(0.0, 0.0), grain=0.012, soft=0.22,
           weight=600, tracking=3.0, steps=False, sharp=0.9)
MID = dict(kind="white", halo=((18, 16, 20), 6, 0.55), streak=(0.02, 0.01), grain=0.02, soft=0.4,
           weight=700, tracking=6.0, sharp=0.6)

WHITE = (222, 221, 225)
COL_LOW = (238, 236, 238)
COL_MID = (206, 202, 202)
RED = np.array([180, 23, 22], np.float32) / 255
YEL = np.array([220, 210, 84], np.float32) / 255
WHT = np.array([232, 232, 228], np.float32) / 255


def L(word, col, seed, look):
    t, bb = word
    return fx.layer(t + str(bb), t, bb, col, seed, **look)


def M(word, look=BIG):
    t, bb = word
    return fx.mask_of(t, bb, look.get("weight", 700), look.get("tracking", 0.0), look.get("name", "oswald"))[0]


def comp(img, layer):
    rgb, a, _ = layer
    return kit.over_img(img, rgb * fx.text_vignette(), a)


def paint_echo(img, alpha, main=None, col=(0.84, 0.84, 0.87)):
    if main is not None:
        alpha = alpha * (1 - main[2])
    return fx.paint(img, alpha * fx.text_vignette()[..., 0], col)


# ------------------------------------------------------------------ 645-721: big white words
def big_words(img, i):
    if 645 <= i <= 658:
        w, seed = DAVAY, 6450
    elif 659 <= i <= 684:
        w, seed = PEREV, 6590
    elif 685 <= i <= 694:
        w, seed = EE, 6850
    elif 695 <= i <= 698:
        w, seed = V, 6950
    elif 699 <= i <= 721:
        w, seed = VSREDU, 6990
    else:
        return img
    lay = L(w, WHITE, seed, BIG)
    bb = w[1]
    cy = (bb[1] + bb[3]) / 2
    pre = []        # echoes painted before the glyph? (they sit over the plate -> after, masked by the glyph)
    post = []
    # ---- entry / exit frames
    if i in (645, 659, 699):
        lay = fx.soften(lay, r=1.5, lum=0.88, grain_amt=0.16, seed=i, smear=70 if i != 699 else 0)
    if i in (658, 698):
        lay = fx.soften(lay, r=1.3, lum=0.95, grain_amt=0.0, seed=i)
    if i == 684:
        lay = fx.soften(fx.fade_bottom(lay, 400, 500), r=1.4, lum=0.9, grain_amt=0.05, seed=i)
    if i == 698:
        lay = fx.fade_bottom(lay, 440, 500)
    if i == 721:
        lay = fx.striped_layer(lay, depth=0.55, lum=0.82, r=1.4)
    # ---- echoes
    E = {646: [(-20, 25, 1.0, 0.45)], 647: [(-20, 25, 1.0, 0.5)], 648: [(-22, 25, 1.0, 0.42)],
         665: [(-30, 0, 1.0, 0.42), (30, 0, 1.0, 0.35)], 666: [(-30, 0, 1.0, 0.45), (30, 0, 1.0, 0.38)],
         667: [(-28, 0, 1.0, 0.42), (32, 0, 1.0, 0.35)], 668: [(-26, 0, 1.0, 0.2)],
         670: [(-60, 0, 1.05, 0.38)], 680: [(25, 0, 1.0, 0.4)],
         705: [(-33, 0, 1.0, 0.5)], 706: [(-33, 0, 1.0, 0.5)], 707: [(-33, 0, 1.0, 0.48)],
         708: [(-33, 0, 1.0, 0.45), (0, 0, 1.08, 0.32)], 709: [(-33, 0, 1.0, 0.45), (0, 0, 1.08, 0.35)],
         710: [(-33, 0, 1.0, 0.42), (0, 0, 1.08, 0.3)], 721: [(0, 0, 1.03, 0.25)]}
    for dx, dy, sc, lum in E.get(i, []):
        al = fx.echo(lay, dx, dy, sc, lum, phase=(i % 7) / 7, cy=cy)
        if i in (646, 647, 648):
            al = fx.crop_x(al, y_min=360)
        post.append(al)
    img = comp(img, lay)
    for al in post:
        img = paint_echo(img, al, lay)
    # ---- fragments / blocks / scratches
    if i in (663, 664):     # bright displaced block of П at the far left
        frag = fx.crop_x(fx.shift2(lay[2], -75), x_max=160, y_min=200, y_max=500)
        img = fx.paint(img, frag * (0.75 if i == 663 else 0.55), (0.9, 0.9, 0.92))
        img = fx.paint(img, fx.crop_x(np.ones((H, W), np.float32), x_min=20, x_max=34, y_min=230, y_max=470) * 0.6)
    if i == 679:
        frag = fx.crop_x(fx.shift2(lay[2], -55), x_max=150, y_min=198, y_max=500)
        img = fx.paint(img, frag * 0.6, (0.82, 0.82, 0.86))
        img = fx.paint(img, fx.crop_x(np.ones((H, W), np.float32), x_min=130, x_max=150, y_min=200, y_max=300) * 0.7)
    if 705 <= i <= 711:
        img = fx.tiles(img, 7050 + i, (bb[0] - 20, bb[1], bb[2] + 20, bb[3]), n=8 if i == 711 else 5, amax=26)
    if i in (656, 657):
        img = fx.paint(img, fx.scratch(i, (205, 540), (445, 315), width=1.6 if i == 656 else 2.4, lum=0.85), (0.95, 0.95, 0.95))
    if i == 707:
        img = fx.paint(img, fx.scratch(i, (625, 190), (700, 470), width=1.5, lum=0.8), (0.95, 0.95, 0.95))
    if i in (719, 720):
        img = fx.paint(img, fx.scratch(i, (490, 180), (770, 520), width=1.7, lum=0.8), (0.95, 0.95, 0.95))
    if i in (699, 701):
        img = fx.paint(img, fx.scratch(i, (742, 196), (760, 160), width=1.3, lum=0.7), (0.9, 0.9, 0.9))
    return img


# ------------------------------------------------------------------ 722-755: lowercase line
def lowercase(img, i):
    if 722 <= i <= 735:
        w = NAD1
    elif 736 <= i <= 743:
        w = NAD2
    elif 744 <= i <= 755:
        w = NAD3
    else:
        return img
    lay = L(w, COL_LOW, 7220 + len(w[0]), LOW)
    E = {730: [(-20, 0.42)], 731: [(-18, 0.25)], 736: [(-25, 0.32), (25, 0.28)], 737: [(-24, 0.18)],
         743: [(-25, 0.28), (25, 0.22)], 744: [(-25, 0.32), (25, 0.3)], 755: [(-22, 0.3)]}
    if i in (736, 744):
        lay = fx.soften(lay, r=1.1, lum=0.9, grain_amt=0.06, seed=i)
    if i == 755:
        lay = fx.striped_layer(lay, depth=0.4, lum=0.9, r=0.8)
    img = comp(img, lay)
    for dx, lum in E.get(i, []):
        img = paint_echo(img, fx.echo(lay, dx, 0, 1.0, lum, smear=3, cy=370), lay)
    return img


# ------------------------------------------------------------------ БОГ (back layer)
CYCLE = ["R", "R", "W", "R", "Y", "R", "off", "R", "W", "Y", "R", "Rd", "Rd", "off", "off"]
LEAD = {750: "R", 751: "R", 752: "R", 753: "W", 754: "split", 755: "Y", 756: "R", 757: "YR", 758: "W", 759: "WY",
        760: "Y", 761: "R", 762: "off", 763: "R", 764: "Wo", 765: "Y", 766: "Rb", 767: "R", 768: "Rdb",
        769: "faint", 770: "off"}


def bog_state(i):
    if i in LEAD:
        return LEAD[i]
    if 771 <= i <= 840:
        return CYCLE[(i - 771) % 15]
    return None


@lru_cache(maxsize=4)
def bog_mask(which):
    w = BOG1 if which == 1 else BOG2
    m = M(w, dict(weight=700, tracking=4.0))
    return kit.blur(m, 5.0)


def _ch(col, a):
    a = np.clip(a, 0, 1)
    return np.asarray(col, np.float32)[None, None] * a[..., None], np.repeat(a[..., None], 3, -1)


def bog(img, i):
    st = bog_state(i)
    if st is None:
        return img
    m = bog_mask(1 if i <= 755 else 2)
    bb = (BOG1 if i <= 755 else BOG2)[1]
    r = kit.rng(9000 + i)
    if st in ("R", "Rb"):
        P, A = _ch(RED, m)
    elif st in ("Rd", "Rdb"):
        P, A = _ch(RED, m * 0.38)
        # orange glow blobs inside the dim glyph
        for _ in range(3):
            bx = r.uniform(bb[0] + 40, bb[2] - 40); by = r.uniform(bb[1] + 60, bb[3] - 60)
            g = fx.blob(bx, by, r.uniform(18, 35), r.uniform(25, 50), soft=14) * m
            P, A = fx.add_ch((P, A), _ch(np.array([0.95, 0.55, 0.2], np.float32), g * 0.7))
    elif st == "off":
        P, A = _ch(RED, m * 0.05)
    elif st == "faint":
        P, A = _ch(RED, m * 0.15)
    elif st in ("W", "Wo"):
        col = WHT if st == "W" else np.array([0.9, 0.78, 0.55], np.float32)
        P, A = fx.prism(*_ch(col, m), dx_r=8, dx_b=-10, blur=4.0)
        Py, Ay = _ch(YEL, fx.shift2(m, 12, 0) * 0.5)
        P, A = fx.add_ch((Py, Ay), (P, A))
    elif st == "Y":
        Pr, Ar = _ch(RED, fx.shift2(m, 9, 2))
        P, A = fx.add_ch((Pr, Ar), _ch(YEL, m))
    elif st == "YR":
        left = (np.arange(W) < 450).astype(np.float32)[None]
        P, A = _ch(RED, m * (1 - left))
        P, A = fx.add_ch((P, A), _ch(np.array([0.85, 0.7, 0.36], np.float32), m * left))
    elif st == "WY":
        Py, Ay = _ch(YEL, fx.shift2(m, 0, 23) * 0.9)
        P, A = fx.add_ch((Py, Ay), fx.prism(*_ch(WHT, m * 0.85), dx_r=6, dx_b=-8, blur=3.0))
    elif st == "split":
        top = (np.arange(H) < 335).astype(np.float32)[:, None]
        P, A = _ch(RED, m * (1 - top))
        P, A = fx.add_ch((P, A), fx.prism(*_ch(np.array([0.9, 0.88, 0.75], np.float32), m * top), 6, -8, 3.0))
    # texture: dither patches on bright states, white burn blobs, striped echo
    if st in ("W", "Wo", "Y", "YR", "WY"):
        for k in range(2):
            x0 = int(r.uniform(bb[0], bb[2] - 90)); y0 = int(r.uniform(bb[1], bb[3] - 90))
            ch = fx.checker(i * 7 + k, (x0, y0, x0 + int(r.uniform(40, 90)), y0 + int(r.uniform(40, 110))), 2, 0.35)
            P = P * ch[..., None]
    if st in ("Rb", "Rdb"):
        for _ in range(3 if st == "Rb" else 2):
            bx = r.uniform(bb[0] + 120, bb[2] - 60); by = r.uniform(bb[1] + 90, bb[3] - 60)
            g = fx.blob(bx, by, r.uniform(10, 22), r.uniform(18, 40), soft=5) * (m > 0.4)
            P, A = fx.add_ch((P, A), _ch(np.array([0.97, 0.95, 0.92], np.float32), g * 0.9))
    if i in (753, 755, 757, 759, 820):     # striped echo, scale 1.1 towards top-left
        e = fx.zoom2(m, 1.1, (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
        e = fx.shift2(e, -14, -18) * fx.scanlines(period=12.0, duty=0.5, soft=0.3)
        if i == 757:
            e = fx.crop_x(e, y_max=bb[1] + 110)
        P, A = fx.add_ch(_ch(np.array([0.85, 0.8, 0.55], np.float32), e * 0.45), (P, A))
    if i >= 836:   # ending: БОГ reads as a grey ghost (dark after the exclusion lift)
        g = P.mean(-1, keepdims=True)
        P = np.repeat(g, 3, -1)
    vig = fx.text_vignette()
    return fx.comp_ch(img, P * vig, A)


def fragment(img, i):
    """chromatic БОГ fragment tile left of centre (visible when БОГ is off)."""
    if i not in (770, 785, 797, 798, 799, 800, 815, 830):
        return img
    cx, cy = (232, 335) if i != 798 else (255, 300)
    g = fx.blob(cx, cy, 22, 38, soft=8)
    xs = np.arange(W, dtype=np.float32)[None]
    red = g * (xs < cx - 4); yel = g * (xs >= cx - 4) * (xs < cx + 8); blu = g * (xs >= cx + 8)
    img = fx.paint(img, red * 0.8, (0.85, 0.25, 0.15))
    img = fx.paint(img, yel * 0.85, (0.95, 0.85, 0.45))
    img = fx.paint(img, blu * 0.7, (0.35, 0.4, 0.9))
    return img


# ------------------------------------------------------------------ СО МНОЙ (middle) and the front words
def middle(img, i):
    if 756 <= i <= 758:
        w = SO
    elif 759 <= i <= 848:
        w = SOMNOY
    else:
        return img
    lay = L(w, COL_MID, 7560 + len(w[0]), MID)
    if 760 <= i <= 768:     # faint striped reflection below
        img = paint_echo(img, fx.echo(lay, 0, 40, 1.0, 0.22, smear=1), None, (0.75, 0.74, 0.74))
    return comp(img, lay)


FRONT = [(769, 774, KOGDA, 7690), (775, 782, YA, 7750), (783, 786, YANA, 7830), (787, 794, YANANEY, 7870),
         (795, 848, EDU, 7950)]


def front(img, i):
    for a, b, w, seed in FRONT:
        if a <= i <= b:
            break
    else:
        return img
    lay = L(w, WHITE, seed, BIG)
    bb = w[1]
    if i == 769:
        lay = fx.soften(lay, r=1.2, lum=0.92, grain_amt=0.12, seed=i)
    if i in (795, 796, 797, 798, 811, 812, 813, 820, 821, 822, 823, 794):
        lay = fx.striped_layer(lay, depth=0.42, lum=0.95, r=0.8, phase=(i % 5) / 5)
    img = comp(img, lay)
    E = {773: [(-25, 0.4)], 774: [(-25, 0.35)], 794: [(-30, 0.4)], 795: [(-20, 0.35)]}
    for dx, lum in E.get(i, []):
        img = paint_echo(img, fx.echo(lay, dx, 0, 1.0, lum, cy=350), lay)
    if i in (769, 794, 797, 806):
        img = fx.tiles(img, 7000 + i, (bb[0] - 10, bb[1], bb[2] + 10, bb[3]), n=5, amax=18)
    if i in (769, 770):
        img = fx.paint(img, fx.scratch(i, (300, 140), (360, 330), 1.3, 0.7), (0.95, 0.95, 0.95))
    if i in (809, 810):
        img = fx.paint(img, fx.scratch(i, (478, 0), (484, 165), 1.2 if i == 809 else 1.6, 0.85), (0.95, 0.95, 0.95))
    return img


# ------------------------------------------------------------------ ending
G = {830: 0.13, 831: 0.25, 832: 0.36, 833: 0.47, 834: 0.57, 835: 0.65, 836: 0.72, 837: 0.79, 838: 0.80, 839: 0.81}
FADE = {845: (0.92, 0.58), 846: (0.72, 0.07), 847: (0.42, 0.0), 848: (0.16, 0.0), 849: (0.02, 0.0)}


def ending(img, i):
    if i < 830:
        return img
    g = G.get(i, 0.81)
    if i >= 833:
        img = kit.grade(img, sat=max(0.15, 1 - (i - 832) * 0.25))
    img = fx.exclusion(img, g)
    if 836 <= i <= 845:
        img = fx.aperture(img, 0.12 if i < 840 else 0.06)
    if 840 <= i <= 849:
        st = fx.tv_static(8400 + i)
        img = img * (0.5 + 0.5 * st)
    if i in FADE:
        c, k = FADE[i]
        d = fx.radial()
        f = np.clip(c - (c - k) * (d / 0.95) ** 1.6, 0, 1)
        img = img * f[..., None]
    return img


# ------------------------------------------------------------------ frame
def frame(i):
    if i >= 850:
        return np.zeros((H, W, 3), np.float32)
    img = bgs.bg(i).astype(np.float32)
    img = big_words(img, i)
    img = lowercase(img, i)
    img = fragment(img, i)
    img = bog(img, i)
    img = middle(img, i)
    img = front(img, i)
    img = ending(img, i)
    return np.clip(img, 0, 1).astype(np.float32)
