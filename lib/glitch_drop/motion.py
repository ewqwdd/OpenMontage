"""Intro (pre-drop) motion: the reference's measured hand-made jitter, replayed as a texture.

The reference has no smooth sine sway. The text jerks in x, drifts slowly and irregularly in y,
wobbles +-0.5 deg, and the background only gets a hand-held jitter. All of it lives in
`assets/textures/<name>.json` as per-frame rows (px@480), indexed by frame since the edit start and
tiled with the texture `period`, so an intro of any length gets the same "dirty" motion.

Word-in: the frame before a new word and the onset frame are softened by a horizontal box on the
text mask (4 px@480 by default; a word may carry its own measured `in_box: [pre, onset]`).
"""
import json

import numpy as np
from PIL import Image

from .util import ASSETS, BH, BW, H, S, W

_TEX = {}


def texture(name="reference_intro"):
    if name not in _TEX:
        _TEX[name] = json.loads((ASSETS / "textures" / f"{name}.json").read_text())
    return _TEX[name]


class IntroMotion:
    def __init__(self, look):
        m = look["motion"]
        self.tex = texture(m["texture"])
        self.period = self.tex["period"]
        self.sway = m["sway"]           # scale of the text dx/dy
        self.rot = m["rotation"]        # scale of the rotation
        self.jitter = m["bg_jitter"]    # scale of the background hand-held jitter
        self.box = m["word_in_box"]
        self.box_max = m["word_in_max"]

    def _row(self, key, f):
        return self.tex[key][f % self.period]

    def text_offset(self, f):
        dx, dy, _ = self._row("text", f)
        return dx * S * self.sway, dy * S * self.sway

    def rotate(self, canvas, f, cx, cy):
        a = self._row("text", f)[2] * self.rot
        if abs(a) < 0.02:
            return canvas
        im = Image.fromarray(canvas.astype(np.float32), mode="F")
        return np.asarray(im.rotate(-a, resample=Image.BICUBIC, center=(cx, cy))).astype(np.float32)

    def crop_bg(self, fr, f, gain=1.0):
        jx, jy = self._row("bg_jitter", f)
        g = gain * self.jitter
        ox = float(np.clip((BW - W) / 2 - jx * S * g, 0, BW - W))
        oy = float(np.clip((BH - H) / 2 - jy * S * g, 0, BH - H))
        ox, oy = int(round(ox)), int(round(oy))
        return fr[oy:oy + H, ox:ox + W]

    def word_in(self, canvas, phase, box=None):
        """phase -1 = frame before a word, 0 = onset frame. box = per-word [pre, onset] px@480."""
        k = (box[0 if phase == -1 else 1] if box else self.box)
        k = min(k, self.box_max) * S
        return hbox(canvas, k)


def hbox(a, k):
    """horizontal box of width round(k), edge padded."""
    k = int(round(k))
    if k < 2:
        return a
    lo = k // 2
    hi = k - lo
    c = np.cumsum(np.pad(a, [(0, 0), (lo + 1, hi)] + [(0, 0)] * (a.ndim - 2), mode="edge"), axis=1)
    return (c[:, k:k + a.shape[1]] - c[:, :a.shape[1]]) / k
