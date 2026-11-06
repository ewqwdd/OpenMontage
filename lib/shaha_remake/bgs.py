"""Backgrounds: bg(i) -> float32 (H, W, 3) background for reference frame i (no text).

Reads spec/backgrounds.json when it exists ({"ref_frames":[a,b], "clip", "clip_t0", "speed", "crop":{"zoom","cx","cy"},
"hflip", "grade":{...}}). Until then returns a dark placeholder plate with the reference vignette, so the
segment builders can work on text and effects.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

import kit

HERE = Path(__file__).parent
SPEC = HERE / "spec" / "backgrounds.json"


@lru_cache(maxsize=1)
def _shots():
    if not SPEC.exists():
        return []
    return json.loads(SPEC.read_text())


_clips = {}


def _clip(k, s):
    if k not in _clips:
        c = s.get("crop") or {}
        a, b = s["ref_frames"]
        _clips[k] = kit.Clip(str(Path(s["clip"]).expanduser()), s.get("clip_t0", 0.0), (b - a + 2) / kit.FPS * s.get("speed", 1.0),
                             zoom=c.get("zoom", 1.0), cx=c.get("cx", 0.5), cy=c.get("cy", 0.5),
                             hflip=s.get("hflip", False), speed=s.get("speed", 1.0))
    return _clips[k]


_VIG = None


def placeholder(i):
    global _VIG
    if _VIG is None:
        _VIG = kit.vignette(strength=0.7)
    base = np.full((kit.H, kit.W, 3), 0.06, np.float32)
    base[..., 2] += 0.01
    return base * _VIG


_REFB = {}


def _bands(a):
    return a[:150].mean(), a[530:].mean()


QS = np.linspace(0, 100, 201)


def _bandpix(a):
    return np.concatenate([a[:150].ravel(), a[530:].ravel(), a[150:530, :90].ravel(), a[150:530, -90:].ravel()])


def _match_ref(img, i):
    """per-frame luma quantile mapping of the text-free border bands onto the reference (same exposure and
    contrast: the reference night is near black with small hard lights)."""
    if i not in _REFB:
        from PIL import Image
        p = HERE / "full" / f"{i + 1:04d}.png"
        if not p.exists():
            return img
        r = np.asarray(Image.open(p).convert("L"), np.float32) / 255
        _REFB[i] = np.percentile(_bandpix(r), QS)
    rq = _REFB[i]
    L = img.mean(-1)
    mq = np.percentile(_bandpix(L), QS)
    mq = np.maximum.accumulate(mq + np.arange(len(mq)) * 1e-6)
    L2 = np.interp(L, mq, rq)
    g = L2 / np.maximum(L, 1e-4)
    return np.clip(img * np.clip(g, 0, 4)[..., None], 0, 1)


_VIGS = {}


def _vig(st):
    if st not in _VIGS:
        _VIGS[st] = kit.vignette(strength=st)
    return _VIGS[st]


def bg(i):
    for k, s in enumerate(_shots()):
        a, b = s["ref_frames"]
        if a <= i <= b and s.get("clip"):
            img = _clip(k, s).frame(i - a)
            g = s.get("grade") or {}
            img = kit.blur(img, g.get("soft", 1.2)) * _vig(g.get("vignette", 0.7))
            img = np.clip(img, 0, 1) ** g.get("gamma", 1.0) * g.get("gain", 1.0) + np.asarray(g.get("off", [0, 0, 0]), np.float32)
            img = np.clip(img, 0, 1).astype(np.float32)
            if g.get("sat", 1.0) != 1.0:
                L = img.mean(-1, keepdims=True)
                img = np.clip(L + (img - L) * g["sat"], 0, 1)
            if g.get("ref_match", True):
                img = _match_ref(img, i)
            return img
    return placeholder(i)
