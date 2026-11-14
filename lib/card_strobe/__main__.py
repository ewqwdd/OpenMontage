"""python -m lib.card_strobe <timeline.json> <out_dir> [--preview | --frames a:b] [--step k] [--workers N] [--crf 16]

Default: <out_dir>/final.mp4 (1080x1920, audio trimmed to the timeline) + render_report.json.
--preview: half-size PNGs of every `--step`-th frame in <out_dir>/preview/ + numbered contact sheets.
--frames a:b: the same for frames a..b-1 only (end exclusive).
Precut clip windows are cached in <out_dir>/_work/precut (or --cache DIR) and reused.
"""
import argparse
import sys
from pathlib import Path

from . import render, timeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="card_strobe")
    ap.add_argument("timeline")
    ap.add_argument("out_dir")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--frames")
    ap.add_argument("--step", type=int)
    ap.add_argument("--workers", type=int)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--cache")
    a = ap.parse_args(argv)
    tl = timeline.load(a.timeline)
    out = Path(a.out_dir).expanduser()
    cache = Path(a.cache).expanduser() if a.cache else None
    if a.preview or a.frames:
        lo, hi = (int(x) for x in a.frames.split(":")) if a.frames else (0, tl["frames"])
        step = a.step or (1 if a.frames else 4)
        sheets = render.preview(tl, out, lo, hi, step, cache_dir=cache)
        print("preview ->", out / "preview")
        for s in sheets:
            print("sheet", s)
    else:
        final, rep = render.video(tl, out, a.workers, a.crf, cache, log=lambda s: print(s, flush=True))
        print(f"done {final}  ({rep['frames']} frames, {rep['wall_s']} s wall, {rep['fps_wall']} fps)")


if __name__ == "__main__":
    sys.exit(main())
