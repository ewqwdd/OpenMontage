"""Segment B (frames 235-436): МНЕ КАЖЕТСЯ… / САМ / ЮРА ХОЙ / НАДЕЮСЬ… / ЗА УПОКОЙ.
Built from spec/segB.json. frame(i) -> float32 (720, 960, 3) 0..1.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

import kit
import bgs
import fx_B as fx

RANGE = (235, 437)
HERE = Path(__file__).parent
SPEC = json.loads((HERE / "spec" / "segB.json").read_text(encoding="utf-8"))
T = {t["id"]: t for t in SPEC["texts"]}
LET = T["A_line"]["letters_per_frame"]
YURA = T["ЮРА"]["state_per_frame"]
HOY = T["ХОЙ"]["state_per_frame"]
ZA = T["ЗА_УПОКОЙ"]["state_per_frame"]

# ------------------------------------------------------------------ A-line phases (text, x0, x1)
A_PH = [(235, "МНЕ", 430, 530), (241, "МНЕ КАЖЕТСЯ", 310, 650), (255, "МНЕ КАЖЕТСЯ, МНОЮ", 218, 742),
        (270, "МНЕ КАЖЕТСЯ, МНОЮ ГОРДИСЯ", 140, 827), (287, "МНЕ КАЖЕТСЯ, МНОЮ ГОРДИСЯ БЫ", 129, 812)]
A_CAP, A_COL = 89, (220, 219, 221)
A_SMEAR = {238, 239, 247, 250, 252, 253, 255, 256, 257, 258, 259, 260, 266, 270, 274, 280, 281, 291, 306, 307, 325, 330}

C_PH = [(336, "НАДЕЮСЬ", 389, 575), (359, "НАДЕЮСЬ ВСЕ", 348, 612), (364, "НАДЕЮСЬ ВСЕ МОИ", 300, 660),
        (377, "НАДЕЮСЬ ВСЕ МОИ КЕНТЫ", 231, 725), (392, "НАДЕЮСЬ ВСЕ МОИ КЕНТЫ ВЫПЬЮТ", 146, 809)]
C_CAP, C_TOP, C_COL = 72, 428, (229, 225, 224)
C_ENTRY = {359: 1.0, 362: 1.0, 363: 1.0, 376: 1.0, 377: 1.0, 392: 0.5}
C_GHOST = {370: .3, 378: .3, 388: .25, 389: .25, 390: .2, 391: .25, 392: .3, 395: .35, 396: .35, 397: .3, 398: .3,
           399: .3, 400: .3, 406: .3, 407: .3, 408: .3, 409: .35, 410: .3, 411: .25, 422: .3, 428: .3, 430: .3,
           434: .55, 435: .7, 436: .65}

BIG_CAP, BIG_TOP = 294, 192
YURA_X, HOY_X = (136, 472), (526, 826)
SAM = ("САМ", 160, 394, 566, 326)
ZA_CAP, ZA_TOP = 179, 232
ZA_FULL = (182, 820)
ZA_ALONE = (138, 233)


def phase(table, i):
    cur = None
    for p in table:
        if i >= p[0]:
            cur = p
    return cur


# ------------------------------------------------------------------ A-line (soft glowing white, dropout)
def a_line(img, i):
    _, text, x0, x1 = phase(A_PH, i)
    top = 308 if i < 297 else 228
    vis = LET.get(str(i))
    m = fx.line(text, A_CAP, x0, x1, top, 700, 0.005, vis=vis)
    sy = 1.0
    if 255 <= i <= 261:                        # МНОЮ entry: box stretched ~1.3 x vertically
        sy = [1.35, 1.4, 1.42, 1.38, 1.3, 1.25, 1.12][i - 255]
        m = fx.scale_about(m, 1.0, sy, 480, top - 12)
    full = fx.line(text, A_CAP, x0, x1, top, 700, 0.005)          # for glow / grain box
    sm = i in A_SMEAR
    soft = fx.blur_hv(m, 3.6, 3.0)
    if sm:
        soft = 0.55 * kit.box_blur_h(soft, 9) + 0.45 * kit.box_blur_h(soft, 26)
    # glow (bloom sigma ~18, 25 %)
    gl = kit.blur(np.maximum(soft, 0.35 * full), 18) * 0.42
    img = fx.screen_col(img, (175, 182, 200), gl)
    # fill with streaks
    st = fx.vstreak_field(i * 7 + 1, amp=0.12)
    a = np.clip(soft * 1.15, 0, 1)
    col = np.asarray(A_COL, np.float32)[None, None] / 255 * st[..., None]
    lay = col
    # halftone patches on the entry glitch / 280
    if 255 <= i <= 261 or i == 280:
        r = kit.rng(i * 13)
        hm = np.zeros_like(a)
        for _ in range(3 if i != 280 else 2):
            bx0 = int(r.integers(x0 - 40, x1 - 80)); bw = int(r.integers(60, 160))
            hm[top - 20:top + A_CAP + 30, max(0, bx0):bx0 + bw] = 1
        if i == 280:
            hm[:, 120:180] = 0; hm[top - 15:top + A_CAP + 10, 120:180] = 1; hm[top - 15:top + A_CAP + 10, 330:420] = 1
        dots = fx.quincunx(np.clip(kit.blur(m, 6) * 1.4 + 0.25 * full, 0, 1), 6.0)
        a = a * (1 - hm) + dots * hm * 0.9
    if 271 <= i <= 273:                        # 12 px scanlines over the new word (right part)
        sl = fx.scanlines(kit.H, kit.W, 12, 0.5, 0.75, phase=i * 3)
        xs = int(x0 + (x1 - x0) * 0.6)
        a[:, xs:] = a[:, xs:] * sl[:, xs:]
    img = kit.over_img(img, lay, a)
    # animated grain on text + halo box
    gb = np.clip(kit.blur(full, 22) * 3.5, 0, 1)
    amp = 0.065 if i == 270 else 0.045
    img = np.clip(img + (fx.grain_field(i * 31 + 5) * amp * gb)[..., None], 0, 1)
    # slices
    if 255 <= i <= 261 or i in (280, 284):
        img = fx.hslices(img, i * 17, (top - 20, top + A_CAP + 40), n=4 if i != 284 else 6, hmin=8, hmax=30,
                         amp=60 if i != 284 else 30, xr=(max(0, x0 - 60), min(kit.W, x1 + 60)))
    if i == 284:                               # partial blackout of the middle
        img[top:top + A_CAP, 430:620] *= 0.35
    return img


# ------------------------------------------------------------------ red САМ
def sam(img, i):
    text, cap, x0, x1, top = SAM
    vis = {297: "СА_", 298: "С_М", 299: "С_М", 300: "__·"}.get(i, "САМ")
    m = fx.line(text, cap, x0, x1, top, 700, 0.0, vis=vis)
    soft = fx.blur_hv(m, 5.0, 6.0)
    img = fx.screen_col(img, (150, 20, 25), kit.blur(soft, 10) * 0.45)
    st = fx.vstreak_field(i * 5 + 3, amp=0.1)
    col = np.asarray((185, 42, 45), np.float32)[None, None] / 255 * st[..., None]
    img = kit.over_img(img, col, np.clip(soft * 1.2, 0, 1))
    return img


# ------------------------------------------------------------------ big prism words
@lru_cache(maxsize=8)
def big_mask(text, x0, x1, top, cap, tracking=0.0):
    return fx.line(text, cap, x0, x1, top, 700, tracking)


def plate(img, m, op=0.88):
    p = kit.blur(kit.dilate(m, 3), 7)
    return kit.over(img, (21, 15, 17), np.clip(p * 1.4, 0, 1) * op)


def white_prism(img, m, i, col=(222, 222, 220), op=1.0, spread=1.0, rainbow=False, soft=(5.5, 6.5)):
    s = fx.blur_hv(m, *soft)
    a3 = fx.prism(s, spread, fx.RAINBOW if rainbow else fx.PRISM_TINTS) * op
    # navy fringe just outside
    nav = np.clip(fx.blur_hv(kit.dilate(m, 4), 7, 7) - s, 0, 1) * 0.55 * op
    img = kit.over(img, (20, 40, 100), nav)
    st = fx.vstreak_field(i * 11 + 7, amp=0.06)
    c = np.asarray(col, np.float32)[None, None] / 255 * st[..., None]
    return img * (1 - a3) + c * a3


def big_word(img, i, which, state):
    if which == "ЮРА":
        m = big_mask("ЮРА", YURA_X[0], YURA_X[1], BIG_TOP, BIG_CAP)
    else:
        m = big_mask("ХОЙ", HOY_X[0], HOY_X[1], BIG_TOP, BIG_CAP)
    img = plate(img, m)
    st = state.split()[0].split("+")[0]
    if st == "W":
        tint = "blue" in state
        img = white_prism(img, m, i, (205, 215, 232) if tint else (222, 222, 220), 0.9 if "dim" in state else 1.0)
    elif st == "B":
        s = fx.blur_hv(m, 6, 6)
        dots = fx.quincunx(np.clip(s, 0, 1), 6.0)
        img = kit.over(img, (95, 140, 200), np.clip(0.25 * s + 0.25 * dots, 0, 1))
    elif st == "M":
        img = white_prism(img, m, i, op=0.6)
        img = fx.hslices(img, i * 19, (BIG_TOP, BIG_TOP + BIG_CAP), n=4, amp=25,
                         xr=(HOY_X[0] - 20, HOY_X[1] + 20) if which == "ХОЙ" else (YURA_X[0] - 20, YURA_X[1] + 20))
    return img


def yura_extras(img, i):
    if i in (303, 304):      # white solid copies of ЮРА bands pushed left
        bands = [(249, 313), (320, 327)] if i == 303 else [(258, 333)]
        m = big_mask("ЮРА", YURA_X[0], YURA_X[1], BIG_TOP, BIG_CAP)
        for a, b in bands:
            band = np.zeros_like(m); band[a:b] = fx.blur_hv(m, 4, 1)[a:b]
            img = kit.over(img, (205, 205, 205), kit.shift(band, -115, 0) * 0.95)
    if i in (312, 327):      # thin red line + blue line under it
        y = 250 if i == 312 else 262
        img[y:y + 3, 110:500] = img[y:y + 3, 110:500] * 0.3 + np.array([0.75, 0.12, 0.12]) * 0.7
        img[y + 3:y + 5, 110:500] = img[y + 3:y + 5, 110:500] * 0.4 + np.array([0.15, 0.3, 0.7]) * 0.6
    if i in (319, 325, 334):  # bottom RGB slices
        x0, x1 = (110, 500) if i != 334 else (500, 850)
        r = kit.rng(i)
        for _ in range(4):
            y = int(r.integers(380, 470)); h = int(r.integers(3, 9)); dx = int(r.integers(-30, 30))
            band = img[y:y + h, x0:x1].copy()
            band = np.roll(band, dx, 1)
            band[..., int(r.integers(0, 3))] *= 0.3
            img[y:y + h, x0:x1] = np.clip(band * 1.3, 0, 1)
    if i == 320:             # zoomed ghost of both words behind
        pass
    return img


# ------------------------------------------------------------------ C-line (sharp, static grunge)
@lru_cache(maxsize=8)
def c_tex(text):
    """static fill texture for the C-line phase: vertical streaks + dark specks + grain (held)."""
    seed = sum(map(ord, text))
    st = fx.vstreak_field(seed, amp=0.09)
    g = fx.grain_field(seed + 1, 0.6) * 0.03
    r = kit.rng(seed + 2)
    sp = (r.random((kit.H, kit.W)) < 0.012).astype(np.float32)
    sp = kit.blur(sp, 0.8) * 2.5
    return np.clip(st * (1 + g) - 0.35 * sp, 0, 1.2)


@lru_cache(maxsize=8)
def c_mask(text, x0, x1):
    m = fx.line(text, C_CAP, x0, x1, C_TOP, 700, 0.005)
    # jagged left edges in bands (static): +-1..3 px
    r = kit.rng(len(text) * 7)
    y = C_TOP - 4
    out = m.copy()
    while y < C_TOP + C_CAP + 14:
        b = int(r.integers(2, 30))
        if r.random() < 0.4:
            out[y:y + b] = np.roll(m[y:y + b], int(r.integers(-2, 3)), axis=1)
        y += b
    return fx.blur_hv(out, 0.7, 0.7)


def c_line(img, i):
    _, text, x0, x1 = phase(C_PH, i)
    if i in (359, 362, 363) and text == "НАДЕЮСЬ ВСЕ" and i >= 362:
        text, x0, x1 = "НАДЕЮСЬ ВСЕ", 348, 612
    m = c_mask(text, x0, x1)
    tex = c_tex(text)
    cx = (x0 + x1) / 2
    # zoomed ghost copy behind
    g = C_GHOST.get(i)
    if g:
        gm = fx.scale_about(m, 1.20, 1.30, cx, C_TOP)
        dots = fx.quincunx(kit.blur(gm, 1.2), 6.0)
        img = kit.over(img, (200, 196, 196), np.clip(0.5 * gm + 0.5 * dots, 0, 1) * g)
    # light leak
    if 388 <= i <= 392:
        yy, xx = np.mgrid[0:kit.H, 0:kit.W].astype(np.float32)
        e = np.exp(-(((xx - 200) / 130) ** 2 + ((yy - 470) / 45) ** 2))
        k = {388: .9, 389: .8, 390: .6, 391: .85, 392: 1.0}[i]
        img = fx.screen_col(img, (110, 80, 95), e * k)
    if i in (345, 346):                          # scale pop
        m = fx.scale_about(m, 1.25, 1.30, cx, C_TOP)
    a = m
    col = np.asarray(C_COL, np.float32)[None, None] / 255 * tex[..., None]
    if i in C_ENTRY:                            # entry glitch: smear + halftone + squash, dimmer
        k = C_ENTRY[i]
        s = fx.scale_about(m, 1.0, 0.9, cx, C_TOP + 36)
        s = kit.box_blur_h(fx.blur_hv(s, 2, 2), int(12 * k))
        dots = fx.quincunx(np.clip(s * 1.2, 0, 1), 6.0)
        a = np.clip(s * (1 - 0.55 * k) + dots * 0.55 * k, 0, 1) * (1 - 0.22 * k)
    if i == 344:                                 # right part shifted down
        a = a.copy(); a[:, 500:] = np.roll(a[:, 500:], 6, 0)
    img = kit.over_img(img, col, a)
    if 347 <= i <= 350:                          # echo below
        img = kit.over(img, (200, 196, 196), kit.shift(m, -2, 11) * 0.35 * (1 - m))
    if i in (386, 387):                          # white scratch
        yy, xx = np.mgrid[500:540, 200:260]
        d = np.abs((yy - 500) - (260 - xx) * 0.55)
        img[500:540, 200:260] = np.maximum(img[500:540, 200:260], (np.clip(1.5 - d, 0, 1) * 0.9)[..., None])
    if i == 436:
        img = fx.hslices(img, 436, (C_TOP - 5, C_TOP + C_CAP + 20), n=5, hmin=8, hmax=20, amp=30)
    return img


# ------------------------------------------------------------------ ЗА УПОКОЙ
def za(img, i):
    st = ZA.get(str(i), "")
    if 413 <= i <= 415:
        m = big_mask("ЗА", ZA_ALONE[0], ZA_ALONE[1], ZA_TOP, ZA_CAP)
        yy = np.arange(kit.H, dtype=np.float32)[:, None]
        if i == 413:
            m = m * (yy < 366)
        grad = np.clip((yy - ZA_TOP) / ZA_CAP, 0, 1)
        img = plate(img, m, 0.5)
        s = fx.blur_hv(m, 5, 6)
        col = (np.array([0.88, 0.89, 0.86])[None, None] * (1 - grad[..., None] * 0.5)
               + np.array([0.25, 0.35, 0.55])[None, None] * grad[..., None] * 0.5)
        a3 = fx.prism(s, 0.8) * (0.72 if i == 415 else 1.0)
        return img * (1 - a3) + col * a3
    if i < 417 or i > 435:
        if i == 422:          # chroma bokeh specks
            r = kit.rng(422)
            for _ in range(7):
                x, y = int(r.integers(190, 820)), int(r.integers(255, 335))
                for c, dx in ((0, -4), (1, 0), (2, 4)):
                    img[y - 4:y + 4, x + dx - 5:x + dx + 5, c] = np.maximum(img[y - 4:y + 4, x + dx - 5:x + dx + 5, c], 0.6)
        return img
    m = big_mask("ЗА УПОКОЙ", ZA_FULL[0], ZA_FULL[1], ZA_TOP, ZA_CAP)
    if st.startswith("OFF"):
        if "faint" in st:
            img = kit.over(img, (120, 125, 150), fx.blur_hv(m, 6, 6) * 0.12)
        return img
    soft = (8.0, 9.5) if "soft" in st else (6.0, 7.5)
    if i == 425:
        m = fx.scale_about(m, 1.05, 1.35, 500, ZA_TOP)
        soft = (12, 10)
    if i == 435:
        m = fx.scale_about(m, 1.17, 1.05, 500, ZA_TOP)
    img = plate(img, m, 0.55)
    op = 1.0
    col = (230, 232, 216)
    if st.startswith("DIM"):
        op, col = 0.38, (120, 150, 210)
    if "dim" in st:
        op = 0.75
    if "blue" in st:
        col = (205, 220, 235)
    img = white_prism(img, m, i, col, op, 1.0, rainbow=True, soft=soft)
    if i == 428:
        img = kit.over(img, (180, 185, 190), kit.shift(fx.blur_hv(m, 6, 6), -38, 0) * 0.25 * (1 - m))
    if i == 420:
        sl = fx.scanlines(kit.H, kit.W, 9, 0.75, 0.55, phase=2)
        img[ZA_TOP - 10:ZA_TOP + ZA_CAP + 10] *= sl[ZA_TOP - 10:ZA_TOP + ZA_CAP + 10, :, None]
    if i in (425, 435):
        reg = slice(ZA_TOP - 20, ZA_TOP + ZA_CAP + 80)
        dots = fx.quincunx(np.clip(img[reg].mean(-1) * 1.3, 0, 1), 6.0)
        img[reg] = img[reg] * (0.45 + 0.55 * dots[..., None])
        if i == 435:
            sl = fx.scanlines(kit.H, kit.W, 5.5, 0.5, 0.45)
            img[reg] *= sl[reg][..., None]
            img = fx.hslices(img, 435, (ZA_TOP, ZA_TOP + ZA_CAP), n=4, amp=30)
    if i == 434:
        r = kit.rng(434)
        for _ in range(4):
            y = int(r.integers(ZA_TOP + 20, ZA_TOP + ZA_CAP)); h = int(r.integers(8, 24))
            img[y:y + h, 24:int(r.integers(120, 260))] = np.maximum(img[y:y + h, 24:int(r.integers(120, 260))], 0.78)
    return img


# ------------------------------------------------------------------ frame
def frame(i):
    img = bgs.bg(i).astype(np.float32).copy()
    if 235 <= i <= 335:
        img = a_line(img, i)
        if i >= 297:
            img = sam(img, i)
        if i >= 300:
            if i == 320:      # zoomed ghost of ЮРА ХОЙ behind
                gm = fx.scale_about(np.maximum(big_mask("ЮРА", *YURA_X, BIG_TOP, BIG_CAP),
                                               big_mask("ХОЙ", *HOY_X, BIG_TOP, BIG_CAP)), 1.12, 1.05, 480, BIG_TOP)
                img = kit.over(img, (150, 150, 160), fx.blur_hv(gm, 8, 6) * 0.3)
            img = big_word(img, i, "ЮРА", YURA.get(str(i), "S"))
            if i >= 313:
                img = big_word(img, i, "ХОЙ", HOY.get(str(i), "S"))
            img = yura_extras(img, i)
    elif 336 <= i <= 436:
        if i == 336:          # 1-frame dark ghost of ЮРА ХОЙ
            gm = np.maximum(big_mask("ЮРА", *YURA_X, BIG_TOP, BIG_CAP), big_mask("ХОЙ", *HOY_X, BIG_TOP, BIG_CAP))
            img = kit.over(img, (45, 42, 46), fx.blur_hv(gm, 8, 8) * 0.6)
        img = c_line(img, i)
        img = za(img, i)
    return np.clip(img, 0, 1).astype(np.float32)
