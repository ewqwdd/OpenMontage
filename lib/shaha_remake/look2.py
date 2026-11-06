"""Text look v2, built from the measured texture (spec/segA.md "Texture").

The reference text was made at ~480x360 and upscaled 2x, so the text layer is composed at HALF
resolution and upscaled bilinearly:
  glyph (soft 5 px edge) -> 2-row-paired band steps (+-1-2 px, 20-70 px bands)
  navy halo: symmetric, ~opaque to 8 px, 50 % at 12-16 px, 0 at 24 px (full-res px)
  fill colour x vertical streaks (2 px wide, 4 px period, full height, std ~10 levels)
           x 1 px mono grain (vertically elongated, std ~10-13 levels), text only
Background stays at full resolution and clean.
"""
import numpy as np
from PIL import Image

import kit

HW, HH = kit.W // 2, kit.H // 2


def up(a):
    """half-res (HH, HW[,3]) -> full res, bilinear."""
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((kit.W, kit.H), Image.BILINEAR), np.float32)
    return np.stack([up(a[..., c]) for c in range(a.shape[2])], -1)


def down(a):
    if a.ndim == 2:
        return a.reshape(HH, 2, HW, 2).mean((1, 3))
    return a.reshape(HH, 2, HW, 2, a.shape[2]).mean((1, 3))


def band_steps(m, seed, bmin=10, bmax=35, amax=1, p=0.5):
    """half-res band shifts (bands of 20-70 full-res px = 10-35 half-res rows, +-1-2 full px)."""
    r = kit.rng(seed)
    out = m.copy()
    y = 0
    while y < m.shape[0]:
        b = int(r.integers(bmin, bmax + 1))
        if r.random() < p:
            out[y:y + b] = np.roll(m[y:y + b], int(r.integers(-amax, amax + 1)), axis=1)
        y += b
    return out


HALO = {  # (colour, radius_full_px at ~50 %, opacity near the glyph)
    "white": ((30, 28, 58), 14, 0.97),
    "cyan": ((24, 34, 66), 16, 0.99),
    "red": ((30, 18, 38), 10, 0.75),
}


def text_layer(text, bbox, col, seed, weight=700, kind="white", tracking=0.0, name="oswald",
               streak=(0.08, 0.04), grain=0.028, soft=0.3, steps=True, halo=None, red_ring=False, sharp=1.2):
    """-> (rgb_full, alpha_full, glyph_full): a text layer to composite over the background."""
    m, _ = kit.text_box(text, bbox, weight, tracking, name)
    h = down(m)
    if steps:
        h = band_steps(h, seed)
    h = kit.blur(h, soft)                                   # half-res blur -> ~5 px edges after upscale
    hc, hr, ha = halo or HALO[kind]
    # halo: dilate ~ radius/2 (half res) then blur
    g = kit.blur(kit.dilate(h, max(1, int(hr / 2.5))), hr / 6)
    g = np.clip(g * 1.6, 0, 1) * ha
    if red_ring:   # ring peaks 6-8 px out instead of hugging the glyph
        g = g * (1 - 0.5 * h)
    r = kit.rng(seed + 1)
    # streaks: 1 px on / 1 px off at half res = 2 px / 4 px at full res, full height with drift
    x = np.arange(HW, dtype=np.float32)
    phase = r.random() < 0.5
    st = 1 - streak[0] * (((x.astype(int) + phase) % 2))[None, :]
    st = st * kit.streaks(HH, HW, seed + 2, amp=streak[1], ylen=30, xsoft=0.0)
    gr = r.normal(0, grain, (HH * 2, HW)).astype(np.float32).reshape(HH, 2, HW).mean(1)  # elongated
    fill = np.asarray(col, np.float32)[None, None] / 255 * (st * (1 + gr))[..., None]
    rgb = np.asarray(hc, np.float32)[None, None] / 255 * np.ones((HH, HW, 1), np.float32)
    rgb = rgb * (1 - h[..., None]) + fill * h[..., None]
    alpha = np.maximum(g, h)
    rgb_f, a_f, h_f = up(np.clip(rgb, 0, 1)), np.clip(up(alpha), 0, 1), np.clip(up(h), 0, 1)
    if sharp:   # the upscale was sharpened (crisp edges with the half-res stair structure)
        h_s = np.clip(h_f + sharp * (h_f - kit.blur(h_f, 2.0)), 0, 1)
        rgb_f = np.clip(rgb_f + sharp * (rgb_f - kit.blur(rgb_f, 2.0)), 0, 1)
        h_f = h_s
    # fine full-res grain on the glyph only (the 1 px speckle)
    fg = kit.rng(seed + 3).normal(0, grain * 0.5, (kit.H, kit.W)).astype(np.float32)
    rgb_f = np.clip(rgb_f * (1 + fg[..., None] * h_f[..., None]), 0, 1)
    return rgb_f, a_f, h_f


def comp(img, layer):
    rgb, a, _ = layer
    return kit.over_img(img, rgb, a)
