"""Free local edit: the three-quarter front full-body figure gets the head of the big three-quarter drawing
(hair + face + upper neck), mirrored to face the same way as the body, scaled down and re-pixelated on the
figure's 2-px grid. The body and the lower neck stay where they are.

Usage: char_34_transplant.py <bodies_name> <head_name> <out_name>
Run from the project directory. Reads/writes assets/gen/char/<name>.png, plus <out_name>_zoom.png.
Coordinates are for t1_bodies.png (figure in x 60..340, facing left) and t1_head34.png (facing right).
"""
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_fill_holes, binary_opening

base, head_name, out_name = sys.argv[1:4]
D = "assets/gen/char/"
im = np.array(Image.open(D + base + ".png").convert("RGB")).astype(int)
pr = np.array(Image.open(D + head_name + ".png").convert("RGB")).astype(int)
H, W = im.shape[:2]

SCALE = 0.239                      # big drawing -> figure: hair top..chin is 632 px there and 151 px here
ANCHOR_P = (640, 672)              # big drawing (as drawn, facing right): lowest point of the chin
ANCHOR_F = (188, 176)              # figure: the same point
HEAD_ROW = 172                     # figure: everything above this row is head or background
FIG = (100, 340)                   # figure: columns of the head


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


# ---------- big drawing: head + upper neck mask ----------
py, px = np.mgrid[0:H, 0:W]
BGp = np.median(pr[5:30, 5:120].reshape(-1, 3), axis=0)
sm = np.stack([gaussian_filter(pr[..., c].astype(float), 1.0) for c in range(3)], axis=-1)
bglike = np.abs(sm - BGp).sum(axis=2) <= 22
lab, _ = label(bglike)
ids, cnt = np.unique(lab[5:30, 5:120], return_counts=True)
outside = lab == ids[np.argmax(cnt * (ids > 0))]
sil = binary_fill_holes(~outside)
# below the line is the hoodie: hair side | neck (kept a little lower) | under the chin and the far hair
line = np.where(px < 420, 696, np.where(px < 595, 730, 680))
head_p = binary_opening(sil & (py < line), np.ones((3, 3)))
lab2, _ = label(head_p)
head_p = lab2 == np.bincount(lab2[head_p]).argmax()
ys_, xs_ = np.nonzero(head_p)
X0, X1, Y0, Y1 = xs_.min(), xs_.max() + 1, ys_.min(), ys_.max() + 1
print("big head box:", X0, Y0, X1, Y1)

crop = pr[Y0:Y1, X0:X1][:, ::-1]                               # mirrored: the body looks to the left
mask = head_p[Y0:Y1, X0:X1][:, ::-1]
ax = (X1 - 1 - ANCHOR_P[0])                                    # anchor inside the mirrored crop
ay = ANCHOR_P[1] - Y0
pal_img = Image.fromarray(crop.astype(np.uint8)).quantize(colors=24, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
idx = np.array(pal_img)
pal = np.array(pal_img.getpalette()[:24 * 3]).reshape(-1, 3)

# ---------- re-pixelate on the 2-px grid ----------
cell = 2.0 / SCALE
hc, wc = int(round(idx.shape[0] / cell)), int(round(idx.shape[1] / cell))
small = np.zeros((hc, wc), int)
smask = np.zeros((hc, wc), bool)
for j in range(hc):
    for i in range(wc):
        a0, a1 = int(round(j * cell)), max(int(round((j + 1) * cell)), int(round(j * cell)) + 1)
        b0, b1 = int(round(i * cell)), max(int(round((i + 1) * cell)), int(round(i * cell)) + 1)
        m = mask[a0:a1, b0:b1]
        if m.size and m.mean() > 0.5:
            smask[j, i] = True
            small[j, i] = np.bincount(idx[a0:a1, b0:b1][m], minlength=24).argmax()
head = np.repeat(np.repeat(pal[small], 2, axis=0), 2, axis=1)
hm = np.repeat(np.repeat(smask, 2, axis=0), 2, axis=1)
hh, hw = hm.shape

# ---------- tones: bring the big drawing's palette to the figure's old head ----------
BGf = np.median(im[5:95, 345:405].reshape(-1, 3), axis=0)
ref = im[25:HEAD_ROW, 130:320].reshape(-1, 3)
ref = ref[np.abs(ref - BGf).sum(axis=1) > 30]
hp = head[hm].astype(float)
for lo, hi in ((0, 150), (150, 256)):                          # darks (hair with its highlights) and skin are matched separately
    a, b = lum(hp), lum(ref)
    sa, sb = (a >= lo) & (a < hi), (b >= lo) & (b < hi)
    if sa.sum() and sb.sum():
        hp[sa] = (hp[sa] - hp[sa].mean(axis=0)) * (ref[sb].std(axis=0) / (hp[sa].std(axis=0) + 1e-6)) + ref[sb].mean(axis=0)
l = lum(hp)
hi_dark = (l > 88) & (l < 150)                                 # hair highlights: re-pixelation turns the strokes into bright specks
hp[hi_dark] *= ((88 + (l[hi_dark] - 88) * 0.35) / l[hi_dark])[:, None]
head[hm] = np.clip(hp, 0, 255).astype(int)

# ---------- erase the old head ----------
# background = smooth field interpolated from the real background around the figure + the grain of a clean patch
isbg = np.abs(np.stack([gaussian_filter(im[..., c].astype(float), 1.0) for c in range(3)], axis=-1) - BGf).sum(axis=2) <= 22
wgt = gaussian_filter(isbg.astype(float), 20) + 1e-6
field = np.stack([gaussian_filter(im[..., c] * isbg, 20) / wgt for c in range(3)], axis=-1)
patch = im[5:95, 345:405].astype(float)
grain = patch - np.stack([gaussian_filter(patch[..., c], 6) for c in range(3)], axis=-1)
grain = np.pad(grain, ((0, H - patch.shape[0]), (0, W - patch.shape[1]), (0, 0)), mode="symmetric")
clean = np.clip(np.round(field + grain), 0, 255).astype(int)
old = np.zeros((H, W), bool)
old[:HEAD_ROW, FIG[0]:FIG[1]] = True
old[HEAD_ROW:180, FIG[0]:168] = True                           # hair curl and background left of the chin
old &= ~isbg                                                   # real background stays untouched
hood = np.median(im[184:190, 176:196].reshape(-1, 3), axis=0).astype(int)
chin = np.zeros((H, W), bool)
chin[HEAD_ROW:182, 168:203] = True
chin &= lum(im) > 120                                          # old chin skin: the hood collar is behind it
im[old] = clean[old]
im[chin] = hood

# ---------- paste ----------
ox = int(round(ANCHOR_F[0] - ax * SCALE))
oy = int(round(ANCHOR_F[1] - ay * SCALE))
ox -= ox % 2
oy -= oy % 2
reg = im[oy:oy + hh, ox:ox + hw]
reg[hm] = head[hm]
print("small head size:", hw, hh, "pasted at:", ox, oy)

o = Image.fromarray(im.astype(np.uint8))
o.save(D + out_name + ".png")
o.crop((100, 0, 340, 240)).resize((960, 960), Image.NEAREST).save(D + out_name + "_zoom.png")
