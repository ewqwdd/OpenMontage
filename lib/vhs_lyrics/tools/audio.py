"""Audio analysis for a new track: stems, ASR draft, beat grid, vocal onsets, lyric alignment.

Runs in the audio venv (torch-CPU, demucs, faster-whisper, librosa):
  .venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio prep  <url|audio|video> <workdir>
  .venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio align <workdir> [--chunks chunks.json]

prep  -> workdir/original.m4a, orig.wav, sep/htdemucs/orig/{vocals,drums,bass,other}.wav,
         asr.txt (whisper draft: '#SEG t0 t1 text' + 't0 t1 prob word'), grid.json
         (tempo, beats, vocal onsets). Read asr.txt only to find line windows: whisper
         mishears slang and names, so the real lyrics must come from the user.
align -> needs workdir/lyrics.txt (one sung line per line, only what the clip contains);
         writes words.json [{line, word, start, end, score}] by torchaudio MMS_FA forced
         alignment on the vocal stem. With --chunks (list of [[line indices], t0, t1], windows
         taken from asr.txt segments) every chunk is aligned inside its window, which stops
         drift on distorted/shouted vocals. Scores < 0.05 = check that word against the vocal
         onsets in grid.json (and the ASR word times) and fix it by hand.
Models are cached in the user profile (htdemucs, whisper medium, MMS_FA): no cost, offline.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
              ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t",
               "u", "f", "h", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))


def prep(src, wd):
    wd.mkdir(parents=True, exist_ok=True)
    if str(src).startswith("http"):
        subprocess.run(["yt-dlp", "-o", str(wd / "source.%(ext)s"), "-f", "mp4/best", src], check=True)
        src = next(wd.glob("source.*"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-c:a", "aac", "-b:a", "256k",
                    str(wd / "original.m4a")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wd / "original.m4a"), "-ar", "44100", "-ac", "2",
                    str(wd / "orig.wav")], check=True)
    subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs", "-o", str(wd / "sep"), str(wd / "orig.wav")], check=True)
    stems = wd / "sep" / "htdemucs" / "orig"

    from faster_whisper import WhisperModel
    m = WhisperModel("medium", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(stems / "vocals.wav"), language="ru", word_timestamps=True, vad_filter=False,
                           beam_size=5, condition_on_previous_text=False)
    lines = []
    for s in segs:
        lines.append("#SEG %.2f %.2f %s" % (s.start, s.end, s.text.strip()))
        lines += ["%.2f %.2f %.2f %s" % (w.start, w.end, w.probability, w.word.strip()) for w in s.words]
    (wd / "asr.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    import librosa
    import numpy as np
    sr, H = 22050, 128
    d, _ = librosa.load(stems / "drums.wav", sr=sr)
    v, _ = librosa.load(stems / "vocals.wav", sr=sr)
    env = librosa.onset.onset_strength(y=d, sr=sr, hop_length=H)
    tempo, beats = librosa.beat.beat_track(onset_envelope=env, sr=sr, hop_length=H, units="time")
    period = float(np.median(np.diff(beats))) if len(beats) > 1 else 60 / float(np.atleast_1d(tempo)[0])
    venv = librosa.onset.onset_strength(y=v, sr=sr, hop_length=H)
    von = librosa.onset.onset_detect(onset_envelope=venv, sr=sr, hop_length=H, units="time", delta=0.08)
    rms = librosa.feature.rms(y=v, hop_length=441)[0]
    voiced = np.flatnonzero(rms > 0.02 * rms.max() + 0.01)
    grid = {"tempo": float(np.atleast_1d(tempo)[0]), "beat_period": period,
            "beats": [round(float(b), 3) for b in beats], "vocal_onsets": [round(float(t), 3) for t in von],
            "vocal_start": round(float(voiced[0]) * 0.02, 2) if len(voiced) else 0,
            "vocal_end": round(float(voiced[-1]) * 0.02, 2) if len(voiced) else 0,
            "duration": round(len(v) / sr, 3)}
    (wd / "grid.json").write_text(json.dumps(grid, indent=1), encoding="utf-8")
    print(f"prep: tempo {grid['tempo']:.1f}, vocal {grid['vocal_start']}-{grid['vocal_end']} s of {grid['duration']} s")
    print("\n".join(l for l in lines if l.startswith("#SEG")))


def align(wd, chunks=None):
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    lines = [l.split() for l in (wd / "lyrics.txt").read_text(encoding="utf-8").lower().splitlines() if l.strip()]
    if chunks is None:
        chunks = [[list(range(len(lines))), 0, None]]
    b = torchaudio.pipelines.MMS_FA
    model, tok, al, R = b.get_model(), b.get_tokenizer(), b.get_aligner(), b.sample_rate
    y, sr = sf.read(wd / "sep" / "htdemucs" / "orig" / "vocals.wav")
    y = y.mean(1) if y.ndim > 1 else y
    wav = torchaudio.functional.resample(torch.tensor(y, dtype=torch.float32)[None], sr, R)
    out = []
    for li, t0, t1 in chunks:
        words = [(l, w) for l in li for w in lines[l]]
        rom = ["".join(TR.get(c, c) for c in w if c in TR or c.isascii() and c.isalpha()) for _, w in words]
        seg = wav[:, int(t0 * R): int(t1 * R) if t1 else None]
        with torch.inference_mode():
            em, _ = model(seg)
            em = torch.log_softmax(em, -1)
        spans = al(em[0], tok(rom))
        ratio = seg.shape[1] / em.shape[1] / R
        for (l, wd_), sp in zip(words, spans):
            out.append({"line": l, "word": wd_, "start": round(t0 + sp[0].start * ratio, 3),
                        "end": round(t0 + sp[-1].end * ratio, 3),
                        "score": round(float(np.mean([x.score for x in sp])), 3)})
    (wd / "words.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for w in out:
        print("%2d %7.3f %7.3f %.2f %s%s" % (w["line"], w["start"], w["end"], w["score"], w["word"],
                                           "   <- check" if w["score"] < 0.05 else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vhs_lyrics.tools.audio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("src")
    p.add_argument("workdir")
    a = sub.add_parser("align")
    a.add_argument("workdir")
    a.add_argument("--chunks")
    args = ap.parse_args(argv)
    if args.cmd == "prep":
        prep(args.src, Path(args.workdir))
    else:
        align(Path(args.workdir), json.loads(Path(args.chunks).read_text()) if args.chunks else None)


if __name__ == "__main__":
    main()
