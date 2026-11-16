"""Find where each syllable of a word starts, from the vocal stem.

    python tools/syllables.py <vocals.wav> --offset 11 --edit chorus --word 2 [--word 5 ...]

--offset  seconds to add to stem time to get track time (the start of the excerpt that was separated)
--edit / --word  the word's index inside its edit in productions/words.final.json

Prints a 10 ms envelope of the word: '#' is vowel-band energy (250-2500 Hz), '+' is hiss (4-9 kHz).
A syllable starts where the '#' bar rises out of a dip (stops: d, k, t, p are short holes; fricatives: f, s, sh
are a '#' dip with '+' still high). Read the frame column and write the offsets from the word's first frame
into the scene set:  syl: { 2: [['МЕ', 0], ['ФЕ', 5], ['ДРОН', 12]] }.  A repeated line is a cross-check.
"""
import argparse, json
from pathlib import Path
import numpy as np, soundfile as sf

PROJ = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("vocals"); ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--edit", required=True); ap.add_argument("--word", type=int, action="append", required=True)
    args = ap.parse_args()
    W = json.loads((PROJ / "productions/words.final.json").read_text(encoding="utf-8"))
    E, fps, lead = W["edits"][args.edit], W.get("fps", 30), W.get("lead", 0.35)
    ws = [w for w in W["words"] if w["edit"] == args.edit]
    y, sr = sf.read(args.vocals); y = y.mean(1) if y.ndim > 1 else y
    n = 1024; win = np.hanning(n); fr = np.fft.rfftfreq(n, 1 / sr); lo = (fr >= 250) & (fr <= 2500); hi = (fr >= 4000) & (fr <= 9000)
    for i in args.word:
        w = ws[i]; t1 = ws[i + 1]["start"] if i + 1 < len(ws) else w["end"]
        f0 = max(0, round((w["start"] - E["start"]) * fps - lead))
        rows = []
        for t in np.arange(w["start"] - 0.06, t1 + 0.03, 0.01):
            k = int((t - args.offset) * sr); seg = y[k:k + n]
            if len(seg) < n: break
            S = np.abs(np.fft.rfft(seg * win)) ** 2
            rows.append((t, 10 * np.log10(S[lo].sum() + 1e-9), 10 * np.log10(S[hi].sum() + 1e-9)))
        mx = max(r[1] for r in rows)
        print(f"\n== {args.edit}[{i}] {w['text']!r}  starts {w['start']:.3f}s = frame {f0}; next word {t1:.3f}s")
        print("   time   frame  +off  vowel band                    hiss")
        for t, v, h in rows:
            f = round((t - E["start"]) * fps - lead)
            print(f"{t:8.2f} {f:6d} {f - f0:5d}  {'#' * max(0, int((v - mx + 40) / 1.5)):<28}| {'+' * max(0, int((h - mx + 45) / 2))}")


if __name__ == "__main__":
    main()
