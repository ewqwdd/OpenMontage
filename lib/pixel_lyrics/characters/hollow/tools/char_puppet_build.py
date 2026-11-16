"""Free local edit: cut the A-pose figure into puppet parts (transparent PNGs) and write the rig.

Usage: char_puppet_build.py <apose_name> <sheet_name> <out_dir>
Run from the project directory. Reads assets/gen/char/<name>.png, writes <out_dir>/parts/*.png, rig.json, parts_sheet.png.
Coordinates are for p1_apose.png (the body) and v16.png (the approved front head).

Sides are the CHARACTER's: arm_r / leg_r are his right, i.e. on the LEFT of the picture.
Every joint overlaps: the part that lies on top carries a round cap of cloth around the joint, so no gap opens
when the part below turns. Draw order (rig "z"): pelvis, shins, thighs, upper arms, torso, head, forearms.
The upper arms go BEHIND the torso: their shoulder cap is a full disc of plain cloth hidden under it (a cap on top
would carry a copy of the chest skull around), and it comes out as a round shoulder when the arm is lowered.
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_fill_holes

apose_n, sheet_n, out_dir = sys.argv[1:4]
D = "assets/gen/char/"
OUT = Path(out_dir)
(OUT / "parts").mkdir(parents=True, exist_ok=True)

CX2 = 1009                         # mirror axis of the body: x' = CX2 - x  (centre line x = 504.5)
NECK = 178                         # A-pose: the head of the drawing ends here, the neck and the hood start
SHOULDER_X = 411                   # A-pose: the picture-left arm is everything left of this column
HIP_Y = 550                        # A-pose: bottom of the hoodie hem, the jeans start
KNEE_Y = 705
S, E = np.array([413., 282.]), np.array([306., 364.])          # picture-left arm: shoulder and elbow joints (the elbow
                                                                # sits a little low so that its cap misses the sleeve skull)
SHOULDER_R, ELBOW_R = 58, 44                                    # radii of the cloth caps
HIP, KNEE = np.array([456., 566.]), np.array([440., 705.])      # picture-left leg: hip and knee joints
HIP_R, KNEE_R = 46, 36
HEAD_CUT = 177                     # approved sheet: the front head ends at this row (chin)
HEAD_COLS = (60, 300)
HEAD_PIVOT = (504, 170)            # A-pose: where the head turns (inside the chin, on the neck)
TORSO_PIVOT = (504, 548)           # the torso leans around the waist


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def silhouette(im):
    bg = np.median(im[3:20, 3:20].reshape(-1, 3), axis=0)
    sm = np.stack([gaussian_filter(im[..., c].astype(float), 1.0) for c in range(3)], axis=-1)
    isbg = np.abs(sm - bg).sum(axis=2) <= 22
    lab, _ = label(isbg)
    return binary_fill_holes(lab != lab[5, 5])


def biggest(m):
    lab, n = label(m)
    return lab == np.bincount(lab[m]).argmax() if n else m


def disc(c, r, shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r


im = np.array(Image.open(D + apose_n + ".png").convert("RGB")).astype(int)
H, W = im.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
sil = silhouette(im)
imf, silf = im[:, ::-1], sil[:, ::-1]                           # mirrored copy; column x of it is column W-1-x
SHIFT = CX2 - (W - 1)                                            # mirrored column -> body column


def mirror_pt(p):
    return np.array([CX2 - p[0], p[1]])


parts = {}                                                       # name -> (rgb, mask) in A-pose coordinates


def cut_arm(src, src_sil):
    """Picture-left arm of `src`: picture, upper-arm mask, forearm mask."""
    arm = biggest(src_sil & (xx < SHOULDER_X) & (yy < 520))
    # under the torso: only the quarter above the joint - it swings out as a round shoulder when the arm is lowered;
    # the quarter below it would swing out under a raised arm as a lump
    cap = disc(S, SHOULDER_R, arm.shape) & (xx >= SHOULDER_X) & (yy <= S[1])
    rgb = src.copy()
    rgb[cap] = cloth[cap]
    rgb[cap & ~disc(S, SHOULDER_R - 2, arm.shape)] = OUTLINE     # the arc becomes the outline of the shoulder
    u = (E - S) / np.linalg.norm(E - S)
    along = (xx - E[0]) * u[0] + (yy - E[1]) * u[1]
    elbow = disc(E, ELBOW_R, arm.shape) & arm
    return rgb, (arm & (along < 0)) | cap | elbow, (arm & (along >= 0)) | elbow


def shifted(a, dx):
    """Columns moved right by dx (fill with zeros)."""
    out = np.zeros_like(a)
    if dx >= 0:
        out[:, dx:] = a[:, :a.shape[1] - dx] if dx else a
    else:
        out[:, :dx] = a[:, -dx:]
    return out


# the mirrored picture, shifted so that the body centre line stays in place
imm, silm = shifted(imf, SHIFT), shifted(silf, SHIFT)

# ---------- arms: the sleeve skull belongs on HIS RIGHT sleeve (picture left), Gemini drew it on the other one,
# so each arm is taken from the mirrored picture ----------
tile = im[268:308, 366:406]                                      # plain sleeve cloth next to the shoulder
cloth = np.tile(tile, (H // 40 + 1, W // 40 + 1, 1))[:H, :W]
OUTLINE = np.array([36, 29, 42])
rgb, up, lo = cut_arm(imm, silm)                                 # picture-left arm of the mirror = the arm with the skull
parts["arm_r_upper"], parts["arm_r_lower"] = (rgb, up), (rgb, lo)
rgb, up, lo = cut_arm(im, sil)                                   # the plain arm, mirrored to the picture right
rgb = shifted(rgb[:, ::-1], SHIFT)
parts["arm_l_upper"] = (rgb, shifted(up[:, ::-1], SHIFT))
parts["arm_l_lower"] = (rgb, shifted(lo[:, ::-1], SHIFT))

# ---------- legs ----------
ext = im.copy()                                                  # cloth under the hem: the top of the legs mirrored upward
ext_sil = sil & (yy >= HIP_Y)
n = HIP_Y - 500
ext[HIP_Y - n:HIP_Y] = im[HIP_Y:HIP_Y + n][::-1]
ext_sil[HIP_Y - n:HIP_Y] = (sil & (yy >= HIP_Y))[HIP_Y:HIP_Y + n][::-1]
for side, half in (("r", xx < 505), ("l", xx >= 505)):
    hip, knee = (HIP, KNEE) if side == "r" else (mirror_pt(HIP), mirror_pt(KNEE))
    leg = ext_sil & half
    cap = disc(knee, KNEE_R, leg.shape) & leg
    parts[f"leg_{side}_upper"] = (ext, (leg & (yy < KNEE_Y)) | cap)
    parts[f"leg_{side}_lower"] = (ext, (leg & (yy >= KNEE_Y)) | cap)

# ---------- pelvis: a dark piece of denim behind the legs, seen only when they spread ----------
tile = im[575:605, 425:485]
reps = (H // tile.shape[0] + 1, W // tile.shape[1] + 1, 1)
denim = (np.tile(tile, reps)[:H, :W] * 0.8).astype(int)
parts["pelvis"] = (denim, ((xx - 504.5) / 74.0) ** 2 + ((yy - 548) / 30.0) ** 2 <= 1)

# ---------- torso: hood, body, neck ----------
torso = sil & (yy >= NECK) & (yy < HIP_Y) & (xx >= SHOULDER_X) & (xx <= CX2 - SHOULDER_X)
torso |= sil & (yy >= 345) & (yy < HIP_Y) & (xx >= 380) & (xx <= CX2 - 380)      # the body is wider than the shoulders lower down
torso = biggest(torso)
body = im.copy()
neck_cols = np.nonzero((lum(im[NECK + 2]) > 120) & (np.abs(xx[0] - 504.5) < 30))[0]
for x in neck_cols:                                              # the neck continues up behind the chin
    body[NECK - 16:NECK, x] = im[NECK + 2, x]
    torso[NECK - 16:NECK, x] = True
parts["torso"] = (body, torso)

# ---------- head: from the approved sheet ----------
sh = np.array(Image.open(D + sheet_n + ".png").convert("RGB")).astype(int)
sh_sil = silhouette(sh)
yy2, xx2 = np.mgrid[0:sh.shape[0], 0:sh.shape[1]]
head = sh_sil & (yy2 < HEAD_CUT) & (xx2 >= HEAD_COLS[0]) & (xx2 < HEAD_COLS[1])
head &= (yy2 < HEAD_CUT - 4) | (np.abs(xx2 - 175) < 28)          # beside the chin the top edge of the hood starts earlier
head = biggest(head)
hy, hx = np.nonzero(head)
dx = int(round(504.5 - (hx.min() + hx.max()) / 2)) // 2 * 2      # centre the head on the body, stay on the 2-px grid
dy = NECK - HEAD_CUT + 1
dy -= dy % 2
head_rgb, head_m = np.zeros_like(im), np.zeros((H, W), bool)
head_rgb[hy + dy, hx + dx] = sh[hy, hx]
head_m[hy + dy, hx + dx] = True
parts["head"] = (head_rgb, head_m)

# ---------- write ----------
Z = ["pelvis", "leg_r_lower", "leg_l_lower", "leg_r_upper", "leg_l_upper", "arm_r_upper", "arm_l_upper",
     "torso", "head", "arm_r_lower", "arm_l_lower"]
PARENT = {"pelvis": None, "torso": "pelvis", "head": "torso",
          "arm_r_upper": "torso", "arm_r_lower": "arm_r_upper", "arm_l_upper": "torso", "arm_l_lower": "arm_l_upper",
          "leg_r_upper": "pelvis", "leg_r_lower": "leg_r_upper", "leg_l_upper": "pelvis", "leg_l_lower": "leg_l_upper"}
PIVOT = {"pelvis": (504, 560), "torso": TORSO_PIVOT, "head": HEAD_PIVOT,
         "arm_r_upper": S, "arm_r_lower": E, "arm_l_upper": mirror_pt(S), "arm_l_lower": mirror_pt(E),
         "leg_r_upper": HIP, "leg_r_lower": KNEE, "leg_l_upper": mirror_pt(HIP), "leg_l_lower": mirror_pt(KNEE)}
rig = {"name": "hollow/front", "canvas": [W, H], "pixel": 2,
       "note": "Sides are the character's (arm_r is on the left of the picture). Angles in degrees, clockwise on screen, "
               "around the part's pivot; a child turns with its parent. origin and pivot are in canvas pixels of the rest pose.",
       "parts": {},
       "poses": {
           "apose": {},
           "stand": {"arm_r_upper": -44, "arm_l_upper": 44, "arm_r_lower": -4, "arm_l_lower": 4,
                     "leg_r_upper": -3, "leg_l_upper": 3},
           "wave": {"arm_r_upper": -44, "arm_r_lower": -4, "arm_l_upper": -70, "arm_l_lower": -55,
                    "leg_r_upper": -3, "leg_l_upper": 3, "head": 5},
           "shrug": {"arm_r_upper": -20, "arm_r_lower": -70, "arm_l_upper": 20, "arm_l_lower": 70,
                     "leg_r_upper": -3, "leg_l_upper": 3, "head": -6},
       }}
tiles = []
for z, name in enumerate(Z):
    rgb, m = parts[name]
    ys, xs = np.nonzero(m)
    x0, y0, x1, y1 = xs.min() // 2 * 2, ys.min() // 2 * 2, xs.max() + 1, ys.max() + 1
    rgba = np.dstack([rgb[y0:y1, x0:x1], m[y0:y1, x0:x1] * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(OUT / "parts" / f"{name}.png")
    rig["parts"][name] = {"file": f"parts/{name}.png", "origin": [int(x0), int(y0)], "size": [int(x1 - x0), int(y1 - y0)],
                          "pivot": [float(PIVOT[name][0]), float(PIVOT[name][1])], "parent": PARENT[name], "z": z}
    tiles.append((name, rgba))
    print(f"{name:12s} origin {x0},{y0} size {x1 - x0}x{y1 - y0}")
(OUT / "rig.json").write_text(json.dumps(rig, indent=1), encoding="utf-8")

# all parts apart on one sheet, for the eye
order = ["head", "torso", "pelvis", "arm_r_upper", "arm_r_lower", "arm_l_upper", "arm_l_lower",
         "leg_r_upper", "leg_r_lower", "leg_l_upper", "leg_l_lower"]
by = dict(tiles)
pad, x, rowh, rows, row = 24, 24, 0, [], []
for name in order:
    t = by[name]
    if x + t.shape[1] + pad > 1400:
        rows.append((row, rowh)); row, x, rowh = [], 24, 0
    row.append((name, x)); x += t.shape[1] + pad; rowh = max(rowh, t.shape[0])
rows.append((row, rowh))
sheet = Image.new("RGB", (1400, sum(h for _, h in rows) + pad * (len(rows) + 1)), (75, 63, 77))
y = pad
for row, h in rows:
    for name, x in row:
        t = Image.fromarray(by[name], "RGBA")
        sheet.paste(t, (x, y), t)
    y += h + pad
sheet.save(OUT / "parts_sheet.png")
