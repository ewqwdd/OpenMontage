"""Free local edit: the high-angle / low-angle sheet. Gemini drew a mouth and a nose with nostrils on the
high-angle face: the mouth is painted over with skin, the nose becomes the same faint round shadow as on the
approved close-up. The background is flattened to the approved sheet's colour and the two figures are saved apart.

Usage: char_angles_fix.py <angles_name> <out_dir>
Run from the project directory. Reads assets/gen/char/<name>.png, writes <out_dir>/angles.png and views/*.png.
Coordinates are for t4_angles.png.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_fill_holes, binary_dilation

name, out_dir = sys.argv[1:3]
D = "assets/gen/char/"
OUT = Path(out_dir)
(OUT / "views").mkdir(parents=True, exist_ok=True)
BG = np.array([75, 63, 77])
im = np.array(Image.open(D + name + ".png").convert("RGB")).astype(float)
H, W = im.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


# ---------- high-angle face: no mouth, the nose is only a faint shadow ----------
skin = np.median(im[196:212, 232:300].reshape(-1, 3), axis=0)
nose_tone = np.median(im[244:254, 748:762].reshape(-1, 3), axis=0)      # nose shadow of the low-angle face (drawn right)
areas = (((xx >= 242) & (xx < 292) & (yy >= 178) & (yy < 196)),                 # mouth
         (((xx - 265) / 14.0) ** 2 + ((yy - 160) / 17.0) ** 2 <= 1))           # nose, clear of the socket rims
for area in areas:
    dark = binary_dilation(area & (lum(im) < lum(skin) - 6), np.ones((3, 3))) & area
    ok = (~dark & (lum(im) > lum(skin) - 10)).astype(float)                    # clean skin around the spot
    wgt = gaussian_filter(ok, 4)
    fill = np.stack([gaussian_filter(im[..., c] * ok, 4) / np.maximum(wgt, 1e-6) for c in range(3)], axis=-1)
    im[dark] = fill[dark]
shadow = ((xx - 265.5) / 9.0) ** 2 + ((yy - 162.5) / 8.0) ** 2 <= 1
shadow = shadow[::2, ::2].repeat(2, axis=0).repeat(2, axis=1)           # on the 2-px grid
im[shadow] = nose_tone

# ---------- flat background ----------
bg = np.median(im[3:20, 3:20].reshape(-1, 3), axis=0)
sm = np.stack([gaussian_filter(im[..., c], 1.0) for c in range(3)], axis=-1)
isbg = np.abs(sm - bg).sum(axis=2) <= 22
lab, _ = label(isbg)
sil = binary_fill_holes(lab != lab[5, 5])
isbg = ~sil
field = 0
for sg in (25, 150):
    wgt = gaussian_filter(isbg.astype(float), sg)
    f = np.stack([gaussian_filter(im[..., c] * isbg, sg) / np.maximum(wgt, 1e-9) for c in range(3)], axis=-1)
    field = f if sg == 25 else np.where((near > 0.05)[..., None], field, f)
    near = wgt
im = np.clip(np.round(im - field + BG), 0, 255).astype(np.uint8)

Image.fromarray(im).save(OUT / "angles.png")
for vname, (c0, c1) in (("high_angle", (0, 512)), ("low_angle", (512, 1024))):
    xs = np.nonzero(sil[:, c0:c1].any(axis=0))[0]
    a, b = max(c0, (c0 + xs.min() - 22) // 2 * 2), min(c1, (c0 + xs.max() + 24) // 2 * 2)
    Image.fromarray(im[:, a:b]).save(OUT / "views" / f"{vname}.png")
    print(vname, "columns", a, b)
Image.fromarray(im[80:270, 150:390]).resize((960, 760), Image.NEAREST).save(D + "_work/t4_face_fixed.png")
