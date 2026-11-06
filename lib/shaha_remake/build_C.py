"""Segment C: frames 437-644 (ПОЛ ЛИТРА / КОНЬЯКА / ГОЛОВА КРУЖИТСЯ / ЗАНИЖЕНАЯ ШАХА / ДЕВЧАТА МУТЯТСЯ).

Built from spec/segC.json + segC.md. frame(i) -> float32 (720, 960, 3) 0..1.
"""
import numpy as np

import kit
import bgs
import fx_C as fx

RANGE = (437, 645)

# ------------------------------------------------------------------ words: bbox (tight glyph box, ref px)
POL = ("ПОЛ", (128, 230, 366, 456))
LITRA = ("ЛИТРА", (459, 230, 846, 456))
KON = ("КОНЬЯКА", (140, 186, 808, 492))
GOL = ("ГОЛОВА", (206, 213, 818, 375))
KRU = ("КРУЖИТСЯ", (196, 429, 762, 509))
ZAN = ("ЗАНИЖЕНАЯ", (217, 321, 742, 388))
SHA = ("ШАХА", (330, 168, 635, 419))
DEV1 = ("ДЕВЧАТА", (337, 288, 645, 424))
DEV2 = ("ДЕВЧАТА", (174, 288, 469, 424))
MUT = ("МУТЯТСЯ", (513, 288, 815, 413))

MONT = "fonts/Montserrat[wght].ttf"
SERIF = "fonts/PT_Serif-Web-Regular.ttf"

WHITE = dict(kind="white", halo=((14, 12, 14), 8, 0.35), streak=(0.035, 0.025), grain=0.02, soft=0.3,
             weight=700, tracking=4.0)
DRIP = dict(WHITE, streak=(0.05, 0.03))
WIDE = dict(kind="white", halo=((14, 12, 18), 6, 0.3), streak=(0.03, 0.02), grain=0.03, soft=0.45,
            weight=800, name=MONT, tracking=0.0, steps=True)
SER = dict(kind="white", halo=((10, 10, 14), 5, 0.25), streak=(0.0, 0.0), grain=0.02, soft=0.35,
           weight=400, name=SERIF, steps=False, sharp=0.8)
RED = dict(kind="red", halo=((30, 22, 60), 13, 0.92), streak=(0.05, 0.03), grain=0.03, soft=0.3,
           weight=700, tracking=2.0)


def L(word, col, seed, look):
    t, bb = word
    return fx.layer(t + str(bb), t, bb, col, seed, **look)


def M(word, look):
    t, bb = word
    return fx.mask_of(t, bb, look.get("weight", 700), look.get("tracking", 0.0), look.get("name", "oswald"))[0]


GREY = np.array([0.62, 0.61, 0.62], np.float32)


def paint(img, alpha, col=GREY):
    return kit.over_img(img, np.broadcast_to(np.asarray(col, np.float32), img.shape), alpha)


def text_ch(layers, mult=None):
    """stack layers (bottom first) into one channel layer, with the text vignette applied."""
    P = np.zeros((kit.H, kit.W, 3), np.float32)
    A = np.zeros((kit.H, kit.W, 3), np.float32)
    for lay in layers:
        p, a = fx.to_ch(lay)
        P, A = fx.add_ch((P, A), (p, a))
    P = P * fx.text_vignette()
    if mult is not None:
        P = P * (mult[..., None] if mult.ndim == 2 else mult)
    return P, A


# ------------------------------------------------------------------ section 1: ПОЛ ЛИТРА 441-462
def pol_litra(img, i):
    lp = L(POL, (218, 214, 215), 4410, WHITE)
    ll = L(LITRA, (246, 243, 244), 4510, WHITE)
    m_pol = M(POL, WHITE)
    m_lit = M(LITRA, WHITE)
    layers = [lp] + ([ll] if i >= 451 else [])
    mult = None
    if i == 441:   # glitch-in: grey striped ghost left, coarse dither noise block in О, ПОЛ dim
        img = paint(img, fx.scan_ghost(m_pol, -52, 0, 0.55, 12.3, 0.2))
        mult = fx.noise_block(m_pol, 441, (196, 256, 368, 470), 0.42) * 0.82
    if i == 451:   # ЛИТРА in: striped ghost of the whole line, noisy ЛИТРА, ПОЛ slightly dim
        m = np.maximum(m_pol, m_lit)
        img = paint(img, fx.scan_ghost(m, -34, 0, 0.6, 12.3, 0.5))
        mult = fx.noise_block(m_lit, 451, (455, 230, 850, 456), 0.22) * 0.86
    if 445 <= i <= 462 and i not in (451, 460):   # very faint ghost dx -48
        m = np.maximum(m_pol, m_lit if i >= 451 else 0)
        img = paint(img, fx.shift2(m, -48) * 0.07)
    P, A = text_ch(layers, mult)
    if i == 460:   # slice glitch: striped bright copy of the upper part shifted -56, bands
        m = np.maximum(m_pol, m_lit)
        ghost = fx.crop_x(fx.scan_ghost(m, -56, -12, 0.85, 12.3, 0.0, smear=0), y_max=430)
        img = paint(img, ghost, np.array([0.75, 0.74, 0.75], np.float32))
        P = fx.bands(P, [(209, 300, -40), (300, 345, 22)])
        A = fx.bands(A, [(209, 300, -40), (300, 345, 22)])
    if i == 452:
        P = P * 0.95
    return fx.comp_ch(img, P, A)


# ------------------------------------------------------------------ section 2: КОНЬЯКА strobe 463-493
SEQ = {463: "g", 464: "K", 465: "K", 466: "Kd", 467: "Kb", 468: "Kb", 469: "g", 470: "K", 471: "g", 472: "K",
       473: "gK", 474: "Kd", 475: "K", 476: "Ks", 477: "K", 478: "g", 479: "K", 480: "g", 481: "K", 482: "K",
       483: "g", 484: "Kh", 485: "Kw", 486: "Kt", 487: "K", 488: "K", 489: "g", 490: "Khalf", 491: "K",
       492: "g", 493: "gf"}


def ghost_pol(img, i, k=1.0):
    """the ПОЛ ЛИТРА ghost frame: dim, smeared, eroded, П left stem gone, faint prism sparkle."""
    lp = L(POL, (160, 156, 158), 4410, WHITE)
    ll = L(LITRA, (166, 162, 165), 4510, WHITE)
    P, A = text_ch([lp, ll])
    P = P * fx.noise_block(None, 4630 + i, (100, 220, 870, 470), 0.35)[..., None]
    P, A = fx.prism(P, A, 3, -4, 6)
    P = fx.crop_x(P, x_min=150) + fx.crop_x(P, x_max=150) * 0.15
    A = fx.crop_x(A, x_min=150) + fx.crop_x(A, x_max=150) * 0.15
    return fx.comp_ch(img, P * 0.62 * k, A * 0.62 * k)


def konyaka(img, i):
    s = SEQ[i]
    if s.startswith("g"):
        img = ghost_pol(img, i, 0.35 if s == "gf" else 1.0)
        if s == "gK":   # lower part of КОНЬЯКА bleeding in
            P, A = _kon(i)
            img = fx.comp_ch(img, fx.crop_x(P, y_min=420) * 0.7, fx.crop_x(A, y_min=420) * 0.7)
        return img
    if s == "Kd":   # dim blue double exposure over the ghost
        img = ghost_pol(img, i, 0.8)
    if s == "Khalf":
        img = ghost_pol(img, i, 0.9)
    P, A = _kon(i)
    m = M(KON, WHITE)
    if s in ("K",) and i == 464 or s == "Kt":   # scanline ghost copy top-left
        img = paint(img, fx.crop_x(fx.scan_ghost(m, -40, -22, 0.5, 13, 0.3), y_max=300 if s == "K" else 232))
    if s == "Kd":
        P, A = P * np.array([0.55, 0.6, 0.95], np.float32), A * 0.75
    if s == "Kb":
        band = [(300, 345, 26 if i == 467 else -18)]
        P, A = fx.bands(P, band), fx.bands(A, band)
        img = paint(img, fx.crop_x(fx.scan_ghost(m, -30, 0, 0.55, 13, 0.1), y_min=290, y_max=360))
    if s == "Kw":
        P, A = fx.hscale(P, 1.1), fx.hscale(A, 1.1)
    if s == "Kt":
        P, A = fx.crop_x(P, y_max=451), fx.crop_x(A, y_max=451)
    if s == "Khalf":
        P, A = fx.crop_x(P, y_max=330), fx.crop_x(A, y_max=330)
    img = fx.comp_ch(img, P, A)
    if s == "Kh":   # blocky halftone blob left
        blob = np.zeros((kit.H, kit.W), np.float32)
        blob[200:320, 50:180] = 0.75
        blob = kit.halftone(kit.blur(blob, 6), 4, np.pi / 4, 1.3)
        img = paint(img, blob * 0.85, np.array([0.8, 0.82, 0.85], np.float32))
    if s == "Ks":
        img = paint(img, fx.scratch(476, (330, 470), (470, 330), 1.3, 0.85), np.array([0.92, 0.92, 0.9], np.float32))
    return img


def _kon(i):
    lay = L(KON, (236, 232, 222), 4640, dict(WHITE, soft=0.6, tracking=-2.0))
    P, A = text_ch([lay])
    # faint halftone inside the lit glyph + grainy smear, then the prism
    dots = kit.halftone(np.ones((kit.H, kit.W), np.float32) * 0.85, 4, np.pi / 4, 1.2)
    P = P * (0.85 + 0.15 * dots)[..., None]
    P = P * (1 + kit.rng(i).normal(0, 0.05, (kit.H, kit.W)).astype(np.float32))[..., None]
    return fx.prism(P, A, 7, -10, 7)


# ------------------------------------------------------------------ section 3: ГОЛОВА КРУЖИТСЯ 497-540
G_OFF = {497, 501, 503, 507, 509, 512, 517, 522, 532, 534, 537}
G_DIM = {502: 0.6, 508: 0.6, 514: 0.55, 519: 0.7, 527: 0.45, 529: 0.75, 533: 0.45}
K_ON_FROM = 514
K_OFF = {517, 522, 534}
K_DIM = {514: 0.35, 524: 0.45, 529: 0.4, 540: 0.3, 518: 1.0}
G_CROP = {500: 650, 515: 700, 530: 700}
G_ONLY_K = {518, 527, 532, 533, 537}


def golova(img, i):
    if i < 498:
        return img
    split = (7, -8, 4) if i < 526 else (2, -1, 2)
    layers_g, layers_k = [], []
    gk = 1.0 if i not in G_DIM else G_DIM[i]
    if i in G_OFF and i not in G_ONLY_K:
        gk = 0
    if i in G_ONLY_K:
        gk = {518: 0.25, 527: 0.45, 533: 0.35}.get(i, 0.0)
    out = img
    mg = M(GOL, WIDE)
    if 524 <= i <= 531 and i in (524, 525, 526, 528, 530):   # wide striped grey ghost of the whole block
        k = 1.35 if i in (525, 526, 528) else 1.0
        mk = M(KRU, WIDE)
        mm = np.maximum(mg, mk if i >= 525 else 0)
        gh = fx.hscale(fx.scan_ghost(mm, -10 if i != 524 else -150, -6, 0.5, 13, 0.4), k)
        out = paint(out, gh)
    if gk > 0:
        P, A = text_ch([L(GOL, (214, 214, 204), 4980, WIDE)])
        if i in G_CROP:
            P, A = fx.crop_x(P, G_CROP[i]), fx.crop_x(A, G_CROP[i])
        if i == 529:
            P, A = fx.halftone_ch(P, A, 4.0, np.pi / 4, 1.2)
        P = P * (1 + kit.rng(i).normal(0, 0.06, (kit.H, kit.W)).astype(np.float32))[..., None]
        P, A = fx.prism(P, A, *split)
        out = fx.comp_ch(out, P * gk, A * gk)
    if i >= K_ON_FROM and i not in K_OFF:
        kk = K_DIM.get(i, 1.0)
        text = "КРУЖИ СЯ" if i == 528 else "КРУЖИТСЯ"
        P, A = text_ch([L((text, KRU[1]), (212, 216, 192), 5150, WIDE)])
        if i == 530:   # КРУЖИТСЯ as a striped ghost only
            P, A = P * fx.scanlines(phase=0.2)[..., None], A * 0.6
        P, A = fx.prism(P, A, *(6, -8, 3) if i < 526 else (2, -1, 2))
        out = fx.comp_ch(out, P * kk, A * kk)
    return out


# ------------------------------------------------------------------ section 4: ЗАНИЖЕНАЯ ШАХА 541-598
Z_GHOST = {541, 542, 550, 557, 558, 575, 576, 577, 579, 586, 589, 590, 591}
Z_RAMP = {541: 0.82, 542: 0.9, 543: 0.95, 544: 0.99}


def zan_ghost(img, i):
    """dim grey copy 1.15x wider with each glyph mirrored in place (reads Ɛ…R at the ends)."""
    t, bb = ZAN
    m, lps = fx.mask_of(t, bb, 400, 0.0, SERIF)
    out = np.zeros_like(m)
    for a, b in lps:
        a, b = int(max(0, a)), int(min(kit.W, b + 1))
        out[:, a:b] = np.maximum(out[:, a:b], m[:, a:b][:, ::-1])
    g = fx.hscale(out, 1.14, 480)
    return paint(img, kit.blur(g, 0.8) * 0.38, np.array([0.7, 0.7, 0.74], np.float32))


def zan_shaha(img, i):
    if i in Z_GHOST:
        img = zan_ghost(img, i)
    k = Z_RAMP.get(i, 1.0) * (0.6 if i == 598 else 1.0)
    lz = L(ZAN, (204, 203, 214), 5410, SER)
    P, A = text_ch([lz])
    if i == 550:
        P, A = fx.bands(P, [(321, 352, -28)]), fx.bands(A, [(321, 352, -28)])
        img = paint(img, fx.hscale(M(ZAN, SER), 1.17) * 0.3)
    img = fx.comp_ch(img, P * k, A * k)
    if i >= 569:
        ls = L(SHA, (178, 44, 52), 5690, RED)
        P, A = text_ch([ls])
        # knock-out plate: the navy halo hides the middle letters of ЗАНИЖЕНАЯ
        m = M(SHA, RED)
        plate = kit.blur(kit.dilate(m, 12), 5)
        plate = np.clip(plate * 1.5, 0, 1) * 0.92
        img = paint(img, plate * k, np.array([30, 22, 60], np.float32) / 255 * 0.8)
        if i >= 575:
            P = P * fx.checker(i // 3, (500, 300, 640, 420), 2, 0.35)[..., None]
        img = fx.comp_ch(img, P * k, A * k)
    return img


# ------------------------------------------------------------------ section 5: ДЕВЧАТА МУТЯТСЯ 599-644
def devchata(img, i):
    two = i >= 619
    dev = DEV2 if two else DEV1
    ld = L(dev, (240, 237, 238), 5990, DRIP)
    layers = [ld]
    m = M(dev, DRIP)
    if two:
        lm = L(MUT, (232, 228, 230), 6190, DRIP)
        mm = M(MUT, DRIP)
        if i in (629, 630):   # broken У: dark diagonal stroke through it
            pass
        layers.append(lm)
        m = np.maximum(m, mm)
    dr = fx.drips(m, 5991 if not two else 6191)
    k = {631: 0.92, 632: 0.93, 641: 0.92, 642: 0.92, 643: 0.92, 644: 0.78, 617: 0.92, 618: 0.9}.get(i, 1.0)
    P, A = text_ch(layers, dr)
    if i in (619, 620):   # glitch-in: whole-line dotted ghost left + scanlines
        g = fx.scan_ghost(m, -45, 0, 0.75 if i == 619 else 0.5, 13.2, 0.0, smear=2) * fx.dot_dither(i)
        img = paint(img, g)
        P = P * (0.75 + 0.25 * fx.scanlines(period=13.2, phase=0.5))[..., None]
    if i == 621 or i in (617, 618):
        img = paint(img, fx.scan_ghost(m, 40 if i == 621 else 30, 0, 0.45, 13.2, 0.3))
    if i in (615, 616):
        img = paint(img, fx.scan_ghost(m, 28, 0, 0.6, 13.2, 0.25))
        P = P * (0.7 + 0.3 * fx.scanlines(period=13.2))[..., None]
        bnd = [(300, 330, -9), (360, 385, 12)]
        P, A = fx.bands(P, bnd), fx.bands(A, bnd)
    if i == 614:
        P, A = fx.bands(P, [(380, 420, -7)]), fx.bands(A, [(380, 420, -7)])
    if i in (631, 632, 644):
        img = paint(img, fx.scan_ghost(m, -40, 0, 0.35, 13.2, 0.1) * fx.dot_dither(i))
    if i == 640:
        img = paint(img, fx.scan_ghost(m, -45, 0, 0.6, 13.2, 0.0))
        img = paint(img, fx.scan_ghost(m, 55, 0, 0.45, 13.2, 0.5))
        bnd = [(288, 330, -10), (330, 372, 8)]
        P, A = fx.bands(P, bnd), fx.bands(A, bnd)
    if i == 644:
        P, A = fx.crop_x(P, x_max=800), fx.crop_x(A, x_max=800)
    img = fx.comp_ch(img, P * k, A * k)
    if two and i in (629, 630):
        img = paint(img, fx.scratch(629, (563, 300), (605, 405), 2.2, 0.85), np.array([0.05, 0.04, 0.05], np.float32))
    return img


# ------------------------------------------------------------------ frame
def frame(i):
    img = bgs.bg(i).astype(np.float32)
    if 441 <= i <= 462:
        img = pol_litra(img, i)
    elif 463 <= i <= 493:
        img = konyaka(img, i)
    elif 497 <= i <= 540:
        img = golova(img, i)
    elif 541 <= i <= 598:
        img = zan_shaha(img, i)
    elif 599 <= i <= 644:
        img = devchata(img, i)
    return kit.grain(img, 9000 + i, 0.012)
