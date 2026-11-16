"""Free local edit: the side full-body figure gets the head of the big profile drawing (hair + face + neck),
scaled down and re-pixelated on the figure's 2-px grid. The body stays where it is.

Usage: char_side_transplant.py <base_name> <profile_name> <out_name>
Run from the project directory. Reads/writes assets/gen/char/<name>.png, plus <out_name>_side.png (zoom).
"""
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_fill_holes, binary_closing, binary_opening

base, prof_name, out_name = sys.argv[1:4]
D = "assets/gen/char/"
im = np.array(Image.open(D + base + ".png").convert("RGB")).astype(int)
pr = np.array(Image.open(D + prof_name + ".png").convert("RGB")).astype(int)
H, W = im.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]

SCALE = 0.21                       # profile drawing -> figure (same hairline-to-chin height as the front figure)
SQ0, SQ1, SQF = 615, 790, 0.8      # profile rows nose..chin are squeezed: the lower face is short, as on the front view
ANCHOR_P = (600, 930)              # profile: front bottom point of the neck (where it meets the hood)
ANCHOR_F = (472, 203)              # side figure: the same point
HOOD_F = 168                       # side figure: everything above this row is head or background
Dk1 = np.array([48, 39, 54])


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


# ---------- profile: shorter lower face ----------
cut = int(round((SQ1 - SQ0) * (1 - SQF)))
ys = np.arange(H - cut)
srcy = np.where(ys < SQ0, ys, np.where(ys < SQ1 - cut, SQ0 + (ys - SQ0) / SQF, ys + cut))
pr = pr[np.clip(np.round(srcy).astype(int), 0, H - 1)]
PH = pr.shape[0]
py, px = np.mgrid[0:PH, 0:W]
ay = ANCHOR_P[1] - cut

# ---------- profile: head + neck mask ----------
BGp = np.median(pr[5:40, 5:200].reshape(-1, 3), axis=0)
sm = np.stack([gaussian_filter(pr[..., c].astype(float), 1.0) for c in range(3)], axis=-1)
bglike = np.abs(sm - BGp).sum(axis=2) <= 22
lab, _ = label(bglike)
ids, cnt = np.unique(lab[5:40, 5:200], return_counts=True)
outside = lab == ids[np.argmax(cnt * (ids > 0))]
sil = binary_fill_holes(~outside)
line = np.where(px < 400, 803 - cut, np.where(px <= 605, 808 - cut + 0.575 * (px - 400), 800 - cut))
head_p = binary_opening(sil & (py < line), np.ones((3, 3)))
lab2, n2 = label(head_p)
head_p = lab2 == np.bincount(lab2[head_p]).argmax()            # one piece: no stray bits of the hood
ys_, xs_ = np.nonzero(head_p)
X0, X1, Y0, Y1 = xs_.min(), xs_.max() + 1, ys_.min(), ys_.max() + 1
print("profile head box:", X0, Y0, X1, Y1)

crop = pr[Y0:Y1, X0:X1]
mask = head_p[Y0:Y1, X0:X1]
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
        if m.mean() > 0.5:
            smask[j, i] = True
            small[j, i] = np.bincount(idx[a0:a1, b0:b1][m], minlength=24).argmax()
head = np.repeat(np.repeat(pal[small], 2, axis=0), 2, axis=1)
hm = np.repeat(np.repeat(smask, 2, axis=0), 2, axis=1)
hh, hw = hm.shape

# the profile was drawn with its own palette: bring its tones to the sheet's (skin and darks of the front head)
ref = im[26:178, 86:266].reshape(-1, 3)
ref = ref[np.abs(ref - np.median(im[5:95, 592:650].reshape(-1, 3), axis=0)).sum(axis=1) > 30]
hp = head[hm].astype(float)
for lo, hi in ((0, 110), (110, 256)):                          # darks and lights are matched separately
    a = lum(hp)
    b = lum(ref)
    sa, sb = (a >= lo) & (a < hi), (b >= lo) & (b < hi)
    if sa.sum() and sb.sum():
        hp[sa] = (hp[sa] - hp[sa].mean(axis=0)) * (ref[sb].std(axis=0) / (hp[sa].std(axis=0) + 1e-6)) + ref[sb].mean(axis=0)
head[hm] = np.clip(hp, 0, 255).astype(int)

# ---------- erase the old head and neck of the side figure ----------
patch = im[5:95, 592:650]
tile = np.pad(patch, ((0, H - patch.shape[0]), (0, W - patch.shape[1]), (0, 0)), mode="symmetric")
old = np.zeros((H, W), bool)
old[:HOOD_F, 340:572] = True
old[HOOD_F:205, 474:572] = True                                # old chin and jaw in front of the neck
im[old] = tile[old]
neck = np.zeros((H, W), bool)                                  # old neck behind the new one: hood interior
neck[HOOD_F:206, 432:474] = True
neck &= binary_closing(lum(im) > 105, np.ones((5, 5)))
im[neck] = Dk1

# ---------- paste ----------
ox = int(round(ANCHOR_F[0] - (ANCHOR_P[0] - X0) * SCALE))
oy = int(round(ANCHOR_F[1] - (ay - Y0) * SCALE))
ox -= ox % 2
oy -= oy % 2
reg = im[oy:oy + hh, ox:ox + hw]
reg[hm] = head[hm]
print("small head size:", hw, hh, "pasted at:", ox, oy)

o = Image.fromarray(im.astype(np.uint8))
o.save(D + out_name + ".png")
o.crop((340, 0, 580, 240)).resize((240 * 4, 240 * 4), Image.NEAREST).save(D + out_name + "_side.png")
