"""Free local edit: one turnaround sheet from the approved sheet and the extra views.

Five full-body figures on one flat background: front, three-quarter front, side, three-quarter back, back.
The background of every source is flattened to the same colour, the sleeve skull of the front view is added
to the views that show the right sleeve (side, three-quarter back, back).

Usage: char_turnaround.py <sheet> <bodies> <back34> <out_dir>
Run from the project directory. Reads assets/gen/char/<name>.png, writes <out_dir>/turnaround.png and views/*.png.
Coordinates are for v16.png, t3_bodies.png and t2_back34.png.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_fill_holes

sheet_n, bodies_n, back34_n, out_dir = sys.argv[1:5]
D = "assets/gen/char/"
OUT = Path(out_dir)
(OUT / "views").mkdir(parents=True, exist_ok=True)
BG = np.array([75, 63, 77])                                    # background of the approved sheet
MARGIN = 22


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def load(name):
    """Picture with its background flattened to BG, and the silhouette of everything drawn on it."""
    im = np.array(Image.open(D + name + ".png").convert("RGB")).astype(float)
    bg = np.median(im[3:20, 3:20].reshape(-1, 3), axis=0)
    sm = np.stack([gaussian_filter(im[..., c], 1.0) for c in range(3)], axis=-1)
    isbg = np.abs(sm - bg).sum(axis=2) <= 22
    lab, _ = label(isbg)
    sil = binary_fill_holes(lab != lab[5, 5])
    isbg = ~sil
    field = 0
    for sg in (25, 150):                                       # near the outline the local background, deep inside the wide one
        wgt = gaussian_filter(isbg.astype(float), sg)
        f = np.stack([gaussian_filter(im[..., c] * isbg, sg) / np.maximum(wgt, 1e-9) for c in range(3)], axis=-1)
        field = f if sg == 25 else np.where((near > 0.05)[..., None], field, f)
        near = wgt
    return np.clip(np.round(im - field + BG), 0, 255).astype(int), sil


sheet, sheet_s = load(sheet_n)
bodies, bodies_s = load(bodies_n)
back34, back34_s = load(back34_n)

# ---------- sleeve skull ----------
chest = sheet[252:316, 206:262]                                # chest skull of the front view
chest_m = lum(chest) > 125
ys, xs = np.nonzero(chest_m)
chest, chest_m = chest[ys.min():ys.max() + 1, xs.min():xs.max() + 1], chest_m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
sleeve = sheet[316:384, 44:84]                                 # the half skull on the sleeve edge of the front view
sleeve_m = lum(sleeve) > 125
ys, xs = np.nonzero(sleeve_m)
sleeve, sleeve_m = sleeve[ys.min():ys.max() + 1, xs.min():xs.max() + 1], sleeve_m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
print("chest skull:", chest_m.shape[::-1], "sleeve skull:", sleeve_m.shape[::-1])


def squeeze(px, m, k):
    """Narrower copy on the 2-px grid (nearest columns)."""
    w = max(2, int(round(px.shape[1] * k / 2)) * 2)
    cols = np.clip((np.arange(w // 2) * 2 / k + 1 / k).astype(int) // 2 * 2, 0, px.shape[1] - 2)
    cols = np.repeat(cols, 2) + np.tile([0, 1], w // 2)
    return px[:, cols], m[:, cols]


def stamp(im, px, m, cx, cy):
    x0, y0 = (cx - px.shape[1] // 2) // 2 * 2, (cy - px.shape[0] // 2) // 2 * 2
    reg = im[y0:y0 + px.shape[0], x0:x0 + px.shape[1]]
    reg[m] = px[m]


stamp(sheet, chest, chest_m, 424, 352)                         # side view: outer side of the right sleeve
p, m = squeeze(chest, chest_m, 0.7)
stamp(back34, p, m, 584, 352)                                  # three-quarter back: the same sleeve, foreshortened
row = np.nonzero(bodies_s[350, 660:980])[0]
edge = 660 + row.max()                                         # back view: right edge of the right sleeve
p, m = sleeve[:, ::-1], sleeve_m[:, ::-1]
stamp(bodies, p, m, edge - p.shape[1] // 2 - 1, 352)

# ---------- panels ----------
views = [("front", sheet, sheet_s, (0, 340)), ("front34", bodies, bodies_s, (40, 360)),
         ("side", sheet, sheet_s, (340, 572)), ("back34", back34, back34_s, (300, 700)),
         ("back", bodies, bodies_s, (660, 980))]
panels = []
for name, im, sil, (c0, c1) in views:
    xs = np.nonzero(sil[:, c0:c1].any(axis=0))[0]
    a = max(c0, (c0 + xs.min() - MARGIN) // 2 * 2)
    b = min(c1, (c0 + xs.max() + 1 + MARGIN + 1) // 2 * 2)
    pan = im[:, a:b]
    panels.append(pan)
    Image.fromarray(pan.astype(np.uint8)).save(OUT / "views" / f"{name}.png")
    print(name, "columns", a, b, "width", b - a)
turn = np.concatenate(panels, axis=1)
Image.fromarray(turn.astype(np.uint8)).save(OUT / "turnaround.png")
print("turnaround:", turn.shape[1], "x", turn.shape[0])
