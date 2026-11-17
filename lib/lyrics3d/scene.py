"""3D horror-game lyric edit: the Blender scene engine. Blender 5.2, EEVEE, rendered at 360x640 (x3 nearest in post).

    blender -b -P lib/lyrics3d/scene.py -- --project projects/<id> --frames 0 441 [--out DIR] [--dbg side|front|back|top]
    (normally through `python -m lib.lyrics3d render|stills`)

This file builds the world that stays the same in every edit: the room, the mess on the floor, the hero, the lights,
and the helpers to pose him and place the camera. The edit itself is the project's `shots.py`: it is executed with
every name of this file in scope, may build its own props, and must define `apply(f)` -> shot name, which poses the
hero, the camera and the props for frame f. Nothing is keyframed: every frame is set up from scratch and rendered.

Per-frame head position on screen goes to <out>/meta_<a>_<b>.json for the glitch pass (post.py).
World: metres, Z up. The hero sits at the origin and faces -Y; +X is his left = screen right when looking at him.
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Quaternion, Vector

KIT = Path(__file__).resolve().parent
REPO = KIT.parents[1]
TEX = KIT / "assets" / "tex"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None, n=1):
    if name not in ARGS:
        return default
    i = ARGS.index(name)
    return ARGS[i + 1] if n == 1 else ARGS[i + 1:i + 1 + n]


PROJECT = Path(arg("--project", ".")).resolve()
EDIT = json.loads((PROJECT / "edit.json").read_text(encoding="utf-8"))
W, H = 360, 640
FPS, NFRAMES = EDIT.get("fps", 30), EDIT["frames"]
OUT = Path(arg("--out", str(PROJECT / "renders" / "seq"))).resolve()
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(REPO / EDIT.get("hero_blend", "lib/pixel_lyrics/characters/hollow/model3d/hollow_smooth.blend")))
scene = bpy.context.scene
col = scene.collection
arm = bpy.data.objects["hollow_rig"]
arm.animation_data_clear()
for ob in list(bpy.data.objects):
    if ob.type == "CAMERA":
        bpy.data.objects.remove(ob)


# ================================================================ materials
def new_nodes(m):
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 1.0
    for k in ("Specular IOR Level", "Specular"):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = 0.0
    return nt, bsdf


def lit_tex(m, img, emit=0.0, alpha=False, rough=1.0, spec=0.0):
    nt, bsdf = new_nodes(m)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image, tex.interpolation = img, "Closest"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = emit
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if alpha:
        cut = nt.nodes.new("ShaderNodeMath")
        cut.operation = "GREATER_THAN"
        cut.inputs[1].default_value = 0.5
        nt.links.new(tex.outputs["Alpha"], cut.inputs[0])
        nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
        for attr, val in (("blend_method", "CLIP"), ("surface_render_method", "DITHERED")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    m.use_backface_culling = False
    return bsdf


MATS = {}


def mtex(name, emit=0.0, alpha=False, rough=1.0, spec=0.0, key=None):
    key = key or (name, emit, alpha, rough, spec)
    if key not in MATS:
        m = bpy.data.materials.new(f"m_{name}_{len(MATS)}")
        own = PROJECT / "assets" / "tex" / f"{name}.png"                 # a project texture wins over the kit's
        img = bpy.data.images.get(f"{name}.png") or bpy.data.images.load(str(own if own.exists() else TEX / f"{name}.png"))
        m["bsdf"] = lit_tex(m, img, emit, alpha, rough, spec).name
        MATS[key] = m
    return MATS[key]


def mflat(name, rgb, emit=0.0, rough=1.0, spec=0.0, alpha=1.0):
    key = ("flat", name)
    if key not in MATS:
        m = bpy.data.materials.new(f"f_{name}")
        nt, bsdf = new_nodes(m)
        c = [pow(v / 255.0, 2.2) for v in rgb] + [1.0]
        bsdf.inputs["Base Color"].default_value = c
        bsdf.inputs["Emission Color"].default_value = c
        bsdf.inputs["Emission Strength"].default_value = emit
        bsdf.inputs["Roughness"].default_value = rough
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        if alpha < 1:
            bsdf.inputs["Alpha"].default_value = alpha
            try:
                m.surface_render_method = "DITHERED"
            except Exception:
                pass
        MATS[key] = m
    return MATS[key]


# the hero: the same drawings, now lit by the room (plus a little of its own light so the face never goes black)
hero_mat = bpy.data.materials["hollow_pixels"]
hero_img = next(n.image for n in hero_mat.node_tree.nodes if n.type == "TEX_IMAGE")
HERO_BSDF = lit_tex(hero_mat, hero_img, emit=0.07, alpha=True)
_nt = hero_mat.node_tree                                   # the pale face must not burn out under the lamp: darker paint
_tex = next(n for n in _nt.nodes if n.type == "TEX_IMAGE")
_hsv = _nt.nodes.new("ShaderNodeHueSaturation")
_hsv.inputs["Value"].default_value = float(arg("--skin", 0.5))
_nt.links.new(_tex.outputs["Color"], _hsv.inputs["Color"])
_nt.links.new(_hsv.outputs["Color"], HERO_BSDF.inputs["Base Color"])


# ================================================================ mesh helpers
def cube_uv(bm, scale=1.0, fit=False):
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        pts = []
        for lp in f.loops:
            c = lp.vert.co
            if ax == 2:
                a, b = (c.x if n.z > 0 else -c.x), c.y
            elif ax == 0:
                a, b = (c.y if n.x > 0 else -c.y), c.z
            else:
                a, b = (-c.x if n.y > 0 else c.x), c.z
            pts.append((a, b))
        if fit:
            a0, a1 = min(p[0] for p in pts), max(p[0] for p in pts)
            b0, b1 = min(p[1] for p in pts), max(p[1] for p in pts)
            pts = [((p[0] - a0) / max(a1 - a0, 1e-9), (p[1] - b0) / max(b1 - b0, 1e-9)) for p in pts]
        else:
            pts = [(p[0] * scale, p[1] * scale) for p in pts]
        for lp, p in zip(f.loops, pts):
            lp[uvl].uv = p


def finish(name, bm, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, smooth=False, mats=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in (mats or [mat]):
        me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.location, ob.rotation_euler = loc, rot
    if parent:
        ob.parent = parent
    return ob


def box(name, size, loc, mat, rot=(0, 0, 0), uv=1.0, fit=False, parent=None, face_mats=None):
    """face_mats: {"+z": mat, "-y": mat ...} overrides on single faces (those faces get fitted UVs)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.normal_update()
    cube_uv(bm, uv, fit)
    mats = [mat]
    if face_mats:
        uvl = bm.loops.layers.uv.verify()
        for key, fm in face_mats.items():
            ax, sg = "xyz".index(key[1]), (1 if key[0] == "+" else -1)
            for f in bm.faces:
                if f.normal[ax] * sg > 0.9:
                    mats.append(fm)
                    f.material_index = len(mats) - 1
                    for lp, p in zip(f.loops, _fit_face(f)):
                        lp[uvl].uv = p
    return finish(name, bm, mat, loc, rot, parent, mats=mats)


def _fit_face(f):
    n = f.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    pts = []
    for lp in f.loops:
        c = lp.vert.co
        if ax == 2:
            a, b = (c.x if n.z > 0 else -c.x), c.y
        elif ax == 0:
            a, b = (c.y if n.x > 0 else -c.y), c.z
        else:
            a, b = (-c.x if n.y > 0 else c.x), c.z
        pts.append((a, b))
    a0, a1 = min(p[0] for p in pts), max(p[0] for p in pts)
    b0, b1 = min(p[1] for p in pts), max(p[1] for p in pts)
    return [((p[0] - a0) / max(a1 - a0, 1e-9), (p[1] - b0) / max(b1 - b0, 1e-9)) for p in pts]


def cyl(name, r, h, loc, mat, rot=(0, 0, 0), seg=8, r2=None, parent=None, cap_mat=None, wrap=1.0):
    """Cylinder / cone along Z, centred. Side UV wraps the texture `wrap` times; caps are fitted."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bm.normal_update()
    uvl = bm.loops.layers.uv.verify()
    mats = [mat] + ([cap_mat] if cap_mat else [])
    for f in bm.faces:
        if abs(f.normal.z) > 0.9:
            for lp in f.loops:
                c = lp.vert.co
                rr = max(r, r2 or r)
                lp[uvl].uv = (c.x / rr * 0.5 + 0.5, c.y / rr * 0.5 + 0.5)
            if cap_mat:
                f.material_index = 1
        else:
            cen = f.calc_center_median()
            base = math.atan2(cen.y, cen.x)
            for lp in f.loops:
                c = lp.vert.co
                a = math.atan2(c.y, c.x)
                while a - base > math.pi:
                    a -= 2 * math.pi
                while a - base < -math.pi:
                    a += 2 * math.pi
                lp[uvl].uv = (-a / (2 * math.pi) * wrap, c.z / h + 0.5)
    return finish(name, bm, mat, loc, rot, parent, smooth=False, mats=mats)


def blob(name, r, loc, mat, seed, squash=(1, 1, 1), parent=None):
    """Crumpled low-poly lump (paper, foil, cloth)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
    for v in bm.verts:
        k = 0.65 + 0.6 * rnd.random()
        v.co = Vector((v.co.x * k * squash[0], v.co.y * k * squash[1], v.co.z * k * squash[2]))
    bm.normal_update()
    cube_uv(bm, 6.0)
    return finish(name, bm, mat, loc, (0, 0, rnd.random() * 6.28), parent)


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    col.objects.link(e)
    e.location = loc
    if parent:
        e.parent = parent
    return e


# ================================================================ the room
RX0, RX1, RY0, RY1, RZ = -2.15, 2.15, -2.3, 1.95, 2.6
WALL = mtex("wallpaper")
box("floor", (RX1 - RX0 + 0.4, RY1 - RY0 + 0.4, 0.1), ((RX0 + RX1) / 2, (RY0 + RY1) / 2, -0.05), mtex("floor"), uv=1.1)
box("rug", (2.5, 3.3, 0.02), (0.0, -0.25, 0.008), mtex("floor"), face_mats={"+z": mtex("rug")})
box("wall_back", (RX1 - RX0, 0.1, RZ), ((RX0 + RX1) / 2, RY1 + 0.05, RZ / 2), WALL, uv=0.95)
box("wall_front", (RX1 - RX0, 0.1, RZ), ((RX0 + RX1) / 2, RY0 - 0.05, RZ / 2), WALL, uv=0.95)
box("wall_left", (0.1, RY1 - RY0, RZ), (RX0 - 0.05, (RY0 + RY1) / 2, RZ / 2), WALL, uv=0.95)
box("wall_right", (0.1, RY1 - RY0, RZ), (RX1 + 0.05, (RY0 + RY1) / 2, RZ / 2), WALL, uv=0.95)
CEIL = box("ceiling", (RX1 - RX0, RY1 - RY0, 0.1), ((RX0 + RX1) / 2, (RY0 + RY1) / 2, RZ + 0.05), mtex("plaster"), uv=0.7)
DARK = mflat("dark", (26, 28, 36))
PLASTIC = mflat("plastic", (44, 46, 56), rough=0.5, spec=0.3)
# skirting
for nm, sz, lc in (("sk_b", (RX1 - RX0, 0.03, 0.09), (0, RY1 - 0.015, 0.045)), ("sk_l", (0.03, RY1 - RY0, 0.09), (RX0 + 0.015, (RY0 + RY1) / 2, 0.045)),
                   ("sk_r", (0.03, RY1 - RY0, 0.09), (RX1 - 0.015, (RY0 + RY1) / 2, 0.045)), ("sk_f", (RX1 - RX0, 0.03, 0.09), (0, RY0 + 0.015, 0.045))):
    box(nm, sz, lc, DARK)
# carpet on the wall behind him, mattress under it
box("wallrug", (2.5, 0.03, 1.55), (0.15, RY1 - 0.02, 1.55), DARK, face_mats={"-y": mtex("wallrug")})
box("mattress", (1.95, 0.92, 0.2), (-0.35, 1.47, 0.1), mtex("mattress"), uv=3.0)
box("blanket", (1.1, 0.8, 0.07), (-0.7, 1.42, 0.235), mtex("plaid"), rot=(0.05, -0.04, 0.22), uv=3.0)
box("blanket2", (0.75, 0.55, 0.09), (0.1, 1.3, 0.245), mtex("plaid"), rot=(-0.08, 0.1, -0.5), uv=3.0)
box("pillow", (0.5, 0.34, 0.11), (0.25, 1.7, 0.26), mflat("pillow", (120, 128, 140)), rot=(0.1, 0.05, 0.3))
# window with blinds on his right-hand wall (screen left in the front shot), radiator under it
box("window", (0.03, 1.05, 1.35), (RX0 + 0.02, 0.35, 1.55), DARK, face_mats={"+x": mtex("window", emit=0.9)})
box("sill", (0.16, 1.2, 0.04), (RX0 + 0.08, 0.35, 0.86), mflat("sill", (120, 126, 134)))
for i in range(7):
    box(f"rad{i}", (0.09, 0.09, 0.5), (RX0 + 0.08, 0.02 + i * 0.11, 0.47), mflat("rad", (110, 116, 124)))
# door, wardrobe, shelf on the other side
box("door", (0.04, 0.85, 2.02), (RX1 - 0.02, -1.2, 1.01), DARK, face_mats={"-x": mtex("door")})
box("wardrobe", (0.55, 1.15, 1.95), (RX1 - 0.3, 1.3, 0.975), mflat("wardrobe", (40, 40, 50)))
box("wardrobe_d", (0.02, 0.54, 1.8), (RX1 - 0.585, 1.02, 0.98), mflat("wardrobe2", (52, 52, 64)))
box("wardrobe_e", (0.02, 0.54, 1.8), (RX1 - 0.585, 1.6, 0.98), mflat("wardrobe2", (52, 52, 64)))
for i, (nm, x, z, s) in enumerate((("poster_0", -1.55, 1.75, 1.0), ("poster_1", 1.42, 1.9, 0.85), ("poster_2", -1.5, 0.95, 0.7))):
    box(f"post{i}", (0.42 * s, 0.01, 0.62 * s), (x, RY1 - 0.012, z), DARK, rot=(0, (i - 1) * 0.06, 0), face_mats={"-y": mtex(nm)})
box("post3", (0.01, 0.42, 0.62), (RX1 - 0.012, 0.1, 1.6), DARK, rot=(0.05, 0, 0), face_mats={"-x": mtex("poster_2")})
box("post4", (0.01, 0.38, 0.56), (RX0 + 0.012, -1.3, 1.5), DARK, rot=(-0.07, 0, 0), face_mats={"+x": mtex("poster_1")})
# bare bulb on a wire
WIRE = cyl("wire", 0.006, 0.5, (0.55, 0.45, RZ - 0.25), DARK, seg=4)
BULB = cyl("bulb", 0.035, 0.07, (0.55, 0.45, RZ - 0.53), mflat("bulb", (210, 230, 255), emit=6.0), seg=6)

# TV on a stand in front of him, console + pad on the floor
TV_Y = -1.72
box("tvstand", (0.9, 0.42, 0.34), (0.05, TV_Y - 0.1, 0.17), mflat("stand", (46, 44, 52)))
box("tv", (0.66, 0.5, 0.52), (0.05, TV_Y - 0.1, 0.6), PLASTIC)
TV_MATS = [mtex(f"tv_{i}", emit=3.0) for i in range(4)]
TV_SCREEN = box("tvscreen", (0.52, 0.02, 0.39), (0.05, TV_Y + 0.155, 0.62), DARK, face_mats={"+y": TV_MATS[0]})
box("console", (0.3, 0.22, 0.06), (-0.55, -1.42, 0.03), mflat("console", (72, 76, 88)), rot=(0, 0, 0.3))
box("pad", (0.15, 0.09, 0.03), (-0.42, -1.0, 0.03), mflat("pad", (66, 70, 82)), rot=(0, 0, -0.5))
for i in range(5):                                           # the pad's cable, a few straight bits
    box(f"cable{i}", (0.012, 0.11, 0.012), (-0.45 - i * 0.02 * (-1) ** i, -1.07 - i * 0.075, 0.008), DARK, rot=(0, 0, 0.5 * (-1) ** i))

# ---------------------------------------------------------------- the mess on the floor
RND = random.Random(11)
GLASS = [mflat("glass_g", (30, 70, 64), rough=0.25, spec=0.6), mflat("glass_b", (60, 44, 34), rough=0.25, spec=0.6),
         mflat("glass_c", (120, 140, 160), rough=0.2, spec=0.7, alpha=0.75)]
WHITE = mflat("white", (224, 228, 234))
PILL_COLS = [WHITE, WHITE, mflat("pill_blue", (96, 150, 226)), mflat("pill_pink", (210, 120, 160)), mflat("pill_yel", (220, 206, 120))]
METAL = mflat("metal", (150, 158, 170), rough=0.3, spec=0.8)


def bottle(i, x, y, lying=False, yaw=0.0, g=0, label=True):
    e = empty(f"bottle{i}", (x, y, 0.036 if lying else 0.0))
    e.rotation_euler = (math.pi / 2, 0, yaw) if lying else (0, 0, yaw)
    lab = mtex("bottle_label") if label else None
    cyl(f"b{i}_body", 0.036, 0.17, (0, 0, 0.085), GLASS[g], parent=e)
    if label:
        cyl(f"b{i}_lab", 0.0375, 0.07, (0, 0, 0.09), lab, parent=e, wrap=2.0)
    cyl(f"b{i}_sh", 0.036, 0.05, (0, 0, 0.195), GLASS[g], r2=0.013, parent=e)
    cyl(f"b{i}_neck", 0.013, 0.07, (0, 0, 0.255), GLASS[g], parent=e, seg=6)
    return e


def can(i, x, y, lying=False, yaw=0.0):
    e = empty(f"can{i}", (x, y, 0.033 if lying else 0.0))
    e.rotation_euler = (math.pi / 2, 0, yaw) if lying else (0, 0, yaw)
    cyl(f"c{i}", 0.033, 0.13, (0, 0, 0.065), mtex("can"), parent=e, cap_mat=METAL, wrap=2.0)
    return e


def syringe(i, x, y, yaw):
    e = empty(f"syr{i}", (x, y, 0.012))
    e.rotation_euler = (math.pi / 2, 0, yaw)
    cyl(f"s{i}_barrel", 0.011, 0.10, (0, 0, 0.0), mflat("syr", (200, 214, 230), rough=0.3, spec=0.5), parent=e, seg=6)
    cyl(f"s{i}_plunger", 0.005, 0.07, (0, 0, -0.085), WHITE, parent=e, seg=4)
    cyl(f"s{i}_cap", 0.016, 0.008, (0, 0, -0.122), WHITE, parent=e, seg=6)
    cyl(f"s{i}_flange", 0.02, 0.006, (0, 0, -0.05), WHITE, parent=e, seg=6)
    cyl(f"s{i}_hub", 0.006, 0.02, (0, 0, 0.06), mflat("hub", (230, 150, 60)), parent=e, seg=4)
    cyl(f"s{i}_needle", 0.0025, 0.06, (0, 0, 0.1), METAL, parent=e, seg=3)
    return e


def pizzabox(i, x, y, yaw, z=0.0, opened=False):
    e = empty(f"pz{i}", (x, y, z))
    e.rotation_euler = (0, 0, yaw)
    card = mtex("cardboard")
    if not opened:
        box(f"pz{i}_b", (0.36, 0.36, 0.045), (0, 0, 0.0225), card, uv=4, parent=e, face_mats={"+z": mtex("pizzabox")})
    else:
        box(f"pz{i}_b", (0.36, 0.36, 0.012), (0, 0, 0.006), card, uv=4, parent=e, face_mats={"+z": mtex("pizza")})
        for k, (sx, sy, lx, ly) in enumerate(((0.36, 0.01, 0, -0.18), (0.01, 0.36, 0.18, 0), (0.01, 0.36, -0.18, 0))):
            box(f"pz{i}_w{k}", (sx, sy, 0.04), (lx, ly, 0.02), card, uv=4, parent=e)
        box(f"pz{i}_lid", (0.36, 0.012, 0.36), (0, 0.2, 0.165), card, rot=(-0.35, 0, 0), uv=4, parent=e, face_mats={"-y": mtex("pizzabox")})
    return e


def pill(i, x, y, big=1.0):
    m = RND.choice(PILL_COLS)
    if RND.random() < 0.35:                                   # a capsule: a short stick
        return box(f"pill{i}", (0.03 * big, 0.012 * big, 0.012 * big), (x, y, 0.008), m, rot=(0, 0, RND.random() * 6.28))
    return cyl(f"pill{i}", 0.011 * big, 0.007 * big, (x, y, 0.006), m, seg=6)


def free_spot(r0=0.5, r1=1.55):
    """A random floor spot around him that is not under his body, legs or hands."""
    for _ in range(200):
        a, r = RND.random() * 6.28, r0 + (r1 - r0) * RND.random() ** 0.8
        x, y = math.cos(a) * r, math.sin(a) * r * 1.05 - 0.15
        if abs(x) < 0.42 and -1.0 < y < 0.85:
            continue
        if x < RX0 + 0.3 or x > RX1 - 0.3 or y < TV_Y + 0.45 or y > 0.95:
            continue
        return x, y
    return 1.2, -0.5


pizzabox(0, 1.0, 0.25, 0.35)
pizzabox(1, 1.03, 0.22, -0.15, z=0.046)
pizzabox(2, 0.97, 0.27, 0.6, z=0.092)
pizzabox(3, -0.95, -0.55, 0.5, opened=True)
pizzabox(4, 0.75, -1.25, -0.4)
bottle(0, 0.72, -0.35, g=0)
bottle(1, 0.86, -0.5, g=1)
bottle(2, -0.82, 0.42, g=0)
bottle(3, -0.62, 0.72, lying=True, yaw=0.8, g=1)
bottle(4, 0.55, 0.55, lying=True, yaw=-1.9, g=2, label=False)
bottle(5, -1.15, 0.05, lying=True, yaw=2.6, g=0)
bottle(6, 1.3, -0.75, g=2, label=False)
can(0, -0.6, -0.95, yaw=1.0)
can(1, 0.6, 0.15, lying=True, yaw=0.4)
can(2, -1.2, -0.3, lying=True, yaw=-1.2)
can(3, 1.25, -0.1)
can(4, -0.5, -1.3, lying=True, yaw=2.2)
for i, (x, y, yaw) in enumerate(((0.52, -0.25, 0.6), (-0.52, 0.1, -2.2), (0.46, -0.72, 2.4), (-0.7, -0.15, 1.2), (0.9, -0.85, -0.7),
                                  (-0.45, 0.95, 0.2), (0.3, 0.95, -2.9))):
    syringe(i, x, y, yaw)
n = 0
for cx, cy, cnt, spread in ((0.6, -0.1, 16, 0.2), (-0.6, -0.3, 14, 0.22), (0.5, 0.75, 10, 0.18), (-0.75, 0.8, 9, 0.2), (0.1, -1.15, 9, 0.25)):
    for _ in range(cnt):
        pill(n, cx + RND.gauss(0, spread), cy + RND.gauss(0, spread), big=1.5)
        n += 1
for _ in range(34):
    x, y = free_spot()
    pill(n, x, y, big=1.5)
    n += 1
for i in range(7):
    x, y = free_spot(0.55, 1.3)
    box(f"blister{i}", (0.11, 0.07, 0.006), (x, y, 0.004), METAL, rot=(0, 0, RND.random() * 6.28), face_mats={"+z": mtex("blister", rough=0.4, spec=0.5)})
for i in range(7):
    x, y = free_spot(0.6, 1.6)
    blob(f"paper{i}", 0.05 + 0.03 * RND.random(), (x, y, 0.035), mflat("paper", (170, 176, 184)), 50 + i, squash=(1, 1, 0.7))
for i in range(3):
    x, y = free_spot(0.6, 1.2)
    blob(f"foil{i}", 0.035, (x, y, 0.02), METAL, 70 + i, squash=(1, 1, 0.5))
# tipped pill bottle with its pills spilled, a second one standing
e = empty("pb0", (0.42, -0.5, 0.03))
e.rotation_euler = (math.pi / 2, 0, 0.9)
cyl("pb0_b", 0.03, 0.075, (0, 0, 0), mflat("amber", (190, 110, 40), rough=0.3, spec=0.5, alpha=0.85), parent=e)
cyl("pb0_l", 0.031, 0.045, (0, 0, 0), mtex("pillbottle"), parent=e, wrap=2.0)
for k in range(9):
    pill(n, 0.5 + RND.gauss(0, 0.06), -0.42 + RND.gauss(0, 0.05), big=1.5)
    n += 1
cyl("pb1_b", 0.03, 0.075, (-0.48, 0.45, 0.0375), mflat("amber", (190, 110, 40)))
cyl("pb1_l", 0.031, 0.045, (-0.48, 0.45, 0.035), mtex("pillbottle"), wrap=2.0)
cyl("pb1_cap", 0.032, 0.02, (-0.48, 0.45, 0.085), WHITE)
# phone, ashtray with butts, lighter, spoon
box("phone", (0.075, 0.15, 0.01), (0.58, 0.38, 0.006), DARK, rot=(0, 0, -0.5), face_mats={"+z": mtex("phone", emit=2.0)})
cyl("ashtray", 0.07, 0.025, (-0.52, -0.62, 0.0125), GLASS[2], seg=8)
for i in range(6):
    a = i * 1.1
    cyl(f"butt{i}", 0.005, 0.035, (-0.52 + math.cos(a) * 0.04 * (1 + (i % 2)), -0.62 + math.sin(a) * 0.04 * (1 + (i % 2)), 0.03 if i % 2 == 0 else 0.006),
        mflat("butt", (200, 170, 120)), rot=(1.2, 0, a), seg=4)
box("lighter", (0.025, 0.07, 0.012), (-0.4, -0.72, 0.007), mflat("lighter", (60, 150, 210)), rot=(0, 0, 0.7))
box("spoon_h", (0.012, 0.1, 0.004), (0.66, -0.62, 0.004), METAL, rot=(0, 0, 0.4))
cyl("spoon_b", 0.02, 0.006, (0.64, -0.565, 0.004), METAL, seg=6)
box("sock", (0.09, 0.2, 0.03), (1.25, 0.75, 0.015), mflat("sock", (150, 156, 166)), rot=(0, 0, 0.9))
blob("hoodie_pile", 0.22, (-1.35, 1.0, 0.07), mflat("cloth", (34, 34, 46)), 90, squash=(1.2, 1, 0.4))
blob("bag", 0.16, (1.45, -1.55, 0.1), mflat("bagp", (70, 80, 96)), 91, squash=(1, 1, 0.8))

# ================================================================ lights, world, camera, render settings
world = bpy.data.worlds.new("w")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
wn = world.node_tree
for n_ in list(wn.nodes):
    wn.nodes.remove(n_)
wo = wn.nodes.new("ShaderNodeOutputWorld")
bg = wn.nodes.new("ShaderNodeBackground")
bg.inputs[0].default_value = (0.004, 0.007, 0.018, 1)
bg.inputs[1].default_value = 1.0
wn.links.new(bg.outputs[0], wo.inputs["Surface"])
if "--nofog" not in ARGS:
    vol = wn.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Color"].default_value = (0.55, 0.7, 1.0, 1)
    vol.inputs["Density"].default_value = float(arg("--fog", 0.012))
    vol.inputs["Anisotropy"].default_value = 0.35
    wn.links.new(vol.outputs[0], wo.inputs["Volume"])


def light(name, kind, loc, energy, color, **kw):
    d = bpy.data.lights.new(name, kind)
    d.energy, d.color = energy, color
    for k, v in kw.items():
        setattr(d, k, v)
    o = bpy.data.objects.new(name, d)
    col.objects.link(o)
    o.location = loc
    return o


BULB_POS = Vector((0.55, 0.45, RZ - 0.58))
L_BULB = light("bulb_spot", "SPOT", BULB_POS, 330, (0.84, 0.92, 1.0), spot_size=math.radians(74), spot_blend=0.75, shadow_soft_size=0.05)
L_BULB.rotation_euler = (Vector((0.0, -0.15, 0.2)) - BULB_POS).to_track_quat("-Z", "Y").to_euler()   # aimed at him
L_TV = light("tv_glow", "AREA", (0.05, TV_Y + 0.2, 0.62), 70, (0.25, 0.45, 1.0), shape="RECTANGLE", size=0.52, size_y=0.39)
L_TV.rotation_euler = (math.radians(90), 0, 0)                           # faces +Y
L_WIN = light("window_glow", "AREA", (RX0 + 0.08, 0.35, 1.55), 34, (0.45, 0.7, 1.0), shape="RECTANGLE", size=1.0, size_y=1.3)
L_WIN.rotation_euler = (0, math.radians(-90), 0)                          # faces +X
L_FILL = light("fill", "POINT", (0.0, -0.9, 1.4), 8, (0.5, 0.65, 1.0), shadow_soft_size=0.4)

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
col.objects.link(cam)
scene.camera = cam
cam_data.sensor_fit = "VERTICAL"
cam_data.sensor_height = 36.0
cam_data.clip_start, cam_data.clip_end = 0.02, 30

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        continue
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W, H, 100
scene.render.fps = FPS
scene.render.film_transparent = False
scene.render.filter_size = float(arg("--filter", 0))        # 0 = no edge smoothing: hard pixel stairs (the user's choice)
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
for k, v in (("taa_render_samples", int(arg("--samples", 12))), ("use_raytracing", False), ("volumetric_tile_size", "4"),
             ("volumetric_samples", 48), ("volumetric_end", 8.0), ("use_volumetric_shadows", True), ("use_shadows", True),
             ("shadow_ray_count", 1), ("shadow_step_count", 4)):
    try:
        setattr(scene.eevee, k, v)
    except Exception as ex:
        print("eevee setting skipped:", k, ex)


# ================================================================ posing the hero
def turn(bone, deg, axis="Y"):
    """Rotate a pose bone around a WORLD axis (name or Vector) through its head; CURL / SPREAD / ROLL are bone-local."""
    pb = arm.pose.bones[bone]
    if axis in ("CURL", "SPREAD"):
        pb.matrix_basis = pb.matrix_basis @ Matrix.Rotation(math.radians(deg), 4, "X" if axis == "CURL" else "Z")
        return
    if axis == "ROLL":
        pb.matrix = pb.matrix @ Matrix.Rotation(math.radians(deg), 4, "Y")
        bpy.context.view_layer.update()
        return
    Mw = arm.matrix_world @ pb.matrix
    piv = Mw.translation.copy()
    Rm = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-piv)
    pb.matrix = arm.matrix_world.inverted() @ Rm @ Mw
    bpy.context.view_layer.update()


FINGER_NAMES = ("thumb", "f_index", "f_middle", "f_ring", "f_pinky")


def fingers(sd, curl):
    if not isinstance(curl, (list, tuple)):
        curl = [curl] * 5
    out = []
    for name, c in zip(FINGER_NAMES, curl):
        k = (0.35, 0.45, 0.6) if name == "thumb" else (0.95, 1.1, 0.75)
        out += [(f"{name}.0{i + 1}.{sd}", c * k[i], "CURL") for i in range(3)]
    return out


def set_pose(pose):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for bone, deg, axis in pose:
        turn(bone, deg, axis)
    bpy.context.view_layer.update()


RELAXED = (12, 16, 22, 28, 34)
SIT_DZ = -0.70                                   # the rig is lowered so that the seat is on the floor


def pose_sit(lean, arms="back", legs_open=8.0):
    """Sitting on the floor, legs straight out in front. lean: degrees the torso is tipped back from upright."""
    p = [("pelvis", -lean, "X")]
    for sd, k in (("R", -1), ("L", 1)):
        p += [(f"thigh.{sd}", -(88 - lean), "X"), (f"thigh.{sd}", k * legs_open, "Z"), (f"shin.{sd}", 3, "X"),
              (f"foot.{sd}", 18, "X"), (f"foot.{sd}", k * 14, "Y")]
        if arms == "back":                        # leaning on straight arms behind him, palms on the floor
            p += [(f"upper_arm.{sd}", k * 48, "Y"), (f"upper_arm.{sd}", 34 + lean, "X"), (f"upper_arm.{sd}", k * 16, "Y"), (f"upper_arm.{sd}", -k * 28, "Z"),
                  (f"forearm.{sd}", -6, "X"), (f"forearm.{sd}", k * -80, "ROLL"), (f"hand.{sd}", -58, "X")]
            p += fingers(sd, (10, 4, 4, 6, 8))
        else:                                     # upright: arms hang, hands rest on the thighs
            p += [(f"upper_arm.{sd}", k * 44, "Y"), (f"upper_arm.{sd}", -14 + lean, "X"), (f"forearm.{sd}", -52, "X"),
                  (f"forearm.{sd}", k * -14, "Y"), (f"forearm.{sd}", k * 60, "ROLL")]
            p += fingers(sd, RELAXED)
    p += [("spine", 4, "X"), ("chest", 5, "X")]   # a little slump
    return p


HEAD_FACE = arm.data.bones["head"].matrix_local.to_3x3().inverted() @ Vector((0, -1, 0))


def head_world():
    pb = arm.pose.bones["head"]
    M = arm.matrix_world @ pb.matrix
    return M, (M.to_3x3() @ HEAD_FACE).normalized()


def spin(bone, q, k=1.0):
    """Rotate a bone by a share k of the world-space quaternion q, about the bone's head."""
    pb = arm.pose.bones[bone]
    Mw = arm.matrix_world @ pb.matrix
    piv = Mw.translation.copy()
    qq = Quaternion().slerp(q, k)
    pb.matrix = arm.matrix_world.inverted() @ (Matrix.Translation(piv) @ qq.to_matrix().to_4x4() @ Matrix.Translation(-piv) @ Mw)
    bpy.context.view_layer.update()


def aim_head(target, amount=1.0):
    """Turn neck + head so that the face looks at a world point."""
    for bone, k in (("neck", 0.45), ("head", 1.0)):
        M, face = head_world()
        want = (Vector(target) - M.translation).normalized()
        spin(bone, face.rotation_difference(want), k * amount)


def head_centre():
    pb = arm.pose.bones["head"]
    M = arm.matrix_world @ pb.matrix
    return M @ Vector((0, 0.11, 0)), M


# ================================================================ easing, noise, camera
def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t, p=3):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** p


def hsh(i, salt=0):
    """Deterministic 0..1 noise per integer."""
    x = math.sin(i * 127.1 + salt * 311.7) * 43758.5453
    return x - math.floor(x)


def wob(f, salt, speed=1.0):
    """Smooth -1..1 wobble for hand-held camera."""
    t = f / FPS * speed
    return (math.sin(t * 1.7 + salt * 2.1) * 0.5 + math.sin(t * 2.9 + salt * 5.3) * 0.3 + math.sin(t * 5.3 + salt * 1.3) * 0.2)


def swing(f, keys):
    """Smooth -1..1 through keys [(frame, value), ...]: cosine swings between them, so it never snaps."""
    if f <= keys[0][0]:
        return keys[0][1]
    for (fa, va), (fb, vb) in zip(keys, keys[1:]):
        if fa <= f <= fb:
            k = 0.5 - 0.5 * math.cos(math.pi * (f - fa) / float(fb - fa))
            return va + (vb - va) * k
    return keys[-1][1]


def jerk(f, table, amp, hold=2, wild=False):
    """Sharp head throws -> (roll about the view axis, side lean) in degrees. No in-betweens: it snaps and holds.
    table: the frames of the hits (syllables). Each hit throws the head to the other side for `hold` frames, then it
    snaps back. wild: from table[0] on the head goes from side to side all the time, changing every `hold` frames."""
    if wild:
        i = (f - table[0]) // hold
        side = 1 if i % 2 == 0 else -1
        return (side * amp * (0.55 + 0.45 * hsh(i, 1)), side * amp * (0.5 + 0.5 * hsh(i, 2)) * 0.8)
    for i, s in enumerate(table):
        if s <= f < s + hold:
            side = 1 if i % 2 == 0 else -1
            return (side * amp * (0.6 + 0.4 * hsh(i, 3)), -side * amp * 0.6 * hsh(i, 4))
    return (0.0, 0.0)


def throw_head(roll, lean):
    """Apply a jerk() / swing() result on top of the current head pose: roll about where the face looks, lean sideways."""
    if roll or lean:
        M, face = head_world()
        spin("head", Quaternion(face, math.radians(roll)))
        spin("neck", Quaternion(Vector((0, 1, 0)), math.radians(lean)), 0.5)
        spin("head", Quaternion(Vector((0, 1, 0)), math.radians(lean)), 0.5)


def camera_at(pos, target, up=(0, 0, 1), roll=0.0, lens=28.0):
    pos, target, up = Vector(pos), Vector(target), Vector(up)
    z = (pos - target).normalized()
    x = up.cross(z)
    if x.length < 1e-4:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    cam.matrix_world = Matrix.Translation(pos) @ M @ Matrix.Rotation(roll, 4, "Z")
    cam_data.lens = lens


DBG = arg("--dbg")
BULB_E, TV_E = float(arg("--bulb", 235)), float(arg("--tv", 36))


def room_tick(f):
    """What the room does on its own on every frame: the TV flickers, the lamp dips now and then."""
    arm.location = (0, 0, SIT_DZ)
    tvk = 0.65 + 0.7 * hsh(f // 2, 9)
    L_TV.data.energy = TV_E * tvk
    TV_SCREEN.data.materials[1] = TV_MATS[(f // 2) % 4]
    L_BULB.data.energy = BULB_E * (1.0 if hsh(f // 3, 12) > 0.06 else 0.5)
    BULB.hide_render = WIRE.hide_render = False
    CEIL.hide_render = False


def debug_camera():
    """--dbg: look at the pose from outside the shot (the ceiling is hidden)."""
    CEIL.hide_render = True
    if DBG == "side":
        camera_at((2.05, -0.2, 0.8), (0, -0.1, 0.45), lens=30)
    elif DBG == "front":
        camera_at((0.0, -1.45, 0.8), (0, 0, 0.5), lens=24)
    elif DBG == "back":
        camera_at((1.2, 1.8, 1.5), (0, 0.2, 0.3), lens=24)
    elif DBG == "top":
        camera_at((0.0, -0.3, 5.5), (0, -0.3, 0), up=(0, 1, 0), lens=36)


def head_meta():
    hc, M = head_centre()
    v = world_to_camera_view(scene, cam, hc)
    camR = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
    v2 = world_to_camera_view(scene, cam, hc + camR * 0.15)
    up = world_to_camera_view(scene, cam, hc + (M.to_3x3() @ Vector((0, 1, 0))).normalized() * 0.15)
    return {"x": v.x * W, "y": (1 - v.y) * H, "r": abs(v2.x - v.x) * W, "z": v.z,
            "ux": (up.x - v.x) * W, "uy": -(up.y - v.y) * H}


# ================================================================ the edit: the project's shots.py
_shots = PROJECT / "shots.py"
exec(compile(_shots.read_text(encoding="utf-8"), str(_shots), "exec"), globals())


def setup(f):
    room_tick(f)
    shot = apply(f)                                          # noqa: F821  (defined by shots.py)
    if DBG:
        debug_camera()
    bpy.context.view_layer.update()
    return shot


if "--save" in ARGS:
    setup(int(arg("--save-frame", 150)))
    bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT / "renders" / "scene.blend"))

frames = []
if "--frames" in ARGS:
    a, b = (int(v) for v in arg("--frames", n=2))
    frames = list(range(a, b + 1))
elif "--stills" in ARGS:
    i = ARGS.index("--stills")
    frames = [int(v) for v in ARGS[i + 1:] if v.lstrip("-").isdigit()]
meta = {}
tag = arg("--tag", "")
for f in frames:
    shot = setup(f)
    scene.frame_set(f)
    scene.render.filepath = str(OUT / f"{tag}{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    meta[f] = dict(head_meta(), shot=shot)
    print("frame", f, shot, flush=True)
if frames:
    (OUT / f"meta_{tag}{frames[0]:04d}_{frames[-1]:04d}.json").write_text(json.dumps(meta))
