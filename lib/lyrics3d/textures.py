"""Low-res textures for the room (PS1-horror look, cold palette). Run with the repo .venv python.

    .venv/Scripts/python lib/lyrics3d/textures.py

Writes assets/tex/*.png. Everything is drawn here: no downloads, no paid generation.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "assets" / "tex"
OUT.mkdir(parents=True, exist_ok=True)
R = np.random.default_rng(7)


def save(name, a):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(OUT / f"{name}.png")


def grime(a, amount=0.25, cell=8, seed=1):
    """Multiply by blotchy low-frequency noise + per-texel noise: worn, dirty surfaces."""
    r = np.random.default_rng(seed)
    h, w = a.shape[:2]
    low = r.random((h // cell + 2, w // cell + 2))
    low = np.array(Image.fromarray((low * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)) / 255.0
    fine = r.random((h, w))
    k = 1 - amount * (0.65 * low + 0.35 * fine)
    return a * k[..., None]


def pal(*cols):
    return np.array(cols, float)


# ---------------------------------------------------------------- rug (floor) and wall carpet
def rug(w, h, P, seed, medallion=True):
    """Soviet-style ornament carpet. P: [dark, field, light, accent, accent2]."""
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    u, v = np.minimum(x, w - 1 - x), np.minimum(y, h - 1 - y)      # distance from the edges
    e = np.minimum(u, v)
    cx, cy = np.abs(x - (w - 1) / 2), np.abs(y - (h - 1) / 2)      # distance from the centre
    idx = np.ones((h, w), int)                                     # field
    lat = (((cx + cy).astype(int) % 14) < 2) | (((cx - cy).astype(int) % 14) < 2)
    idx[lat] = 0
    dots = (((cx + cy).astype(int) % 14) == 7) & (((cx - cy).astype(int) % 14) == 7)
    idx[dots] = 3
    if medallion:
        d = cx / (w * 0.30) + cy / (h * 0.36)
        ring = (d * 9).astype(int)
        m = d < 1
        idx[m] = np.choose(ring[m] % 4, [2, 3, 0, 4])
        star = (np.abs(cx - cy * w / h) < 2) & m
        idx[star] = 2
    # borders, from the outside in
    zz = (((u + v) // 2) % 4)
    idx[e < 15] = np.choose(zz[e < 15], [3, 0, 4, 0])
    idx[(e < 15) & (((u - v) % 6) == 0)] = 2
    idx[e < 12] = 0
    idx[(e < 11) & (e >= 4)] = np.choose(((u + v)[(e < 11) & (e >= 4)] // 3) % 2, [2, 1])
    idx[(e < 11) & (e >= 4) & ((np.maximum(u, v) % 9) < 2)] = 3
    idx[e < 4] = 0
    idx[e < 2] = 4
    fringe = (e < 1) & ((x + y) % 2 == 0)
    a = P[idx]
    a[fringe] = P[2]
    a += r.normal(0, 9, a.shape[:2])[..., None]                     # pile noise
    wear = r.random((h, w)) < 0.05
    a[wear] = a[wear] * 0.7
    return grime(a, 0.35, 12, seed)


RUG = pal((18, 22, 38), (38, 52, 86), (176, 182, 178), (112, 44, 60), (70, 116, 138))
save("rug", rug(96, 128, RUG, 3))
WALLRUG = pal((14, 18, 34), (30, 60, 84), (160, 170, 172), (96, 36, 58), (56, 104, 120))
save("wallrug", rug(128, 80, WALLRUG, 5))


# ---------------------------------------------------------------- wallpaper
def wallpaper(w=64, h=64, seed=2):
    r = np.random.default_rng(seed)
    base, stripe, flower, leaf = pal((74, 86, 100), (60, 72, 88), (128, 138, 140), (48, 70, 78))
    a = np.tile(base, (h, w, 1))
    y, x = np.mgrid[0:h, 0:w]
    a[(x % 32) < 3] = stripe
    a[(x % 32) == 16] = stripe
    for ox, oy in ((9, 8), (25, 40), (9 + 32, 40 + 0), (25 + 32, 8)):
        for dx, dy in ((0, 0), (-2, -1), (2, -1), (-1, 2), (1, 2), (0, -3)):
            a[(oy + dy) % h, (ox + dx) % w] = flower
            a[(oy + dy + 1) % h, (ox + dx) % w] = flower
        for k in range(1, 9):
            a[(oy + 3 + k) % h, (ox + (k // 3) % 2) % w] = leaf
        a[(oy + 8) % h, (ox + 2) % w] = leaf
        a[(oy + 7) % h, (ox + 3) % w] = leaf
    a += r.normal(0, 4, (h, w))[..., None]
    return grime(a, 0.3, 16, seed)


save("wallpaper", wallpaper())

# floor boards (around the rug)
h, w = 32, 64
a = np.tile(pal((52, 50, 56))[0], (h, w, 1))
y, x = np.mgrid[0:h, 0:w]
a[(y % 8) == 0] = (26, 26, 32)
a[((x + (y // 8) * 23) % 40) == 0] = (26, 26, 32)
a += (np.random.default_rng(4).normal(0, 1, (h // 8 + 1, 1)).repeat(8, 0)[:h] * 9)[..., None]
save("floor", grime(a, 0.4, 6, 4))

# ceiling / plaster, door
a = np.tile(pal((88, 92, 98))[0], (32, 32, 1))
save("plaster", grime(a, 0.5, 5, 9))
a = np.tile(pal((70, 76, 84))[0], (64, 32, 1))
y, x = np.mgrid[0:64, 0:32]
a[(x < 2) | (x > 29) | (y < 2) | (y > 61)] = (40, 44, 52)
a[((x > 5) & (x < 26) & (((y > 6) & (y < 28)) | ((y > 34) & (y < 58)))) & ((x == 6) | (x == 25) | (y == 7) | (y == 27) | (y == 35) | (y == 57))] = (46, 50, 58)
save("door", grime(a, 0.3, 8, 10))

# mattress ticking, blanket plaid
a = np.tile(pal((120, 126, 132))[0], (32, 32, 1))
y, x = np.mgrid[0:32, 0:32]
a[(x % 8) < 2] = (52, 66, 96)
a[(x % 8) == 4] = (90, 98, 112)
save("mattress", grime(a, 0.45, 6, 11))
a = np.tile(pal((36, 44, 66))[0], (32, 32, 1))
a[(x % 16) < 5] = (52, 64, 90)
a[(y % 16) < 5] = a[(y % 16) < 5] * 0.75 + np.array((30, 30, 44)) * 0.25 + 14
a[(x % 16) == 9] = (110, 40, 56)
a[(y % 16) == 9] = (110, 40, 56)
save("plaid", grime(a, 0.35, 6, 12))

# cardboard, pizza box lid, pizza
a = np.tile(pal((132, 118, 100))[0], (32, 32, 1))
a[(y % 4) == 0] = (120, 106, 90)
save("cardboard", grime(a, 0.3, 6, 13))
a = np.tile(pal((150, 138, 122))[0], (48, 48, 1))
y, x = np.mgrid[0:48, 0:48]
d = np.hypot(x - 23.5, y - 22)
a[(d < 15) & (d > 12)] = (150, 40, 48)
a[(d < 9)] = (150, 40, 48)
a[(d < 9) & ((np.arctan2(y - 22, x - 23.5) * 4 / np.pi).astype(int) % 2 == 0)] = (222, 208, 180)
a[(y > 40) & (y < 45) & (x > 8) & (x < 40) & (x % 4 != 0)] = (150, 40, 48)
a[(x < 2) | (x > 45) | (y < 2) | (y > 45)] = (112, 98, 84)
save("pizzabox", grime(a, 0.3, 8, 14))
a = np.tile(pal((170, 150, 110))[0], (32, 32, 1))
y, x = np.mgrid[0:32, 0:32]
d = np.hypot(x - 15.5, y - 15.5)
a[d < 14] = (196, 150, 70)
a[d < 12] = (170, 60, 44)
rr = np.random.default_rng(15)
for _ in range(26):
    px, py = rr.integers(5, 27, 2)
    if np.hypot(px - 15.5, py - 15.5) < 10:
        a[py:py + 2, px:px + 2] = (224, 200, 140) if rr.random() < 0.6 else (110, 30, 30)
a[d >= 14] = (150, 138, 122)
save("pizza", grime(a, 0.2, 6, 15))


# ---------------------------------------------------------------- TV static (4 frames), console, posters, misc
for i in range(4):
    r = np.random.default_rng(100 + i)
    n = r.random((48, 64))
    band = (np.sin((np.arange(48) + i * 9) / 5.0) * 0.5 + 0.5)[:, None]
    lumi = 0.35 + 0.65 * n * (0.55 + 0.45 * band)
    a = np.stack([lumi * 90, lumi * 150, lumi * 255], -1)
    a[(np.arange(48) % 2) == 0] *= 0.82
    save(f"tv_{i}", a)

FONT = None
for cand in ("C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/arialbd.ttf"):
    if Path(cand).exists():
        FONT = cand
        break


def label(name, text, size, fg, bg, fs=10, border=None):
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, fs) if FONT else ImageFont.load_default()
    lines = text.split("\n")
    th = sum(d.textbbox((0, 0), ln, font=f)[3] + 1 for ln in lines)
    yy = (size[1] - th) // 2
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=f)
        d.text(((size[0] - bb[2]) // 2, yy), ln, font=f, fill=fg)
        yy += bb[3] + 1
    if border:
        d.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=border)
    im = im.resize(size, Image.NEAREST)
    im.save(OUT / f"{name}.png")
    return np.array(im).astype(float)


# posters: abstract cold pixel posters
def poster(name, seed, cols):
    r = np.random.default_rng(seed)
    a = np.tile(np.array(cols[0], float), (48, 32, 1))
    y, x = np.mgrid[0:48, 0:32]
    k = r.integers(0, 3)
    if k == 0:
        d = np.hypot(x - 16, y - 20)
        a[(d.astype(int) // 3) % 2 == 0] = cols[1]
        a[d < 6] = cols[2]
    elif k == 1:
        a[((x // 4 + y // 4) % 2) == 0] = cols[1]
        a[14:30, 8:24] = cols[2]
        a[18:26, 12:20] = cols[0]
    else:
        for i in range(0, 48, 6):
            a[i:i + 3, : int(8 + r.integers(0, 22))] = cols[1]
        a[30:44, 6:26] = cols[2]
    a[40:46, 3:29][(x[40:46, 3:29] % 3) != 0] = cols[2]
    a[(x < 1) | (x > 30) | (y < 1) | (y > 46)] = (150, 156, 160)
    save(name, grime(a, 0.3, 8, seed))


poster("poster_0", 21, [(20, 26, 44), (60, 110, 150), (190, 196, 200)])
poster("poster_1", 22, [(110, 36, 52), (24, 28, 40), (180, 186, 190)])
poster("poster_2", 26, [(28, 60, 74), (14, 18, 30), (170, 190, 196)])

# window: night glass behind blinds
a = np.zeros((64, 48, 3))
y, x = np.mgrid[0:64, 0:48]
a[:] = (70, 110, 170)
a[(y % 5) < 3] = (150, 190, 235)
a[(y % 5) == 4] = (30, 44, 70)
a[(x < 2) | (x > 45) | (y < 2) | (y > 61) | (x == 23) | (x == 24)] = (36, 40, 50)
save("window", a)

# ---------------------------------------------------------------- the four things (pickups)
# baggie with powder
a = np.zeros((40, 32, 4))
a[..., :3] = (150, 176, 200)
a[..., 3] = 255
y, x = np.mgrid[0:40, 0:32]
a[(y < 5)] = (70, 120, 200, 255)
a[(y == 5) | (y == 2)] = (220, 232, 245, 255)
m = (y > 16) & (x > 3) & (x < 28) & (y < 37)
m |= (y > 12) & (y <= 16) & (x > 3 + (16 - y) * 2) & (x < 28 - (16 - y))
rr = np.random.default_rng(31)
pw = np.tile(np.array((236, 240, 246, 255), float), (40, 32, 1))
pw[..., :3] -= rr.integers(0, 30, (40, 32))[..., None]
a[m] = pw[m]
a[(x < 1) | (x > 30) | (y > 38)] = (210, 224, 240, 255)
save("baggie", a)

# blotter sheet 5x5 tabs
a = np.zeros((40, 40, 3))
y, x = np.mgrid[0:40, 0:40]
tabs = [(214, 92, 150), (240, 214, 90), (90, 200, 220), (236, 240, 240), (120, 100, 210)]
for j in range(5):
    for i in range(5):
        c = np.array(tabs[(i * 2 + j * 3) % 5], float)
        a[j * 8:j * 8 + 8, i * 8:i * 8 + 8] = c
        a[j * 8 + 2:j * 8 + 6, i * 8 + 2:i * 8 + 6] = c * 0.55
        a[j * 8 + 3:j * 8 + 5, i * 8 + 3:i * 8 + 5] = (250, 250, 250)
a[(x % 8 == 0) | (y % 8 == 0)] = (250, 250, 250)
save("blotter", a)

# xanax bar top
a = np.tile(np.array((232, 236, 240), float), (12, 48, 1))
y, x = np.mgrid[0:12, 0:48]
a[(x % 12) == 0] = (150, 160, 176)
a[(x % 12) == 11] = (250, 252, 255)
a[(y == 0) | (y == 11) | (x == 0) | (x == 47)] = (176, 184, 198)
for i, ch in enumerate("XANA"):
    im = Image.new("L", (10, 8), 0)
    ImageDraw.Draw(im).text((2, -2), ch, font=ImageFont.truetype(FONT, 9) if FONT else None, fill=255)
    g = np.array(im) > 120
    sub = a[2:10, i * 12 + 1:i * 12 + 11]
    sub[g] = (140, 150, 168)
save("xanbar", a)

# oxy pill top (round, blue, "30")
a = np.zeros((24, 24, 4))
y, x = np.mgrid[0:24, 0:24]
d = np.hypot(x - 11.5, y - 11.5)
a[d < 12] = (96, 150, 226, 255)
a[(d < 12) & (d > 10)] = (64, 108, 190, 255)
a[(d < 10) & (x + y < 20)] = (124, 176, 240, 255)
im = Image.new("L", (24, 24), 0)
ImageDraw.Draw(im).text((5, 5), "30", font=ImageFont.truetype(FONT, 12) if FONT else None, fill=255)
a[(np.array(im) > 120) & (d < 10)] = (36, 66, 140, 255)
save("oxy", a)

# small stuff
label("blister", "", (24, 16), (0, 0, 0), (150, 158, 170))
a = np.tile(np.array((150, 158, 170), float), (16, 24, 1))
y, x = np.mgrid[0:16, 0:24]
a[((x % 6) > 1) & ((x % 6) < 5) & ((y % 8) > 1) & ((y % 8) < 6)] = (210, 216, 226)
a[((x % 6) == 3) & ((y % 8) == 2)] = (250, 250, 255)
save("blister", grime(a, 0.15, 4, 40))
label("can", "NRG", (32, 24), (220, 240, 255), (20, 60, 140), fs=11)
label("bottle_label", "40", (32, 16), (30, 40, 60), (200, 206, 212), fs=12)
label("pillbottle", "OXY\n30mg", (32, 24), (40, 50, 70), (214, 220, 226), fs=9)
label("phone", "03:47", (16, 32), (190, 220, 255), (24, 40, 80), fs=7)
label("console", "", (32, 16), (0, 0, 0), (60, 64, 74))
print("textures ->", OUT, len(list(OUT.glob("*.png"))))
