"""Song structure for a glitch-drop edit, numpy only (no librosa / scipy).

  .venv/bin/python -m lib.glitch_drop.tools.music <audio|video> [--out analysis.json] [--drop SEC]

Finds the tempo and beat grid, the DROP and the strong low (808 / kick) hits.
- Tempo: comb fit of the spectral-flux envelope, period then phase.
- The drop is NOT the biggest bass jump. The reference song gets +30 dB sub at bar 5 and the edit
  ignores it. The drop is the beat boundary with the largest jump in the bright/noisy group
  (2-5 kHz, 5-16 kHz, spectral flatness, centroid) + 0.5x the low group, with the low end already
  present before it (or the loudest section after it). Bars are then counted so that the drop is
  a downbeat.
- Low hits: peaks of the sub-band (< 90 Hz) flux. The flash of each glitch cell is nudged onto
  the strongest one.

Output JSON: duration, tempo, period, phase, beats[], downbeats[], drop{time, beat, score,
candidates[]}, low_hits[[t, strength]], section energies per bar.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

SR = 22050
HOP = 220          # ~10 ms
NF = 2048


def load(path, sr=SR, start=0.0, end=None):
    cut = ["-ss", str(start)] + (["-t", str(end - start)] if end else [])
    raw = subprocess.run(["ffmpeg", "-v", "error", *cut, "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def features(x, sr=SR):
    n = max(1, (len(x) - NF) // HOP + 1)
    x = np.pad(x, (0, max(0, NF + HOP * n - len(x))))
    win = np.hanning(NF).astype(np.float32)
    X = np.empty((n, NF // 2 + 1), np.float32)
    for a in range(0, n, 512):                     # chunked: keeps memory flat on long songs
        idx = np.arange(NF)[None, :] + HOP * np.arange(a, min(n, a + 512))[:, None]
        X[a:a + len(idx)] = np.abs(np.fft.rfft(x[idx] * win, axis=1))
    fr = np.fft.rfftfreq(NF, 1 / sr)
    t = (np.arange(n) * HOP + NF / 2) / sr
    L = np.log1p(100 * X)
    flux = np.vstack([np.zeros((1, X.shape[1]), np.float32), np.maximum(L[1:] - L[:-1], 0)])
    F = dict(t=t)
    for k, (lo, hi) in dict(sub=(20, 90), low=(20, 150), lowmid=(150, 500), mid=(500, 2000),
                            pres=(2000, 5000), high=(5000, 11000)).items():
        m = (fr >= lo) & (fr < hi)
        F["E_" + k] = 10 * np.log10((X[:, m] ** 2).sum(1) + 1e-9)
        F["F_" + k] = flux[:, m].sum(1)
    F["flux"] = flux.sum(1)
    P = X ** 2 + 1e-12
    F["flat"] = np.exp(np.log(P).mean(1)) / P.mean(1)
    F["cent"] = (X * fr).sum(1) / (X.sum(1) + 1e-9)
    return F


def _env(e):
    e = e - np.convolve(e, np.ones(50) / 50, "same")
    e = np.maximum(e, 0)
    return e / (e.std() + 1e-9)


def tempo(F, bpm_range=(70, 170)):
    """period (s) by autocorrelation of the onset envelope, refined by a comb fit; phase (s) by comb."""
    t = F["t"]; dt = t[1] - t[0]
    env = _env(F["flux"]) + 0.5 * _env(F["F_low"])
    e = env - env.mean()
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    ac /= ac[0] + 1e-9
    lags = np.arange(len(ac)) * dt
    lo, hi = 60 / bpm_range[1], 60 / bpm_range[0]
    best = None
    for i in np.where((lags >= lo) & (lags <= hi))[0]:
        # reward the lag and its double (bar-level periodicity), prefer 90-150 BPM a little
        j = min(len(ac) - 1, 2 * i)
        bpm = 60 / lags[i]
        s = ac[i] + 0.5 * ac[j] + (0.05 if 90 <= bpm <= 150 else 0)
        if best is None or s > best[0]:
            best = (s, lags[i])
    P0 = best[1]

    def comb(P, ph):
        bt = np.arange(ph, t[-1], P)
        k = np.clip(np.round((bt - t[0]) / dt).astype(int), 0, len(env) - 1)
        return env[k].sum() / max(1, len(k))
    cands = [(comb(P, ph), P, ph) for P in np.linspace(P0 * 0.985, P0 * 1.015, 61)
             for ph in np.arange(0, P, dt)]
    _, P, ph = max(cands)
    return float(P), float(ph % P)


def per_beat(F, beats):
    keys = ["E_sub", "E_low", "E_lowmid", "E_mid", "E_pres", "E_high", "flat", "cent", "flux"]
    t = F["t"]
    R = []
    for a, b in zip(beats[:-1], beats[1:]):
        m = (t >= a) & (t < b)
        R.append([float(np.mean(F[k][m])) if m.any() else np.nan for k in keys])
    R = np.array(R)
    R = np.where(np.isnan(R), np.nanmean(R, 0), R)
    return keys, R


def find_drop(F, beats, win=4, min_beat=4):
    keys, R = per_beat(F, beats)
    Z = (R - R.mean(0)) / (R.std(0) + 1e-9)
    hi = [keys.index(k) for k in ("E_pres", "E_high", "flat", "cent")]
    lo = [keys.index(k) for k in ("E_sub", "E_low")]
    sub = R[:, keys.index("E_sub")]
    loud = R[:, :6].mean(1)
    out = []
    for b in range(min_beat, len(R) - 2):
        nxt, prv = Z[b:b + win], Z[max(0, b - win):b]
        st = nxt.mean(0) - prv.mean(0)
        score = st[hi].sum() + 0.5 * st[lo].sum()
        sub_before = sub[max(0, b - win):b].mean() > np.median(sub) - 6
        loudest_after = loud[b:b + 8].mean() >= np.percentile(loud, 75)
        if not (sub_before or loudest_after):
            score -= 3
        out.append((float(score), b))
    out.sort(reverse=True)
    return out


def low_hits(F, thr=1.5):
    e = _env(F["F_sub"]) + 0.5 * _env(F["F_low"])
    t = F["t"]
    pk = [i for i in range(2, len(e) - 2) if e[i] > thr and e[i] == e[i - 2:i + 3].max()]
    return [[round(float(t[i]), 3), round(float(e[i]), 2)] for i in pk]


def analyse(path, drop=None, start=0.0, end=None):
    """all times in the result are relative to `start` (the excerpt the edit uses)."""
    x = load(path, start=start, end=end)
    F = features(x)
    dur = len(x) / SR
    P, ph = tempo(F)
    beats = np.arange(ph, dur + 1e-6, P)
    cands = find_drop(F, beats)
    if drop is not None:
        b = int(np.argmin(np.abs(beats - drop)))
        cands = [(9.99, b)] + [c for c in cands if c[1] != b]
    db = cands[0][1]
    downbeats = [float(beats[i]) for i in range(db % 4, len(beats), 4)]
    keys, R = per_beat(F, beats)
    bars = []
    for i0 in range(db % 4, len(R), 4):
        r = R[i0:i0 + 4].mean(0)
        bars.append(dict(t=round(float(beats[i0]), 3), sub=round(r[0], 1), pres=round(r[4], 1),
                         high=round(r[5], 1), flat=round(r[6], 3)))
    return dict(source=str(path), duration=round(dur, 3), tempo=round(60 / P, 2), period=round(P, 5),
                phase=round(ph, 4), beats=[round(float(b), 4) for b in beats],
                downbeats=[round(d, 4) for d in downbeats],
                drop=dict(time=round(float(beats[db]), 4), beat=int(db), score=round(cands[0][0], 2),
                          candidates=[dict(time=round(float(beats[b]), 3), beat=int(b), score=round(s, 2))
                                      for s, b in cands[:5]]),
                low_hits=low_hits(F), bars=bars)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="glitch_drop.tools.music")
    ap.add_argument("audio")
    ap.add_argument("--out")
    ap.add_argument("--drop", type=float, help="force the drop near this time (s, excerpt time)")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    a = ap.parse_args(argv)
    res = analyse(a.audio, a.drop, a.start, a.end)
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    d = res["drop"]
    print(f"tempo {res['tempo']} BPM, beat {res['period'] * 30:.2f} fr@30, duration {res['duration']} s")
    print(f"drop {d['time']} s (beat {d['beat']}, score {d['score']})  candidates: "
          + ", ".join(f"{c['time']}s/{c['score']}" for c in d["candidates"]))


if __name__ == "__main__":
    main()
