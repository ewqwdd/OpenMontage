"""Frame-by-frame regression: decode two videos and report the mean absolute error per frame.

  .venv/bin/python -m lib.card_strobe.tools.compare <a.mp4> <b.mp4> [--out mae.json] [--worst 10]

MAE is on 8-bit RGB at full resolution. Re-encoding the same frames costs about 0.3-1.0 (codec
noise); anything above ~4 on a frame is a real difference worth looking at.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


def _reader(path, w, h):
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-"], stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


def _size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(path)], capture_output=True, check=True, text=True).stdout
    return tuple(int(x) for x in out.strip().split(",")[:2])


def compare(a, b):
    sa, sb = _size(a), _size(b)
    if sa != sb:
        raise SystemExit(f"size differs: {sa} vs {sb}")
    mae = []
    for x, y in zip(_reader(a, *sa), _reader(b, *sb)):
        mae.append(float(np.abs(x.astype(np.int16) - y.astype(np.int16)).mean()))
    return np.array(mae)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="card_strobe.tools.compare")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out")
    ap.add_argument("--worst", type=int, default=10)
    a = ap.parse_args(argv)
    mae = compare(a.a, a.b)
    order = np.argsort(-mae)[:a.worst]
    res = dict(frames=len(mae), mean=round(float(mae.mean()), 4), median=round(float(np.median(mae)), 4),
               max=round(float(mae.max()), 4), worst=[[int(i), round(float(mae[i]), 3)] for i in order],
               above_4=[int(i) for i in np.where(mae > 4)[0]])
    print(json.dumps(res))
    if a.out:
        Path(a.out).write_text(json.dumps(dict(res, per_frame=[round(float(v), 4) for v in mae])))


if __name__ == "__main__":
    main()
