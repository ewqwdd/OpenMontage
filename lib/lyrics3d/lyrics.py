"""Glitch text for the 3D lyric edit (approved on «mefedron», 2026-11-17), after the grammar of the glitch-drop lyrics kit (lib/glitch_drop/text.py):
CAPS in Cormorant Garamond, one centred line that grows word by word, lavender glow, split chroma, a scanline tear
that runs on its own clock, the line dims on a word onset; on glitch frames the line jumps every frame, smears,
leaves a ghost and is cut into slices. One accent word is crimson (the kit's "red word").

Drawn in the 360x640 render grid, so the letters get the same x3 pixels and dither as the picture.

The line is torn less than the head (level x 0.62, every third frame nearly clean): it has to be read.
Two other looks were tried and turned down by the user on 2026-11-17: a white bitmap font (Fixedsys) and yellow
Oswald Bold with a black outline. Do not offer them again unless asked.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, uniform_filter1d

REPO = Path(__file__).resolve().parents[2]
FONT = str(REPO / "lib/glitch_drop/assets/fonts/CormorantGaramond.ttf")
W, H = 360, 640
SS = 4                                             # the mask is drawn 4x bigger and box-filtered down

CORE, GLOW = np.array((228, 234, 252)) / 255.0, np.array((70, 86, 170)) / 255.0
RED_CORE, RED_GLOW = np.array((225, 34, 70)) / 255.0, np.array((150, 14, 50)) / 255.0


def hsh(i, salt=0):
    x = np.sin(i * 127.1 + salt * 311.7) * 43758.5453
    return float(x - np.floor(x))


def _tear_profile():
    rng = np.random.default_rng(2446)
    d = np.zeros(H, np.float32)
    y = 0
    while y < H:
        n = int(rng.integers(1, 4))
        d[y:y + n] = float(np.clip(rng.normal(0, 1.5), -3.2, 3.2))
        y += n
    return d


TEAR = _tear_profile()


class Lyrics:
    def __init__(self, project, edit):
        """edit: the project's edit.json. "screens": [first word, last word, accent] by word index inside the edit;
        each screen is one line that grows word by word and stays until the next screen's first word."""
        data = json.loads((Path(project) / edit.get("words", "words.json")).read_text(encoding="utf-8"))
        name, fps = edit["edit"], edit.get("fps", 30)
        t0 = data["edits"][name]["start"]
        ws = [w for w in data["words"] if w.get("edit", name) == name]
        self.screens = [tuple(x) for x in edit["screens"]]
        self.words = [w["text"].upper() for w in ws]
        self.on = [int(round((w["start"] - t0) * fps)) for w in ws]
        self.onsets = set(self.on)
        self._cache = {}
        self.prev = None                                # previous position, for the ghost

    def _font(self, size):
        f = ImageFont.truetype(FONT, size)
        try:
            f.set_variation_by_axes([700])
        except Exception:
            pass
        return f

    def _size(self, si):
        """One font size per screen, from its full line, so that the line does not resize while it grows."""
        a, b, red = self.screens[si]
        full = " ".join(self.words[a:b + 1]).rstrip(",")
        cap = 30.0 if a == b else 23.0                  # cap height in render pixels
        if red:
            cap *= 1.2
        f0 = self._font(400)
        bb = f0.getbbox("Н")
        size = 400 * cap * SS / (bb[3] - bb[1])
        wid = self._font(int(size)).getlength(full)
        if wid > 326 * SS:
            size *= 326 * SS / wid
        return int(size)

    def mask(self, si, k):
        key = (si, k)
        if key not in self._cache:
            a, b, red = self.screens[si]
            txt = " ".join(self.words[a:k + 1]).rstrip(",")
            f = self._font(self._size(si))
            pad = 8 * SS
            bb = f.getbbox(txt)
            im = Image.new("L", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
            ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=255)
            im = im.resize((max(1, im.width // SS), max(1, im.height // SS)), Image.BOX)
            self._cache[key] = np.asarray(im, np.float32) / 255.0
        return self._cache[key]

    def state(self, f):
        si = k = None
        for i, (a, b, _) in enumerate(self.screens):
            if f >= self.on[a]:
                si = i
        if si is None:
            return None
        a, b, red = self.screens[si]
        k = max(j for j in range(a, b + 1) if f >= self.on[j])
        return si, k, red

    def draw(self, img, f, lvl, shot, text_y):
        """shot: the shot's name (the ghost does not cross a cut); text_y: the line's height, 0 top .. 1 bottom."""
        st = self.state(f)
        if st is None:
            return img
        si, k, red = st
        m = self.mask(si, k)
        cy = text_y * H
        rng = np.random.default_rng(7000 + f)
        lvl = lvl * 0.62                                 # the line is torn less than the head: it has to be read
        if f % 3 == 0:
            lvl = min(lvl, 0.25)                         # and every third frame is clean
        hot = lvl > 0.3                                  # a glitch frame: the kit's drop behaviour
        jx = rng.normal(0, 1.0 + 5.5 * lvl) if hot else np.sin(f / 9.0) * 1.2
        jy = rng.normal(0, 0.6 + 3.0 * lvl) if hot else np.sin(f / 15.0) * 0.8
        cx = W / 2 + jx
        cy = cy + jy
        can = self._place(m, cx, cy)
        if self.prev is not None and self.prev[2] != shot:
            self.prev = None                             # no ghost across a cut
        if hot and self.prev is not None:                # ghost of where the line was a frame ago
            g = uniform_filter1d(self._place(m, *self.prev[:2]), 5, axis=1)
            can = np.maximum(can, g * 0.45)
        self.prev = (cx, cy, shot)
        if hot and rng.random() < 0.55:                  # motion smear, mostly sideways; the word stays readable under it
            ln = int(3 + 11 * lvl)
            ax = 1 if rng.random() < 0.75 else 0
            can = uniform_filter1d(can, ln, axis=ax) * 0.5 + can * 0.6
        if lvl > 0.55:                                   # slices of the line thrown left and right
            y = int(cy - 22)
            while y < cy + 22:
                hh = int(rng.integers(2, 7))
                if 0 <= y < H:
                    can[y:y + hh] = np.roll(can[y:y + hh], int(rng.integers(-18, 19) * lvl), axis=1)
                y += hh
        # the scanline tear: one fixed profile, a free-running amplitude (never on the beat)
        amp = (hsh(f, 32) * 2 - 1) * 1.8 if hsh(f // 2, 31) < 0.28 else 0.35 * np.sin(f / 7.0)
        sh = np.rint(TEAR * amp).astype(int)
        rows = np.nonzero(can.max(1) > 0.01)[0]
        for y in rows:
            if sh[y]:
                can[y] = np.roll(can[y], sh[y])
        # onset dim: darker on the frame before a new word and on the word itself
        op = 0.55 if (f + 1) in self.onsets else 0.8 if f in self.onsets else 1.0
        can = np.clip(can, 0, 1) * op
        core, glow = (RED_CORE, RED_GLOW) if red else (CORE, GLOW)
        out = img * (1 - 0.5 * np.clip(gaussian_filter(can, 7) * 2.2, 0, 1))[..., None]      # a dark bed under the line
        out = out + (gaussian_filter(can, 2.0) * 1.1 + gaussian_filter(can, 6.0) * 1.3)[..., None] * glow
        k_ = 1 + (1 if lvl > 0.5 else 0)                 # split chroma: red to the right, blue to the left
        r, b = np.roll(can, k_, 1), np.roll(can, -k_, 1)
        a = np.stack([np.maximum(can * 0.75, r), can, np.maximum(can * 0.75, b)], -1)
        out = out * (1 - a * 0.92) + a * core
        return np.clip(out, 0, 1.2)

    @staticmethod
    def _place(m, cx, cy):
        can = np.zeros((H, W), np.float32)
        h, w = m.shape
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        if xb > xa and yb > ya:
            can[ya:yb, xa:xb] = m[ya - y0:yb - y0, xa - x0:xb - x0]
        return can
