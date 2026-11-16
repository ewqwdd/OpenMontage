"""Shared 2D helpers for the hollow 3D build (run with the project's .venv python)."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import (binary_closing, binary_dilation, binary_fill_holes, binary_opening,
                           distance_transform_edt, gaussian_filter, gaussian_filter1d, label)

HERE = Path(__file__).resolve().parent
CH = HERE.parent                                   # lib/pixel_lyrics/characters/hollow
WORK = HERE / "work"
WORK.mkdir(exist_ok=True)

CX = 504.5                                         # body centre line of the A-pose canvas
BG = (75, 63, 77)


def load(rel):
    return np.array(Image.open(CH / rel).convert("RGB")).astype(int)


def lum(a):
    a = np.asarray(a)
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def silhouette(im):
    bg = np.median(im[3:20, 3:20].reshape(-1, 3), axis=0)
    sm = np.stack([gaussian_filter(im[..., c].astype(float), 1.0) for c in range(3)], axis=-1)
    isbg = np.abs(sm - bg).sum(axis=2) <= 22
    lab, _ = label(isbg)
    return binary_fill_holes(lab != lab[5, 5])


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def biggest(m):
    lab, n = label(m)
    return lab == np.bincount(lab[m]).argmax() if n else m


def bleed(rgb, mask):
    """Fill everything outside `mask` with the nearest colour inside it."""
    idx = distance_transform_edt(~mask, return_distances=False, return_indices=True)
    return rgb[idx[0], idx[1]]


def row_extents(mask):
    """Per row: first and last True column (nan where the row is empty)."""
    h = mask.shape[0]
    x0, x1 = np.full(h, np.nan), np.full(h, np.nan)
    for y in range(h):
        xs = np.nonzero(mask[y])[0]
        if len(xs):
            x0[y], x1[y] = xs[0], xs[-1] + 1
    return x0, x1


def smooth_nan(a, sigma):
    """Gaussian smoothing of a 1D array over its valid run only."""
    out = a.copy()
    ok = ~np.isnan(a)
    if ok.sum() > 3:
        i = np.nonzero(ok)[0]
        seg = a[i[0]:i[-1] + 1].copy()
        bad = np.isnan(seg)
        if bad.any():
            seg[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], seg[~bad])
        out[i[0]:i[-1] + 1] = gaussian_filter1d(seg, sigma, mode="nearest")
    return out


def load_parts():
    """Puppet parts pasted on the 1024 A-pose canvas: name -> (rgb, mask)."""
    rig = json.loads((CH / "puppet/front/rig.json").read_text(encoding="utf-8"))
    out = {}
    for name, p in rig["parts"].items():
        a = np.array(Image.open(CH / "puppet/front" / p["file"]).convert("RGBA")).astype(int)
        rgb = np.zeros((1024, 1024, 3), int)
        m = np.zeros((1024, 1024), bool)
        ox, oy = p["origin"]
        h, w = a.shape[:2]
        rgb[oy:oy + h, ox:ox + w] = a[..., :3]
        m[oy:oy + h, ox:ox + w] = a[..., 3] > 127
        out[name] = (rgb, m)
    return out, rig


def save(name, arr):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(WORK / name)


def dedither(rgb, mask, radius=3, sigma_s=1.7, sigma_r=11.0, passes=2):
    """Dither -> the flat tone it stands for; outlines, creases, prints and other detail stay as drawn.

    The drawings shade with a fine dot dither (1-3 px pitch). Turned or scaled in 3D with nearest filtering it can
    shimmer, so a second atlas carries the smoothed tone instead: an edge-preserving (bilateral) blur that averages
    neighbours of nearly the same brightness and leaves real edges alone.
    """
    out = bleed(rgb, mask).astype(float)
    for _ in range(passes):
        l0 = lum(out)
        acc, wsum = np.zeros_like(out), np.zeros(l0.shape)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sh = np.roll(out, (dy, dx), axis=(0, 1))
                w = np.exp(-(dx * dx + dy * dy) / (2 * sigma_s ** 2) - (lum(sh) - l0) ** 2 / (2 * sigma_r ** 2))
                acc += sh * w[..., None]
                wsum += w
        out = acc / wsum[..., None]
    return np.where(mask[..., None], np.rint(out), rgb).astype(int)
