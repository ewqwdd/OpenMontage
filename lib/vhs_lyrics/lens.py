"""CRT barrel lens: ffmpeg chain for post + inverse mapping for text boxes.

Measured on the reference: radial k1=0.17 about the frame centre (R0 = half diagonal),
constant over time. To keep corners filled the frame is zoomed 1.17 first.
Boxes are measured on the *distorted* reference, so before rasterising a word its box is
mapped back to pre-lens coordinates (remap_box) — after the lens it lands on the measurement.
"""
import numpy as np

K1, ZOOM = 0.17, 1.17


def ffmpeg_chain(w, h, k1=K1, zoom=ZOOM):
    zw, zh = round(w * zoom / 2) * 2, round(h * zoom / 2) * 2
    return (f"scale={zw}:{zh}:flags=bicubic,lenscorrection=k1={k1 * zoom * zoom:.4f}:i=bilinear,"
            f"crop={w}:{h}")


def make_remap(w, h, k1=K1, zoom=ZOOM):
    cx, cy, r0 = w / 2, h / 2, np.hypot(w, h) / 2

    def fwd(xs, ys):
        dx, dy = xs - cx, ys - cy
        ru = np.hypot(dx, dy) * zoom
        rd = ru.copy()
        for _ in range(30):
            rd -= (rd * (1 + k1 * (rd / r0) ** 2) - ru) / (1 + 3 * k1 * (rd / r0) ** 2)
        s = np.where(ru > 0, rd / np.maximum(np.hypot(dx, dy), 1e-9), 1 / zoom)
        return cx + dx * s, cy + dy * s

    def bbox_out(x0, x1, y0, y1, n=200):
        t = np.linspace(0, 1, n)
        xs = np.r_[x0 + (x1 - x0) * t, x0 + (x1 - x0) * t, np.full(n, x0), np.full(n, x1)]
        ys = np.r_[np.full(n, y0), np.full(n, y1), y0 + (y1 - y0) * t, y0 + (y1 - y0) * t]
        X, Y = fwd(xs, ys)
        return np.array([X.min(), X.max(), Y.min(), Y.max()])

    def remap_box(b):
        """(x0, x1, y0, y1) in % as seen on screen -> % before the lens"""
        tgt = np.array([b[0] * w, b[1] * w, b[2] * h, b[3] * h]) / 100
        src = np.r_[cx + (tgt[:2] - cx) / zoom, cy + (tgt[2:] - cy) / zoom]
        for _ in range(60):
            src -= (bbox_out(*src) - tgt) * 0.8
        return tuple(src / np.array([w, w, h, h]) * 100)

    return remap_box
