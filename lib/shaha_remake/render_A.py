"""Segment A final render: clean frame -> 8px block jitter -> MPEG-2 pass -> fine post grain on the text.
python -I render_A.py a:b [outdir]"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import kit, build_A, crunch  # noqa: E402

Q, JP, JA, JH = 6, 0.24, 4, (2, 8)
WYLEN = 14
WFINE = 0.22
JP_RANGE = [((83, 108), 0.08), ((109, 126), 0.13), ((33, 82), 0.34), ((127, 215), 0.34), ((216, 234), 0.34)]


def _jp(i):     # per-word density, matched to the ref temporal diff of each word
    for (a, b), p in JP_RANGE:
        if a <= i <= b:
            return p
    return JP


JIT = {28: (0.6, 6), 29: (0.35, 3), 32: (0.4, 4)}   # stronger block tearing on entry / pre-cut frames


def post_grain(img, mask, sigma, seed, kind="fine"):
    r = kit.rng(seed)
    if kind == "col":       # white: vertical streak texture, per column, slowly varying in y (ref dv 3 / dh 10)
        n = kit.streaks(kit.H, kit.W, seed, amp=1.0, ylen=WYLEN, xsoft=0.9) - 1
        n = (n + WFINE * r.normal(0, 1, (kit.H, kit.W)).astype(np.float32)) / (1 + WFINE ** 2) ** 0.5
    else:
        n = r.normal(0, 1, (kit.H + 1, kit.W)).astype(np.float32)
        n = (n[:-1] + 0.6 * n[1:]) / 1.166          # 1 px wide, slightly elongated vertically
    return np.clip(img * (1 + sigma * n * mask)[..., None], 0, 1)


def main():
    f0, f1 = map(int, sys.argv[1].split(":"))
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "out" / "build_A"
    clean = HERE / "out" / "clean"; dec = HERE / "out" / "dec"
    clean.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    masks = {}
    for i in range(f0, f1):
        im = build_A.frame(i)
        jp, ja = JIT.get(i, (_jp(i), JA))
        im = crunch.edge_jitter(im, i * 13 + 1, p=jp, amax=ja, hmul=JH)
        Image.fromarray(kit.to_u8(np.clip(im, 0, 1))).save(clean / f"{i:04d}.png")
        if i in build_A.POST:
            m, s, kd = build_A.POST[i]
            masks[i] = (np.clip(m, 0, 1), s, kd)
    crunch.codec_pass(clean, dec, f0, f1, q=Q)
    for i in range(f0, f1):
        im = np.asarray(Image.open(dec / f"{i:04d}.png").convert("RGB"), np.float32) / 255
        if i in masks:
            im = post_grain(im, masks[i][0], masks[i][1], i * 977 + 3, masks[i][2])
        for fn in build_A.POST_FX.get(i, []):
            im = fn(im)
        im = speckle(im, i)
        Image.fromarray(kit.to_u8(im)).save(out / f"{i:04d}.png")



# ---------------------------------------------------------------- speckle blocks (16 px), positions measured on the reference
import json as _json  # noqa: E402
SPECK = {int(k): v for k, v in _json.loads((HERE / "spec" / "speckle_A.json").read_text()).items()}


def _hp_mean(a):
    return np.abs(a - kit.gblur(a, 1.0)).mean()


def speckle(img, i):
    if i not in SPECK:
        return img
    r = kit.rng(i * 4049 + 11)
    out = img.copy()
    L = img.mean(-1)
    for bx, by, target in SPECK[i]:
        ys, xs = slice(by * 16, by * 16 + 16), slice(bx * 16, bx * 16 + 16)
        cur = _hp_mean(L[max(0, by * 16 - 3):by * 16 + 19, max(0, bx * 16 - 3):bx * 16 + 19] * 255)
        need = max(0.0, target ** 2 - cur ** 2) ** 0.5
        s = need / 0.62 / 255          # mean |hp| of unit white noise after the sigma-1 high-pass ~0.62
        n = r.normal(0, 1, (16, 16)).astype(np.float32)
        blk = out[ys, xs]
        lum = blk.mean(-1, keepdims=True)
        # mostly luminance noise, scaled up on bright pixels (text) and floored on black
        out[ys, xs] = np.clip(blk + n[..., None] * s * (0.45 + 0.55 * np.clip(lum * 3, 0, 1)) / 0.75, 0, 1)
    return out


if __name__ == "__main__":
    main()
