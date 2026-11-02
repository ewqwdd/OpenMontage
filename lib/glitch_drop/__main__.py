"""python -m lib.glitch_drop <timeline.json> <out_dir> [--preview] [--frames a:b] [--crf 15]

Default: <out_dir>/final.mp4 (1440x1080, audio trimmed to the timeline).
--preview / --frames a:b: 640x480 PNGs in <out_dir>/preview/ (a:b = frame range, end exclusive).
"""
import argparse
import sys
from pathlib import Path

from . import render, timeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="glitch_drop")
    ap.add_argument("timeline")
    ap.add_argument("out_dir")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--frames")
    ap.add_argument("--crf", type=int, default=15)
    a = ap.parse_args(argv)
    tl = timeline.load(a.timeline)
    out = Path(a.out_dir).expanduser()
    if a.preview or a.frames:
        only = tuple(int(x) for x in a.frames.split(":")) if a.frames else None
        print("preview ->", render.preview(tl, out, only))
    else:
        print("done", render.video(tl, out, a.crf, log=lambda s: print(s, flush=True)))


if __name__ == "__main__":
    sys.exit(main())
