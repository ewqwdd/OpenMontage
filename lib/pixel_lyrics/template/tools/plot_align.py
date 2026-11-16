"""Plot the vocal-stem spectrogram + RMS with word marks, one image per lyric line.

    .venv-audio/Scripts/python tools/plot_align.py analysis --offset 11 [--user words.json] [--final productions/words.final.json]

Red = forced alignment (analysis/words.json), green dashes = the user's rough timings, cyan = final words.
A word start must sit on the rise of its first syllable (or on its leading consonant noise).
Needs matplotlib in the audio venv:  uv pip install --python .venv-audio/Scripts/python.exe matplotlib
"""
import argparse, json
from pathlib import Path
import numpy as np, librosa, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("workdir"); ap.add_argument("--offset", type=float, default=0.0)
ap.add_argument("--user"); ap.add_argument("--final")
args = ap.parse_args()
wd = Path(args.workdir); OFF = args.offset
user = json.loads(Path(args.user).read_text(encoding="utf-8"))["words"] if args.user else []
fa = json.loads((wd / "words.json").read_text(encoding="utf-8"))
final = json.loads(Path(args.final).read_text(encoding="utf-8"))["words"] if args.final else None
y, sr = librosa.load(wd / "sep/htdemucs/orig/vocals.wav", sr=22050)
d, _ = librosa.load(wd / "sep/htdemucs/orig/drums.wav", sr=22050)
hop = 128
S = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=1024, hop_length=hop)), ref=np.max)
rms = librosa.feature.rms(y=y, frame_length=512, hop_length=hop)[0]
drms = librosa.onset.onset_strength(y=d, sr=sr, hop_length=hop)
tt = np.arange(len(rms)) * hop / sr
out = wd / "plots"; out.mkdir(exist_ok=True)
lines = sorted({w["line"] for w in fa})
for li in lines:
    ws = [w for w in fa if w["line"] == li]
    t0, t1 = ws[0]["start"] - 0.5, ws[-1]["end"] + 0.4
    fig, ax = plt.subplots(3, 1, figsize=(22, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1.2, 0.8]})
    f1 = int(5000 / (sr / 1024))
    ax[0].imshow(S[:f1], origin="lower", aspect="auto", extent=[0, len(y) / sr, 0, 5000], cmap="magma", vmin=-60, vmax=0)
    m = (tt >= t0) & (tt <= t1)
    ax[1].plot(tt[m], rms[m], "k", lw=1); ax[2].plot(tt[m], drms[m], "b", lw=1)
    for a in ax[:2]:
        for w in ws:
            a.axvline(w["start"], color="red", lw=1.6)
            a.axvline(w["end"], color="red", lw=0.6, ls=":")
        for w in user:
            if t0 <= w["start"] - OFF <= t1: a.axvline(w["start"] - OFF, color="lime", lw=1.2, ls="--")
        if final:
            for w in final:
                if t0 <= w["start"] - OFF <= t1: a.axvline(w["start"] - OFF, color="cyan", lw=2.2)
    for w in ws:
        ax[0].text(w["start"] + 0.01, 4600, w["word"], color="white", fontsize=13, rotation=0)
    if final:
        for w in final:
            if t0 <= w["start"] - OFF <= t1: ax[0].text(w["start"] - OFF + 0.01, 4100, w["text"], color="cyan", fontsize=13)
    ax[0].set_xlim(t0, t1); ax[0].set_xticks(np.arange(np.floor(t0 * 10) / 10, t1, 0.1))
    ax[0].tick_params(axis="x", labelbottom=True, labelsize=7)
    ax[2].set_xticks(np.arange(np.floor(t0 * 10) / 10, t1, 0.1)); ax[2].tick_params(axis="x", labelsize=7, rotation=90)
    ax[0].set_title(f"line {li}  (excerpt time; track = +{OFF}s)  red=FA  green=user json  cyan=final")
    plt.tight_layout(); plt.savefig(out / f"line{li}{'_final' if final else ''}.png", dpi=70); plt.close()
print("ok", out)
