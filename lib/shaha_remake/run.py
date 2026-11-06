"""Render frames of a segment module and compare with the reference.

  python -I run.py segA --frames 28:60 [--sheet out.png] [--zoom x0,y0,x1,y1] [--step 1]

Writes out/<seg>/<frame>.png and, with --sheet, a contact sheet: row pairs (mine on top, ref below),
8 frames per row, frame numbers printed. --zoom adds a 3x nearest-neighbour crop of that box instead
of the full frame (pixel-structure check).
"""
import argparse
import importlib
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import kit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seg")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--sheet")
    ap.add_argument("--zoom")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--cols", type=int, default=8)
    a = ap.parse_args()
    mod = importlib.import_module(a.seg)
    f0, f1 = map(int, a.frames.split(":"))
    out = HERE / "out" / a.seg
    out.mkdir(parents=True, exist_ok=True)
    idx = list(range(f0, f1, a.step))
    t = time.time()
    mine = {}
    for i in idx:
        img = kit.to_u8(mod.frame(i))
        Image.fromarray(img).save(out / f"{i:04d}.png")
        mine[i] = img
    print(f"{len(idx)} frames in {time.time() - t:.1f}s")
    if not a.sheet:
        return
    if a.zoom:
        x0, y0, x1, y1 = map(int, a.zoom.split(","))
        tw, th = (x1 - x0) * 3, (y1 - y0) * 3
        cut = lambda im: im.crop((x0, y0, x1, y1)).resize((tw, th), Image.NEAREST)
    else:
        tw, th = 240, 180
        cut = lambda im: im.resize((tw, th), Image.LANCZOS)
    cols = a.cols
    rows = (len(idx) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th * 2 + rows * 4), (60, 0, 0))
    d = ImageDraw.Draw(sheet)
    for k, i in enumerate(idx):
        x = (k % cols) * tw
        y = (k // cols) * (2 * th + 4)
        sheet.paste(cut(Image.fromarray(mine[i])), (x, y))
        sheet.paste(cut(Image.open(HERE / "full" / f"{i + 1:04d}.png").convert("RGB")), (x, y + th))
        d.rectangle([x, y, x + 34, y + 12], fill=(0, 0, 0))
        d.text((x + 2, y), str(i), fill=(255, 255, 0))
    sheet.save(a.sheet)
    print("sheet", a.sheet, sheet.size)


if __name__ == "__main__":
    main()
