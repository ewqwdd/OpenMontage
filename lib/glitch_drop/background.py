"""Background footage: loading, grading, softening, and the drop's regrade.

Grading maps the clip's own luma p5/p50/p95 to a target triple `pct` and tints it toward the mean
colour `rgb`. Both were measured on the reference for every shot. Without measurements, `target`
(the median luma) derives a dark, cool night grade from the reference's average shot.
"""
import subprocess

import numpy as np
from PIL import Image, ImageFilter

from .util import BH, BW, H, S, W, Y, hblur, lum, resample_soft


def load_clip(path, off, n, fps, stretch=1.0, ay=0.5):
    """n frames (BW x BH, cover-cropped) from `path` starting at `off` s; the last frame is held if short."""
    vf = (f"setpts=PTS*{stretch},fps={fps},scale={BW}:{BH}:force_original_aspect_ratio=increase:flags=bicubic,"
          f"crop={BW}:{BH}:(iw-{BW})/2:(ih-{BH})*{ay}")
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{off:.3f}", "-i", str(path), "-vf", vf, "-frames:v", str(n),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, BH, BW, 3)
    if len(fr) < n:
        fr = np.concatenate([fr, np.repeat(fr[-1:], n - len(fr), 0)])
    return fr


def auto_grade(target):
    """pct/rgb for a median-luma target (scaled from the reference's average intro shot)."""
    return dict(pct=(round(0.3 * target, 1), target, round(min(235.0, 2.1 * target), 1)),
                rgb=(target * 1.03, target * 0.97, target * 1.06))


def make_grader(frames, pct, rgb, sat=0.55, tint_amt=0.7):
    small = frames[::4, ::8, ::8].astype(np.float32)
    s5, s50, s95 = np.percentile(lum(small), [5, 50, 95])
    t5, t50, t95 = pct
    lut = np.interp(np.arange(256), [0, s5, s50, s95, 255], [0, t5, t50, t95, min(255, t95 + 70)]).astype(np.float32)
    m = np.mean(rgb)
    tint = np.array([(c / m) ** tint_amt for c in rgb], np.float32)

    def grade(img):
        x = img.astype(np.float32)
        l = lum(x)
        ln = lut[np.clip(l, 0, 255).astype(np.uint8)]
        g = ln[..., None]
        x = x * ((ln + 1) / (l + 1))[..., None]
        x = g + (x - g) * sat
        return np.clip(x * tint, 0, 255)
    return grade


def soften(x, r=2.2):
    """480p round trip + gaussian: the reference's soft capture."""
    im = Image.fromarray(x.astype(np.uint8))
    im = im.resize((640, 480), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r * 0.45))
    return np.asarray(im.resize((W, H), Image.BICUBIC)).astype(np.float32)


def bloom(img):
    hi = np.clip(img - 175, 0, 255)
    im = Image.fromarray(hi.astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    return np.clip(img + np.asarray(im).astype(np.float32) * 1.4, 0, 255)


def vignette(strength=0.28):
    yy, xx = np.mgrid[0:H, 0:W]
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    return np.clip(1 - strength * d, 0.55, 1)[..., None].astype(np.float32)


# ---------------------------------------------------------------- drop regrade
# Reference drop frames: bright top (ceiling + lamp), near-black bottom. Each row gets a gain and a
# lift, profile rows in px@480.
ROW_PROFILE = dict(y=[0, 72, 150, 210, 255, 300, 345, 480],
                   gain=[1.15, 1.12, 1.0, 0.8, 0.55, 0.26, 0.13, 0.12],
                   add=[62, 55, 35, 8, 0, 0, 0, 0])


def _aniso_blur(m, sx, sy):
    k = max(1.0, sx / max(sy, 1e-3))
    sm = Image.fromarray(np.clip(m * 255, 0, 255).astype(np.uint8)).resize((max(8, int(W / (4 * k))), H // 4), Image.BILINEAR)
    sm = sm.filter(ImageFilter.GaussianBlur(sy / 4))
    return np.asarray(sm.resize((W, H), Image.BICUBIC)).astype(np.float32) / 255


class DropRegrade:
    def __init__(self, shift_up=55, profile=None):
        p = profile or ROW_PROFILE
        gy = np.array(p["y"], np.float32) * S
        self.rowg = np.interp(np.arange(H), gy, np.array(p["gain"], np.float32)).astype(np.float32)[:, None, None]
        self.rowa = np.interp(np.arange(H), gy, np.array(p["add"], np.float32)).astype(np.float32)[:, None, None]
        self.shift = Y(shift_up)

    def __call__(self, bg):
        sh = self.shift
        x = np.concatenate([bg[sh:], np.repeat(bg[-1:], sh, 0)], 0) if sh else bg
        x = resample_soft(x, 4)
        x = x * 0.5 + hblur(x, 12 * S) * 0.5
        x = np.where(x > 135, 135 + (x - 135) * 0.32, x)
        x = x * self.rowg + self.rowa
        hi = np.clip((lum(x) - 120) / 90, 0, 1) ** 1.5
        g = _aniso_blur(hi, 70 * S, 8 * S) * 1.6 + _aniso_blur(hi, 14 * S, 14 * S) * 0.35
        x = x + np.clip(g, 0, 1.4)[..., None] * np.array([120, 118, 140], np.float32)
        return np.clip(x, 0, 255)
