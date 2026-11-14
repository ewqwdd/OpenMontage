"""Contact sheets with burned-in frame numbers and timestamps.

  .venv/bin/python -m lib.card_strobe.tools.sheet <video.mp4 | png_dir> <out_dir> [--every 4] [--from a --to b]

Sheets are at most 2400 px on the long side (readable with an image viewer or the Read tool).
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..fonts import font

MAX_SIDE = 2400


def contact_sheet(items, out_dir, fps=30, cols=10, rows=3, prefix="sheet"):
    """items = [(frame, png path | PIL image)] -> sheet jpgs of cols x rows tiles, numbered"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not items:
        return []
    first = items[0][1]
    im0 = first if isinstance(first, Image.Image) else Image.open(first)
    aspect = im0.height / im0.width
    tw = MAX_SIDE // cols
    th = int(tw * aspect)
    while rows * (th + 22) > MAX_SIDE and rows > 1:
        rows -= 1
    try:
        f = font("sub", 15)
    except Exception:                       # pragma: no cover - only without any font file
        f = ImageFont.load_default()
    per = cols * rows
    sheets = []
    for s in range(0, len(items), per):
        chunk = items[s:s + per]
        sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for k, (fr, src) in enumerate(chunk):
            im = src if isinstance(src, Image.Image) else Image.open(src)
            im = im.convert("RGB").resize((tw, th), Image.BILINEAR)
            x, y = (k % cols) * tw, (k // cols) * (th + 22)
            sheet.paste(im, (x, y + 22))
            d.text((x + 4, y + 3), f"f{fr}  {fr / fps:.2f}s", fill=(255, 220, 0), font=f)
        p = out_dir / f"{prefix}_{chunk[0][0]:04d}-{chunk[-1][0]:04d}.jpg"
        sheet.save(p, quality=85)
        sheets.append(p)
    return sheets


def video_frames(path, every=4, a=0, b=None, width=216):
    """decode every `every`-th frame (a..b) of a video at `width` px -> [(frame, PIL image)]"""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf", f"scale={width}:-2",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(path)], capture_output=True, check=True, text=True).stdout
    w, h = (int(x) for x in probe.strip().split(",")[:2])
    hh = int(round(width * h / w / 2) * 2)
    fr = np.frombuffer(raw, np.uint8).reshape(-1, hh, width, 3)
    b = len(fr) if b is None else min(b, len(fr))
    return [(i, Image.fromarray(fr[i])) for i in range(a, b, every)]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="card_strobe.tools.sheet")
    ap.add_argument("src")
    ap.add_argument("out_dir")
    ap.add_argument("--every", type=int, default=4)
    ap.add_argument("--from", dest="a", type=int, default=0)
    ap.add_argument("--to", dest="b", type=int)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--cols", type=int, default=10)
    a = ap.parse_args(argv)
    src = Path(a.src).expanduser()
    if src.is_dir():
        items = sorted((int(p.stem.lstrip("f")), p) for p in src.glob("f*.png"))
        items = [(i, p) for i, p in items if i >= a.a and (a.b is None or i < a.b)][::a.every]
    else:
        items = video_frames(src, a.every, a.a, a.b)
    for p in contact_sheet(items, Path(a.out_dir).expanduser(), a.fps, cols=a.cols, prefix=src.stem):
        print(p)


if __name__ == "__main__":
    main()
