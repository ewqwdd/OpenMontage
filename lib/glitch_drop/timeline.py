"""Timeline JSON -> resolved edit. All times are SECONDS; frames = round(t * fps).

{
  "fps": 30, "size": [1440, 1080],              # the kit renders 1440x1080 (4:3) only
  "duration": 23.3334,                          # video length (default audio.duration)
  "audio": {"path": "song.m4a", "start": 0.0, "duration": 23.292, "fade_out": 0.03},
  "drop": {"time": 16.5,                        # first frame of the glitch section
           "schedule": "reference",             # or a list, see glitch.build
           "bg": {"clip": "x.mp4", "offset": 0, "stretch": 1.37, "ay": 0.5,
                  "grade": {"pct": [10, 58, 228], "rgb": [55.7, 54.7, 60.4], "sat": 0.4, "tint": 1.0},
                  "shift_up": 55, "jitter": [9, 6], "soften": 2.6, "bloom": true},
           "tone": 0.85, "jpeg": 38},
  "lines": [                                    # one screen = one line growing word by word
    {"words": [[0.0, "я"], [0.8, "стою"], {"t": 1.43, "text": "на", "in_box": [3.5, 7.0]}],
     "clip": "street.mp4", "offset": 2.0, "stretch": 1.0, "ay": 0.5,   # intro lines only
     "xf": 12,                                  # background crossfade INTO this line, frames
     "grade": {"pct": [18, 51, 116], "rgb": [55.7, 53.8, 58.9], "sat": 0.55} | {"target": 50},
     "jitter": 1.0, "exposure": {"xp": [...], "fp": [...]},
     "start": 0.0},                             # default = first word; line ends at the next line
    {"words": [[16.5, "Я"], ...], "red": false} # lines starting at/after drop.time = drop lines (caps)
  ],
  "look": {...}                                 # see DEFAULT_LOOK, deep-merged
}
Paths are relative to the JSON file or absolute.
"""
import copy
import json
from pathlib import Path

DEFAULT_LOOK = {
    "text": {"weight": 430, "y": 233.0, "tear": True, "tear_scale": 1.32, "onset_dim": [0.87, 0.87], "style": {}},
    "motion": {"texture": "reference_intro", "sway": 1.0, "rotation": 1.0, "bg_jitter": 1.0,
               "word_in_box": 4.0, "word_in_max": 10.0},
    "flicker": {"mode": "measured", "strength": 1.0, "deflicker": True, "exposure": True, "pre_drop": True},
    "vignette": 0.28, "grain": 2.3, "soften": 2.2,
    "drop_text": {"weight": 560, "sx": 1.02, "sy": 1.45, "core": [196, 210, 232], "glow": [70, 80, 150],
                  "red_core": [205, 30, 62], "red_glow": [110, 10, 40], "red_scale": [1.22 * 1.05, 1.22 * 1.04]},
}
DEFAULT_DROP = {"schedule": "reference", "tone": 0.85, "jpeg": 38,
                "bg": {"offset": 0.0, "stretch": 1.0, "ay": 0.5, "shift_up": 55, "jitter": [9, 6], "soften": 2.6,
                       "bloom": True, "grade": {"pct": [10, 58, 228], "rgb": [55.7, 54.7, 60.4], "sat": 0.4, "tint": 1.0}}}


def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _path(base, p):
    p = Path(p).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def _word(w):
    if isinstance(w, dict):
        return dict(t=float(w["t"]), text=w["text"], in_box=w.get("in_box"))
    return dict(t=float(w[0]), text=w[1], in_box=w[2] if len(w) > 2 else None)


def load(path):
    path = Path(path)
    tl = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    fps = tl.setdefault("fps", 30)
    if tuple(tl.get("size", (1440, 1080))) != (1440, 1080):
        raise ValueError("glitch_drop renders 1440x1080 only (all measurements are 4:3 480p x 2.25)")
    fr = lambda t: int(round(float(t) * fps))
    au = tl["audio"]
    au["path"] = _path(base, au["path"])
    au.setdefault("start", 0.0)
    au.setdefault("fade_out", 0.03)
    tl["n"] = fr(tl.get("duration", au["duration"]))
    tl["look"] = merge(DEFAULT_LOOK, tl.get("look"))
    tl["drop"] = drop = merge(DEFAULT_DROP, tl["drop"])
    G = tl["G"] = fr(drop["time"])
    if "clip" not in drop["bg"]:
        raise ValueError("drop.bg.clip is required")
    drop["bg"]["clip"] = _path(base, drop["bg"]["clip"])

    lines = []
    for L in tl["lines"]:
        L = dict(L)
        L["words"] = [_word(w) for w in L["words"]]
        for w in L["words"]:
            w["f"] = fr(w["t"])
        L["s"] = fr(L["start"]) if "start" in L else L["words"][0]["f"]
        lines.append(L)
    lines.sort(key=lambda L: L["s"])
    intro = [L for L in lines if L["s"] < G]
    drops = [L for L in lines if L["s"] >= G]
    if not intro or not drops:
        raise ValueError("need at least one line before and one at/after drop.time")
    intro[0]["s"], drops[0]["s"] = 0, G
    for grp, end in ((intro, G), (drops, tl["n"])):
        for i, L in enumerate(grp):
            L["e"] = grp[i + 1]["s"] if i + 1 < len(grp) else end
            if L["e"] <= L["s"]:
                raise ValueError(f"empty line at {L['s']}: {L['words']}")
    for L in intro:
        if "clip" not in L:
            raise ValueError(f"intro line at frame {L['s']} needs a clip")
        L["clip"] = _path(base, L["clip"])
        L.setdefault("offset", 0.0)
        L.setdefault("stretch", 1.0)
        L.setdefault("ay", 0.5)
        L.setdefault("xf", 0)
        L.setdefault("jitter", 1.0)
        g = L.get("grade") or {"target": 50}
        if "target" in g:
            from .background import auto_grade
            g = dict(auto_grade(g["target"]), **{k: v for k, v in g.items() if k != "target"})
        g.setdefault("sat", 0.55)
        g.setdefault("tint", 0.7)
        L["grade"] = g
    tl["intro"], tl["drops"] = intro, drops
    tl["onsets"] = sorted({w["f"] for L in lines for w in L["words"]})
    return tl


def current_words(L, f):
    return " ".join(w["text"] for w in L["words"] if w["f"] <= f)
