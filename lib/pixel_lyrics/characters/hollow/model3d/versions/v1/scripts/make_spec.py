"""Stage 1 + mesh maths for the hollow 3D model (no Blender here).

Reads the approved drawings (A-pose puppet parts for the front, views/side.png, views/back.png), measures each
body part row by row and lofts it into a volume: the front outline comes from the front drawing, the depth from the
side drawing. Every face is textured with the pixels of the drawing that looks at it (front / back / side), so the
model seen head-on IS the drawing.

Writes work/spec.json (meshes, UVs, weights, bones), work/atlas.png and 2D checks (work/check_*.png).
Coordinates in the spec are drawing pixels: x right, y down, d = depth towards the viewer of the front view.
Sides are the CHARACTER's: *_r is his right, i.e. on the LEFT of the front drawing (x < 504.5).
"""
import math

from common import *

CS = 105.0            # side view: column of the body axis (d = column - CS)
M = 24                # points per ring
CX2 = 1009            # mirror axis of the A-pose canvas: x' = CX2 - x
S_J, E_J = np.array([413., 282.]), np.array([306., 364.])     # right arm: shoulder and elbow (puppet rig)
HIP_J, KNEE_J = np.array([456., 566.]), np.array([440., 705.])
HEAD_BOTTOM = 178
SKULL_AT = 20.0       # the sleeve skull: degrees from the outer side of the arm towards the front (as on the sheet)
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


# The approved FRONT drawing is the truth for the face and for the hair that frames it: it is wrapped this far round
# the head (degrees from straight ahead). The side drawing gives the depth, the ear and the hair behind it.
FRONT_ZONE = 68.0     # hair shell
FACE_BOX = 6.0        # how boxy the face is seen from above: 2 = round (a muzzle in profile), 6 = flat face, flat cheeks
SKULL_ZONE = 45.0     # skull: front drawing up to here, then the side drawing (the sockets meet on the seam)
SOCK_F = [((478, 116), (26, 23)), ((531, 116), (26, 23))]
SOCK_S = [((163, 116), (16, 22))]
face_f, skin_f = face_mask(head_rgb, head_m, SOCK_F)
face_f = binary_opening(face_f, disk(8)) | (face_f & (YY < 112))      # the ear bumps go, the narrow parting stays

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
add_tex("head_shell_f", head_rgb, head_m, hb, alpha=~face_f)
def wrap_socket(rgb, c, r, sign, ext):
    """Carry the dark of a socket on to the edge of the flat face (sign: +1 right, -1 left), so that the socket of
    the front drawing and the socket of the side drawing meet round the corner instead of leaving a pale bar."""
    rgb = rgb.copy()
    for y in range(int(c[1] - r[1]) + 1, int(c[1] + r[1])):
        w = r[0] * math.sqrt(max(0.0, 1 - ((y - c[1]) / r[1]) ** 2))
        if w < 3:
            continue
        x_src = int(round(c[0] + sign * 0.62 * w))
        for k in range(int(0.62 * w), int(w + ext * w / r[0]) + 1):
            x = int(round(c[0] + sign * k))
            if 0 <= x < rgb.shape[1]:
                rgb[y, x] = rgb[y, x_src]
    return rgb


skull_f = wrap_socket(wrap_socket(head_rgb, *SOCK_F[0], -1, 12), *SOCK_F[1], 1, 12)
add_tex("head_skull_f", skull_f, head_m, hb)
sb_box = (0, s_top - 6, side.shape[1], HEAD_BOTTOM + DYS + 7)
add_tex("head_shell_s", side, side_head, sb_box, alpha=~face_s)
add_tex("head_skull_s", wrap_socket(side, *SOCK_S[0], 1, 12), side_head, sb_box)
add_tex("head_b", back, back_head, (0, b_top - 6, back.shape[1], HEAD_BOTTOM + DYB + 7))


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


def superellipse(n, n_front=None, m=M):
    """Ring profile; n_front makes the half that faces the viewer boxier (a flat front wall)."""
    th = 2 * np.pi * np.arange(m) / m
    c, s = np.cos(th), np.sin(th)
    e = np.where(s > 1e-9, 2 / (n_front or n), 2 / n)
    return np.sign(c) * np.abs(c) ** e, np.sign(s) * np.abs(s) ** e, th


def loft(name, sections, uvfun, cap0=True, cap1=True, m=M):
    """sections: dicts with c (x, y, d), a, b, ax_u, ax_v, n, w (bone weights), anything else for uvfun.
    uvfun(obj, face_vertex_ids, outward_normal) -> (texture name, [(sx, sy), ...]) in source pixels."""
    o = Obj(name)
    rings = []
    for k, s in enumerate(sections):
        u, v, th = superellipse(s["n"], s.get("n_front"), m)
        c = np.asarray(s["c"], float)
        ids = []
        for j in range(m):
            p = c + s["a"] * u[j] * np.asarray(s["ax_u"]) + s["b"] * v[j] * np.asarray(s["ax_v"])
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


# ============================================================ head: hair shell + skull
fx0, fx1 = ext(head_m, 2.0)
sx0, sx1 = ext(side_head, 2.0)
# The hair hangs BEHIND the face: beside the cheeks it only comes forward as far as the side drawing shows hair.
# There the shell gets a flat front wall (the curtains of hair of the front drawing) and the face stands out of it.
hair_s = biggest(side_head & ~binary_dilation(face_s, disk(3)))        # without the dark outline of the profile
hfront = fill_edges(ext(hair_s, 3.0)[1])
hfront = np.minimum(hfront, fill_edges(sx1))
bx0, bx1 = (fill_edges(a) for a in ext(back_head, 2.0))
bmid = np.full(1024, float(round(np.median(((bx0 + bx1) / 2)[HEAD_TOP + 20:HEAD_BOTTOM - 20]))))
# back drawing column = KB - x, KB a whole number: a drifting sub-pixel offset turns the dither into moire
KB_HEAD = float(round(bmid[0] + np.nanmedian(((fx0 + fx1) / 2)[HEAD_TOP + 20:HEAD_BOTTOM - 20])))
W_HEAD = {"head": 1.0}


def head_uv(shell):
    tf, ts = ("head_shell_f", "head_shell_s") if shell else ("head_skull_f", "head_skull_s")

    def f(o, ids, nrm):
        P = np.array([o.v[i] for i in ids])
        s0 = o.meta[ids[0]]["s"]
        q = zone(o, ids, FRONT_ZONE, 45.0) if shell else zone(o, ids, SKULL_ZONE, 0.0)
        if q == "front":
            return tf, [(p[0], p[1]) for p in P]
        if q == "side":
            return ts, [(p[2] + CS, p[1] + DYS) for p in P]
        return "head_b", [(KB_HEAD - p[0], p[1] + DYB) for p in P]
    return f


secs = []
for y in rows_between(HEAD_TOP + 1.0, HEAD_BOTTOM + 0.5, 4):
    a0, a1 = at(fx0, y), at(fx1, y)
    d0, d1 = at(sx0, y + DYS) - CS, at(hfront, y + DYS) - CS
    recess = blend(at(sx1, y + DYS) - at(hfront, y + DYS), 4, 26)     # 0: hair is the front of the head (fringe)
    rnd = math.sqrt(max(0.02, 1 - (max(0.0, HEAD_TOP + 15 - y) / 15) ** 2))      # a round crown instead of a flat lid
    secs.append(dict(c=((a0 + a1) / 2, y, (d0 + d1) / 2), a=max((a1 - a0) / 2 * rnd, 2), b=max((d1 - d0) / 2 * rnd, 2),
                     ax_u=AX_X, ax_v=AX_D, n=2.3, n_front=2.3 + 3.2 * recess, w=W_HEAD))
loft("head_shell", secs, head_uv(True))

# skull: covers the whole face opening (front and side), stays inside the hair everywhere else
ffx0, ffx1 = ext(face_f, 2.0)
fsx0, fsx1 = ext(face_s, 2.0)
SK_TOP = HEAD_TOP + 10
half_f = np.nanmax(np.stack([CX - ffx0, ffx1 - CX]), axis=0) + 1.0        # nan where no face in the row
YW = int(np.nanargmax(np.where(np.arange(1024) < 150, half_f, np.nan)))
AW_ = half_f[YW]
secs = []
for y in rows_between(SK_TOP, HEAD_BOTTOM + 0.5, 4):
    cap = math.sqrt(max(0.0, 1 - ((YW - y) / (YW - SK_TOP)) ** 2)) if y < YW else 1.0
    shell_half = (at(fx1, y) - at(fx0, y)) / 2
    hf = at(half_f, y)
    a = AW_ * cap if y < YW else (hf if not np.isnan(hf) else AW_)
    if not np.isnan(hf):
        a = max(a, hf)
    a = min(a, max(shell_half - 3, hf if not np.isnan(hf) else 0))
    ys = y + DYS
    if not np.isnan(hf):                                    # where the face stands out of the hair it is exactly
        rec = blend(at(sx1, ys) - at(hfront, ys), 4, 26)    # as wide as the opening the front drawing leaves for it
        a = a * (1 - rec) + hf * rec
    a -= 2.0                                                # clear of the hair shell: no z-fight
    front = at(fsx1, ys)
    if np.isnan(front):
        front = at(sx1, ys) - 6
    else:
        front = min(front, at(sx1, ys)) - (0.5 if front - at(hfront, ys) > 8 else 4.0)
    backe = at(sx0, ys) + 12
    fb = at(fsx0, ys)
    if not np.isnan(fb):
        backe = min(backe, fb - 1)
    cd, b = (front + backe) / 2 - CS, (front - backe) / 2
    if y < YW:
        b *= max(cap, 0.05)
    secs.append(dict(c=(CX, y, cd), a=max(a, 2), b=max(b, 2), ax_u=AX_X, ax_v=AX_D, n=2.2, n_front=FACE_BOX,
                     w=W_HEAD))
sk = loft("head_skull", secs, head_uv(False), m=48)
# the sockets are real hollows: seen from the side they sit behind the brow, as on the side drawing
DENT = 3.0
for i, mt in enumerate(sk.meta):
    if mt["th"] is None or mt["v"] < 0.1:
        continue
    for c, r in SOCK_F:
        q = ((sk.v[i][0] - c[0]) / (r[0] - 1)) ** 2 + ((sk.v[i][1] - c[1]) / (r[1] - 1)) ** 2
        if q < 1:
            ridge = blend(abs(sk.v[i][0] - CX), 4, 12)          # the bridge of the nose stays: it is the profile line
            sk.v[i][2] -= DENT * math.sqrt(1 - q) * min(1.0, (mt["v"] - 0.1) / 0.25) * ridge

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
    for t in np.arange(-24, 400, 6.0):
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
        stations[i] = dict(stations[first_ok], t=-24 + 6.0 * i)
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
    for s, p0, p1 in zip(stations, p0s, p1s):
        t = s["t"]
        if t < t_hand - 20:
            p0 = max(p0, p1 - SLEEVE_W)                     # keep the upper edge, drop the drape below it
        c2 = S + t * u + (p0 + p1) / 2 * w
        a = max((p1 - p0) / 2, 2)
        hand = blend(t, t_hand - 4, t_hand + 8)
        b = a * ((1.4 - 0.3 * blend(t, 40, t_hand)) * (1 - hand) + 0.6 * hand)   # an oversized sleeve is deeper than wide
        e = blend(t, tE - 14, tE + 14)
        hw = blend(t, t_hand - 6, t_hand + 6)
        wts = {f"upper_arm.{sd.upper()}": (1 - e), f"forearm.{sd.upper()}": e * (1 - hw), f"hand.{sd.upper()}": e * hw}
        tw = 0.0
        secs.append(dict(c=(c2[0], c2[1], dS), a=a, b=b, ax_u=(w[0], w[1], 0), ax_v=AX_D, n=2.0,
                         w={k: v for k, v in wts.items() if v > 1e-4}, tw=tw, t=t, hand=hand))
    ARM_TIP[sd] = dict(S=S, E=E, u=u, t_hand=t_hand, t_tip=stations[-1]["t"], d=dS)

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

# ============================================================ legs (with the shoes)
LEG_TOP, MIRROR_Y = 506, 640


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
    for y in rows_between(LEG_TOP, SOLE + 0.5, 7):
        a0, a1 = at(f0, y), at(f1, y)
        d0, d1 = at(sl0, y) - CS, at(sl1, y) - CS
        k, fw = blend(y, KNEE_J[1] - 22, KNEE_J[1] + 22), blend(y, 938, 952)
        wts = {f"thigh.{up}": 1 - k, f"shin.{up}": k * (1 - fw), f"foot.{up}": k * fw}
        secs.append(dict(c=((a0 + a1) / 2, y, (d0 + d1) / 2), a=(a1 - a0) / 2, b=(d1 - d0) / 2, ax_u=AX_X, ax_v=AX_D,
                         n=2.2 + 0.9 * blend(y, 935, 955), w={k_: v for k_, v in wts.items() if v > 1e-4}))

    def uv(o, ids, nrm):
        P = np.array([o.v[i] for i in ids])
        s0 = o.meta[ids[0]]["s"]
        q = zone(o, ids)
        if P[:, 1].mean() > 930 and nrm[1] < -0.45:
            q = "side"                                      # the top of the shoe: laces as the side drawing shows them
        if q == "front":
            return "legs_f", [(p[0], p[1]) for p in P]
        if q == "side":
            return "legs_s", [(p[2] + CS, p[1]) for p in P]
        return "legs_b", [(kb - p[0], p[1]) for p in P]
    loft(f"leg_{sd}", secs, uv)


build_leg("r")
build_leg("l")
D_LEG = lambda y: (at(sl0, y) + at(sl1, y)) / 2 - CS

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


def bone(name, head, tail, parent, connect=False):
    BONES.append(dict(name=name, head=[float(c) for c in head], tail=[float(c) for c in tail], parent=parent,
                      connect=connect))


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
      round(NECK_D, 1), "t_hand", {k: v["t_hand"] for k, v in ARM_TIP.items()}, "YW", YW)

# ============================================================ 2D checks
from PIL import ImageDraw

front = np.zeros((1024, 1024, 3), int) + np.array(BG)
for name in ["leg_r_lower", "leg_l_lower", "leg_r_upper", "leg_l_upper", "arm_r_upper", "arm_l_upper", "torso", "head",
             "arm_r_lower", "arm_l_lower"]:
    rgb, m = parts[name]
    front[m] = rgb[m]
COL = dict(head_shell=(255, 80, 80), head_skull=(80, 255, 120), torso=(80, 160, 255), neck=(255, 255, 0),
           arm_r=(255, 160, 0), arm_l=(255, 160, 0), leg_r=(255, 0, 255), leg_l=(0, 255, 255))
for view, base, fx, fy in (("front", front, lambda p: p[0], lambda p: p[1]),
                           ("side", side.copy(), lambda p: p[2] + CS, lambda p: p[1])):
    im = Image.fromarray(base.astype(np.uint8)).resize((base.shape[1] * 2, base.shape[0] * 2), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for o in OBJS:
        if view == "side" and o.name.startswith("arm"):
            continue
        dy = DYS if (view == "side" and o.name.startswith("head")) else 0
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
