"""Free local edit of the character close-up, from the user's second markup:
shorter lower face (chin up to the marked line), nose higher, dark empty eye sockets, clear bags.

Usage: char_face2.py <out_name> [--deep]      (--deep: hair inside the sockets sinks into the dark, the drawn round shape stays)
Run from the project directory. Base: assets/gen/char/v7_b.png
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

out_name = sys.argv[1]
HAIR_F = 0.16 if "--deep" in sys.argv else 0.5      # how much of the hair shows inside a socket
D = "assets/gen/char/"
im = np.array(Image.open(D + "v7_b.png").convert("RGB")).astype(int)
H, W = im.shape[:2]


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def mx(mask, size):
    return np.array(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(size))) > 0


skin = np.median(im[300:360, 852:900].reshape(-1, 3), axis=0).astype(int)
sl = lum(skin)
dark = np.median(im[lum(im) < 60].reshape(-1, 3), axis=0).astype(int)

# ---------- nose: lift it off the face ----------
NX0, NY0, NX1, NY1 = 846, 368, 913, 433
nose = im[NY0:NY1, NX0:NX1].copy()
nose_m = lum(nose) < sl - 5
im[NY0:NY1, NX0:NX1][nose_m] = skin

# ---------- shorter lower face: rows EYE..CHIN squeezed into EYE..NEW_CHIN, everything below moves up ----------
PX0 = 572                       # left border of the close-up panel
EYE, CHIN, NEW_CHIN = 352, 505, 461
shift = CHIN - NEW_CHIN
src = np.arange(H, dtype=float)
ys = np.arange(H)
band = (ys >= EYE) & (ys < NEW_CHIN)
src[band] = EYE + (ys[band] - EYE) * (CHIN - EYE) / (NEW_CHIN - EYE)
below = (ys >= NEW_CHIN) & (ys < H - shift)
src[below] = ys[below] + shift          # rows under the chin move up; the last `shift` rows repeat the old bottom
src = np.clip(np.round(src).astype(int), 0, H - 1)
im[:, PX0:] = im[src][:, PX0:]

# ---------- nose back, higher ----------
NOSE_TOP = 360
reg = im[NOSE_TOP:NOSE_TOP + nose.shape[0], NX0:NX1]
reg[nose_m] = nose[nose_m]

# ---------- sockets from the user's markup ----------
sm = np.array(Image.open(D + "_work/sockets.png").convert("L").resize((1889, 1889)))
cov = Image.fromarray(((sm < 128) * 255).astype(np.uint8)).resize((512, 512), Image.BOX)
sock = np.array(cov.point(lambda v: 255 if v > 127 else 0).resize((1024, 1024), Image.NEAREST)) > 0
skinlike = lum(im) > 150
# ---------- palette taken from the sheet itself ----------
from scipy.ndimage import distance_transform_edt, gaussian_filter, label
yy, xx = np.mgrid[0:H, 0:W]
S = np.array([[199, 184, 184], [172, 153, 163], [142, 125, 138], [109, 95, 102]])   # skin shadows: nose, neck, neck dots
Dk = np.array([[36, 29, 42], [48, 39, 54], [62, 51, 66], [84, 71, 84], [109, 95, 102]])  # darks: hoodie/hair ramp


def dots(size, period=8):
    """Halftone lattice like the one on the neck and the nose of the sheet."""
    h = period // 2
    return (((xx % period) < size) & ((yy % period) < size)) | \
           ((((xx + h) % period) < size) & (((yy + h) % period) < size))


def halftone(f):
    """Coverage 0..1 -> mask drawn with lattice dots."""
    m = (f >= .10) & (f < .24) & dots(2)
    m |= (f >= .24) & (f < .42) & dots(3)
    m |= (f >= .42) & (f < .60) & dots(4)
    m |= (f >= .60) & (f < .78) & ~dots(3)
    m |= (f >= .78) & (f < .90) & ~dots(2)
    m |= f >= .90
    return m


def halftone_fine(f):
    """Same idea on a 4-px lattice: for smears that fade over a few pixels."""
    m = (f >= .14) & (f < .38) & dots(2, 4) & dots(2, 8)
    m |= (f >= .38) & (f < .62) & dots(2, 4)
    m |= (f >= .62) & (f < .86) & ~(dots(2, 4) & dots(2, 8))
    m |= f >= .86
    return m


def ramp(q, tones, fine=False):
    """Continuous level q -> tones, steps joined with halftone dots."""
    q = np.clip(q, 0, len(tones) - 1.001)
    base = np.floor(q).astype(int)
    up = (halftone_fine if fine else halftone)(q - base)
    return tones[np.minimum(base + up, len(tones) - 1)]


# face skin (one clean region); hair that crosses a socket stays in front of it
lab, _ = label(np.array(Image.fromarray((skinlike * 255).astype(np.uint8))
                        .filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))) > 0)
face = lab == lab[330, 876]
face = np.array(Image.fromarray((face * 255).astype(np.uint8))
                .filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))) > 0   # drop thin slivers
din = distance_transform_edt(sock)
dout = distance_transform_edt(~sock)
gy, gx = np.gradient(gaussian_filter(din - dout, 4.0))
gn = np.hypot(gx, gy) + 1e-6
gx, gy = gx / gn, gy / gn                               # points into the socket
L = np.array([-0.42, -0.62, 0.66])                      # light: from the upper left, a little from the front
L = L / np.linalg.norm(L)
base_im = im.copy()
BAG_H, BAG_P = 19, 0.72                              # smear height under the socket (px), falloff
BAG_T = np.array([skin, S[0], S[1], S[2]])
bag_all = np.zeros((H, W), bool)
for x0, x1 in ((700, 880), (881, 1024)):
    s = sock.copy()
    s[:, :x0] = False
    s[:, x1:] = False
    ys_, xs_ = np.nonzero(s)
    cy = (ys_.min() + ys_.max()) / 2
    t = np.clip(din / din[s].max(), 0, 1)
    # a pit: walls lean towards the centre, the bottom is lost in the dark
    w = 0.95 * (1 - t) ** 0.8
    lam = w * (gx * L[0] + gy * L[1]) + np.sqrt(1 - w * w) * L[2]
    q = np.clip(lam, 0, 1) * (1 - t) ** 1.7 * 4.3       # only a thin lit crescent on the lower right wall
    q = np.where(din <= 3, np.minimum(q, 0.6), q)       # dark outline keeps the drawn shape
    inner = s & face
    im[inner] = ramp(q, Dk)[inner]
    # hair over the socket: stays, but sinks into the shadow
    hair_in = s & ~face
    k = halftone(np.clip(din / 7.0, 0, 1))
    for m_, f_ in ((hair_in & k, HAIR_F), (hair_in & ~k, 0.5 + HAIR_F / 2)):
        c = Dk[0] + (base_im[m_] - Dk[0]) * f_
        c[lum(c) > lum(Dk[2]) + 3] = Dk[2]              # no bright strands or light edge pixels inside the pit
        im[m_] = c.astype(int)
    # bag: a smeared shadow under the socket - darkest at the socket, melting into the skin (no crease line)
    wide = mx(s, 9)
    down = np.zeros_like(s)
    down[BAG_H:] = wide[:-BAG_H]
    b = down & ~sock & (yy > cy + 10) & face
    bag_all |= b
    e = distance_transform_edt(b | sock)                # distance to the outer border of the smear
    u = dout / (dout + e + 1e-6)                        # 0 at the socket, 1 at the outer border
    lvl = 3.0 * (1 - u) ** BAG_P
    im[b] = ramp(lvl, BAG_T, fine=True)[b]
    # soft skin transition around the rest of the socket
    ring = face & ~sock & ~b & (dout < 12) & (xx >= x0 - 30) & (xx < x1 + 30)
    f = np.where(yy < cy, 0.55 - dout / 7.0, 0.8 - dout / 11.0)
    rm = ring & halftone(np.clip(f, 0, 1))
    im[rm] = S[0]
paint, bag = sock, bag_all
print("sock px:", int(paint.sum()), "bag px:", int(bag.sum()))

o = Image.fromarray(im.astype(np.uint8))
o.save(D + out_name + ".png")
f = o.crop((590, 0, 1024, 520))
f.resize((f.width * 2, f.height * 2), Image.NEAREST).save(D + out_name + "_face.png")
