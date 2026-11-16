"""Free local edit: the front full-body figure gets the WHOLE head of the close-up (hair + face), scaled down
and re-pixelated on the figure's 2-px grid. The old head is erased, the neck and the body stay where they are.

Usage: char_head_transplant.py <base_name> <out_name> [scale=0.33]
Run from the project directory. Reads/writes assets/gen/char/<name>.png, plus <out_name>_head.png (zoom).
"""
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_fill_holes, binary_closing, binary_opening

base, out_name = sys.argv[1], sys.argv[2]
SCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 0.33
D = "assets/gen/char/"
src_im = Image.open(D + base + ".png").convert("RGB")
im = np.array(src_im).astype(int)
H, W = im.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
rng = np.random.default_rng(11)

CX_C, CHIN_C = 880, 462            # close-up: face axis, chin row
CUT_C = 456                        # close-up: hair ends above this row, the hood starts below
CX_F, CHIN_F = 176, 178            # front figure: axis, chin row (top of the existing neck)
HOOD_F = 181                       # front figure: everything above this row is head or background
NECK = (160, 193)                  # front figure: neck columns


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


# ---------- background of the sheet ----------
pool = im[5:95, 592:650].reshape(-1, 3)
BG = np.median(pool, axis=0)
sm = np.stack([gaussian_filter(im[..., c].astype(float), 1.0) for c in range(3)], axis=-1)
bglike = np.abs(sm - BG).sum(axis=2) <= 22
lab, _ = label(bglike)
ids, cnt = np.unique(lab[5:95, 592:650], return_counts=True)
outside = lab == ids[np.argmax(cnt * (ids > 0))]              # background connected to the corner of the close-up panel

# ---------- close-up head: hair + face (no neck, no hood) ----------
skin = (lum(im) > 150)
skin[:130] = False
skin[CHIN_C + 1:] = False
skin[:, :690] = False
lab2, _ = label(binary_fill_holes(binary_closing(skin, np.ones((5, 5)))))
face_c = lab2 == lab2[420, 876]
sil = binary_fill_holes(~outside & (xx >= 575))
head_c = (sil & (yy < CUT_C)) | face_c
head_c = binary_opening(head_c, np.ones((3, 3)))
ys, xs = np.nonzero(head_c)
X0, Y0, Y1 = xs.min(), ys.min(), CHIN_C + 1
X1 = 2 * CX_C - X0 + 1                                          # the cheek and hair cut by the sheet edge are mirrored
print("close-up head box:", X0, Y0, X1, Y1)


def ext(a):
    """Close-up array -> crop X0..X1, columns beyond the sheet edge mirrored about the face axis."""
    cols = np.arange(X0, X1)
    cols = np.where(cols >= W, 2 * CX_C - cols, cols)
    return a[Y0:Y1][:, cols]


pal_img = Image.fromarray(ext(im).astype(np.uint8)).quantize(colors=24, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
idx = np.array(pal_img)
pal = np.array(pal_img.getpalette()[:24 * 3]).reshape(-1, 3)
mask = ext(head_c)

# ---------- re-pixelate: one 2-px cell of the figure = the most common colour of its block in the close-up ----------
cell = 2.0 / SCALE                                              # close-up pixels per cell
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
print("small head size:", hw, hh)

# ---------- erase the old head ----------
old = np.zeros((H, W), bool)
old[:HOOD_F, 20:330] = True
old[CHIN_F:HOOD_F, NECK[0]:NECK[1]] = False                    # the neck stays
orig = im.copy()
patch = orig[5:95, 592:650]                                    # clean background, tiled by reflection (keeps its grain)
tile = np.pad(patch, ((0, H - patch.shape[0]), (0, 400 - patch.shape[1]), (0, 0)), mode="symmetric")
im[old] = tile[:, :W][old] if tile.shape[1] >= W else tile[yy[old], xx[old] % tile.shape[1]]
rim = np.zeros((H, W), bool)                                   # the hood rim under the old hair: its dark pixels stay
rim[HOOD_F - 6:HOOD_F, 118:233] = True
rim &= lum(orig) < 62
rim[:, NECK[0]:NECK[1]] = False
im[rim] = orig[rim]

# ---------- paste ----------
oy = CHIN_F + 1 - hh
ox = int(round(CX_F - (CX_C - X0) * SCALE))
ox -= ox % 2
oy -= oy % 2
reg = im[oy:oy + hh, ox:ox + hw]
reg[hm] = head[hm]
print("pasted at:", ox, oy)

# ---------- side figure: one socket seen from the side, nothing is moved ----------
from scipy.ndimage import distance_transform_edt
from PIL import ImageDraw, ImageFilter
S = np.array([[199, 184, 184], [172, 153, 163], [142, 125, 138]])
Dk = np.array([[36, 29, 42], [48, 39, 54], [62, 51, 66], [84, 71, 84], [109, 95, 102]])
L = np.array([-0.42, -0.62, 0.66])
L = L / np.linalg.norm(L)


def mx(mask, size):
    return np.array(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(size))) > 0


def ramp(q, tones):
    q = np.clip(q, 0, len(tones) - 1.001)
    b = np.floor(q).astype(int)
    fr = q - b
    up = (fr > .68) | ((fr > .32) & ((xx // 2 + yy // 2) % 2 == 0))
    return tones[np.minimum(b + up, len(tones) - 1)]


pm = Image.new("L", (W, H), 0)
ImageDraw.Draw(pm).ellipse((506, 104, 522, 134), fill=255)
s_ = np.array(pm) > 0
sk = np.zeros((H, W), bool)
sk[95:195, 440:560] = lum(im[95:195, 440:560]) > 150
lab3, _ = label(binary_closing(sk, np.ones((3, 3))))
face_s = lab3 == lab3[160, 515]
skin_s = np.median(im[150:165, 500:520].reshape(-1, 3), axis=0).astype(int)
base_im = im.copy()
din = distance_transform_edt(s_)
dout = distance_transform_edt(~s_)
gy, gx = np.gradient(gaussian_filter(din - dout, 1.3))
gn = np.hypot(gx, gy) + 1e-6
gx, gy = gx / gn, gy / gn
t = np.clip(din / din.max(), 0, 1)
w = 0.95 * (1 - t) ** 0.8
lam = w * (gx * L[0] + gy * L[1]) + np.sqrt(1 - w * w) * L[2]
q = np.clip(lam, 0, 1) * (1 - t) ** 1.7 * 4.3
q = np.where(din <= 1, np.minimum(q, 0.3), q)
inner = s_ & face_s
im[inner] = ramp(q, Dk)[inner]
hair = s_ & ~face_s
c = Dk[0] + (base_im[hair] - Dk[0]) * 0.16
im[hair] = c.astype(int)
wide = mx(s_, 3)
down = np.zeros_like(s_)
down[6:] = wide[:-6]
b = down & ~s_ & (yy > 119 + 4) & face_s
e = distance_transform_edt(b | s_)
u = dout / (dout + e + 1e-6)
im[b] = ramp(3.0 * (1 - u) ** 0.72, np.array([skin_s, S[0], S[1], S[2]]))[b]
print("side socket/bag px:", int(s_.sum()), int(b.sum()))

o = Image.fromarray(im.astype(np.uint8))
o.save(D + out_name + ".png")
o.crop((400, 40, 580, 230)).resize((180 * 4, 190 * 4), Image.NEAREST).save(D + out_name + "_side.png")
o.crop((40, 0, 310, 260)).resize((270 * 4, 260 * 4), Image.NEAREST).save(D + out_name + "_head.png")
