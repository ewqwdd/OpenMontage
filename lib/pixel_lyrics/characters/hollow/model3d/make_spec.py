"""Stage 1 + mesh maths for the hollow 3D model (no Blender here).

Reads the approved drawings (A-pose puppet parts for the front, views/side.png, views/back.png) and builds the
character as a MODEL made of separate things: a head with one face, two ears, hair (a big mass and two locks of
fringe), a torso, sleeves, jeans, shoes made of a sole, an upper, a toe cap and laces. The drawings give the
measures (front outline from the front drawing, depth from the side drawing) and the paint of each thing.
Clothes are painted with the drawing that looks at them (front / back / side); the head and the shoes are not -
there every feature exists once, as geometry or as paint in one place.

Writes work/spec.json (meshes, UVs, weights, bones), work/atlas.png and 2D checks (work/check_*.png).
Coordinates in the spec are drawing pixels: x right, y down, d = depth towards the viewer of the front view.
Sides are the CHARACTER's: *_r is his right, i.e. on the LEFT of the front drawing (x < 504.5).
"""
import math

from scipy.ndimage import binary_erosion

from common import *

CS = 105.0            # side view: column of the body axis (d = column - CS)
M = 24                # points per ring
CX2 = 1009            # mirror axis of the A-pose canvas: x' = CX2 - x
S_J, E_J = np.array([413., 282.]), np.array([306., 364.])     # right arm: shoulder and elbow (puppet rig)
HIP_J, KNEE_J = np.array([456., 566.]), np.array([440., 705.])
HEAD_BOTTOM = 178
SKULL_AT = 20.0       # the sleeve skull: degrees from the outer side of the arm towards the front (as on the sheet)
SHOULDER_R = 30.0     # the sleeve begins this far inside the body, rounded off like a ball: the shoulder
SLEEVE_W = 64.0       # widest sleeve across, drawing pixels (the hanging sleeve of the sheet)
ARM_E = 0.95          # the sleeve drawing is wrapped round the arm without stretching up to this share of its half-width

parts, rig = load_parts()
side = load("views/side.png")
back = load("views/back.png")
side_sil, back_sil = silhouette(side), silhouette(back)
YY, XX = np.mgrid[0:1024, 0:1024]

TEX = {}              # name -> dict(rgba, ox, oy): source pixel (x, y) lives at rgba[y - oy, x - ox]


def add_tex(name, rgb, mask, box, alpha=None):
    """box = (x0, y0, x1, y1) in source pixels. Outside `mask` the picture is bled from the nearest inside pixel."""
    x0, y0, x1, y1 = box
    px0, py0 = max(0, x0 - 8), max(0, y0 - 8)                # the smoothed variant: on the box only (plus a margin)
    sm = dedither(rgb[py0:y1 + 8, px0:x1 + 8], mask[py0:y1 + 8, px0:x1 + 8])
    sm, rgb, mask = sm[y0 - py0:y1 - py0, x0 - px0:x1 - px0], rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    a = np.full(mask.shape, 255) if alpha is None else alpha[y0:y1, x0:x1].astype(int) * 255
    out = []
    for pic in (rgb, sm):
        rgba = bleed(np.dstack([pic, a]), mask)
        if alpha is not None:                               # just outside the drawing, next to an opening: open too
            hole = mask & (a == 0)
            rgba[..., 3][~mask & binary_dilation(hole, disk(7))] = 0
        out.append(rgba)
    TEX[name] = dict(rgba=out[0], smooth=out[1], ox=x0, oy=y0)


# ============================================================ head masks
head_rgb, head_m = parts["head"]
hy, hx = np.nonzero(head_m)
HEAD_TOP = int(hy.min())


def ellipse(shape, c, r):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx - c[0]) / r[0]) ** 2 + ((yy - c[1]) / r[1]) ** 2 <= 1


def face_mask(rgb, inside, sockets, min_area=60):
    """Skin plus the empty sockets = what belongs to the skull, the rest of `inside` is hair."""
    skin = inside & (lum(rgb) > 118)
    m = skin.copy()
    for c, r in sockets:
        m |= ellipse(m.shape, c, r) & inside
    m = binary_fill_holes(binary_closing(m, disk(3)) & inside)
    m = binary_opening(m, disk(2))                          # a smooth hairline: no wisps left hanging in the opening
    lab, n = label(m)
    keep = np.zeros_like(m)
    for i in range(1, n + 1):
        if (lab == i).sum() >= min_area:
            keep |= lab == i
    return keep, skin & keep


FRONT_ZONE = 68.0     # hair: the front drawing reaches this far round (degrees from straight ahead), then the side one
SKIN = (223, 215, 204)
HAIR_DARK = (41, 33, 47)
SKIN_SHADE = (172, 153, 163)      # the second skin shade of the character's palette (character.md)
PROFILE_K = 0.35      # how much of the drawn nose bump the profile keeps: the face is flat seen from the side
FACE_N = 3.0          # the front of the head seen from above: 2 = round, more = flatter across the face
SKULL_W = 53.0        # half-width of the head under the hair, drawing pixels
EAR_C = 112.0         # side-drawing column of the widest point of the head (just in front of the ear)
EAR_OUT = 4.5         # how far the ear stands off the head
EAR_WALL = 86.0       # side-drawing column of the hair behind the ear
SOCK_END = 68.0       # each socket runs round the corner of the face to here: pixels along the skin from the middle
FRINGE_BOTTOM = 100   # row where the locks of the fringe end
DENT = 3.0            # depth of the sockets
SIDE_TOP, SIDE_BOTTOM = 100, 170      # rows of the hair that lies on the sides of the head
SIDE_THICK = 5.0      # its thickness where it joins the big mass, pixels
SOCK_F = [((478, 116), (26, 23)), ((531, 116), (26, 23))]
SOCK_S = [((163, 116), (16, 22))]
face_raw, skin_f = face_mask(head_rgb, head_m, SOCK_F)
face_f = binary_opening(face_raw, disk(8)) | (face_raw & (YY < 112))      # the ear bumps go, the narrow parting stays

s_top = int(np.nonzero(side_sil.any(axis=1))[0][0])
DYS = SOCK_S[0][0][1] - SOCK_F[0][0][1]                 # front row y is side row y + DYS (heads aligned by the sockets)
b_top = int(np.nonzero(back_sil.any(axis=1))[0][0])
DYB = b_top - HEAD_TOP
side_head = side_sil.copy()
side_head[HEAD_BOTTOM + DYS + 1:] = False
cols = np.nonzero(side_head[:150 + DYS].any(axis=0))[0]
side_head[:, :cols.min()] = False
side_head[:, cols.max() + 1:] = False
face_s, skin_s = face_mask(side, side_head, SOCK_S, min_area=40)
back_head = back_sil.copy()
back_head[HEAD_BOTTOM + DYB + 1:] = False
cols = np.nonzero(back_head[:150 + DYB].any(axis=0))[0]
back_head[:, :cols.min()] = False
back_head[:, cols.max() + 1:] = False

hb = (int(hx.min()) - 6, HEAD_TOP - 6, int(hx.max()) + 7, HEAD_BOTTOM + 7)
sb_box = (0, s_top - 6, side.shape[1], HEAD_BOTTOM + DYS + 7)
# hair paint: hair only. What is skin on a drawing is filled with the hair next to it, so no face, no ear and no
# cheek is ever painted on the hair.
hair_only_f = head_m & ~binary_dilation(face_raw, disk(2))
add_tex("hair_f", bleed(head_rgb, hair_only_f), head_m, hb)
hair_only_s = side_head & ~binary_dilation(face_s, disk(2))
add_tex("hair_s", bleed(side, hair_only_s), side_head, sb_box)
add_tex("head_b", back, back_head, (0, b_top - 6, back.shape[1], HEAD_BOTTOM + DYB + 7))
# face paint: plain skin with the features of the FRONT drawing in the middle - the sockets (made whole where the
# hair of the drawing hangs over them), the bags under them, the shade of the nose. Nothing of the hair, no outline.
face_rgb = np.zeros_like(head_rgb) + np.array(SKIN)
feat = binary_erosion(face_f, disk(6))
face_rgb[feat] = head_rgb[feat]
inner = binary_erosion(face_f, disk(2))
socks_ = np.zeros_like(face_f)
for c_, r_ in SOCK_F:
    socks_ |= ellipse(face_f.shape, c_, r_)
face_rgb[(np.abs(XX - CX) > 44) & ~socks_] = SKIN           # no stray marks of the drawing out on the cheeks
for c_, r_ in SOCK_F:
    e_ = ellipse(face_f.shape, c_, r_)
    dark = e_ & inner & (lum(head_rgb) < 110)
    face_rgb[e_] = np.where((e_ & inner)[e_][:, None], head_rgb[e_], bleed(head_rgb, dark)[e_])
add_tex("face", face_rgb, np.ones_like(face_f), (int(CX) - 84, HEAD_TOP + 8, int(CX) + 86, HEAD_BOTTOM + 7))
# ear paint: the ear of the side drawing
lab_, n_ = label(skin_s)
ear_m = np.zeros_like(skin_s)
for i_ in range(1, n_ + 1):
    ys_, xs_ = np.nonzero(lab_ == i_)
    if xs_.max() < 125 and len(ys_) > 100:
        ear_m = binary_fill_holes(binary_dilation(lab_ == i_, disk(2)))
ey_, ex_ = np.nonzero(ear_m)
add_tex("ear", side, ear_m, (int(ex_.min()) - 4, int(ey_.min()) - 4, int(ex_.max()) + 5, int(ey_.max()) + 5))


def mode_colour(rgb, mask):
    cols_, cnt = np.unique(rgb[mask].reshape(-1, 3), axis=0, return_counts=True)
    return tuple(int(v) for v in cols_[cnt.argmax()])


# flat paints, one 8x8 block each
SY, SX = np.mgrid[0:side.shape[0], 0:side.shape[1]]
PAL_RGB = dict(skin=SKIN, skin_shade=SKIN_SHADE, hair=HAIR_DARK,
               shoe_black=mode_colour(side, side_sil & (SY > 960) & (SY < 974) & (SX > 125) & (SX < 160)),
               shoe_white=mode_colour(side, side_sil & (SY > 955) & (SY < 972) & (SX > 172) & (SX < 195) & (lum(side) > 150)),
               denim=mode_colour(side, side_sil & (SY > 880) & (SY < 925)))
pal_img = np.zeros((8 * len(PAL_RGB), 8, 4), int)
pal_img[..., 3] = 255
PAL = {}
for i_, (k_, v_) in enumerate(PAL_RGB.items()):
    pal_img[8 * i_:8 * i_ + 8, :, :3] = v_
    PAL[k_] = (4.0, 8 * i_ + 4.0)
TEX["pal"] = dict(rgba=pal_img, smooth=pal_img, ox=0, oy=0)


# ============================================================ mesh container
class Obj:
    def __init__(self, name):
        self.name, self.v, self.f, self.uv, self.meta, self.w = name, [], [], [], [], []

    def add_v(self, p, meta, w):
        self.v.append([float(c) for c in p])
        self.meta.append(meta)
        self.w.append(w)
        return len(self.v) - 1


OBJS = []


def superellipse(n, n_front=None, m=M, seam=None, taper=0.02):
    """Ring profile; n_front makes the half that faces the viewer boxier (a flat front wall).

    seam (degrees from straight ahead): the ring is as wide as it gets exactly there, and from the seam back to the
    middle of the side it runs straight, leaning in by `taper`. Seen from the front the sides are then out of sight:
    the front drawing fills the whole outline, and what is painted on the sides (the cheek window) cannot peep round.
    """
    th = 2 * np.pi * np.arange(m) / m
    c, s = np.cos(th), np.sin(th)
    e = np.where(s > 1e-9, 2 / (n_front or n), 2 / n)
    u, v = np.sign(c) * np.abs(c) ** e, np.sign(s) * np.abs(s) ** e
    if seam is not None:
        ef = 2 / (n_front or n)
        t0 = math.radians(90 - seam)
        us, vs = math.cos(t0) ** ef, math.sin(t0) ** ef
        front = s >= math.sin(t0) - 1e-9
        side = (s >= 0) & ~front
        u = np.where(front, np.clip(u / us, -1, 1), u)
        u = np.where(side, np.sign(c) * (1 - taper * (1 - v / vs)), u)
        u = np.where(s < 0, u * (1 - taper), u)
    return u, v, th


def loft(name, sections, uvfun, cap0=True, cap1=True, m=M):
    """sections: dicts with c (x, y, d), a, b, ax_u, ax_v, n, w (bone weights), anything else for uvfun.
    uvfun(obj, face_vertex_ids, outward_normal) -> (texture name, [(sx, sy), ...]) in source pixels."""
    o = Obj(name)
    rings = []
    for k, s in enumerate(sections):
        u, v, th = superellipse(s["n"], s.get("n_front"), m, s.get("seam"))
        c = np.asarray(s["c"], float)
        ids = []
        for j in range(m):
            b_ = s["b"] if v[j] >= 0 else s.get("b_back", s["b"])
            p = c + s["a"] * u[j] * np.asarray(s["ax_u"]) + b_ * v[j] * np.asarray(s["ax_v"])
            ids.append(o.add_v(p, dict(k=k, u=u[j], v=v[j], th=th[j], s=s), s["w"]))
        rings.append(ids)
    faces = []
    for k in range(len(rings) - 1):
        for j in range(m):
            j2 = (j + 1) % m
            faces.append(([rings[k][j], rings[k + 1][j], rings[k + 1][j2], rings[k][j2]],
                          (np.asarray(sections[k]["c"]) + np.asarray(sections[k + 1]["c"])) / 2))
    for on, k in ((cap0, 0), (cap1, len(rings) - 1)):
        if not on:
            continue
        s = sections[k]
        cid = o.add_v(s["c"], dict(k=k, u=0.0, v=0.0, th=None, s=s), s["w"])
        inner = np.asarray(sections[1 if k == 0 else k - 1]["c"], float)
        for j in range(m):
            faces.append(([cid, rings[k][j], rings[k][(j + 1) % m]], inner))
    V = np.array(o.v)
    for ids, inside in faces:
        P = V[ids]
        nrm = np.cross(P[1] - P[0], P[2] - P[0])
        if len(ids) == 4 and np.linalg.norm(nrm) < 1e-9:
            nrm = np.cross(P[2] - P[0], P[3] - P[0])
        if np.dot(nrm, P.mean(axis=0) - inside) < 0:
            ids = ids[::-1]
            nrm = -nrm
        nrm = nrm / (np.linalg.norm(nrm) + 1e-12)
        tex, pts = uvfun(o, ids, nrm)
        o.f.append(ids)
        o.uv.append((tex, pts))
    OBJS.append(o)
    return o


def loft_rings(name, rings, cents, w):
    """A lock of hair: a solid from explicit rings of (x, y, d, angle) points, the same count in each, closed at
    both ends. Points with an angle lie on the round front of the head and take the hair paint of the drawing that
    looks at them; points without (angle None) are the walls and the underside: flat dark hair."""
    o = Obj(name)
    idr = [[o.add_v(q[:3], dict(k=k, th=None, t=q[3]), w) for q in ring] for k, ring in enumerate(rings)]
    m = len(rings[0])
    faces = []
    for k in range(len(rings) - 1):
        inside = (np.asarray(cents[k], float) + np.asarray(cents[k + 1], float)) / 2
        for j in range(m):
            j2 = (j + 1) % m
            faces.append(([idr[k][j], idr[k + 1][j], idr[k + 1][j2], idr[k][j2]], inside))
    for k, kin in ((0, 1), (len(rings) - 1, len(rings) - 2)):
        cid = o.add_v(cents[k], dict(k=k, th=None, t=None), w)
        for j in range(m):
            faces.append(([cid, idr[k][j], idr[k][(j + 1) % m]], np.asarray(cents[kin], float)))
    V = np.array(o.v)
    for ids, inside in faces:
        P = V[ids]
        nrm = np.cross(P[1] - P[0], P[2] - P[0])
        if len(ids) == 4 and np.linalg.norm(nrm) < 1e-9:
            nrm = np.cross(P[2] - P[0], P[3] - P[0])
        if np.dot(nrm, P.mean(axis=0) - inside) < 0:
            ids = ids[::-1]
        ts = [o.meta[i]["t"] for i in ids]
        if any(t is None for t in ts):
            uv = ("pal", [PAL["hair"]] * len(ids))
        elif math.degrees(sum(ts) / len(ts)) < FRONT_ZONE:
            uv = ("hair_f", [(o.v[i][0], o.v[i][1]) for i in ids])
        else:
            uv = ("hair_s", [(o.v[i][2] + CS, o.v[i][1] + DYS) for i in ids])
        o.f.append(ids)
        o.uv.append(uv)
    OBJS.append(o)
    return o


def merge(name, part_names):
    """Several solids -> one mesh."""
    o = Obj(name)
    for pn in part_names:
        src = next(q for q in OBJS if q.name == pn)
        off = len(o.v)
        o.v += src.v
        o.meta += src.meta
        o.w += src.w
        o.f += [[i + off for i in f] for f in src.f]
        o.uv += src.uv
        OBJS.remove(src)
    OBJS.append(o)


def zone(o, ids, phi_front=45.0, phi_back=45.0):
    """front / back / side from where the face sits on its ring: straight seams along the loft."""
    ths = [o.meta[i]["th"] for i in ids if o.meta[i]["th"] is not None]
    ang = math.degrees(math.atan2(sum(math.sin(t) for t in ths), sum(math.cos(t) for t in ths))) % 360
    if abs(ang - 90) < phi_front:
        return "front"
    if abs(ang - 270) < phi_back:
        return "back"
    return "side"


def fold(c, alpha0=60.0, edge=0.95):
    """Front projection that does not smear at the sides: plain projection up to alpha0 from the centre line,
    then the drawing keeps its scale and folds back at `edge` (the drawn outline is left out)."""
    a0 = math.radians(alpha0)
    al = math.asin(min(1.0, abs(c)))
    s_ = math.sin(al) if al <= a0 else math.sin(a0) + math.cos(a0) * (al - a0)
    if s_ > edge:
        s_ = 2 * edge - s_
    return math.copysign(s_, c)


def fill_edges(a):
    """nan outside the measured rows -> the nearest measured value."""
    a = a.copy()
    i = np.nonzero(~np.isnan(a))[0]
    a[:i[0]], a[i[-1] + 1:] = a[i[0]], a[i[-1]]
    return a


def ext(mask, sigma, lo=None, hi=None):
    x0, x1 = row_extents(mask)
    if lo is not None:
        x0[:lo] = np.nan; x1[:lo] = np.nan
    if hi is not None:
        x0[hi + 1:] = np.nan; x1[hi + 1:] = np.nan
    return smooth_nan(x0, sigma), smooth_nan(x1, sigma)


AX_X, AX_D = (1, 0, 0), (0, 0, 1)


def rows_between(y0, y1, step):
    n = max(2, int(round((y1 - y0) / step)) + 1)
    return np.linspace(y0, y1, n)


def at(arr, y):
    """Linear lookup of a per-row array at a continuous row."""
    y = float(np.clip(y, 0, len(arr) - 1.001))
    i = int(y)
    a, b = arr[i], arr[i + 1]
    if np.isnan(a):
        return b
    if np.isnan(b):
        return a
    return a + (b - a) * (y - i)


def blend(y, y0, y1):
    return float(np.clip((y - y0) / (y1 - y0), 0, 1))


# ============================================================ head: a head, two ears and hair - separate things
# Not drawings pasted on a ball. The head is a head: skin all round, ONE face on its front, ears that stand on its
# sides. The hair is its own volumes: a mass over the crown, behind the ears and down the nape, and two locks of
# fringe with the parting between them. The drawings give the measures and the paint of each thing, once:
# the face comes from the front drawing only, the ear from the side drawing only, hair only ever goes on hair.
fx0, fx1 = ext(head_m, 2.0)
sx0, sx1 = ext(side_head, 2.0)
ffx0, ffx1 = ext(face_f, 2.0)
fsx1 = fill_edges(ext(face_s, 2.0)[1])
half_f = np.nanmax(np.stack([CX - ffx0, ffx1 - CX]), axis=0)             # nan where the row has no face
bx0, bx1 = (fill_edges(a) for a in ext(back_head, 2.0))
bmid = np.full(1024, float(round(np.median(((bx0 + bx1) / 2)[HEAD_TOP + 20:HEAD_BOTTOM - 20]))))
# back drawing column = KB - x, KB a whole number: a drifting sub-pixel offset turns the dither into moire
KB_HEAD = float(round(bmid[0] + np.nanmedian(((fx0 + fx1) / 2)[HEAD_TOP + 20:HEAD_BOTTOM - 20])))
W_HEAD = {"head": 1.0}
SK_TOP, Y_BROW = HEAD_TOP + 17, 100
F0 = float(np.nanmedian(fsx1[Y_BROW + DYS:134 + DYS]))                  # the brow line of the profile (side column)
FACE_ROW0 = int(np.nonzero(~np.isnan(half_f))[0][0])                    # where the parting opens


def skull_front(y):
    """Side-drawing column of the front of the face. The profile is kept FLAT: of the drawn nose bump only
    PROFILE_K is left, the forehead goes straight up and leans back towards the crown."""
    if y < Y_BROW:
        return F0 - 0.012 * max(0.0, 78 - y) ** 2
    d = at(fsx1, y + DYS) - F0
    return F0 + d * (PROFILE_K if d > 0 else (0.8 if y <= 169 else 1.0))


def skull_dims(y):
    """half-width, depth in front of the ear line, depth behind it (drawing pixels)."""
    cap = math.sqrt(max(0.0, 1 - ((Y_BROW - y) / (Y_BROW - SK_TOP)) ** 2)) ** 0.7 if y < Y_BROW else 1.0
    hf = at(half_f, y) if y >= 106 else np.nan
    a = SKULL_W * cap if np.isnan(hf) else hf
    return max(a, 2.0), max((skull_front(y) - EAR_C) * cap, 2.0), max((EAR_C - at(sx0, y + DYS) - 16) * cap, 2.0)


def skull_col(y, x):
    """Side column of the skin at |x - CX| = x on the front half of the head."""
    a, bf, _ = skull_dims(y)
    return EAR_C + bf * max(0.0, 1 - min(1.0, x / a) ** FACE_N) ** (1 / FACE_N)


def skull_uv(o, ids, nrm):
    """The face is wrapped on to the head along its surface (no smear at the corners). Each socket runs on round
    the corner of the face as ONE socket: its outer half is drawn out to SOCK_END pixels along the surface."""
    if not hasattr(o, "arc"):
        o.arc = {}
        for k in {mt["k"] for mt in o.meta}:
            ring = sorted((i for i, mt in enumerate(o.meta) if mt["k"] == k and mt["th"] is not None),
                          key=lambda i: o.meta[i]["th"])
            m_ = len(ring)
            j0 = m_ // 4                                    # th = 90 degrees: the middle of the face
            P = np.array([[o.v[i][0], o.v[i][2]] for i in ring])
            seg = np.linalg.norm(P - np.roll(P, 1, axis=0), axis=1)          # seg[j]: from j-1 to j
            for step in (1, -1):
                s, j = 0.0, j0
                o.arc[ring[j0]] = 0.0
                for _ in range(m_ // 2):
                    j2 = (j + step) % m_
                    s += seg[j2] if step == 1 else seg[j]
                    o.arc[ring[j2]] = s
                    j = j2
    if any(o.meta[i]["th"] is None for i in ids):
        return "pal", [PAL["skin"]] * len(ids)
    r0 = SOCK_F[1][1][0]
    pts = []
    for i in ids:
        s, (x, y, _) = o.arc[i], o.v[i]
        far = 2 * r0 + (s - SOCK_END) if s > SOCK_END else r0 + (s - r0) * r0 / (SOCK_END - r0)
        xd = min(far if s > r0 else s, 78.0)
        pts.append((CX + math.copysign(xd, x - CX), y))
    return "face", pts


secs = []
for y in rows_between(SK_TOP, HEAD_BOTTOM + 0.5, 4):
    a, bf, bb = skull_dims(y)
    secs.append(dict(c=(CX, y, EAR_C - CS), a=a, b=bf, b_back=bb, ax_u=AX_X, ax_v=AX_D, n=2.4,
                     n_front=FACE_N - (FACE_N - 2.0) * blend(y, 146, 172), w=W_HEAD))       # the jaw comes to a chin
sk = loft("head", secs, skull_uv, m=48)
for i, mt in enumerate(sk.meta):                            # the sockets are shallow hollows
    if mt["th"] is None or mt["v"] < 0.1:
        continue
    for c, r in SOCK_F:
        q = ((sk.v[i][0] - c[0]) / (r[0] - 1)) ** 2 + ((sk.v[i][1] - c[1]) / (r[1] - 1)) ** 2
        if q < 1:
            ridge = blend(abs(sk.v[i][0] - CX), 4, 12)      # the bridge of the nose stays: it is the profile line
            sk.v[i][2] -= DENT * math.sqrt(1 - q) * min(1.0, (mt["v"] - 0.1) / 0.25) * ridge

# ---- ears: small solids on the sides of the head, where and as big as the side drawing has the ear
ey, ex = np.nonzero(ear_m)
for sgn, nm in ((-1, "ear_r"), (1, "ear_l")):
    secs = []
    for y in rows_between(ey.min() + 0.5, ey.max() + 0.5, 4):
        cols_ = np.nonzero(ear_m[int(np.clip(round(y), ey.min(), ey.max()))])[0]
        c0, c1 = cols_.min(), cols_.max() + 1
        a, bf, bb = skull_dims(y - DYS)
        v_ = (EAR_C - (c0 + c1) / 2) / bb
        xs = a * max(0.0, 1 - min(1.0, abs(v_)) ** 2.4) ** (1 / 2.4)         # the side of the head at that depth
        secs.append(dict(c=(CX + sgn * (xs + 1.0), y - DYS, (c0 + c1) / 2 - CS), a=(c1 - c0) / 2, b=EAR_OUT, ax_u=AX_D,
                         ax_v=(sgn, 0, 0), n=2.6, w=W_HEAD))
    loft(nm, secs, lambda o, ids, nrm: ("ear", [(o.v[i][2] + CS, o.v[i][1] + DYS) for i in ids]), m=12)

# ---- hair, the big mass: the crown, behind the ears, the nape. Beside the face it has a front WALL.
hair_s = biggest(side_head & ~binary_dilation(face_s, disk(3)))
hairline = np.minimum(fill_edges(ext(hair_s, 3.0)[1]), fill_edges(sx1))


def part(y, sgn=0):
    """Half-width of the parting / face opening at row y (0 above it)."""
    if y < FACE_ROW0:
        return 0.0
    l, r = CX - at(ffx0, y), at(ffx1, y) - CX
    v = max(l, r) if sgn == 0 else (l if sgn < 0 else r)
    return 0.0 if np.isnan(v) else float(v)


def hair_wall(y):
    """Side column of the front of the big mass. On the crown: the front of the head. Lower it stands just behind
    the skin the fringe leaves open; under the fringe it steps back behind the ear, then follows the drawn hairline
    down the nape."""
    ys = y + DYS
    full = at(sx1, ys)
    if y <= 62:
        return full
    w = skull_col(y, part(min(y, FRINGE_BOTTOM)) + 2.0) - 3.0
    if y > FRINGE_BOTTOM:
        low = min(at(hairline, ys), EAR_WALL + 3.0 * max(0.0, y - 150))
        w = w + (min(low, w) - w) * blend(y, FRINGE_BOTTOM, FRINGE_BOTTOM + 9)
    return full + (w - full) * blend(y, 62, 70)


def hair_uv(o, ids, nrm):
    P = np.array([o.v[i] for i in ids])
    if any(o.meta[i]["th"] is None for i in ids) and P[:, 1].mean() > 100:
        return "pal", [PAL["hair"]] * len(ids)             # under the hair
    q = zone(o, ids, FRONT_ZONE, 45.0)
    if q == "front":
        return "hair_f", [(p[0], p[1]) for p in P]
    if q == "side":
        return "hair_s", [(p[2] + CS, p[1] + DYS) for p in P]
    return "head_b", [(KB_HEAD - p[0], p[1] + DYB) for p in P]


secs = []
for y in rows_between(HEAD_TOP + 1.0, HEAD_BOTTOM + 0.5, 4):
    a0, a1 = at(fx0, y), at(fx1, y)
    wl = hair_wall(y)
    d0, d1 = at(sx0, y + DYS) - CS, wl - CS
    rec = blend(at(sx1, y + DYS) - wl, 4, 26)               # 0: the hair is the front of the head; 1: a flat wall
    rnd = math.sqrt(max(0.02, 1 - (max(0.0, HEAD_TOP + 15 - y) / 15) ** 2))      # a round crown instead of a flat lid
    secs.append(dict(c=((a0 + a1) / 2, y, (d0 + d1) / 2), a=max((a1 - a0) / 2 * rnd, 2), b=max((d1 - d0) / 2 * rnd, 2),
                     ax_u=AX_X, ax_v=AX_D, n=2.3, n_front=2.3 + rec * (5.7 if y < FRINGE_BOTTOM + 6 else 2.7), w=W_HEAD))
loft("hair", secs, hair_uv, m=48)

# ---- hair, the fringe: two thick locks on the forehead, the parting is the gap between them. Each is a solid of
# its own: the round front of the head outside, a wall on the parting, closed underneath.
# They do not end on a level line: every point of the last ring hangs as low as the drawing that looks at it has
# hair there (the front drawing over the sockets, the side drawing over the temple).
NA = 12
FRINGE_ROWS = list(rows_between(60, 88, 4)) + [float(FRINGE_BOTTOM)]


def lock_end(x, col, t):
    """Row where the hair ends over this point of the fringe."""
    if t < math.radians(FRONT_ZONE):
        rows_ = np.nonzero(face_f[76:130, int(np.clip(round(x), 0, 1023))])[0]
    else:
        c_ = int(np.clip(round(col), 0, side.shape[1] - 1))
        rows_ = np.nonzero(face_s[76 + DYS:130 + DYS, c_])[0] if c_ >= 126 else []
    return float(np.clip(76 + rows_[0] if len(rows_) else 110, 90, 114))


for sgn, nm in ((-1, "fringe_r"), (1, "fringe_l")):
    rings, cents = [], []
    for y in FRINGE_ROWS:
        last = y == FRINGE_ROWS[-1]
        ys = y + DYS
        a0, a1 = at(fx0, y), at(fx1, y)
        cxh, ah = (a0 + a1) / 2, (a1 - a0) / 2
        ch, bh = (at(sx0, ys) + at(sx1, ys)) / 2, (at(sx1, ys) - at(sx0, ys)) / 2
        back_c = hair_wall(y) - 10.0
        p_rel = float(np.clip((CX + sgn * part(y, sgn) - cxh) * sgn, 0.0, ah - 8.0))
        t0 = math.asin(min(1.0, (p_rel / ah) ** 1.15))
        t1 = math.acos(float(np.clip((back_c - ch) / bh, 0.0, 1.0)) ** 1.15)
        t1 = max(t1, t0 + 0.25)
        arc = []
        tip = 0.65 if last else 0.25 * blend(y, 76, 88)       # the ends of the locks curl in to the head
        a_sk = skull_dims(y)[0]
        for t in np.linspace(t0, t1, NA):
            x_, col = cxh + sgn * ah * math.sin(t) ** (2 / 2.3), ch + bh * math.cos(t) ** (2 / 2.3)
            lie = max(skull_col(y, min(abs(x_ - CX), a_sk - 1.0)), back_c + 3.0) + 3.0      # lying flat on the head
            arc.append([x_, y, col - tip * max(0.0, col - lie) - CS, t])
        if last:
            ends = [lock_end(q[0], q[2] + CS, q[3]) for q in arc]
            for j, q in enumerate(arc):                     # a soft wave, not a saw
                q[1] = (ends[max(j - 1, 0)] + 2 * ends[j] + ends[min(j + 1, NA - 1)]) / 4
        xi, xo, dbk = arc[0][0], arc[-1][0], min(back_c, arc[-1][2] + CS) - CS
        ring = [tuple(q) for q in arc] + [(xo + (xi - xo) * f, y, dbk, None) for f in (0.33, 0.67, 1.0)]             + [(xi, arc[0][1], dbk + (arc[0][2] - dbk) * f, None) for f in (0.33, 0.67)]
        rings.append(ring)
        cents.append(((xi + xo) / 2, y, (dbk + arc[0][2]) / 2))
    loft_rings(nm, rings, cents, W_HEAD)

# ---- hair, the sides: hair lying on the temple, in front of the ear and under it, as far forward as the side
# drawing has hair there. Without it the hair ends on a straight cut and the whole side of the head is bare.
# A thin solid on the skin (thick where it joins the mass and the ear, thin at its front edge); the ear stays free.
def skull_x(y, col):
    """How far from the middle the skin is at this side-drawing column."""
    a, bf, bb = skull_dims(y)
    if col >= EAR_C:
        return a * max(0.0, 1 - min(1.0, (col - EAR_C) / bf) ** FACE_N) ** (1 / FACE_N)
    return a * max(0.0, 1 - min(1.0, (EAR_C - col) / bb) ** 2.4) ** (1 / 2.4)


NS = 7
for sgn, nm in ((-1, "side_r"), (1, "side_l")):
    rings, cents = [], []
    for y in rows_between(SIDE_TOP, SIDE_BOTTOM, 4):
        yi = int(round(y + DYS))
        ear_cols = np.nonzero(ear_m[yi])[0]
        cb = ear_cols.max() + 1.0 if len(ear_cols) else hair_wall(y) - 4.0       # from the ear, or from the mass
        skin = np.nonzero(face_s[yi, 108:])[0]                                    # the cheek begins here
        cf = max(108.0 + skin[0] - 1 if len(skin) else at(hairline, yi), cb + 6.0)
        outer, inner = [], []
        for f in np.linspace(0, 1, NS):
            col = cb + f * (cf - cb)
            x_ = skull_x(y, col)
            outer.append((CX + sgn * (x_ + SIDE_THICK - (SIDE_THICK - 1.0) * f ** 2), y, col - CS, math.pi / 2))
            inner.append((CX + sgn * (x_ - 2.5), y, col - CS, None))
        rings.append(outer + inner[::-1])
        cents.append((CX + sgn * skull_x(y, (cb + cf) / 2), y, (cb + cf) / 2 - CS))
    loft_rings(nm, rings, cents, W_HEAD)

# ============================================================ torso
torso_rgb, torso_m = parts["torso"]
TOP_T, HEM = 180, 549
tx0, tx1 = ext(torso_m, 3.0, lo=TOP_T - 2)
stx0, stx1 = ext(side_sil, 3.0, lo=TOP_T - 2, hi=HEM + 2)
bsx0, bsx1 = row_extents(back_sil)
CXB = float(round(np.nanmean(((bsx0 + bsx1) / 2)[260:500])))
ty, tx = np.nonzero(torso_m)
add_tex("torso_f", torso_rgb, torso_m, (int(tx.min()) - 6, int(ty.min()) - 6, int(tx.max()) + 7, int(ty.max()) + 7))
add_tex("torso_b", back, back_sil, (0, 150, back.shape[1], 570))


def torso_w(y):
    t1, t2 = blend(y, 300, 400), blend(y, 470, 540)
    w = {"chest": (1 - t1), "spine": t1 * (1 - t2), "pelvis": t1 * t2}
    return {k: v for k, v in w.items() if v > 1e-4}


def torso_uv(o, ids, nrm):
    front = zone(o, ids, 90.0, 90.0) == "front"
    pts = []
    for i in ids:
        mt = o.meta[i]
        s = mt["s"]
        x = s["c"][0] + (s["a"] * fold(math.cos(mt["th"])) if mt["th"] is not None else 0.0)
        pts.append((x, o.v[i][1]) if front else (CXB - (x - CX), o.v[i][1]))
    return ("torso_f" if front else "torso_b"), pts


secs = []
for y in rows_between(TOP_T, HEM + 0.5, 6):
    a0, a1 = at(tx0, y), at(tx1, y)
    d0, d1 = at(stx0, y) - CS, at(stx1, y) - CS
    secs.append(dict(c=((a0 + a1) / 2, y, (d0 + d1) / 2), a=(a1 - a0) / 2, b=(d1 - d0) / 2,
                     ax_u=AX_X, ax_v=AX_D, n=2.6, w=torso_w(y)))
loft("torso", secs, torso_uv)
D_TORSO = lambda y: (at(stx0, y) + at(stx1, y)) / 2 - CS

# ---- neck: a skin column between the chin and the collar
nk = skin_s.copy()
neck_rows = [r for r in range(HEAD_BOTTOM + DYS - 8, HEAD_BOTTOM + DYS + 1) if nk[r].any()]
nx0 = np.mean([np.nonzero(nk[r])[0][0] for r in neck_rows])
nx1 = np.mean([np.nonzero(nk[r])[0][-1] + 1 for r in neck_rows])
neck_cols = np.nonzero(torso_m[168])[0]
NECK_A = (neck_cols[-1] + 1 - neck_cols[0]) / 2
NECK_D, NECK_B = (nx0 + nx1) / 2 - CS, min((nx1 - nx0) / 2, NECK_A * 1.05)


def neck_uv(o, ids, nrm):
    return "torso_f", [(o.v[i][0], o.v[i][1]) for i in ids]


secs = [dict(c=(CX, y, NECK_D - 10 * blend(y, 165, 210)), a=NECK_A, b=NECK_B, ax_u=AX_X,
             ax_v=AX_D, n=2.0, w={"neck": 1.0} if y > 165 else {"head": 1.0}) for y in rows_between(150, 210, 10)]
loft("neck", secs, neck_uv)

# ============================================================ arms
ARM_TIP = {}


def build_arm(sd):
    mir = sd == "l"
    rgb = np.where(parts[f"arm_{sd}_lower"][1][..., None], parts[f"arm_{sd}_lower"][0], parts[f"arm_{sd}_upper"][0])
    m = parts[f"arm_{sd}_upper"][1] | parts[f"arm_{sd}_lower"][1]
    m = m & ((XX > CX2 - 411) if mir else (XX < 411))
    ay, ax = np.nonzero(m)
    if mir:
        add_tex("arm_l", rgb, m, (int(ax.min()) - 6, int(ay.min()) - 6, int(ax.max()) + 7, int(ay.max()) + 7))
    S = np.array([CX2 - S_J[0], S_J[1]]) if mir else S_J
    E = np.array([CX2 - E_J[0], E_J[1]]) if mir else E_J
    u = (E - S) / np.linalg.norm(E - S)
    w = np.array([-u[1], u[0]])
    if w[1] > 0:
        w = -w                                              # perpendicular pointing up and out
    L = lum(rgb)
    ps = np.arange(-95, 95.01, 0.5)
    stations = []
    cut_x = (CX2 - 411) if mir else 411
    for t in np.arange(-SHOULDER_R, 400, 6.0):
        pts = S[None] + t * u[None] + ps[:, None] * w[None]
        xi, yi = np.round(pts[:, 0]).astype(int), np.round(pts[:, 1]).astype(int)
        ok = (xi >= 0) & (xi < 1024) & (yi >= 0) & (yi < 1024)
        hit = np.zeros(len(ps), bool)
        hit[ok] = m[yi[ok], xi[ok]]
        if hit.sum() < 6:
            stations.append(None)
            continue
        lab, n = label(hit)
        best = np.bincount(lab[hit]).argmax()
        run = lab == best
        p0, p1 = ps[run][0], ps[run][-1]
        # a run that ends on the cut towards the torso is not the real width of the sleeve
        ends = S[None] + t * u[None] + np.array([p0 - 1.0, p1 + 1.0])[:, None] * w[None]
        clipped = any(abs(e[0] - cut_x) < 2.5 for e in ends) or t < 4
        skin = float((L[yi[run], xi[run]] > 135).mean())
        stations.append(dict(t=t, p0=p0, p1=p1, clipped=clipped, skin=skin))
    last = max(i for i, s in enumerate(stations) if s)
    stations = stations[:last + 1]
    first_ok = next(i for i, s in enumerate(stations) if s and not s["clipped"])
    for i in range(first_ok):
        stations[i] = dict(stations[first_ok], t=-SHOULDER_R + 6.0 * i)
    stations = [s for s in stations if s]
    t_hand = next((s["t"] for s in stations if s["skin"] > 0.6 and s["t"] > 150), stations[-1]["t"] - 30)
    tE = float(np.linalg.norm(E - S))
    p0s = gaussian_filter1d(np.array([s["p0"] for s in stations]), 1.2, mode="nearest")
    p1s = gaussian_filter1d(np.array([s["p1"] for s in stations]), 1.2, mode="nearest")
    dS = D_TORSO(S[1])
    sk = None
    if not mir:
        # the sleeve skull: on the A-pose drawing it is squeezed against the top edge of the sleeve, so the sleeve
        # itself is the plain one and the skull is a patch cut from the side drawing, laid on the outer side
        sel = m & (L > 150) & (((XX - S[0]) * u[0] + (YY - S[1]) * u[1]) < tE)
        t_c = float(((XX[sel] - S[0]) * u[0] + (YY[sel] - S[1]) * u[1]).mean())
        br = side_sil & (lum(side) > 150)
        br[:290] = False
        br[410:] = False
        lab, n = label(binary_dilation(br, disk(2)))
        best = max(range(1, n + 1), key=lambda i: (lab == i).sum())
        by_, bx_ = np.nonzero(lab == best)
        sk = dict(xc=(bx_.min() + bx_.max() + 1) / 2, yc=(by_.min() + by_.max() + 1) / 2,
                  hw=(bx_.max() - bx_.min()) / 2 + 7, hh=(by_.max() - by_.min()) / 2 + 7, t=t_c,
                  th=math.radians(SKULL_AT))
        add_tex("sleeve_skull", side, side_sil, (int(sk["xc"] - sk["hw"] - 14), int(sk["yc"] - sk["hh"] - 14),
                                                  int(sk["xc"] + sk["hw"] + 15), int(sk["yc"] + sk["hh"] + 15)))
        print("sleeve skull patch", {k: round(v, 1) for k, v in sk.items()})
    secs = []
    hs = [(p0 + p1) / 2 for s, p0, p1 in zip(stations, p0s, p1s) if t_hand <= s["t"] <= t_hand + 12]
    for s, p0, p1 in zip(stations, p0s, p1s):
        t = s["t"]
        if t >= t_hand:
            break                                           # the sleeve ends at the cuff: the hand is built apart
        if t < t_hand - 20:
            p0 = max(p0, p1 - SLEEVE_W)                     # keep the upper edge, drop the drape below it
        ball = math.sqrt(max(0.03, 1 - (min(t, 0.0) / (SHOULDER_R + 2)) ** 2))    # the sleeve starts as a round shoulder:
        a = max((p1 - p0) / 2 * ball, 2)                    # rounded off from below, the top line of the sleeve runs on
        c2 = S + t * u + (p1 - a) * w                       # into the body
        hand = 0.0
        b = a * (1.4 - 0.3 * blend(t, 40, t_hand))          # an oversized sleeve is deeper than wide
        e = blend(t, tE - 14, tE + 14)
        hw = 0.0                                            # the cuff stays with the forearm when the wrist bends
        sh = blend(t, -6, 42)                               # the top of the sleeve stays with the body: a sloping shoulder
        wts = {"chest": 1 - sh, f"upper_arm.{sd.upper()}": sh * (1 - e), f"forearm.{sd.upper()}": e * (1 - hw),
               f"hand.{sd.upper()}": e * hw}
        tw = 0.0
        secs.append(dict(c=(c2[0], c2[1], dS), a=a, b=b, ax_u=(w[0], w[1], 0), ax_v=AX_D, n=2.0,
                         w={k: v for k, v in wts.items() if v > 1e-4}, tw=tw, t=t, hand=hand))
    ARM_TIP[sd] = dict(S=S, E=E, u=u, w=w, t_hand=t_hand, t_tip=stations[-1]["t"], d=dS, cw=float(np.mean(hs)),
                       t_cuff=secs[-1]["t"])
    print("hand", sd, "t_hand", t_hand, "t_tip", stations[-1]["t"], "centre off axis", round(float(np.mean(hs)), 1),
          "widths", [(s["t"], round(p1 - p0, 1)) for s, p0, p1 in zip(stations, p0s, p1s) if s["t"] >= t_hand - 6])

    def uv(o, ids, nrm):
        ring = [i for i in ids if o.meta[i]["th"] is not None]
        if sk and len(ring) == len(ids):
            wrap = lambda a_: (a_ + math.pi) % (2 * math.pi) - math.pi
            arc = [o.meta[i]["s"]["b"] * wrap(o.meta[i]["th"] - sk["th"]) for i in ids]
            dt = [o.meta[i]["s"]["t"] - sk["t"] for i in ids]
            if abs(sum(arc) / len(arc)) <= sk["hw"] and abs(sum(dt) / len(dt)) <= sk["hh"] and max(arc) - min(arc) < 60:
                return "sleeve_skull", [(sk["xc"] + a_, sk["yc"] + d_) for a_, d_ in zip(arc, dt)]
        pts, plain = [], []
        for i in ids:
            mt = o.meta[i]
            s = mt["s"]
            if mt["th"] is None:
                pts.append((s["c"][0], s["c"][1]))
                continue
            psi = (math.degrees(mt["th"] + s["tw"]) - 90 + 180) % 360 - 180     # from the centre line of the drawing
            backh = abs(psi) > 90
            r = math.radians(180 - abs(psi) if backh else abs(psi))
            if s["hand"] > 0.5:
                sv, folded = math.sin(r), False                 # a flat hand: plain projection
            else:
                folded = r > ARM_E                               # past the edge of the drawing: plain cloth, folded back
                sv = 2 * ARM_E - r if folded else r
            uu = -sv if psi > 0 else sv
            plain.append(backh or folded)
            pts.append((s["c"][0] + s["a"] * uu * s["ax_u"][0], s["c"][1] + s["a"] * uu * s["ax_u"][1]))
        if mir:
            return "arm_l", pts
        return "arm_l", [(CX2 - x, y) for x, y in pts]          # his right sleeve = the plain sleeve mirrored
    loft(f"arm_{sd}", secs, uv)


build_arm("l")
build_arm("r")

# ============================================================ hands: a palm, four fingers and a thumb, each a solid
# of its own with its own bones. One flat skin paint; the sides of the fingers are a shade darker so that they read
# apart. Rest pose: an open hand in the plane of the drawing, its back to the viewer, the thumb on the lower side:
# lowered and turned by the "stand" pose (forearm roll), the palm then faces the thigh and the thumb points forward.
# Sizes are shares of the drawn length of the hand (wrist to fingertip).
PALM_L = 0.46         # palm, wrist to knuckles
PALM_A, WRIST_A, PALM_B = 0.27, 0.20, 0.085     # half-width at the knuckles and at the wrist, half-thickness
FING_A, FING_B = 0.062, 0.052                   # a finger at its base: half-width, half-thickness
FINGERS = [           # name, place across the knuckles (-1..1, + = thumb side), fan angle, length
    ("f_index", 0.75, 9.0, 0.50), ("f_middle", 0.25, 2.0, 0.54), ("f_ring", -0.25, -6.0, 0.49), ("f_pinky", -0.75, -15.0, 0.39)]
THUMB = dict(at=0.22, ang=50.0, lift=0.25, ln=0.40, a=0.072, b=0.062)
JOINTS = (0.42, 0.72)                           # the two joints of a finger, shares of its length
HAND_BONES = []


def skin_uv(lat):
    def uv(o, ids, nrm):
        return "pal", [PAL["skin_shade" if abs(float(np.dot(nrm, lat))) > 0.55 else "skin"]] * len(ids)
    return uv


def build_hand(sd):
    A, up = ARM_TIP[sd], sd.upper()
    U, Wd, N = np.array([*A["u"], 0.0]), np.array([*A["w"], 0.0]), np.array([0.0, 0.0, 1.0])
    Lh = A["t_tip"] - A["t_hand"]
    O = np.array([*(A["S"] + A["t_hand"] * A["u"] + A["cw"] * A["w"]), A["d"]])
    Wd, N = -Wd, -N                                         # from here on: Wd = the thumb side, N = out of the palm
    Lp = PALM_L * Lh
    hb = f"hand.{up}"
    names = [f"palm_{sd}"]
    # the palm: starts inside the cuff, widens to the knuckles, rounded off at its end
    secs = []
    for q in list(np.arange(A["t_cuff"] - A["t_hand"] - 6, Lp - 3.5, 3.0)) + [Lp - 3.5, Lp - 1.5, Lp]:
        k = math.sqrt(max(0.2, 1 - (max(0.0, q - (Lp - 3.5)) / 4.2) ** 2))
        a = (WRIST_A + (PALM_A - WRIST_A) * blend(q, 0, Lp * 0.75)) * Lh * (0.5 + 0.5 * k)
        secs.append(dict(c=tuple(O + q * U), a=a, b=PALM_B * Lh * k, ax_u=tuple(Wd), ax_v=tuple(N), n=3.0, w={hb: 1.0}))
    loft(names[0], secs, skin_uv(Wd), m=12)

    def finger(name, base, F, lat, nrm_, L, a0, b0, zdir):
        """One finger: a tapering solid along F with a round tip, three bones, the weights blended over each joint."""
        bn = [f"{name}.0{i}.{up}" for i in (1, 2, 3)]
        js = (0.0, JOINTS[0] * L, JOINTS[1] * L, L)
        n_ = max(8, int(round((L + 4) / 2.0)))
        secs = []
        for q in np.linspace(-4.0, L, n_ + 1):
            k = 1 - 0.22 * max(0.0, q) / L
            rt = a0 * 1.1
            if q > L - rt:
                k *= math.sqrt(max(0.06, 1 - ((q - (L - rt)) / rt) ** 2))
            w1, w2, w3 = blend(q, -1.5, 1.5), blend(q, js[1] - 1.5, js[1] + 1.5), blend(q, js[2] - 1.5, js[2] + 1.5)
            wts = {hb: 1 - w1, bn[0]: w1 * (1 - w2), bn[1]: w2 * (1 - w3), bn[2]: w3}
            secs.append(dict(c=tuple(base + q * F), a=a0 * k, b=b0 * k, ax_u=tuple(lat), ax_v=tuple(nrm_), n=2.4,
                             w={k_: v for k_, v in wts.items() if v > 1e-4}))
        loft(f"{name}_{sd}", secs, skin_uv(lat), m=8)
        names.append(f"{name}_{sd}")
        for i in range(3):
            HAND_BONES.append(dict(name=bn[i], head=base + js[i] * F, tail=base + js[i + 1] * F,
                                   parent=bn[i - 1] if i else hb, connect=i > 0, z=zdir))

    for name, pos, ang, ln in FINGERS:
        r = math.radians(ang)
        F, lat = math.cos(r) * U + math.sin(r) * Wd, -math.sin(r) * U + math.cos(r) * Wd
        base = O + (Lp - 2.0 - 3.0 * pos * pos) * U + pos * (PALM_A - FING_A) * Lh * Wd
        finger(name, base, F, lat, N, ln * Lh, FING_A * Lh, FING_B * Lh, N)
    r = math.radians(THUMB["ang"])
    F = math.cos(r) * U + math.sin(r) * Wd + THUMB["lift"] * N
    F /= np.linalg.norm(F)
    lat = np.cross(F, N)
    lat /= np.linalg.norm(lat)
    nrm_ = np.cross(lat, F)
    base = O + THUMB["at"] * Lp * U + (WRIST_A + 0.02) * Lh * Wd
    flex = 0.6 * N + 0.8 * (math.sin(r) * U - math.cos(r) * Wd)          # the thumb closes across the palm
    finger("thumb", base, F, lat, nrm_, THUMB["ln"] * Lh, THUMB["a"] * Lh, THUMB["b"] * Lh, flex)
    merge(f"hand_{sd}", names)


build_hand("l")
build_hand("r")

# ============================================================ legs: the jeans down to the hem
LEG_TOP, MIRROR_Y = 506, 640
HEM = 958             # the jeans end here; under it there is a shoe, a thing of its own
HEM_F, HEM_S = 936, 928   # last rows of pure denim on the front and on the side drawing (lower: the shoe)


def mirror_hips(rgb, m):
    """Above MIRROR_Y the drawing shows hands and the hem, not the thigh: repeat the rows below, mirrored."""
    rgb, m = rgb.copy(), m.copy()
    for y in range(480, MIRROR_Y):
        rgb[y], m[y] = rgb[2 * MIRROR_Y - y], m[2 * MIRROR_Y - y]
    return rgb, m


def clean_hips(rgb, m, top=566, shift=80):
    """The thigh as a texture: the hanging hands painted out with the denim next to them; above `top` (the hem,
    hidden under the hoodie) the rows below repeated - shifted, not mirrored, a mirror closes the creases into rings."""
    rgb = rgb.copy()
    rows = np.arange(rgb.shape[0])[:, None]
    hand = binary_dilation(m & (lum(rgb) > 135) & (rows >= top - 12) & (rows < 660), disk(3)) & m
    src = m & (rows >= top) & (rows < 720) & ~hand
    rgb[hand] = bleed(rgb, src)[hand]
    for y in range(top - 1, 470, -1):
        rgb[y] = rgb[y + shift]
    return rgb


legs_rgb = np.zeros((1024, 1024, 3), int)
legs_m = {}
for sd in "rl":
    mm = parts[f"leg_{sd}_upper"][1] | parts[f"leg_{sd}_lower"][1]
    legs_m[sd] = mm
    legs_rgb[mm] = np.where(parts[f"leg_{sd}_lower"][1][..., None], parts[f"leg_{sd}_lower"][0],
                            parts[f"leg_{sd}_upper"][0])[mm]
allm = legs_m["r"] | legs_m["l"]
ly, lx = np.nonzero(allm)
add_tex("legs_f", legs_rgb, allm, (int(lx.min()) - 6, int(ly.min()) - 6, int(lx.max()) + 7, 1024))
side_leg_m = mirror_hips(side, side_sil)[1]
side_leg_rgb = clean_hips(side, side_sil, top=598)       # the hem and the cuff hang lower on the side drawing
add_tex("legs_s", side_leg_rgb, side_leg_m, (0, 480, side.shape[1], 1024))
back_leg_m = mirror_hips(back, back_sil)[1]
back_leg_rgb = clean_hips(back, back_sil)
add_tex("legs_b", back_leg_rgb, back_leg_m, (0, 480, back.shape[1], 1024))
gap = []
for y in range(700, 900):
    lab, n = label(back_leg_m[y])
    if n == 2:
        gap.append((np.nonzero(lab == 1)[0][-1] + 1 + np.nonzero(lab == 2)[0][0]) / 2)
XCB = float(np.median(gap)) if gap else CXB
half = np.arange(back.shape[1])[None, :] < XCB
bl0, bl1 = (fill_edges(a) for a in ext(back_leg_m & half, 2.0, lo=480))   # picture-left leg of the back view = his LEFT leg
br0, br1 = (fill_edges(a) for a in ext(back_leg_m & ~half, 2.0, lo=480))
sl0, sl1 = (fill_edges(a) for a in ext(side_leg_m, 1.5, lo=480))
sl1 = np.minimum(sl1, 202)                                   # the far shoe peeks out in front of the near one
SOLE = int(ly.max())


def build_leg(sd):
    f0, f1 = (fill_edges(a) for a in ext(legs_m[sd], 2.0))
    b0, b1 = (bl0, bl1) if sd == "l" else (br0, br1)
    kb = float(round(np.median(((b0 + b1) / 2 + (f0 + f1) / 2)[600:920])))     # back drawing column = kb - x
    up = sd.upper()
    secs = []
    for y in rows_between(LEG_TOP, HEM, 7):
        a0, a1 = at(f0, min(y, HEM_F)), at(f1, min(y, HEM_F))
        # the hem is cut on a slant: low over the heel, high over the instep, where the laces show
        d0, d1 = at(sl0, y) - CS, at(sl1, min(y, HEM_S)) - 1.2 * max(0.0, y - HEM_S) - CS
        k = blend(y, KNEE_J[1] - 22, KNEE_J[1] + 22)
        wts = {f"thigh.{up}": 1 - k, f"shin.{up}": k}
        secs.append(dict(c=((a0 + a1) / 2, y, (d0 + d1) / 2), a=(a1 - a0) / 2, b=(d1 - d0) / 2, ax_u=AX_X, ax_v=AX_D,
                         n=2.2, w={k_: v for k_, v in wts.items() if v > 1e-4}))

    def cuff(y, last):
        """Below the last row of pure denim the rows above it come again, mirrored: a cuff, never a painted shoe."""
        return y if y <= last else 2 * last - y

    def uv(o, ids, nrm):
        P = np.array([o.v[i] for i in ids])
        if any(o.meta[i]["th"] is None for i in ids) and P[:, 1].mean() > 900:
            return "pal", [PAL["denim"]] * len(ids)         # inside the hem
        q = zone(o, ids)
        if q == "front":
            return "legs_f", [(p[0], cuff(p[1], HEM_F)) for p in P]
        if q == "side":
            return "legs_s", [(p[2] + CS, cuff(p[1], HEM_S)) for p in P]
        return "legs_b", [(kb - p[0], p[1]) for p in P]
    loft(f"leg_{sd}", secs, uv)


build_leg("r")
build_leg("l")
D_LEG = lambda y: (at(sl0, y) + at(sl1, y)) / 2 - CS

# ============================================================ shoes: modelled, nothing pasted
# A sneaker made of its parts: a thick rubber sole, a canvas upper, a rubber toe cap, laces. Each part has its own
# shape and one flat paint (the sole: its stripes, row by row, as the side drawing has them). Measures - length,
# sole height, where the laces and the toe cap sit - are read off the side drawing.
SOLE_H = 25           # height of the sole
TOE_OUT = 14.0        # the toes point outwards: sideways shift of the toe against the heel, pixels
STN = [0, .03, .07, .12, .2, .3, .4, .47, .54, .61, .68, .76, .82, .87, .92, .96, .985, 1.0]     # heel 0 .. toe 1
K_CAP = STN.index(.76)                                                  # the toe cap starts at this station
LACES = (.52, .57, .62, .67, .72)
sole_img = np.zeros((SOLE_H + 6, 8, 4), int)
sole_img[..., 3] = 255
for i_ in range(SOLE_H + 6):
    y_ = min(SOLE - SOLE_H - 3 + i_, SOLE)
    sole_img[i_, :, :3] = np.median(side[y_, 80:170][side_sil[y_, 80:170]], axis=0)
TEX["sole"] = dict(rgba=sole_img, smooth=sole_img, ox=0, oy=SOLE - SOLE_H - 3)


def build_shoe(sd):
    up, sgn = sd.upper(), (-1 if sd == "r" else 1)
    f0, f1 = (fill_edges(a) for a in ext(legs_m[sd], 2.0))
    xc = (at(f0, HEM_F) + at(f1, HEM_F)) / 2
    d_heel, d_toe = at(sl0, 975) - CS + 2, 200.0 - CS
    ln, sole_top = d_toe - d_heel, SOLE - SOLE_H
    W = {f"foot.{up}": 1.0}
    xs = lambda t: xc + sgn * TOE_OUT * (t - 0.35)

    def plan(t):
        """Half-width of the shoe seen from above: a round heel, wider at the ball, a blunt round toe."""
        if t < 0.12:
            return 27 * math.sqrt(1 - 0.6 * ((0.12 - t) / 0.12) ** 2)
        if t < 0.62:
            return 27 + 7 * blend(t, 0.12, 0.62)
        return 34 * max(0.0, 1 - ((t - 0.62) / 0.38) ** 2.4) ** (1 / 2.4)

    def top(t):
        """Row of the top line of the upper: level under the jeans, down the instep, round over the toe cap."""
        if t < 0.45:
            return 936.0
        if t < 0.76:
            return 936 + 15 * blend(t, 0.45, 0.76)
        return 951 + (sole_top - 5 - 951) * (1 - math.sqrt(max(0.0, 1 - ((t - 0.76) / 0.24) ** 2)))

    def ring(t):
        tp = top(t)
        return (tp + sole_top + 3) / 2, (sole_top + 3 - tp) / 2, max(plan(t) - 2, 2)       # centre row, half-height, half-width

    secs = []
    for t in STN:
        yc, hh, hw = ring(t)
        secs.append(dict(c=(xs(t), yc, d_heel + t * ln), a=hw, b=hh, ax_u=AX_X, ax_v=(0, 1, 0), n=2.6, n_front=6.0, w=W))
    loft(f"upper_{sd}", secs, lambda o, ids, nrm: ("pal", [PAL["shoe_white" if min(o.meta[i]["k"] for i in ids) >= K_CAP
                                                               else "shoe_black"]] * len(ids)), m=16)
    secs = [dict(c=(xs(t), SOLE - SOLE_H / 2, d_heel - 2 + t * (ln + 4)), a=max(plan(t) + 1.5, 3), b=SOLE_H / 2, ax_u=AX_X,
                 ax_v=(0, 1, 0), n=7.0, w=W) for t in STN]
    loft(f"sole_{sd}", secs, lambda o, ids, nrm: ("sole", [(4.0, o.v[i][1]) for i in ids]), m=16)
    names = [f"upper_{sd}", f"sole_{sd}"]
    for n_, t in enumerate(LACES):                          # each lace: a white bar lying across the instep
        yc, hh, hw = ring(t)
        secs = []
        for f in np.linspace(-0.62, 0.62, 5):
            ysurf = yc - hh * (1 - abs(f) ** 2.6) ** (1 / 2.6)
            secs.append(dict(c=(xs(t) + f * hw, ysurf - 0.3, d_heel + t * ln), a=2.3, b=1.5, ax_u=AX_D, ax_v=(0, 1, 0),
                             n=3.0, w=W))
        loft(f"lace_{sd}_{n_}", secs, lambda o, ids, nrm: ("pal", [PAL["shoe_white"]] * len(ids)), m=8)
        names.append(f"lace_{sd}_{n_}")
    merge(f"shoe_{sd}", names)


build_shoe("r")
build_shoe("l")
PARTS = list(OBJS)                                          # the solids one by one, for the 2D checks
merge("head", ["head", "ear_r", "ear_l"])
merge("hair", ["hair", "fringe_r", "fringe_l", "side_r", "side_l"])

# ============================================================ atlas
PAD = 4
names = sorted(TEX, key=lambda n: -TEX[n]["rgba"].shape[0])
AW = 1024
x = y = rowh = 0
for n in names:
    h, w = TEX[n]["rgba"].shape[:2]
    if x + w + PAD > AW:
        x, y, rowh = 0, y + rowh + PAD, 0
    TEX[n]["ax"], TEX[n]["ay"] = x, y
    x += w + PAD
    rowh = max(rowh, h)
AH = 1 << int(math.ceil(math.log2(y + rowh)))
for key, fname in (("rgba", "atlas.png"), ("smooth", "atlas_smooth.png")):   # as drawn / dither smoothed
    atlas = np.zeros((AH, AW, 4), np.uint8)
    atlas[..., :3] = BG
    atlas[..., 3] = 255
    for n in names:
        t = TEX[n]
        h, w = t[key].shape[:2]
        atlas[t["ay"]:t["ay"] + h, t["ax"]:t["ax"] + w] = t[key]
    Image.fromarray(atlas, "RGBA").save(WORK / fname)

# ============================================================ bones
BONES = []


def bone(name, head, tail, parent, connect=False, z=None):
    """z: where the bone's own Z looks (drawing axes). Turning the bone round its own X then moves it that way."""
    BONES.append(dict(name=name, head=[float(c) for c in head], tail=[float(c) for c in tail], parent=parent,
                      connect=connect, z=None if z is None else [float(c) for c in z]))


dP = D_TORSO(540)
bone("root", (CX, SOLE + 1, 0), (CX, SOLE + 1, -60), None)
bone("pelvis", (CX, 560, dP), (CX, 505, dP), "root")
bone("spine", (CX, 505, dP), (CX, 380, D_TORSO(380)), "pelvis", True)
bone("chest", (CX, 380, D_TORSO(380)), (CX, 212, NECK_D), "spine", True)
bone("neck", (CX, 212, NECK_D), (CX, 170, NECK_D), "chest", True)
bone("head", (CX, 170, NECK_D), (CX, 40, NECK_D), "neck", True)
for sd in "rl":
    A, up = ARM_TIP[sd], sd.upper()
    P = lambda t: (A["S"][0] + t * A["u"][0], A["S"][1] + t * A["u"][1], A["d"])
    tE = float(np.linalg.norm(A["E"] - A["S"]))
    bone(f"upper_arm.{up}", P(0), P(tE), "chest")
    bone(f"forearm.{up}", P(tE), P(A["t_hand"]), f"upper_arm.{up}", True)
    bone(f"hand.{up}", P(A["t_hand"]), P(A["t_tip"]), f"forearm.{up}", True)
    mx = (lambda v: CX2 - v) if sd == "l" else (lambda v: v)
    hip, knee = (mx(HIP_J[0]), HIP_J[1]), (mx(KNEE_J[0]), KNEE_J[1])
    f0, f1 = ext(legs_m[sd], 2.0)
    ank = ((at(f0, 946) + at(f1, 946)) / 2, 946)
    bone(f"thigh.{up}", (*hip, D_LEG(600)), (*knee, D_LEG(705)), "pelvis")
    bone(f"shin.{up}", (*knee, D_LEG(705)), (*ank, D_LEG(900)), f"thigh.{up}", True)
    bone(f"foot.{up}", (*ank, D_LEG(900)), (ank[0], SOLE - 8, at(sl1, 985) - CS - 10), f"shin.{up}", True)

for b_ in HAND_BONES:                                       # the fingers, after the hands they hang on
    bone(**b_)

# ============================================================ write the spec
out = dict(px_height=SOLE + 1 - HEAD_TOP, sole_y=SOLE + 1, cx=CX, atlas=[AW, AH], bones=BONES, objects=[])
for o in OBJS:
    uvs = []
    for tex, pts in o.uv:
        t = TEX[tex]
        uvs.append([[(sx - t["ox"] + t["ax"]) / AW, 1 - (sy - t["oy"] + t["ay"]) / AH] for sx, sy in pts])
    out["objects"].append(dict(name=o.name, verts=o.v, faces=o.f, uvs=uvs,
                               weights=[[[k, round(float(v), 4)] for k, v in w.items()] for w in o.w]))
(WORK / "spec.json").write_text(json.dumps(out), encoding="utf-8")
print("objects:", [(o.name, len(o.v), len(o.f)) for o in OBJS], "atlas", AW, AH)
print("DYS", DYS, "DYB", DYB, "CXB", round(CXB, 1), "XCB", round(XCB, 1), "neck", round(NECK_A, 1), round(NECK_B, 1),
      round(NECK_D, 1), "t_hand", {k: v["t_hand"] for k, v in ARM_TIP.items()})

# ============================================================ 2D checks
from PIL import ImageDraw

front = np.zeros((1024, 1024, 3), int) + np.array(BG)
for name in ["leg_r_lower", "leg_l_lower", "leg_r_upper", "leg_l_upper", "arm_r_upper", "arm_l_upper", "torso", "head",
             "arm_r_lower", "arm_l_lower"]:
    rgb, m = parts[name]
    front[m] = rgb[m]
COL = dict(hair=(255, 80, 80), head=(80, 255, 120), torso=(80, 160, 255), neck=(255, 255, 0),
           arm_r=(255, 160, 0), arm_l=(255, 160, 0), leg_r=(255, 0, 255), leg_l=(0, 255, 255))
for view, base, fx, fy in (("front", front, lambda p: p[0], lambda p: p[1]),
                           ("side", side.copy(), lambda p: p[2] + CS, lambda p: p[1])):
    im = Image.fromarray(base.astype(np.uint8)).resize((base.shape[1] * 2, base.shape[0] * 2), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for o in PARTS:
        if o.name not in COL or (view == "side" and o.name.startswith("arm")):
            continue
        dy = DYS if (view == "side" and o.name in ("head", "hair")) else 0
        ks = sorted({mt["k"] for mt in o.meta})
        for k in ks:
            pts = [(fx(v) * 2, (fy(v) + dy) * 2) for v, mt in zip(o.v, o.meta) if mt["k"] == k and mt["th"] is not None]
            xs = [p[0] for p in pts]
            yv = pts[0][1]
            dr.line([(min(xs), yv), (max(xs), yv)] if not o.name.startswith("arm") else pts + pts[:1],
                    fill=COL[o.name], width=1)
    im.save(WORK / f"check_{view}.png")
fm = front.copy()
fm[face_f] = (fm[face_f] * 0.4 + np.array([0, 255, 0]) * 0.6).astype(int)
sm_ = side.copy()
sm_[face_s] = (sm_[face_s] * 0.4 + np.array([0, 255, 0]) * 0.6).astype(int)
a = Image.fromarray(fm[15:190, 400:610].astype(np.uint8))
b = Image.fromarray(sm_[10:190].astype(np.uint8))
im = Image.new("RGB", (a.width + b.width, 180))
im.paste(a, (0, 0)); im.paste(b, (a.width, 0))
im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(WORK / "check_face.png")
