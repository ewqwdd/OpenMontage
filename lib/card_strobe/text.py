"""Text masks and compositing (float32 masks 0..1, numpy + PIL).

Sizes: `cap_px` is the cap height of 'H' in pixels; `cap_size()` turns it into a font size. Every
helper paste()s a solid colour through a mask centred at (cx, cy), clipped to the image.
"""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .fonts import font


@lru_cache(maxsize=256)
def text_mask(text, role, size, stroke=0, outline=False):
    """tight mask of `text`. outline=True: only the `stroke`-px ring outside the glyphs."""
    f = font(role, size)
    b = f.getbbox(text, stroke_width=stroke)
    pad = stroke + 2
    im = Image.new("L", (b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), text, font=f, fill=0 if outline else 255,
                            stroke_width=stroke, stroke_fill=255)
    return np.asarray(im, np.float32) / 255


@lru_cache(maxsize=64)
def cap_size(role, cap_px):
    """font size whose 'H' cap height is cap_px"""
    b = font(role, 200).getbbox("H")
    return 200 * cap_px / (b[3] - b[1])


@lru_cache(maxsize=64)
def fitted_mask(text, role, w, h, outline_px=0):
    """text stretched exactly to w x h (the hero-card look). outline_px > 0: a ring of that width."""
    m = text_mask(text, role, 400)
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((int(w), int(h)), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    if outline_px:
        big = np.asarray(im.filter(ImageFilter.MaxFilter(2 * outline_px + 1)), np.float32) / 255
        a = np.clip(big - a, 0, 1)
    return a


@lru_cache(maxsize=32)
def blocky_mask(text, cap_px, block=6, role="blocky"):
    """pixel-stencil glyphs: a mono bold face rendered small, thresholded, nearest-neighbour upscaled"""
    small = text_mask(text, role, cap_size(role, cap_px) / block)
    im = Image.fromarray((small * 255).astype(np.uint8))
    im = im.point(lambda v: 255 if v > 110 else 0)
    im = im.resize((im.width * block, im.height * block), Image.NEAREST)
    return np.asarray(im, np.float32) / 255


def rotated(mask, deg):
    im = Image.fromarray((mask * 255).astype(np.uint8)).rotate(deg, Image.BICUBIC, expand=True)
    return np.asarray(im, np.float32) / 255


def scaled(mask, s):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


def _region(img, mask, cx, cy):
    H_, W_ = img.shape[:2]
    h, w = mask.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    sx0, sy0, dx0, dy0 = max(0, -x0), max(0, -y0), max(0, x0), max(0, y0)
    ww, hh = min(w - sx0, W_ - dx0), min(h - sy0, H_ - dy0)
    if ww <= 0 or hh <= 0:
        return None
    return (slice(dy0, dy0 + hh), slice(dx0, dx0 + ww)), mask[sy0:sy0 + hh, sx0:sx0 + ww]


def paste(img, mask, color, cx, cy, opacity=1.0):
    """solid colour through mask, centred at cx, cy (in place)"""
    r = _region(img, mask, cx, cy)
    if r is None or opacity <= 0:
        return img
    (ys, xs), a = r
    a = a[..., None] * opacity
    reg = img[ys, xs].astype(np.float32)
    img[ys, xs] = (reg * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)
    return img


def paste_shadow(img, mask, cx, cy, blur=10, strength=0.6, off=(4, 6)):
    pad = blur * 2
    im = Image.fromarray((np.pad(mask, pad) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
    sh = np.asarray(im, np.float32) / 255
    return paste(img, sh, (0, 0, 0), cx + off[0], cy + off[1], strength)


def paste_difference(img, mask, cx, cy):
    """difference blend with white: the text inverts the picture under it"""
    r = _region(img, mask, cx, cy)
    if r is None:
        return img
    (ys, xs), a = r
    a = a[..., None]
    reg = img[ys, xs].astype(np.float32)
    img[ys, xs] = (reg * (1 - a) + (255 - reg) * a).astype(np.uint8)
    return img


def subtitle_mask(text, cursor=False, size=41, max_w=660, role="sub"):
    """one subtitle line (41 px = cap ~29 px at 1080), optional block cursor after the last word"""
    m = text_mask(text, role, size)
    if m.shape[1] > max_w:
        m = scaled(m, max_w / m.shape[1])
    if cursor:
        h, w = m.shape
        cw, ch = 20, 8
        out = np.zeros((max(h, ch), w + 8 + cw), np.float32)
        out[:h, :w] = m
        out[h - ch - 2:h - 2, w + 8:w + 8 + cw] = 1.0
        m = out
    return m


def outline_stack(img, text, role, cap, rows, cx, cy, pitch, stroke=3, color=(255, 255, 255)):
    """`rows` outline copies of `text` stacked around cy with `pitch` px between rows"""
    m = text_mask(text, role, cap_size(role, cap), stroke, True)
    for r in range(rows):
        paste(img, m, color, cx, cy + (r - (rows - 1) / 2) * pitch)
    return img
