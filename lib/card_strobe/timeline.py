"""Timeline JSON -> resolved edit.

ALL EVENT TIMES ARE INTEGER FRAMES at `fps` (frame 0 = audio.start). The style is frame-exact: a
polarity flip lasts 2-3 frames, a flash 1 frame, so the planner converts seconds/beats to frames
once and the renderer never rounds again. Points are pixels: `at` / subtitle positions are in
SQUARE coordinates (0..square); camera points (`about`, `center`, `track`) are in CANVAS coordinates
(the precut clip: square + 2 * margin, 1210 for 1080).

{
  "about": "free text",
  "fps": 30, "size": [1080, 1920],
  "square": {"size": 1080, "y": 420, "margin": 65},     # picture square in the 9:16 frame, canvas margin
  "frames": 364,                                         # default round(audio.duration * fps)
  "audio": {"path": "song.m4a", "start": 47.265, "duration": 12.133, "fade_out": 0.03, "fade_in": 0.01},
  "fonts": {"card": "/path/font.ttf"},                   # optional role overrides, see fonts.py
  "palettes": {"teal": [[[0, [0, 0, 0]], [1, [80, 255, 230]]], 1.0]},   # extra duotones (grade.PALETTES)
  "clips": {"C": {"src": "video.mp4", "t0": 91.95, "dur": 1.5, "ax": 0.42, "ay": 0.5,   # precut windows
                 "fps": 60}},                            # optional: precut at the source rate (slow speeds
                                                         # then show new frames instead of duplicates)

  "shots": [                                             # cover 0..frames-1, in order, f = [first, last]
    {"kind": "flat", "f": [26, 26], "value": 254},       # white / flash 242 / black 0; bars follow the value;
                                                         # "subs": true draws subtitles on it (default for dark)
    {"kind": "card", "f": [27, 42], "font": "card", "fg": 254, "bg": 0,
     "swap": [27, 28, 32, 33],                           # frames with swapped polarity (white card, black type)
     "states": [{"from": 27, "lines": [{"text": "MASTER", "fit": [1040, 823], "at": [543, 541.5]}]},
                {"from": 167, "align": "left",           # lines after the first share its left edge
                 "lines": [{"text": "ZAE-", "cap": 431, "at": [589, 247.5]}, {"text": "BAL", "cap": 431, "at": [0, 772]}]}],
     "fg_frames": {"460": [50, 225, 193]},               # optional: recolour the type on single frames
     "show": [338, 339],                                 # optional: only these frames are the card ...
     "under": {"clip": "N", "t": 115.25, "grade": "redmono", "camera": {}}},   # ... the others this clip
    {"kind": "clip", "f": [45, 86], "clip": "C",
     "t": 91.95, "from": 45,                             # source time at frame `from` (default f[0])
     "conform": 20,                                      # stutter: 20 fps inside 30 (null = full rate)
     "speed": 1.0, "pingpong": [5, 2],                   # optional time maps (span, hold)
     "grade": "orange", "gain": 0.82, "gain_frames": {"17": 0.3}, "levels": [p5, p95],
     "levels_roi": [x0, y0, x1, y1], "levels_pct": [5, 95],   # measure the grade on a face box (canvas px)
     "camera": {"zoom": 1.3 | "zoom_steps": [[45, 1.3], [50, 1.7]] | "push": {"to": 1.5, "frames": 44}
                | "drift": 0.0018 | "pulse": {"hits": [87, 92], "base": 0.97, "amp": 0.11, "tau": 4, "wobble": [0.02, 22.5]},
                "punch": {"frames": [204, 205], "k": 1.04}, "crash": 0.11, "min_zoom": [132, 1.0],
                "about": [560, 470] | "center": [430, 480]
                | "track": {"keys": [[0, 640, 880], [10, 625, 870]], "keep_inside": false},  # keys: precut frame n
                "kick": {"frames": [93, 117], "amp": 0.10, "tau": 4},   # 808 zoom kick, on top of any mode
                "flip": false},
     "fx": {"sharpen": [4, 140, 2], "entry": {"frames": 4}, "hue_cycle": {"f": [75, 83], "deg": -40},
            "wash": {"first": 92, "rest": 82, "gamma": 0.55}, "keep_colour": {"rgb": [70, 235, 95]},
            "pulses": {"frames": [188, 197], "amp": 70}, "strobe": {"f": [247, 271], "peaks": [[248, 244]], "soft": [],
                                                                     "curve": {"mode": "soft"}},   # grade.SOFT_STROBE
            "scratches": {"seed": 1000}}}
  ],
  "text": [                                              # drawn in order on footage frames (canvas)
    {"kind": "word", "f": [50, 86], "text": "EU", "font": "pop", "cap": 65 | "size": 128 | "fit": [w, h],
     "at": [390, 680], "dim_at": 61, "dim": 0.35, "rot": 0, "shadow": false | true | [blur, k, dx, dy],
     "outline": 0, "color": [255, 255, 255], "only": [frames],
     "scale": [1.0, 0.75, 0.6], "dx": [640, 80, 0], "dy": [60, 30, 0],     # per frame from f[0], last held
     "opacity": 1.0 | [0.6, 0.6, 0.35, 0.15],                               # constant or per frame
     "alt": {"frames": [114, 115], "text": "$", "cap": 170, "shadow": true}},   # swap look on these frames
    {"kind": "typing", "f": [0, 25], "font": "blocky", "at": [540, 540], "steps": [[0, "ЯП", 124], [4, "ЯПОН", 124]]},
    {"kind": "clones", "f": [75, 86], "text": "HA", "cap": 95, "positions": [[540, 270]], "every": 1,   # 1.5 ok
     "faint": {"every": 3, "opacity": 0.55}, "dim_at": 79},
    {"kind": "stack", "f": [81, 87], "text": "PAYPAL", "cap": 125, "at": [540, 540], "rows": [2, 3, 5, 8], "pitch": 156}
  ],
  "subtitles": [{"f": [182, 228], "style": "band" | "plain" | "diff" | "cursor",
                 "words": [[183, "бро"], [191, "так"]], "halo_from": 313, "slide_in": 6}],
  "motion": [{"f": [182, 228], "dx": [[182, 0], [194, -48]] | {"132": 4, "133": 16}, "dy": [...],
              "ease": "cosine" | "linear"}],                 # composite (footage + text) offsets, px
  "events": {"inverts": [58, 81], "bar_flash": [25], "mosaic": {"frames": [3, 4], "block": 36},
             "invert_modes": {"222": "hue"}},           # rgb (default) | hue | duotone, see grade.invert
  "look": {...},                                         # DEFAULT_LOOK, deep-merged
  "fused": {...},                                        # optional: the fused style (fused.py docstring)
  "render": {"edges": [0, 112, 224, 494]}                # optional chunk edges for the parallel encode
}
Paths are relative to the JSON file or absolute (~ allowed).
"""
import copy
import json
from pathlib import Path

from . import grade

DEFAULT_LOOK = {
    "white": 254,                    # card / flash white (not 255: ref3 measures 254)
    "dim": 0.35,                     # past pop words (ref3 #15)
    "band": {"y": [522, 562], "k": 0.35},          # the translucent subtitle bar, square y
    "sub": {"size": 41, "max_w": 660, "x": 540, "y": 540, "band_y": 543, "rot": -3},
    "word_shadow": [10, 0.55, 5, 7],
    "blur_threshold": 8,             # composite moves more than this (px/frame) -> motion blur
    "blur_samples": 8,
}
KINDS = ("clip", "flat", "card")
INVERT_MODES = ("rgb", "hue", "duotone")


def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _path(base, p):
    p = Path(p).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def _check_clip_shot(s, clips, palettes, where):
    if s.get("clip") not in clips:
        raise ValueError(f"{where}: unknown clip {s.get('clip')!r}")
    if s.get("grade") not in palettes:
        raise ValueError(f"{where}: unknown grade {s.get('grade')!r} (have {', '.join(sorted(palettes))})")
    if "t" not in s:
        raise ValueError(f"{where}: clip shot needs a source time 't'")


def _lint_clip_shot(s, clips, fps, where, warn):
    """things that render but look wrong: duplicated frames from slow speeds, black edges"""
    c = clips[s["clip"]]
    sp = float(s.get("speed", 1))
    cf = c.get("fps") or fps
    if sp < 1 and not s.get("conform") and cf * sp < fps - 0.01:
        warn.append(f"{where}: speed {sp} on a {cf:g} fps precut repeats frames (set clips.{s['clip']}.fps "
                    f"to the source rate, e.g. 60, or use speed >= {fps / cf:g})")
    cam = s.get("camera") or {}
    z = cam.get("zoom", 1.0)
    if z < 1 and (cam.get("about") or cam.get("center")):
        warn.append(f"{where}: zoom {z} < 1 with an off-centre about/center can show black edges")


def load(path):
    path = Path(path)
    return resolve(json.loads(path.read_text(encoding="utf-8")), path.parent)


def dumps(tl):
    """readable JSON: one shot / layer / clip per line"""
    def one(v):
        return json.dumps(v, ensure_ascii=False)
    out = []
    for k, v in tl.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            body = ",\n".join("  " + one(x) for x in v)
            out.append(f' {one(k)}: [\n{body}\n ]')
        elif isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()):
            body = ",\n".join(f"  {one(n)}: {one(x)}" for n, x in v.items())
            out.append(f' {one(k)}: {{\n{body}\n }}')
        else:
            out.append(f" {one(k)}: {one(v)}")
    return "{\n" + ",\n".join(out) + "\n}\n"


def resolve(tl, base=Path(".")):
    tl = copy.deepcopy(tl)
    fps = tl.setdefault("fps", 30)
    tl["size"] = list(tl.get("size", [1080, 1920]))
    sq = tl["square"] = merge({"size": 1080, "y": (tl["size"][1] - tl["size"][0]) // 2, "margin": 65},
                              tl.get("square"))
    if sq["size"] != tl["size"][0]:
        raise ValueError("square.size must equal the frame width")
    au = tl["audio"]
    au["path"] = str(_path(base, au["path"]))
    au.setdefault("start", 0.0)
    au.setdefault("fade_out", 0.03)
    n = tl.setdefault("frames", int(round(float(au["duration"]) * fps)))
    au.setdefault("duration", n / fps)
    tl["look"] = merge(DEFAULT_LOOK, tl.get("look"))

    pal = dict(grade.PALETTES)
    for k, (stops, gamma) in (tl.get("palettes") or {}).items():
        pal[k] = (tuple((float(p), tuple(int(c) for c in rgb)) for p, rgb in stops), float(gamma))
    tl["_palettes"] = pal

    clips = tl.setdefault("clips", {})
    for c in clips.values():
        c["src"] = str(_path(base, c["src"]))
        c.setdefault("ax", 0.5)
        c.setdefault("ay", 0.5)
    warn = tl["_warnings"] = []

    shots = sorted(tl["shots"], key=lambda s: s["f"][0])
    want = 0
    for s in shots:
        a, b = s["f"]
        where = f"shot {s.get('kind')} f{a}-{b}"
        if s.get("kind") not in KINDS:
            raise ValueError(f"{where}: kind must be one of {KINDS}")
        if a != want or b < a:
            raise ValueError(f"{where}: shots must cover every frame once, in order (expected start {want})")
        want = b + 1
        if s["kind"] == "clip":
            _check_clip_shot(s, clips, pal, where)
            _lint_clip_shot(s, clips, fps, where, warn)
        if s["kind"] == "card":
            if not s.get("states"):
                raise ValueError(f"{where}: card needs states")
            if "under" in s:
                _check_clip_shot(s["under"], clips, pal, where + " under")
                _lint_clip_shot(s["under"], clips, fps, where + " under", warn)
            if "show" in s:                 # frame_spec() works on a freshly loaded timeline
                s["_show"] = set(s["show"])
                s["_under"] = dict(s["under"], f=s["f"])
        if s["kind"] == "flat":
            s.setdefault("value", 0)
    if want != n:
        raise ValueError(f"shots cover frames 0..{want - 1}, timeline has {n}")
    tl["shots"] = shots
    tl["_starts"] = [s["f"][0] for s in shots]
    tl.setdefault("text", [])
    tl.setdefault("subtitles", [])
    tl.setdefault("motion", [])
    ev = tl.setdefault("events", {})
    ev["inverts"] = set(int(x) for x in ev.get("inverts", []))
    ev["bar_flash"] = set(int(x) for x in ev.get("bar_flash", []))
    ev.setdefault("mosaic", {"frames": [], "block": 36})
    ev["mosaic"]["frames"] = set(int(x) for x in ev["mosaic"].get("frames", []))
    ev["invert_modes"] = {int(k): v for k, v in (ev.get("invert_modes") or {}).items()}
    for k, v in ev["invert_modes"].items():
        if v not in INVERT_MODES:
            raise ValueError(f"events.invert_modes[{k}]: {v!r} is not one of {INVERT_MODES}")
    if tl.get("fused"):
        from .fused import resolve_fused
        resolve_fused(tl)
    return tl
