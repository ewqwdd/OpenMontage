"""Plan a glitch-drop edit for a new song: audio + timed words + clips -> timeline.json.

  .venv/bin/python -m lib.glitch_drop.tools.plan --audio song.m4a --words words.json \
      --clips a.mp4 b.mp4 c.mp4 ... --drop-clip fast.mp4 --out projects/<id>/timeline.json \
      [--start S --end S] [--drop SEC] [--red WORD | --no-red] [--grade 45]

words.json = [{"line": 0, "word": "я", "start": 0.0}, ...] in seconds of the ORIGINAL audio (the
vhs_lyrics `align` output works as is). One `line` = one sung breath-phrase from the user's lyrics.

What the planner decides (the grammar, lib/glitch_drop/grammar.py):
- tempo, beat grid and the drop (tools/music.py; --drop overrides it, snapped to the nearest beat);
- intro lines = phrases before the drop, lowercase, <= 25 chars (split at the biggest breath gap);
  a phrase that straddles the drop is cut there; drop lines = CAPS, <= 17 chars;
- red word = the last word of the excerpt (or --red), alone on its own line, held to the end;
- one clip per intro line (cycled from --clips), a dissolve of ~0.6 beat (6-12 frames) ending on
  the line's first syllable; one clip (--drop-clip) for the whole drop;
- the drop schedule: reference glitch cells warped onto the beat grid, flash on the 808 hits,
  A/B/C colour rotation, INV layer on for the first 3 cells and the red cell.
Writes timeline.json and plan_report.json (analysis + the cell table) next to it.
"""
import argparse
import json
from pathlib import Path

from .. import grammar
from ..util import ASSETS
from . import music


def load_words(path):
    ws = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for w in ws:
        out.setdefault(int(w["line"]), []).append((float(w["start"]), str(w["word"])))
    return [sorted(v) for _, v in sorted(out.items())]


def plan(audio, words, clips, drop_clip, out, start=0.0, end=None, drop=None, red=None, no_red=False,
         grade=45, fps=30, clip_offset=0.0):
    an = music.analyse(audio, None if drop is None else drop - start, start, end)
    dur = an["duration"]
    end = start + dur
    P = an["period"]
    t_drop = an["drop"]["time"]
    hits = [tuple(h) for h in an["low_hits"]]
    lines = [[(t - start, w) for t, w in L if start <= t < end] for L in words]
    lines = [L for L in lines if L]

    # cut phrases at the drop: the drop section starts on its first frame
    G = int(t_drop * fps) + grammar.DROP_LAG
    tG = G / fps
    intro, drops = [], []
    for L in lines:
        a = [(t, w) for t, w in L if t < tG - 0.5 / fps]
        b = [(t, w) for t, w in L if t >= tG - 0.5 / fps]
        if a:
            intro.append(a)
        if b:
            drops.append(b)
    if not intro or not drops:
        raise SystemExit(f"drop at {t_drop:.2f}s leaves no lines on one side; pass --drop")

    # red word -> own line, last
    red_t = None
    if not no_red:
        flat = [(i, j) for i, L in enumerate(drops) for j, (_, w) in enumerate(L)]
        pick = flat[-1]
        if red:
            m = [(i, j) for i, j in flat if drops[i][j][1].lower().strip(".,!?") == red.lower()]
            pick = m[-1] if m else pick
        i, j = pick
        word = drops[i][j]
        before, after = drops[i][:j], drops[i][j + 1:]
        drops = drops[:i] + ([before] if before else []) + [[word] + after] + drops[i + 1:]
        red_t = word[0]

    intro = [p for L in intro for p in grammar.split_line(L, grammar.MAX_CHARS[0])]
    dl = []
    for k, L in enumerate(drops):
        is_red = red_t is not None and L[0][0] == red_t
        dl += [(p, is_red and q == 0) for q, p in enumerate([L] if is_red else grammar.split_line(L, grammar.MAX_CHARS[1]))]

    xf = grammar.crossfade(P, fps)
    tl_lines = []
    for i, L in enumerate(intro):
        s = 0 if i == 0 else int(round(L[0][0] * fps))
        prev_s = 0 if i == 0 else (0 if i == 1 else int(round(intro[i - 1][0][0] * fps)))
        tl_lines.append(dict(words=[[round(t, 4), w.lower()] for t, w in L],
                             clip=str(clips[i % len(clips)]), offset=clip_offset,
                             xf=0 if i == 0 else min(xf, max(0, s - prev_s - 2)),
                             grade={"target": grade}))
    for k, (L, is_red) in enumerate(dl):
        words_ = [[round(max(t, tG), 4), w.upper()] for t, w in L]
        d = dict(words=words_)
        if is_red:
            d["red"] = True
        tl_lines.append(d)

    n = int(round(dur * fps))
    G2, steps, cells = grammar.drop_schedule(ASSETS / "patterns" / "reference_drop.txt", fps, t_drop, P, n,
                                             red_time=red_t, low_hits=hits)
    assert G2 == G
    tl = {
        "about": f"glitch-drop edit planned from {Path(audio).name}: {an['tempo']} BPM, drop {t_drop:.3f}s",
        "fps": fps, "size": [1440, 1080], "duration": round(n / fps, 4),
        "audio": {"path": str(Path(audio).resolve()), "start": start, "duration": dur, "fade_out": 0.03},
        "drop": {"time": round(G / fps, 4), "schedule": steps,
                 "bg": {"clip": str(Path(drop_clip).resolve()), "offset": 0.0, "stretch": 1.37}},
        "lines": tl_lines,
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    rep = dict(tempo=an["tempo"], period=P, beat_frames=round(P * fps, 2), drop=an["drop"], drop_frame=G,
               cell_beats=grammar.cell_beats(P), cells=cells, red=red_t, crossfade=xf,
               intro_lines=[" ".join(w for _, w in L) for L in intro],
               drop_lines=[" ".join(w for _, w in L) + (" [red]" if r else "") for L, r in dl])
    (out.parent / "plan_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return tl, rep


def main(argv=None):
    ap = argparse.ArgumentParser(prog="glitch_drop.tools.plan")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--words", required=True)
    ap.add_argument("--clips", nargs="+", required=True)
    ap.add_argument("--drop-clip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--drop", type=float)
    ap.add_argument("--red")
    ap.add_argument("--no-red", action="store_true")
    ap.add_argument("--grade", type=float, default=45)
    ap.add_argument("--clip-offset", type=float, default=0.0)
    a = ap.parse_args(argv)
    _, rep = plan(a.audio, load_words(a.words), a.clips, a.drop_clip, a.out, a.start, a.end, a.drop, a.red,
                  a.no_red, a.grade, clip_offset=a.clip_offset)
    print(f"{rep['tempo']} BPM, drop frame {rep['drop_frame']}, cell = {rep['cell_beats']} beats, "
          f"{len(rep['cells'])} cells, crossfade {rep['crossfade']} fr")
    print("intro:", " / ".join(rep["intro_lines"]))
    print("drop: ", " / ".join(rep["drop_lines"]))
    for c in rep["cells"]:
        print(f"  cell @{c['start']} {c['frames']}fr {c['colour']} inv={c['inv']} {c['template']} flash~{c['flash']}")


if __name__ == "__main__":
    main()
