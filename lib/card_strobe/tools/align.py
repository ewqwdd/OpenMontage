"""Forced alignment: the user's lyric file (CORRECT text, ROUGH times) -> the same file with real word times.

The user's lyric tool exports {"words": [{"row", "start", "end", "text"}]}. The text, rows and order are
right; the times are not (on «mefedron master 4» every word was late by 0.30 s on average, up to 1.56 s,
and the scatter inside a row was 0.13 s). This tool keeps every word and its spelling and only moves the
times, the method that held up on that track (see skills/creative/card-strobe.md, "Lyrics"):

1. vocal stem: demucs htdemucs (--demucs) or a stem you pass (--stem). The full mix also works, worse.
2. MMS_FA forced alignment (torchaudio, the multilingual uroman CTC model) of the known text, Cyrillic
   romanised. Pass 1 aligns the whole text at once (a `*` token between rows absorbs ad-libs, samples and
   untexted vocals), so no row can drift. Pass 2 re-aligns each row in a window from 0.4 s before its
   pass-1 start to just after the next row's pass-1 start, chained so rows can't overlap. The rough
   times only bound the search (the first row - 3 s .. the last row + 3 s) and flag big moves.
3. onset refinement on the stem: a 5 ms energy-rise novelty in two bands (150-8k and 3-8k). Where an onset
   and MMS agree within 40 ms the word start is their mean (conf 0.9); where MMS is unsure (score < 0.2)
   and an onset lies up to 120 ms BEFORE it, the onset (conf 0.75: a short "Эй," after a gap); else MMS alone
   (conf 0.7: legato joins like "Я люблю" have no acoustic boundary).
4. words with 3+ vowels get `syllables` (onsets from the MMS character spans), for syllable card swaps.

It prints (and writes to <out>.report.json) the words to check by ear: a low MMS score, no onset, or a
big move from the rough time. Spot-check those on the stem; fix by hand in the output file.

Needs torch + torchaudio (+ demucs for --demucs), which the repo .venv does not have. One-time setup:
    uv venv ~/.cache/card_strobe_align && uv pip install --python ~/.cache/card_strobe_align torch torchaudio demucs
Run (from the repo root):
    ~/.cache/card_strobe_align/bin/python -m lib.card_strobe.tools.align --audio song.mp3 --words words.json \\
        --out ~/Downloads/<project>/words_aligned.json [--demucs | --stem vocals.wav]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

SR = 16000
TR = dict(а="a", б="b", в="v", г="g", д="d", е="e", ё="yo", ж="zh", з="z", и="i", й="y", к="k", л="l", м="m",
          н="n", о="o", п="p", р="r", с="s", т="t", у="u", ф="f", х="kh", ц="ts", ч="ch", ш="sh", щ="shch", ъ="",
          ы="y", ь="", э="e", ю="yu", я="ya")
VOWELS = set("аеёиоуыэюяaeiouy")


def token(s):
    """lowercase letters only (Cyrillic and Latin)"""
    return re.sub(r"[^а-яёa-z]", "", s.lower())


def romanise(t):
    return "".join(TR.get(c, c) for c in t)


def load_words(path):
    """the user's file ({"words": [...]}, or a bare list) -> (top-level dict, words with row/text/start)"""
    raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    top = raw if isinstance(raw, dict) else {"words": raw}
    words = []
    for w in top["words"]:
        words.append(dict(w, row=int(w.get("row", w.get("line", 0))), text=str(w.get("text", w.get("word", ""))),
                          start=float(w["start"])))
    return top, words


def audio16(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.3f}"]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()


def demucs_vocals(path, out_wav):
    """htdemucs vocal stem (44.1 kHz stereo in, written to out_wav)"""
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "2", "-ar", "44100",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = torch.tensor(np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy())
    m = get_model("htdemucs")
    m.eval()
    ref = x.mean(0)
    with torch.no_grad():
        out = apply_model(m, ((x - ref.mean()) / ref.std())[None], device="cpu", shifts=1, split=True, overlap=0.25,
                          progress=False)[0]
    voc = (out[m.sources.index("vocals")] * ref.std() + ref.mean()).numpy().T.astype(np.float32)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "f32le", "-ar", "44100", "-ac", "2", "-i", "-",
                    str(out_wav)], input=voc.tobytes(), check=True)
    return out_wav


# ---------------------------------------------------------------- MMS forced alignment
class MMS:
    def __init__(self):
        import torch
        from torchaudio.pipelines import MMS_FA
        self.torch = torch
        self.model = MMS_FA.get_model(with_star=True)
        self.model.eval()
        self.dict = MMS_FA.get_dict(star="*")

    def emissions(self, x):
        with self.torch.inference_mode():
            em, _ = self.model(self.torch.tensor(x)[None])
        return em[0], em.shape[1] / (len(x) / SR)

    def align(self, em, fps, t0, t1, texts, rows=None):
        """forced alignment of texts inside t0..t1; a star token at both ends and between rows"""
        import torchaudio.functional as F
        torch = self.torch
        e = em[int(t0 * fps):int(t1 * fps)]
        seq, wm = [self.dict["*"]], [-1]
        for k, t in enumerate(texts):
            if rows is not None and k and rows[k] != rows[k - 1]:
                seq.append(self.dict["*"])
                wm.append(-1)
            for c in romanise(token(t)):
                if c in self.dict:
                    seq.append(self.dict[c])
                    wm.append(k)
        seq.append(self.dict["*"])
        wm.append(-1)
        al, sc = F.forced_align(e[None], torch.tensor([seq], dtype=torch.int32), blank=0)
        spans = F.merge_tokens(al[0], sc[0].exp())
        out = []
        for k in range(len(texts)):
            ts = [s for s, m in zip(spans, wm) if m == k]
            if not ts:
                out.append(None)
                continue
            out.append(dict(start=t0 + ts[0].start / fps, end=t0 + ts[-1].end / fps,
                            score=float(np.mean([s.score for s in ts])), chars=[t0 + s.start / fps for s in ts]))
        return out


# ---------------------------------------------------------------- onsets
def onset_peaks(x, hop=80, win=512, thr=3.0):
    """5 ms energy-rise novelty (150-8k level and 3-8k level, 20 ms lag) -> (peak times, peak dB)"""
    n = (len(x) - win) // hop + 1
    idx = np.arange(win)[None] + hop * np.arange(n)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * np.hanning(win), axis=1)) ** 2
    f = np.fft.rfftfreq(win, 1 / SR)
    t = np.arange(n) * hop / SR + win / 2 / SR
    rms = 10 * np.log10(S[:, (f > 150) & (f < 8000)].sum(1) + 1e-9)
    hf = 10 * np.log10(S[:, (f > 3000) & (f < 8000)].sum(1) + 1e-9)

    def sm(v):
        return np.convolve(v, np.ones(3) / 3, "same")
    r, h = sm(np.maximum(rms, rms.max() - 60)), sm(np.maximum(hf, hf.max() - 60))
    lag = 4
    nov = np.zeros_like(r)
    nov[lag:] = np.maximum(np.maximum(r[lag:] - r[:-lag], 0), 0.7 * np.maximum(h[lag:] - h[:-lag], 0))
    pk = [i for i in range(1, len(nov) - 1) if nov[i] >= nov[i - 1] and nov[i] > nov[i + 1] and nov[i] > thr]
    return t[pk] - 0.010, nov[pk]


def syllables(tok, chars):
    """syllable onsets of a word with 3+ vowels from its MMS character times"""
    if sum(c in VOWELS for c in tok) < 3 or not chars:
        return None
    pos, k = [], 0
    for c in tok:
        pos.append(k)
        k += len(romanise(c))
    out = []
    for j, c in enumerate(tok):
        if c in VOWELS:
            on = j - 1 if j > 0 and tok[j - 1] not in VOWELS else j
            out.append(round(chars[min(pos[on], len(chars) - 1)], 3))
    return sorted(out)


# ---------------------------------------------------------------- main
def align(audio, words_path, out, stem=None, use_demucs=False, margin=3.0, log=print):
    top, W = load_words(words_path)
    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    if stem:
        src, kind = stem, "stem"
    elif use_demucs:
        log("demucs htdemucs vocal stem ...")
        src, kind = demucs_vocals(audio, out.with_suffix(".vocals.wav")), "demucs"
    else:
        src, kind = audio, "mix"
        log("WARNING: aligning on the full mix (pass --demucs or --stem for better onsets)")
    x = audio16(src)
    dur = len(x) / SR
    mms = MMS()
    em, fps = mms.emissions(x)
    pt, pv = onset_peaks(x)
    order = sorted(range(len(W)), key=lambda i: (W[i]["start"], i))
    W = [W[i] for i in order]
    g0 = max(0.0, W[0]["start"] - margin)
    g1 = min(dur, max(w["start"] for w in W) + margin)
    log(f"pass 1: whole text in {g0:.2f}-{g1:.2f} s")
    glob = mms.align(em, fps, g0, g1, [w["text"] for w in W], [w["row"] for w in W])
    rows = []
    for i, w in enumerate(W):
        if not rows or rows[-1][0] != w["row"]:
            rows.append((w["row"], []))
        rows[-1][1].append(i)

    def g_start(ids):
        return next((glob[i]["start"] for i in ids if glob[i]), W[ids[0]]["start"])

    res, prev_end = [None] * len(W), None
    for k, (r, ids) in enumerate(rows):
        s0 = max(0.0, g_start(ids) - 0.4)
        if prev_end is not None:
            s0 = max(s0, prev_end - 0.1)
        if k + 1 < len(rows):
            s1 = g_start(rows[k + 1][1]) + 0.15
        else:
            s1 = max([glob[i]["end"] for i in ids if glob[i]] or [W[ids[-1]]["start"]]) + 1.5
        s1 = min(dur, max(s1, s0 + 0.5))
        al = mms.align(em, fps, s0, s1, [W[i]["text"] for i in ids])
        for i, a in zip(ids, al):
            res[i] = a or glob[i]
        done = [a for a in al if a]
        if done:
            prev_end = done[-1]["end"]
    report, new = [], []
    for i, w in enumerate(W):
        a = res[i]
        ev = dict(i=i, row=w["row"], text=w["text"], rough=w["start"])
        if a is None:
            ev.update(start=w["start"], method="rough (no letters to align)", conf=0.3)
        else:
            sel = np.where(np.abs(pt - a["start"]) <= 0.12)[0]
            best = max(sel, key=lambda j: pv[j] * np.exp(-0.5 * ((pt[j] - a["start"]) / 0.06) ** 2), default=None)
            on = None if best is None else float(pt[best])
            if on is not None and abs(on - a["start"]) <= 0.04:
                st, method, conf = (a["start"] + on) / 2, "mms+onset", 0.9
            elif on is not None and on < a["start"] and a["score"] < 0.2:   # MMS late + unsure (a short "Эй,"
                # after a gap); an onset AFTER the MMS start is usually the next syllable of a legato word
                st, method, conf = on, "onset", 0.75
            else:
                st, method, conf = a["start"], "mms", 0.7
            ev.update(start=round(st, 3), mms=round(a["start"], 3), mms_end=round(a["end"], 3),
                      score=round(a["score"], 3),
                      onset=None if on is None else round(on, 3), method=method, conf=conf)
            sy = syllables(token(w["text"]), a["chars"])
            if sy:
                sy[0] = round(st, 3)
                ev["syllables"] = sy
        ev["check"] = bool(ev["conf"] < 0.9 and (ev.get("score", 0) < 0.1 or abs(ev["start"] - w["start"]) > 0.6))
        report.append(ev)
    for k, (w, ev) in enumerate(zip(W, report)):
        nxt = report[k + 1]["start"] if k + 1 < len(report) and report[k + 1]["row"] == w["row"] else None
        end = ev.get("mms_end", ev["start"] + 0.3)
        if nxt is not None:
            end = min(end, nxt)
        nw = {kk: v for kk, v in w.items() if kk not in ("start", "end", "syllables")}
        nw.update(start=ev["start"], end=round(max(end, ev["start"] + 0.04), 3))
        if "syllables" in ev:
            nw["syllables"] = ev["syllables"]
        new.append(nw)
    d = np.array([ev["start"] - ev["rough"] for ev in report])
    stats = dict(source=kind, words=len(W), mean_shift=round(float(d.mean()), 3),
                 median_abs_shift=round(float(np.median(np.abs(d))), 3), max_abs_shift=round(float(np.abs(d).max()), 3),
                 mms_plus_onset=sum(ev["method"] == "mms+onset" for ev in report),
                 to_check=[f"{ev['i']} {ev['text']} {ev['start']}" for ev in report if ev["check"]])
    top = dict(top, words=new)
    out.write_text(json.dumps(top, ensure_ascii=False, indent=1), encoding="utf-8")
    rep = json.dumps(dict(stats=stats, words=report), ensure_ascii=False, indent=1)
    out.with_suffix(".report.json").write_text(rep, encoding="utf-8")
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(prog="card_strobe.tools.align")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--words", required=True, help="the user's lyric file: correct text, rough times")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stem", help="a vocal stem to align on (better than the mix)")
    ap.add_argument("--demucs", action="store_true", help="separate the vocal stem with demucs htdemucs first")
    ap.add_argument("--margin", type=float, default=3.0, help="s searched outside the rough first/last word")
    a = ap.parse_args(argv)
    st = align(a.audio, a.words, a.out, a.stem, a.demucs, a.margin)
    print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
