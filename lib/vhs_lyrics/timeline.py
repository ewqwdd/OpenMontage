"""Timeline JSON -> flat list of word clips.

All times are FRAMES (int). A scene owns its background and its items; an item without
"until" lives until the scene's end (words vanish on the cut).

Item kinds
  {"text": "НОЖ", "at": 706, "style": "grunge", "box": [21, 82, 46, 98], "color": "red",
   "shadow": "mid", "until": 717, "fx": "glitch|camo", "skew": -6, "amp": 4.5, "dil": 5,
   "track": 0.2}
  {"grow": [["И", 114], ["И БУДЕШЬ", 117], ["И БУДЕШЬ ПЛАКАТЬ", 129]], ...same keys...}
      a centred line growing word by word; box = the full (last) state, partial states keep
      its scale and stay centred on it.
box = [x0, x1, y0, y1] in % of the frame AS SEEN ON SCREEN (after the CRT lens).
"""
import json
import math
from pathlib import Path

ITEM_KEYS = ("style", "box", "color", "shadow", "fx", "skew", "amp", "dil", "track")


def load(path):
    tl = json.loads(Path(path).read_text(encoding="utf-8"))
    tl.setdefault("fps", 30)
    tl.setdefault("width", 1440)
    tl.setdefault("height", 1080)
    tl["frames"] = tl.get("frames") or tl["scenes"][-1]["end"]
    tl["base"] = Path(path).parent
    return tl


def sec(n, fps):
    """frame -> seconds, floored so a clip starts exactly on frame n"""
    return math.floor(n / fps * 1000) / 1000


def words(tl):
    fps, out = tl["fps"], []
    for sc in tl["scenes"]:
        for it in sc["items"]:
            base = {k: it[k] for k in ITEM_KEYS if k in it}
            base.setdefault("color", "white")
            end = it.get("until", sc["end"])
            if "grow" in it:
                states, full = it["grow"], it["grow"][-1][0]
                for k, (txt, at) in enumerate(states):
                    nxt = states[k + 1][1] if k + 1 < len(states) else end
                    out.append(dict(base, text=txt, f0=at, f1=nxt, yref=full))
            else:
                out.append(dict(base, text=it["text"], f0=it["at"], f1=end, yref=None))
    for e in out:
        e["t0"], e["t1"] = sec(e["f0"], fps), sec(e["f1"], fps)
    return out


def cuts(tl):
    return [sc["start"] for sc in tl["scenes"][1:]]
