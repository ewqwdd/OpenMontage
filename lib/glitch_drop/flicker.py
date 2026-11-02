"""Intro screen flicker: a global, multiplicative, luma-only brightness flicker over everything
(footage + text), applied after the vignette and before the grain. It does not run in the drop.

    log g(f) = sum_k c_k cos(w_k f) + s_k sin(w_k f)      (model: 3.18 Hz +-7.3 %, 7.38 Hz +-4.5 %)

Modes:
- `measured`: the reference's own per-frame gain. This is the texture `flicker_log_gain`, tiled.
- `model`: the clean two-sine fit.
- `off`.

The other parts:
- `deflicker` cancels the flicker already baked into the user's footage. A prepass estimates each
  shot's own high-frequency gain, and that gain is divided out.
- `exposure` applies an optional per-line luma LUT (line["exposure"] = {xp, fp}).
- `pre_drop` is the measured lift/wash toward grey on the 2 frames right before the drop.
"""
import math

import numpy as np

from .util import LUMA, luma_lut


class Flicker:
    def __init__(self, look, tex, fps, drop_frame, line_ranges, line_exposure):
        c = look["flicker"]
        self.mode, self.strength = c["mode"], c["strength"]
        self.deflicker, self.exposure, self.events = c["deflicker"], c["exposure"], c["pre_drop"]
        self.tex, self.fps, self.drop = tex, fps, drop_frame
        self.lines, self.line_exposure = line_ranges, line_exposure
        self.own_gain = None

    def log_gain(self, f):
        if not (0 <= f < self.drop) or self.mode == "off":
            return 0.0
        if self.mode == "measured":
            g = self.tex["flicker_log_gain"]
            return float(g[f % len(g)])
        lg = 0.0
        for fq, c, s in self.tex["flicker_model"]:
            w = 2 * math.pi * fq / self.fps
            lg += c * math.cos(w * f) + s * math.sin(w * f)
        return lg

    def apply(self, img, f):
        x = img.astype(np.float32, copy=False)
        if f >= self.drop:
            return np.clip(x, 0, 255)
        if self.exposure:
            li = next((i for i, (s, e) in enumerate(self.lines) if s <= f < e), None)
            e = self.line_exposure[li] if li is not None else None
            if e:
                x = luma_lut(x, e["xp"], e["fp"])
        g = 1.0
        if self.deflicker and self.own_gain is not None:
            og = self.own_gain[f]
            if og and np.isfinite(og):
                g /= float(np.clip(og, 0.6, 1.6))
        if self.mode != "off":
            g *= math.exp(self.log_gain(f) * self.strength)
        if g != 1.0:
            x = x * np.float32(g)
        if self.events:
            ev = self.tex["pre_drop"].get(str(f - self.drop))
            if ev:
                x = luma_lut(x, ev["xp"], ev["fp"])
        return np.clip(x, 0, 255)


# ---------------------------------------------------------------- own-flicker estimate (prepass)
def _gsmooth_loo(X, sig=1.5):
    n = len(X)
    k = int(3 * sig)
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sig) ** 2)
    out = np.zeros_like(X)
    for i in range(n):
        a, b = max(0, i - k), min(n, i + k + 1)
        ww = w[a - i + k:b - i + k].copy()
        ww[i - a] = 0.0
        out[i] = (ww[:, None] * X[a:b]).sum(0) / ww.sum()
    return out


def fit_gain(X, iters=5):
    """X: (n, P) luma samples of one continuous shot -> per-frame gain (mean 1)."""
    n = len(X)
    a = np.ones(n)
    if n < 4:
        return a
    for _ in range(iters):
        Sm = _gsmooth_loo(X / a[:, None])
        a = (Sm * X).sum(1) / np.maximum((Sm * Sm).sum(1), 1e-9)
        a = a / a.mean()
    return a


def bg_mask(h, w, text_band=(170 / 480, 300 / 480)):
    m = np.ones((h, w), bool)
    m[int(text_band[0] * h):int(text_band[1] * h)] = False
    m[:int(0.15 * h), :int(0.17 * w)] = False
    m[int(0.8 * h):, int(0.8 * w):] = False
    return m


def thumb_luma(img, th=60, tw=80):
    with np.errstate(all="ignore"):
        l = np.asarray(img, np.float32) @ LUMA
    h, w = l.shape
    l = l[:h - h % th, :w - w % tw]
    return l.reshape(th, l.shape[0] // th, tw, l.shape[1] // tw).mean((1, 3))


def own_gain(thumbs, segments):
    """thumbs (n,60,80) background luma thumbnails; segments [(s,e)] continuous shots."""
    m = bg_mask(60, 80)
    X = np.asarray(thumbs, np.float64)[:, m]
    g = np.ones(len(X))
    with np.errstate(all="ignore"):
        for s, e in segments:
            if e - s < 4 or not np.any(X[s:e]):
                continue
            g[s:e] = np.nan_to_num(fit_gain(X[s:e]), nan=1.0)
            if e - s > 6:
                for j in (s, s + 1, e - 2, e - 1):
                    g[j] = g[j] ** 0.5
    return g
