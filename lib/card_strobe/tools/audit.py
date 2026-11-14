"""QA numbers for a finished card-strobe / fused edit, measured on the ENCODED video (they caught real
problems that the contact sheets did not on the «mefedron master 4» edits).

  .venv/bin/python -m lib.card_strobe.tools.audit <final.mp4> [--timeline timeline.json] \\
      [--track track.json | --hits hits.json] [--cold a:b] [--out audit.json]

Frames are decoded at 270x480 (area); the square = rows 105:375; luma BT.601; energy = mean |diff| of
the square to the previous frame.
- 808 coverage: low hits (from --track's low_hits or a json list of seconds, original-audio time) with no
  visual event, i.e. max energy < 25 within +-1 frame. Each one is a kick the picture ignores.
- duplicate clip frames: energy < 1.0 between two footage frames (needs --timeline): a slow `speed` on a
  30 fps precut, a frozen source. Fix with clips.X.fps = 60 or speed >= 1.
- warm/rainbow pixel fraction per frame (green / pink / yellow, saturated): `iri` or a plain invert
  leaking onto a cold palette. --cold a:b limits the check to the frames that should stay cold.
- loop seam: mean |square(last) - square(0)|. Mastermind measures 44.8; under ~50 loops cleanly.
- brightest frames (the drop white should be the only full-white square), flat runs (std < 8),
  section energy means.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def decode(path, w=270, h=480):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32)


def warm_fraction(sq):
    r, g, b = sq[..., 0], sq[..., 1], sq[..., 2]
    mx, mn = sq.max(-1), sq.min(-1)
    sat = (mx - mn) / (mx + 1e-3)
    warm = ((g > b + 25) | ((r > b + 25) & (r > g + 25) & (g > 60))) & (sat > 0.35) & (mx > 90)
    return float(warm.mean())


def runs(frames):
    out, cur = [], []
    for f in frames:
        if cur and f != cur[-1] + 1:
            out.append([cur[0], cur[-1]])
            cur = []
        cur.append(f)
    if cur:
        out.append([cur[0], cur[-1]])
    return out


def load_hits(path):
    j = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    hs = j.get("low_hits", j) if isinstance(j, dict) else j
    return [float(h["t"] if isinstance(h, dict) else (h[0] if isinstance(h, (list, tuple)) else h)) for h in hs]


def audit(video, tl=None, hits=None, cold=None, fps=30.0, start=0.0):
    fr = decode(video)
    sq = fr[:, 105:375]
    y = sq @ LUMA
    ml, sd = y.mean((1, 2)), y.std((1, 2))
    e = np.concatenate([[0.0], np.abs(np.diff(y, axis=0)).mean((1, 2))])
    n = len(fr)
    res = {"frames": n, "energy_mean": round(float(e.mean()), 2),
           "loop_seam": round(float(np.abs(sq[0] - sq[-1]).mean()), 1),
           "brightest": [[int(i), round(float(ml[i]), 1)] for i in np.argsort(-ml)[:5]],
           "flat_runs": [r for r in runs([i for i in range(n) if sd[i] < 8]) if r[1] - r[0] >= 2]}
    if hits is not None:
        hf = sorted({int(round((t - start) * fps)) for t in hits if 0 <= (t - start) * fps < n})
        quiet = [h for h in hf if max(e[max(0, h - 1):h + 2]) < 25]
        res["low_hits"] = len(hf)
        res["low_hits_without_event"] = quiet
    if tl is not None:
        from .. import render
        kinds = [render.frame_spec(tl, i)[0] for i in range(min(n, tl["frames"]))]
        res["dup_clip_frames"] = [i for i in range(1, len(kinds)) if e[i] < 1.0 and kinds[i] == kinds[i - 1] == "clip"]
        res["energy_by_kind"] = {k: round(float(np.mean([e[i] for i, kk in enumerate(kinds) if kk == k])), 1)
                                 for k in set(kinds)}
    a, b = cold if cold else (0, n - 1)
    warm = {i: warm_fraction(sq[i]) for i in range(a, min(b, n - 1) + 1)}
    res["warm_px_max"] = round(max(warm.values()), 4) if warm else 0.0
    res["warm_frames_gt_1pct"] = [i for i, v in warm.items() if v > 0.01]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="card_strobe.tools.audit")
    ap.add_argument("video")
    ap.add_argument("--timeline")
    ap.add_argument("--track", help="beat analysis json with low_hits [{t}] (original-audio seconds)")
    ap.add_argument("--hits", help="json list of 808 times (original-audio seconds)")
    ap.add_argument("--cold", help="a:b frames that must not turn warm / rainbow")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    tl, fps, start = None, 30.0, 0.0
    if a.timeline:
        from .. import timeline
        tl = timeline.load(a.timeline)
        fps, start = tl["fps"], tl["audio"]["start"]
    hits = load_hits(a.track or a.hits) if (a.track or a.hits) else None
    cold = tuple(int(x) for x in a.cold.split(":")) if a.cold else None
    res = audit(a.video, tl, hits, cold, fps, start)
    print(json.dumps(res, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
