"""Colour: per-shot duotones and the pixel effects that live inside a shot.

A duotone throws the source colour away. Luma is normalised by the shot's own p5/p95 (constant over
the shot, so there is no flicker), raised to `gamma` and mapped through a gradient of colour stops.
p5 lands on stop 0, so blacks are crushed; that is the style (ref3 §6: crushed blacks, saturation
either ~0 or near max, neighbouring shots never share a hue).
"""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter

# name: (stops ((pos 0..1, (r, g, b)), ...), gamma). Measured medians in ref3.md §6 are in the comments.
PALETTES = {
    "mauve": (((0, (0, 0, 0)), (0.5, (3, 1, 2)), (0.8, (22, 15, 18)), (1, (70, 52, 60))), 1.9),       # intro, luma ~7
    "amber": (((0, (0, 0, 0)), (0.35, (40, 24, 20)), (0.6, (96, 64, 52)), (0.85, (205, 148, 112)),
               (1, (252, 222, 190))), 1.0),                                                          # lights on (62,44,40)
    "orange": (((0, (0, 0, 0)), (0.2, (45, 14, 6)), (0.5, (140, 72, 50)), (0.8, (222, 150, 108)),
                (1, (236, 214, 196))), 2.4),                                                         # (112,70,64)
    "violet": (((0, (0, 0, 0)), (0.4, (14, 0, 30)), (0.72, (105, 30, 150)), (1, (215, 168, 222))), 1.25),  # (10,0,21)
    "khaki": (((0, (46, 45, 22)), (0.5, (150, 148, 98)), (1, (236, 234, 198))), 1.0),                 # washed (165,164,110)
    "red": (((0, (0, 0, 0)), (0.45, (100, 0, 12)), (0.8, (215, 6, 28)), (1, (255, 60, 72))), 1.0),     # home colour (91,0,12)
    "bw": (((0, (0, 0, 0)), (0.5, (58, 60, 62)), (1, (252, 252, 252))), 1.25),                        # hard B&W
    "magenta": (((0, (0, 0, 0)), (0.5, (50, 0, 80)), (0.85, (120, 0, 190)), (1, (190, 40, 255))), 1.0),  # (48,0,75)
    "lilac": (((0, (16, 6, 40)), (0.45, (150, 112, 200)), (0.75, (190, 160, 235)), (1, (250, 242, 255))), 0.75),  # (174,135,220)
    "redmono": (((0, (0, 0, 0)), (0.45, (112, 0, 15)), (0.8, (220, 20, 40)), (1, (255, 120, 120))), 1.0),  # (112,0,15)
    "khakih": (((0, (0, 0, 0)), (0.3, (52, 50, 26)), (0.62, (165, 164, 110)), (1, (250, 249, 226))), 1.0),  # burst: real black/white
    # fused style (the «mefedron master 4» edits): a lifted night mauve the serif can sit on, cold blues, a cold
    # negative for INV-looking shots, a warm night amber and a saturated gold that reads apart from orange
    "dusk": (((0, (0, 0, 0)), (0.5, (20, 12, 26)), (0.85, (86, 66, 96)), (1, (168, 140, 178))), 1.4),
    "ice": (((0, (0, 0, 0)), (0.45, (18, 40, 70)), (0.8, (120, 170, 215)), (1, (235, 245, 255))), 1.1),
    "teal": (((0, (0, 0, 0)), (0.4, (0, 46, 56)), (0.75, (20, 170, 200)), (1, (200, 250, 255))), 1.0),
    "icen": (((0, (225, 238, 252)), (0.25, (120, 170, 215)), (0.6, (18, 40, 70)), (1, (0, 0, 0))), 0.9),
    "nightamber": (((0, (0, 0, 0)), (0.5, (34, 20, 10)), (0.85, (120, 80, 44)), (1, (210, 160, 110))), 1.5),
    "gold": (((0, (0, 0, 0)), (0.35, (60, 36, 4)), (0.65, (170, 118, 30)), (0.88, (240, 196, 90)),
              (1, (255, 240, 190))), 1.0),
}
WARM = {"amber", "orange", "red", "khaki", "khakih", "redmono", "nightamber", "gold"}   # a plain invert turns these cyan


def luma(img):
    return img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114


def clip_levels(frames, lo=5, hi=95):
    """p5 / p95 of luma over a stack of frames (subsampled 1/8): one constant pair per shot"""
    y = luma(np.asarray(frames)[:, ::8, ::8].astype(np.float32))
    return float(np.percentile(y, lo)), float(np.percentile(y, hi))


@lru_cache(maxsize=64)
def _lut(stops, gamma):
    u = (np.arange(256) / 255.0) ** gamma
    pos = [s[0] for s in stops]
    return np.stack([np.interp(u, pos, [s[1][c] for s in stops]) for c in range(3)], -1).clip(0, 255).astype(np.uint8)


def duotone(img, stops, p5, p95, gamma=1.0, gain=1.0):
    """remap luma completely: (Y - p5) / (p95 - p5) -> gradient stops. p5 -> stop 0 (crushed)."""
    y = luma(img.astype(np.float32))
    u = np.clip((y - p5) / max(1.0, p95 - p5), 0, 1)
    idx = (u * 255).astype(np.uint8)
    out = _lut(tuple((float(a), tuple(b)) for a, b in stops), float(gamma))[idx]
    if gain != 1.0:
        out = np.clip(out.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    return out


def hue_matrix(deg):
    t = np.radians(deg)
    to = np.array([[.299, .587, .114], [.596, -.274, -.322], [.211, -.523, .312]])
    back = np.linalg.inv(to)
    rot = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    return (back @ rot @ to).astype(np.float32)


def hue_rotate(img, deg):
    out = img.astype(np.float32) @ hue_matrix(deg).T
    return np.clip(out, 0, 255).astype(np.uint8)


def washed(img, lift, gamma=0.55):
    """over-exposed burst frame: blacks lifted to `lift`, mids pushed up"""
    x = img.astype(np.float32) / 255
    return (lift + (255 - lift) * x ** gamma).clip(0, 255).astype(np.uint8)


def green_mask(img, thr=6, soft=22.0):
    x = img.astype(np.int16)
    return np.clip((x[..., 1] - np.maximum(x[..., 0], x[..., 2]) - thr) / soft, 0, 1)


def restore_colour(img, mask, rgb=(70, 235, 95), blur=3):
    """paint `rgb` back through a (blurred) mask: e.g. a green belt survives the lilac duotone"""
    gm = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur)),
                    np.float32)[..., None] / 255
    return (img * (1 - gm) + np.array(rgb, np.float32) * gm).astype(np.uint8)


def pulse(img, i, frames, amp=70, decay=(1, 0.5, 0.2), blue=0.25, lift=90):
    """syllable light pulse: +amp on R (and blue*amp on B) with a short decay; on the hit frame
    itself the highlights get a one-frame white-ish lift"""
    a = max([amp * decay[i - p] for p in frames if 0 <= i - p < len(decay)] + [0])
    if not a:
        return img
    x = img.astype(np.int16)
    x[..., 0] += int(a)
    x[..., 2] += int(a * blue)
    if i in frames and lift:
        y = luma(img.astype(np.float32))
        x += (np.clip((y - 40) / 60, 0, 1) * lift)[..., None].astype(np.int16)
    return np.clip(x, 0, 255).astype(np.uint8)


SOFT_STROBE = {"gain": 0.6, "lift": 28.0, "knee": 180.0, "ceiling": 220.0, "scale": 120.0, "floor": 0.27}


def exposure_strobe(img, i, window, peaks, soft=(), decay=(1.0, 0.55, 0.22, 0.05), curve=None):
    """B&W exposure strobe (ref3 #4): peaks [(frame, peak luma)], 1 f attack, fast decay, troughs at
    half exposure. `soft` peaks lift without clipping (screen-like) so a detail stays readable.

    curve = {"mode": "soft", ...SOFT_STROBE}: the face-safe strobe of the fused edits. The same timing and
    troughs, but the gain is capped at 1 + gain (1.6x) plus `lift`, and highlights roll off from `knee`
    toward `ceiling`, so lips and chin don't burn into glossy white blobs (the ref3 curve goes to
    x * 3.6 + 150 and clips)."""
    if not window[0] <= i <= window[1]:
        return img
    if curve and curve.get("mode", "soft") == "soft":
        c = dict(SOFT_STROBE, **{k: v for k, v in curve.items() if k != "mode"})
        e = 0.0
        for p, peak in peaks:
            if 0 <= i - p < len(decay):
                e = max(e, min(1.0, (peak - 30) / c["scale"]) * decay[i - p])
        x = img.astype(np.float32)
        if e < c["floor"]:
            return np.clip(x * 0.5, 0, 255).astype(np.uint8)
        y = x * (1 + c["gain"] * e) + c["lift"] * e
        knee, w = c["knee"], c["ceiling"] - c["knee"]
        y = np.where(y > knee, knee + w * (1 - np.exp(-(y - knee) / w)), y)
        return np.clip(y, 0, 255).astype(np.uint8)
    e = 0.0
    for p, peak in peaks:
        if 0 <= i - p < len(decay):
            e = max(e, (peak - 30) / 214 * decay[i - p])
    x = img.astype(np.float32)
    if e < 0.15:
        return np.clip(x * 0.5, 0, 255).astype(np.uint8)
    hard = [p for p, _ in peaks if p not in soft]
    if any(0 <= i - p < len(decay) for p in soft) and not any(0 <= i - p < len(decay) for p in hard):
        return (255 - (255 - x) * (1 - 0.75 * e) - 10 * (x > 240)).clip(0, 236).astype(np.uint8)
    return np.clip(x * (1 + 2.6 * e) + 150 * e, 0, 255).astype(np.uint8)


LUMA_W = np.array([0.299, 0.587, 0.114], np.float32)


def invert(sq, mode="rgb", palette=None):
    """1-frame invert. rgb: 255 - x (a warm duotone turns cyan/teal). hue: the luma flips but the hue
    stays (255 - x rotated 180 deg in YIQ). duotone: luma reversed through `palette` (stops, gamma), so
    an ice or violet shot stays ice or violet (the "cold invert"); without a palette it falls back to rgb."""
    if mode == "hue":
        return hue_rotate(255 - sq, 180)
    if mode == "duotone" and palette is not None:
        stops, gamma = palette
        lut = _lut(tuple((float(a), tuple(b)) for a, b in stops), float(gamma))
        y = np.clip(sq.astype(np.float32) @ LUMA_W, 0, 255).astype(np.uint8)
        return lut[255 - y]
    return 255 - sq


def scratches(img, seed):
    """film dust: 1-3 thin vertical scratches + 6-15 specks (in place, seeded per frame)"""
    rng = np.random.default_rng(seed)
    H_, W_ = img.shape[:2]
    for _ in range(int(rng.integers(1, 4))):
        x = int(rng.integers(40, W_ - 40))
        y0 = int(rng.integers(0, H_ // 2))
        y1 = int(rng.integers(y0 + 200, H_))
        v = int(rng.integers(150, 230))
        img[y0:y1, x:x + 1] = np.maximum(img[y0:y1, x:x + 1], v)
    for _ in range(int(rng.integers(6, 16))):
        x, y = int(rng.integers(0, W_ - 4)), int(rng.integers(0, H_ - 4))
        s = int(rng.integers(2, 5))
        img[y:y + s, x:x + s] = 225 if rng.random() < 0.6 else 10
    return img
