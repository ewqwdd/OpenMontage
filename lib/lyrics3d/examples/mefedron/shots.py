"""«mefedron» chorus: the shots. Executed by lib/lyrics3d/scene.py with the whole engine in scope.

Frames at 30 fps; frame 0 = 13.95 s of the track. Four shots, cut on the first word of each line (edit.json "shots"):
  A  0    «Я люблю мефедрон, марки, ксан, оксикодон»   bust; the four things pop up in an arc over his head
  B  118  «Пидорасит слишком сильно, залипаю в потолок»  from the ceiling, pulling up and turning; he stares into the lens
  C  225  the first line again                           low flight over the floor past the four things
  D  335  the second line again                          the ceiling again, the other way round, harder

Head motion (the user's rules): smooth and sparse in the close shot; from above it is thrown sharply, with no
in-betweens, for as long as the camera is up there.
"""
# ---------------------------------------------------------------- props: the four things
THINGS = []          # dicts: pivot, mats (bsdf nodes for the glow)


def thing(name, build):
    piv = empty(f"thing_{name}")
    bs = build(piv)
    THINGS.append({"name": name, "pivot": piv, "bsdf": bs})


def _glow(m):
    return m.node_tree.nodes[m["bsdf"]]


def t_baggie(p):
    m = mtex("baggie", key=("baggie", "thing"))
    box("t_baggie", (0.105, 0.012, 0.13), (0, 0, 0), mflat("bag_edge", (180, 200, 226)), parent=p, face_mats={"-y": m, "+y": m})
    return [_glow(m)]


def t_blotter(p):
    m = mtex("blotter", key=("blotter", "thing"))
    box("t_blotter", (0.125, 0.006, 0.125), (0, 0, 0), WHITE, parent=p, face_mats={"-y": m, "+y": m})
    return [_glow(m)]


def t_xan(p):
    m = mtex("xanbar", key=("xanbar", "thing"))
    s = mflat("xan_side", (200, 206, 216))
    box("t_xan", (0.155, 0.026, 0.042), (0, 0, 0), s, rot=(0, 0.35, 0), parent=p, face_mats={"-y": m, "+y": m})
    return [_glow(m), s.node_tree.nodes[1]]


def t_oxy(p):
    m = mtex("oxy", alpha=True, key=("oxy", "thing"))
    s = mflat("oxy_side", (70, 116, 200))
    cyl("t_oxy", 0.056, 0.024, (0, 0, 0), s, rot=(math.pi / 2, 0, 0), seg=10, parent=p)
    cyl("t_oxy_f", 0.056, 0.0245, (0, 0, 0), s, rot=(math.pi / 2, 0, 0), seg=10, parent=p, cap_mat=m)
    return [_glow(m), s.node_tree.nodes[1]]


for nm, fn in (("baggie", t_baggie), ("blotter", t_blotter), ("xan", t_xan), ("oxy", t_oxy)):
    thing(nm, fn)
# where they lie on the floor (the fly-over path of line 3; also seen from the ceiling)
FLOOR_SPOTS = [(-0.98, -1.28, -1.25), (-0.50, -1.14, -1.55), (-0.04, -1.20, -1.2), (0.40, -1.02, -1.5)]


CUT_B, CUT_C, CUT_D = (s["from"] for s in EDIT["shots"][1:])     # 118, 225, 335
APPEAR_A = [34, 61, 73, 85]                      # shot A: the frame each thing pops up = the first frame of its word
PASS_C = [254, 280, 291, 302]                    # shot C: the frame the camera is over each thing
# shot A: one slow, smooth tilt per hook word (the long last word gets two). (frame of the extreme, side)
SWAY_A = [(26, 0.0), (41, 1.0), (66, -1.0), (79, 1.0), (92, -1.0), (109, 1.0), (126, 0.0)]
SWAY_AMP = 11.0
# shots B and D: syllable frames of "пидорасит слишком сильно, залипаю в потолок"
JERK_B = [118, 124, 130, 136, 143, 150, 157, 164, 171, 177, 183, 189, 195, 199, 206, 212, 218]
JERK_D = [335, 341, 347, 353, 360, 367, 374, 381]


def place_thing(i, loc, rot=(0, 0, 0), scale=1.0, glow=0.0, show=True):
    t = THINGS[i]
    t["pivot"].location, t["pivot"].rotation_euler = loc, rot
    t["pivot"].scale = (scale, scale, scale)
    for ch in t["pivot"].children:
        ch.hide_render = not show
    for b in t["bsdf"]:
        b.inputs["Emission Strength"].default_value = glow


def things_on_floor(glow=0.0):
    for i, (x, y, yaw) in enumerate(FLOOR_SPOTS):
        place_thing(i, (x, y, 0.03), (-math.pi / 2, 0, yaw), 0.85, glow)


def apply(f):
    """The hero, the camera, the things and the fill light for frame f. Returns the shot name."""
    if f < CUT_B:                                            # ---- A: bust, the things come up in an arc over his head
        shot = "A"
        set_pose(pose_sit(4, arms="lap"))
        hc0, _ = head_centre()
        HC_Z = hc0.z                                         # the arc hangs over where his head rests, it does not sway with it
        a = swing(f, SWAY_A) * SWAY_AMP
        turn("neck", a * 0.35, "Y")
        turn("head", a * 0.65, "Y")
        turn("chest", a * 0.12, "Y")
        hc = hc0
        push = ease(f / 117.0)
        cpos = Vector((0.02 + 0.012 * wob(f, 1), -0.84 + 0.10 * push + 0.008 * wob(f, 2), hc.z + 0.02 + 0.01 * wob(f, 3)))
        camera_at(cpos, (0.0 + 0.006 * wob(f, 4), hc.y, hc.z + 0.13 - 0.02 * push), roll=math.radians(1.2 * wob(f, 5, 0.6)), lens=22)
        for i, f0 in enumerate(APPEAR_A):
            ang = math.radians((146, 111, 69, 34)[i])
            pop = ease_out((f - f0 + 1) / 4.0)
            sc = (1.55 - 0.55 * pop) if f >= f0 else 0.0
            bob = 0.012 * math.sin((f + i * 9) / 7.0)
            loc = (math.cos(ang) * 0.30, hc.y - 0.02, HC_Z + 0.12 + math.sin(ang) * 0.30 + bob)
            place_thing(i, loc, (0, 0, math.radians(32) * math.sin((f + i * 13) / 9.0)), 1.05 * sc,
                        glow=0.5 + (2.5 if f - f0 < 2 else 0.0), show=f >= f0)
        L_FILL.location, L_FILL.data.energy = (0.0, -0.9, 1.3), 3
    elif f < CUT_C or f >= CUT_D:                            # ---- B / D: from the ceiling, pulling up and turning
        second = f >= CUT_D
        shot = "D" if second else "B"
        f0 = CUT_D if second else CUT_B
        n = (NFRAMES - CUT_D) if second else (CUT_C - CUT_B)
        t = (f - f0) / float(n)
        set_pose(pose_sit(30, arms="back"))
        things_on_floor()
        hc, _ = head_centre()
        hgt = 1.28 + (RZ - 0.12 - 1.28) * ease_out(t, 2.4 if second else 2.0)
        spin_a = math.radians((-14 + 46 * t) if not second else (20 - 62 * t))
        rise = ease_out(t, 2.4 if second else 2.0)
        cpos = Vector((0.03 * wob(f, 1), 0.34 - 0.24 * rise + 0.03 * wob(f, 2), hgt))
        tgt = Vector((0.0, 0.22 - 0.2 * rise, 0.2))
        up = Vector((math.sin(spin_a), math.cos(spin_a), 0))
        camera_at(cpos, tgt, up=up, lens=20 if second else 21)
        BULB.hide_render = WIRE.hide_render = True          # the camera hangs where the lamp is
        aim_head(cpos)
        # seen from above the head is thrown sharply, with no in-betweens, the whole time: on every syllable the first
        # time (snap, hold 3 frames, snap back), from side to side every 2 frames the second time
        throw_head(*jerk(f, JERK_D if second else JERK_B, 34 if second else 26, hold=2 if second else 3, wild=second))
        L_FILL.location, L_FILL.data.energy = (0.0, 0.2, 2.0), 5
    else:                                                    # ---- C: low over the floor, past the things
        shot = "C"
        set_pose(pose_sit(30, arms="back"))
        things_on_floor(glow=0.16)
        pts = [Vector((x, y, 0.0)) for x, y, _ in FLOOR_SPOTS]
        start = pts[0] + (pts[0] - pts[1]).normalized() * 0.38
        keys = [(CUT_C, start)] + list(zip(PASS_C, pts)) + [(CUT_D, pts[3] + Vector((0.12, 0.1, 0)))]
        for (fa, pa), (fb, pb_) in zip(keys, keys[1:]):
            if fa <= f <= fb:
                k = (f - fa) / float(fb - fa)
                k = ease_out(k, 2.6) if fa == CUT_C else (ease(k) ** 0.8 if fb != CUT_D else ease_out(k, 2))
                over = pa.lerp(pb_, k)
                break
        head_dir = (pts[3] - pts[0]).normalized()
        end = ease((f - 308) / 24.0)                         # the last beat: the camera lifts its look to him
        hgt = 0.33 + 0.035 * wob(f, 3) + 0.14 * end
        cpos = over - head_dir * 0.27 + Vector((0.01 * wob(f, 1), 0.01 * wob(f, 2), hgt))
        hc, _ = head_centre()
        tgt = (over + Vector((0, 0, 0.0))).lerp(hc + Vector((0, 0, -0.1)), end * 0.85)
        camera_at(cpos, tgt, roll=math.radians(7 * wob(f, 5, 0.7) + 5), lens=19)
        aim_head(Vector((0.4, -2.0, 1.4)).lerp(cpos, end))
        L_FILL.location, L_FILL.data.energy = (cpos.x, cpos.y - 0.2, 0.7), 2.5
    return shot
