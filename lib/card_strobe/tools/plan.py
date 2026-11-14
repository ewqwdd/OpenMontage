"""Plan a card-strobe edit for a new song: audio + timed words + source moments -> timeline.json.

  .venv/bin/python -m lib.card_strobe.tools.plan --audio song.m4a --start S --end S --words words.json \
      --moments moments.json --out ~/Downloads/<project>/timeline.json \
      [--bpm 160] [--drop SEC] [--break A:B | --break none] [--card1 MASTER/MIND] [--card2 ZAE-/BAL] \
      [--end-card CALVIN/KLEIN] [--script-words доллар падал] [--cyrillic-cards] \
      [--style fused [--narrator serif|subs]] [--track track.json | --beat0 SEC] [--top 24]

Times on the command line and in words.json are seconds of the ORIGINAL audio file.

words.json   [{"line": 0, "word": "японский", "start": 47.286, "end": 48.05}, ...]; one `line` = one sung
             phrase of the user's lyrics (the vhs_lyrics `align` output fits as is). `end` is optional.
             The user's lyric-tool file {"words": [{"row", "start", "end", "text"}]} works as is: run it
             through tools/align.py first (its times are rough).
moments.json [{"src": "video.mp4", "t_in": 91.9, "t_out": 93.4, "subject_x": 0.42, "subject_y": 0.45,
               "kind": "face" | "action" | ..., "energy": 1-5, "desc": "..."}, ...]   (also "t"/"dur").
             The ORDER is the priority: moment 0 is the intro, the next ones are the verse clips (one per
             bar, cycled; repeats are fine), the burst samples all of them. A shot-list json without "src"
             works with --src video.mp4 (e.g. the `*_shots.json` files of a source review).
             A curated picks file {"picks": [{"src", "t_in", "t_out", "best_t", "square_crop": {"x", "size"},
             "kind": "hero_portrait", ...}]} (CURATED.json) works too: the square crop sets the framing,
             best_t the first in-point, hero_portrait counts as a face; --top N keeps the first N picks.

--track track.json  a beat analysis {"beat_period", "grid_origin", "low_hits": [{"t", "rel_db"}]} replaces
             the comb tempo and the low-hit detector (trap songs: the comb picks 2/3 or 1/2 tempo).
             --bpm B --beat0 SEC does the grid alone (SEC = any beat, original-audio seconds).
--style fused   the Mastermind skeleton fused with the first edit (lib/card_strobe/fused.py): a serif lead-in
             under a VHS window instead of the typed glyphs, a drop ramp (lift / wash / expo), Cyrillic
             captions under every card, the serif narrator instead of the tiny subtitles in verse B
             (--narrator subs keeps them), glitch accents on the strong 808s of verse B (clean clip heads,
             INV family first, face-safe ops), hue-safe inverts on warm clips, soft exposure strobes and
             the crimson word riding the whip.

What the planner decides (the rules are in lib/card_strobe/grammar.py):
- grid: tempo from lib.glitch_drop.tools.music (comb fit; pass --bpm when it picks a dotted / half
  tempo). DROP 1 = the strongest low (808) hit in the first 45 % of the excerpt, snapped to the beat.
- 808 gap (BREAK) = the first run of >= 3 eighths with the sub band 4 dB under the body median after
  the first card; its end = DROP 2. No gap -> no burst / second card (pass --break A:B to force one).
- intro: moment 0 in a mauve duotone, the first sung word typed in blocky glyphs, a band subtitle,
  2 mosaic frames, amber "lights on" 1.6 eighths before the drop.
- drop 1: bars white on the 808 frame, white 254 frame, hero card for 3 eighths (polarity 2,3,2,3...).
  Card text = the words sung inside it (a long word is split into two syllables), Latin caps.
- verse: one clip per bar on the half-note grid, rotating duotones; first half: pop words / clones /
  outline stack / hue cycle / 808 zoom; second half: tiny subtitles, outline word, exposure strobe,
  red pulses, bounces. 1-frame inverts on the strongest 808s.
- break: flash-cut burst, black frame, card 2 (line 1 alone 5 f, then both lines strobing).
- end: crimson card of the last line's last words alternating with footage, then a 5-frame whip.
Writes timeline.json and plan_report.json (grid, anchors, shot table, text events, warnings).
"""
import argparse
import json
from pathlib import Path

import numpy as np

from ...glitch_drop.tools import music
from .. import footage, timeline
from .. import grammar as g
from .. import text as tx

FPS = 30
SQ, MARGIN = 1080, 65
CV = SQ + 2 * MARGIN


# ===================================================================== inputs
def load_words(path):
    """kit words [{"line", "word", "start"}] or the user's lyric-tool file {"words": [{"row", "text", "start"}]}"""
    ws = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(ws, dict):
        ws = ws["words"]
    out = []
    for w in ws:
        d = {"line": int(w.get("line", w.get("row", 0))), "word": str(w.get("word", w.get("text", ""))).strip(),
             "start": float(w["start"]), "end": float(w["end"]) if w.get("end") is not None else None}
        if w.get("syllables"):
            d["syllables"] = [float(x) for x in w["syllables"]]
        out.append(d)
    return sorted(out, key=lambda w: w["start"])


FACE_KINDS = {"face", "hero_portrait", "portrait", "stare"}


def load_moments(path, src=None, top=None):
    ms = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(ms, dict):
        ms = ms.get("picks") or ms.get("moments") or []
    if top:
        ms = ms[:top]
    out = []
    for m in ms:
        s = m.get("src", src)
        if not s:
            raise SystemExit("moments need a 'src' (or pass --src video.mp4)")
        t_in = float(m.get("t_in", m.get("t", 0.0)))
        t_out = float(m.get("t_out", t_in + float(m.get("dur", 2.0))))
        kind = m.get("kind", "")
        d = dict(src=str(Path(s).expanduser().resolve()), t_in=t_in, t_out=t_out,
                 sx=float(m.get("subject_x", 0.5)), sy=float(m.get("subject_y", 0.45)),
                 kind="face" if kind in FACE_KINDS else kind, energy=float(m.get("energy", 3)),
                 desc=m.get("desc", m.get("key", "")))
        sq = m.get("square_crop")
        if sq and "subject_x" not in m:
            d["square"] = (float(sq["x"]), float(sq.get("size", 1080)))
        if m.get("best_t") is not None:
            d["best"] = float(m["best_t"])
        out.append(d)
    if not out:
        raise SystemExit("no moments")
    return out


# ===================================================================== audio
def load_track(path, start, end):
    """a beat analysis json -> (period s, phase s rel. to start, low hits [(t rel., strength)])"""
    tr = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    P = float(tr.get("beat_period") or 60.0 / float(tr["tempo"]))
    ph = (float(tr.get("grid_origin", 0.0)) - start) % P
    hits = []
    for h in tr.get("low_hits", []):
        t = float(h["t"] if isinstance(h, dict) else h[0])
        if start <= t < end:              # strength: within 2 dB of the loudest hit counts as strong (>= 2)
            st = 3.0 + float(h.get("rel_db", 0.0)) / 2 if isinstance(h, dict) else float(h[1])
            hits.append([round(t - start, 3), round(st, 2)])
    return P, ph, hits


def analyse(audio, start, end, bpm=None, drop=None, brk=None, gap_db=g.GAP_DB, track=None, beat0=None):
    """grid + anchors of the excerpt, all times relative to `start`"""
    x = music.load(audio, start=start, end=end)
    F = music.features(x)
    dur = len(x) / music.SR
    hits = None
    if track:
        P, ph, hits = load_track(track, start, end)
    elif bpm and beat0 is not None:
        P = 60.0 / bpm
        ph = (beat0 - start) % P
    else:
        P, ph = music.tempo(F, (bpm * 0.98, bpm * 1.02) if bpm else (70, 170))
    beats = np.arange(ph, dur + 1e-6, P)
    if hits is None:
        hits = music.low_hits(F)
    E = P / 2
    note = []
    if drop is None:
        early = [h for h in hits if h[0] < g.DROP_SEARCH * dur] or hits
        t_hit = max(early, key=lambda h: h[1])[0]
        b = float(beats[np.argmin(np.abs(beats - t_hit))])
        drop = b if abs(b - t_hit) <= 0.1 else t_hit
        note.append(f"drop 1 = strongest early low hit {t_hit:.3f}s -> beat {drop:.3f}s")
    else:
        note.append(f"drop 1 forced at {drop:.3f}s")
    gaps = g.find_gaps(F["t"], F["E_sub"], drop, drop + 4 * E, dur - 4 * P, E, gap_db)
    if brk == "none":
        gap = None
    elif brk is not None:
        gap = (brk[0], brk[1], None)
        note.append(f"break forced {brk[0]:.3f}-{brk[1]:.3f}s")
    else:
        gap = gaps[0] if gaps else None
    strong = sorted(h for h in hits if h[1] >= max(2.0, np.percentile([h[1] for h in hits], 70)))
    return dict(duration=dur, tempo=round(60 / P, 2), period=P, phase=ph, eighth=E, beats=beats.tolist(),
                drop=float(drop), gap=gap, gaps=gaps, low_hits=hits, strong_hits=strong, notes=note)


# ===================================================================== helpers
class Moments:
    def __init__(self, ms):
        self.ms = ms
        self.dims = {}
        for m in ms:
            if m["src"] not in self.dims:
                w, h, _, _ = footage.probe(m["src"])
                self.dims[m["src"]] = (w, h)
            if "square" in m:                # curated square crop: its centre is the subject
                x, size = m["square"]
                m["sx"] = (x + size / 2) / self.dims[m["src"]][0]
        self.k = 0
        self.uses = {}

    def next(self, skip_first=True, prefer=None):
        if prefer:                       # the next moment of this kind in rotation order (rotation not advanced)
            for d in range(len(self.ms)):
                i = (self.k + d) % len(self.ms)
                if self.ms[i]["kind"] == prefer and not (skip_first and i == 0 and len(self.ms) > 1):
                    if d == 0:
                        self.k += 1
                    return i
        i = self.k % len(self.ms)
        if skip_first and len(self.ms) > 1 and i == 0:
            self.k += 1
            i = self.k % len(self.ms)
        self.k += 1
        return i

    def face(self):
        faces = [i for i, m in enumerate(self.ms) if m["kind"] == "face"]
        return max(faces, key=lambda i: self.ms[i]["energy"]) if faces else 0

    def offset(self, i, need):
        """start time inside moment i: later each time it is reused (repeats show new frames)"""
        m = self.ms[i]
        u = self.uses.get(i, 0)
        self.uses[i] = u + 1
        span = max(0.0, m["t_out"] - m["t_in"] - need)
        if u == 0 and "best" in m:           # first use: the curated best frame lands early in the shot
            return float(np.clip(m["best"] - min(0.3, need / 4), m["t_in"], m["t_in"] + span))
        return m["t_in"] + (span * (0.5 * u % 1.0) if span > 0 else 0.0)


def _clamp_center(q, zoom):
    lo, hi = SQ / 2 / zoom, CV - SQ / 2 / zoom
    return [round(float(np.clip(q[0], lo, hi)), 1), round(float(np.clip(q[1], lo, hi)), 1)]


def _width(text, role, cap):
    return tx.text_mask(text, role, round(tx.cap_size(role, cap), 1)).shape[1]


def _clean(w):
    return w.strip(" ,.!?;:—–-\"«»…")


# ===================================================================== plan
def plan(audio, start, end, words, moments, out, bpm=None, drop=None, brk=None, card1=None, card2=None,
         end_card=None, script_words=(), latin=True, gap_db=g.GAP_DB, edit_style="mastermind", narrator="serif",
         track=None, beat0=None):
    brk_rel = brk if brk in (None, "none") else (brk[0] - start, brk[1] - start)
    an = analyse(audio, start, end, bpm, None if drop is None else drop - start, brk_rel, gap_db, track, beat0)
    dur, P, E = an["duration"], an["period"], an["eighth"]
    Ef, Hf, BARf = E * FPS, 4 * E * FPS, 8 * E * FPS
    N = int(round(dur * FPS))
    d808 = an["drop"] * FPS
    warn = []
    M = Moments(moments)
    script_words = {s.lower() for s in script_words}

    # words -> excerpt frames (onset - 1)
    W_ = []
    for w in words:
        t = w["start"] - start
        if 0 <= t < dur:
            W_.append(dict(w, t=t, f=max(0, int(round(t * FPS)) - g.WORD_LEAD), text=_clean(w["word"])))
    W_ = [w for w in W_ if w["text"]]
    used = set()

    # ---------------------------------------------------------------- anchors
    W = int(round(an["drop"] * FPS)) + g.DROP_LAG
    c1a, c1b = W + 1, W + int(round(g.CARD1_E * Ef)) - 1
    def grid(a, b):
        return g.grid_points(d808, Hf, a, b)
    gp = [x for x in grid(c1b + 1, N) if int(round(x)) + g.CUT_LAG - c1b - 1 >= 2]
    cut = int(round(gp[0])) + g.CUT_LAG if gp else c1b + 3
    if cut - c1b - 1 > g.TAIL_MAX:
        cut = c1b + 3
    end_whip = N - len(g.WHIP_OUT)

    # end card: the last line's last <= 2 words
    end_words = []
    if W_:
        last_line = [w for w in W_ if w["line"] == W_[-1]["line"]][-2:]
        end_words = [w for w in last_line if cut + BARf * 0.5 <= w["f"] < end_whip - 4]
    end_a = end_words[0]["f"] if end_words else end_whip
    end_b = end_whip - 1

    gap = an["gap"]
    burst = None
    if gap and gap[0] * FPS > cut + BARf * 0.5 and gap[1] * FPS < end_a - Ef:
        ret = gap[1] * FPS
        c2a = int(round(ret - g.CARD2_LEAD_E * Ef))
        c2w = [w for w in W_ if ret - 2 * Ef <= w["f"] <= ret + Ef][:2]     # the word(s) across the return
        if c2w and c2w[0]["f"] < c2a:
            c2a = c2w[0]["f"]
        b0s = [x for x in grid(0, gap[0] * FPS)]
        b0 = int(round(b0s[-1])) + 2 if b0s else int(gap[0] * FPS)
        if c2a - 1 - b0 < 6:
            b0 = c2a - 7
        vb = [x for x in grid(ret + Ef, N)]
        vb0 = int(round(vb[0])) + g.CUT_LAG if vb else int(ret + 2 * Ef)
        if b0 > cut + 0.5 * BARf and vb0 < end_a - 0.5 * BARf:
            burst = dict(a=b0, black=c2a - 1, c2a=c2a, c2b=vb0 - 1, ret=ret, words=c2w)
        else:
            warn.append(f"808 gap {gap[0]:.2f}-{gap[1]:.2f}s too close to the drop or the end: no burst / card 2")
    elif gap:
        warn.append(f"808 gap {gap[0]:.2f}-{gap[1]:.2f}s outside the verse: ignored")

    # ---------------------------------------------------------------- sections -> clip spans
    def bars(a, b):
        """[a, b] split into ~1-bar clips with cuts on the half-note grid"""
        out, s = [], a
        while s <= b:
            nxt = [x for x in grid(s + BARf * 0.75, b + 1) if True]
            e = int(round(nxt[0])) + g.CUT_LAG - 1 if nxt else b
            if b - e < BARf * g.MIN_CLIP_BARS:
                e = b
            out.append((s, min(e, b)))
            s = min(e, b) + 1
        return out

    if burst:
        spans_a = bars(cut, burst["a"] - 1)
        spans_b = bars(burst["c2b"] + 1, end_a - 1) if end_a - 1 >= burst["c2b"] + 1 else []
    else:
        spans = bars(cut, end_a - 1) if end_a - 1 >= cut else []
        k = (len(spans) + 1) // 2 if len(spans) >= 2 else len(spans)
        spans_a, spans_b = spans[:k], spans[k:]

    # ---------------------------------------------------------------- builders
    clips, shots, text, subs, motion = {}, [], [], [], []
    inverts, report_shots = set(), []

    def window(role, mi, f0, f1, conform=None, offset=None):
        """clip window + time map for moment mi over frames f0..f1"""
        m = M.ms[mi]
        n = f1 - f0 + 1
        need = n / FPS
        t0 = M.offset(mi, need) if offset is None else offset
        avail = m["t_out"] - t0
        spec = {}
        if avail < need:
            if avail >= 0.5 * need:
                spec["speed"] = round(avail / need - 0.005, 3)
            else:
                spec["pingpong"] = [max(1, int(avail * FPS) - 1), 2]
                warn.append(f"moment {mi} ({m['t_in']:.2f}-{m['t_out']:.2f}s) is short for {n} frames: ping-pong")
        if conform:
            spec["conform"] = conform
        sw, sh = M.dims[m["src"]]
        ax = round(footage.subject_ax(sw, sh, m["sx"], CV), 3)
        name = f"{role}{len(clips)}"
        clips[name] = {"src": m["src"], "t0": round(t0, 3), "dur": round(min(need * spec.get("speed", 1), avail) + 0.12, 3),
                       "ax": ax, "ay": 0.5}
        subj = footage.subject_in_canvas(sw, sh, m["sx"], m["sy"], ax, 0.5, CV)
        return name, round(t0, 3), spec, subj

    def add_clip(role, mi, f0, f1, grade, camera=None, fx=None, conform=None, offset=None, section=""):
        name, t0, spec, subj = window(role, mi, f0, f1, conform, offset)
        s = {"kind": "clip", "f": [f0, f1], "clip": name, "t": t0, "grade": grade}
        s.update(spec)
        if grade in g.GAIN:
            s["gain"] = g.GAIN[grade]
        cam = dict(camera or {})
        z = cam.get("zoom", (cam.get("zoom_steps") or [[0, 1.0]])[0][1])
        if cam.get("center") == "subject":          # aim at the moment's subject, without black edges
            cam["center"] = _clamp_center(subj, z)
        if cam.get("about") == "subject":
            cam["about"] = [round(subj[0], 1), round(subj[1], 1)]
        if cam:
            s["camera"] = cam
        if fx:
            s["fx"] = fx
        shots.append(s)
        report_shots.append(dict(f=[f0, f1], kind="clip", section=section, grade=grade, moment=mi,
                                 src=Path(M.ms[mi]["src"]).name, t=t0, desc=M.ms[mi]["desc"][:60]))
        return s, subj

    def words_in(a, b):
        return [w for w in W_ if a <= w["f"] <= b and id(w) not in used]

    # ---------------------------------------------------------------- intro
    intro_w = words_in(0, W - 1)
    lights = max(1, W - int(round(g.LIGHTS_ON_E * Ef)))
    mi0 = 0
    if W < 6:
        warn.append(f"drop at frame {W}: no room for an intro")
        if W > 0:
            shots.append({"kind": "flat", "f": [0, W - 1], "value": 0})
        lights = W
    else:
        t_intro = M.offset(mi0, W / FPS)
        jump = [int(round(x)) for x in grid(12, lights - 10)]
        if lights >= 30 and jump:          # long intro: one jump cut on the half-note grid (ref3 A1 -> A2)
            j = min(jump, key=lambda x: abs(x - lights / 2))
            m0 = M.ms[mi0]
            t_jump = min(m0["t_out"] - (lights - j) / FPS, t_intro + j / FPS + 0.5)
            add_clip("intro", mi0, 0, j - 1, "mauve", conform=20, offset=t_intro, section="intro")
            add_clip("intro", mi0, j, lights - 1, "mauve", conform=20, offset=round(max(t_intro, t_jump), 3),
                     camera={"zoom": 1.25, "center": "subject"}, section="intro jump")
        else:
            add_clip("intro", mi0, 0, lights - 1, "mauve", conform=20, offset=t_intro, section="intro")
        s, _ = add_clip("intro", mi0, lights, W - 1, "amber", offset=round(t_intro + lights / FPS, 3),
                        section="lights on")
        s["gain_frames"] = {str(lights + k): v for k, v in enumerate(g.LIGHTS_GAIN[:2]) if lights + k < W}
    # typed glyphs: the intro words, a couple more characters every TYPE_EVERY frames
    steps = []
    for k, w in enumerate(intro_w[:2] if W >= 6 else []):
        word = "".join(ch for ch in w["text"].upper() if ch.isalnum())
        if not word:
            continue
        cap = g.TYPE_CAP[0] if len(word) >= 6 else g.TYPE_CAP[1]
        wpx = tx.blocky_mask(word, cap).shape[1]
        if wpx > 1000:
            cap = int(cap * 1000 / wpx)
        nxt = intro_w[k + 1]["f"] if k + 1 < len(intro_w) else W
        per = max(2, int(np.ceil(len(word) / 4)))
        a = 0 if k == 0 and w["f"] < 6 else w["f"]
        j = 0
        while True:
            f, n = a + j * g.TYPE_EVERY, min(len(word), (j + 1) * per)
            if j and f >= nxt:
                steps[-1][1] = word          # finish the word before the next one starts
                break
            steps.append([f, word[:n], cap])
            if n == len(word):
                break
            j += 1
    if steps and W > 0:
        text.append({"kind": "typing", "f": [0, W - 1], "font": "blocky", "at": [540, 540], "color": [250, 250, 250],
                     "steps": steps})
    if intro_w and W > 0:
        subs.append({"f": [0, W - 1], "style": "band", "words": [[w["f"], w["text"]] for w in intro_w]})
        used.update(id(w) for w in intro_w)
    mosaic = [f for f in ((intro_w[0]["f"] if intro_w else 0) + g.MOSAIC_AT + k for k in range(2)) if f < lights]

    # ---------------------------------------------------------------- drop 1: white + hero card
    shots.append({"kind": "flat", "f": [W, W], "value": 254})
    report_shots.append(dict(f=[W, W], kind="white", section="drop 1"))
    cw = words_in(W - 1, c1b)
    states = []
    if card1:
        parts = [p for p in card1.split("/") if p]
        for k, p in enumerate(parts):
            states.append((c1a + int(round(k * (c1b - c1a + 1) / len(parts))), p.upper()))
    else:
        if not cw:
            nxt = [w for w in W_ if w["f"] > c1b]
            cw = nxt[:1] if nxt else intro_w[-1:]
            warn.append("no word sung inside card 1: used the nearest word " + (cw[0]["text"] if cw else "-"))
        texts = [(w["f"], g.card_text(w["text"], latin)) for w in cw[:3]]
        if len(texts) == 1 and len(texts[0][1]) >= g.CARD_SPLIT_MIN:
            a_, b_ = g.split_syllables(texts[0][1])
            f2 = texts[0][0] if texts[0][0] > c1a + 3 else (c1a + c1b) // 2
            states = [(c1a, a_), (min(f2, c1b - 3), b_)]
        else:
            states = [(max(c1a, f) if k else c1a, t) for k, (f, t) in enumerate(texts)]
    used.update(id(w) for w in cw)
    shots.append({"kind": "card", "f": [c1a, c1b], "font": "card", "fg": 254, "bg": 0,
                  "swap": g.strobe_swaps(c1a, c1b),
                  "states": [{"from": f, "lines": [{"text": t, "fit": g.hero_fit(t), "at": [540, 540]}]} for f, t in states]})
    report_shots.append(dict(f=[c1a, c1b], kind="card", section="drop 1", text="/".join(t for _, t in states)))

    # tail: a face under the whole line so far (2-8 frames)
    if cut > c1b + 1:
        add_clip("tail", M.face(), c1b + 1, cut - 1, "amber",
                 camera={"zoom": 1.45, "center": "subject"}, section="tail")
        line = [w["text"] for w in intro_w] + [w["text"] for w in cw]
        tw = words_in(c1b + 1, cut - 1)
        used.update(id(w) for w in tw)
        if line or tw:
            subs.append({"f": [c1b + 1, cut - 1], "style": "band",
                         "words": ([[c1b + 1, " ".join(line)]] if line else []) + [[w["f"], w["text"]] for w in tw]})

    # ---------------------------------------------------------------- verse A: pop words
    slot = [0]

    def pop_clip(idx, a, b, grade):
        ws = words_in(a, b)
        used.update(id(w) for w in ws)
        fxd = {}
        if idx:
            fxd["entry"] = {"frames": g.ENTRY_FRAMES}
        hits = [int(np.floor(t * FPS)) for t, _ in an["strong_hits"] if a <= t * FPS <= b]
        if idx % 2 == 0:
            zs = [[a, 1.3]] + [[w["f"], z] for w, z in zip(ws[1:3], (1.7, 2.0))]
            camera = {"zoom_steps": zs, "center": "subject"}
            if idx == 0:
                fxd["sharpen"] = [4, 140, 2]
                mid = [w for w in ws if w["f"] + g.HUE_FRAMES - 1 <= b]
                if mid:
                    h = min(mid, key=lambda w: abs(w["f"] - (a + b) / 2))
                    fxd["hue_cycle"] = {"f": [h["f"], h["f"] + g.HUE_FRAMES - 1], "deg": -40}
        else:
            pulse = {"hits": sorted(set([a] + hits)), "base": 0.97, "amp": 0.11, "tau": 4.0, "wobble": [0.02, 22.5]}
            camera = {"pulse": pulse, "min_zoom": [b - 7, 1.0]}
        s, subj = add_clip("verse", M.next(), a, b, grade, camera=camera, fx=fxd or None,
                           conform=20 if idx == 0 else None, section=f"verse A{idx}")
        for k, w in enumerate(ws):
            nxt = ws[k + 1]["f"] if k + 1 < len(ws) else None
            hold = (nxt if nxt is not None else b + 1) - w["f"]
            script = w["text"].lower() in script_words
            t = w["text"] if script else w["text"].upper()
            base = {"f": [w["f"], b], "text": t}
            if nxt is not None:
                base["dim_at"] = nxt
            if script:
                pos = g.POP_SLOTS[slot[0] % len(g.POP_SLOTS)]
                slot[0] += 1
                text.append(dict(base, kind="word", font="script", size=128, at=list(pos), shadow=[12, 0.7, 6, 8],
                                 **g.pop_move("slide" if k % 2 else "rise")))
            elif hold >= g.HOLD_E * Ef and len(t) <= 3:
                text.append(dict(base, kind="clones", font="pop", cap=95, every=1, faint={"every": 3, "opacity": 0.55},
                                 positions=[list(p) for p in g.CLONE_SLOTS]))
            elif hold >= g.HOLD_E * Ef and nxt is None and len(t) >= 4 and b - w["f"] >= 4:
                cap = min(125, int(125 * 900 / max(1, _width(t, "pop", 125))))
                text.append({"kind": "word", "f": [w["f"], w["f"] + 1], "text": t, "font": "pop", "cap": cap,
                             "at": [540, 540], "shadow": True})
                text.append({"kind": "stack", "f": [w["f"] + 2, min(b + 1, N - 1)], "text": t, "font": "pop", "cap": cap,
                             "at": [540, 540], "rows": list(g.STACK_ROWS), "pitch": int(cap * 1.25), "stroke": 3})
            else:
                cap = g.pop_cap(t)
                wpx = _width(t, "pop", cap)
                if wpx > 900:
                    cap = int(cap * 900 / wpx)
                pos = g.POP_SLOTS[slot[0] % len(g.POP_SLOTS)]
                slot[0] += 1
                move = g.POP_MOVES[k % len(g.POP_MOVES)]
                text.append(dict(base, kind="word", font="pop", cap=cap, at=list(pos), **g.pop_move(move)))
        return s, hits

    rot_a = list(g.ROTATION_A)
    for idx, (a, b) in enumerate(spans_a):
        pop_clip(idx, a, b, rot_a[idx % len(rot_a)])
    # wind-up whip into the burst
    if burst and spans_a:
        e = burst["a"] - 1
        motion.append({"f": [e - len(g.WHIP_IN) + 1, e], "dx": g.whip_in(e)})

    # ---------------------------------------------------------------- break: burst, black, card 2
    if burst:
        runs = g.burst_runs(burst["black"] - burst["a"])
        f, k, pool = burst["a"], 0, list(range(len(M.ms)))
        bw = words_in(burst["a"], burst["black"])
        used.update(id(w) for w in bw)
        flips = (False, False, True, False, False, True, False, True, False)
        for j, n in enumerate(runs):
            fa, fb = f, f + n - 1
            if j in (0, 2):
                shots.append({"kind": "flat", "f": [fa, fb], "value": g.BURST_FLASH})
            else:
                mi = pool[k % len(pool)]
                zoom = (1.0, 1.35)[k % 2]
                cam = {"zoom": zoom, "crash": 0.11, "center": "subject"}
                if flips[k % len(flips)]:
                    cam["flip"] = True
                fxd = {"wash": {"first": 92, "rest": 82, "gamma": 0.55}} if k % 2 == 1 else None
                add_clip("burst", mi, fa, fb, "khakih", camera=cam, fx=fxd, section="burst")
                k += 1
            f = fb + 1
        report_shots.append(dict(f=[burst["a"], burst["black"] - 1], kind="burst", section="break", runs=runs))
        shots.append({"kind": "flat", "f": [burst["black"], burst["black"]], "value": 0})
        if bw:
            subs.append({"f": [burst["a"], burst["black"]], "style": "band", "words": [[w["f"], w["text"]] for w in bw]})
        # card 2
        c2a, c2b = burst["c2a"], burst["c2b"]
        if card2:
            lines = [p for p in card2.split("/") if p]
        else:
            ws = [w for w in burst["words"] if id(w) not in used] or burst["words"]
            if not ws:
                nb = min(W_, key=lambda w: abs(w["f"] - burst["ret"])) if W_ else None
                ws = [nb] if nb else []
            used.update(id(w) for w in ws)
            if len(ws) >= 2:
                lines = [g.card_text(w["text"], latin) for w in ws[:2]]
            elif ws:
                a_, b_ = g.split_syllables(g.card_text(ws[0]["text"], latin))
                lines = [a_ + "-", b_] if b_ else [a_]
            else:
                lines = ["DROP"]
        cap = 431
        for ln in lines:
            wpx = _width(ln, "card", cap)
            if wpx > 1000:
                cap = int(cap * 1000 / wpx)
        solo = c2a + g.CARD2_SOLO
        st = [{"from": c2a, "lines": [{"text": lines[0], "cap": cap, "at": [540, 536.5]}]}]
        if len(lines) > 1:
            st.append({"from": solo, "align": "left", "lines": [{"text": lines[0], "cap": cap, "at": [540, 247.5]},
                                                                 {"text": lines[1], "cap": cap, "at": [540, 772]}]})
        shots.append({"kind": "card", "f": [c2a, c2b], "font": "card", "fg": 254, "bg": 0,
                      "swap": g.strobe_swaps(solo, c2b, g.CARD2_RUNS), "states": st})
        report_shots.append(dict(f=[c2a, c2b], kind="card", section="drop 2", text="/".join(lines)))

    # ---------------------------------------------------------------- verse B: subtitles
    rot_b = list(g.ROTATION_B)
    if not burst and spans_a:      # no break: keep neighbours apart
        prev = shots[-1].get("grade")
        while rot_b[0] == prev:
            rot_b = rot_b[1:] + rot_b[:1]
    grades_b = [rot_b[i % len(rot_b)] for i in range(len(spans_b))]
    if grades_b and end_words and grades_b[-1] == "red":     # the end card is red-mono: never two reds in a row
        grades_b[-1] = "lilac" if len(grades_b) < 2 or grades_b[-2] != "lilac" else "magenta"
    outline_done = False
    for idx, (a, b) in enumerate(spans_b):
        grade = grades_b[idx]
        ws = words_in(a, b)
        used.update(id(w) for w in ws)
        fxd, camera = {}, None
        if grade == "red":
            mids = [w["f"] for w in ws[1:]]
            punch = mids[len(mids) // 2] if mids else a + (b - a) // 2
            camera = {"push": {"to": 1.5, "frames": min(44, max(8, b - a - 2))},
                      "punch": {"frames": [punch, punch + 1], "k": 1.04}, "about": "subject"}
            pf = sorted({w["f"] for w in ws} | {int(np.floor(t * FPS)) for t, _ in an["strong_hits"] if a <= t * FPS <= b})
            pulses = []
            for x in pf:
                if not pulses or x - pulses[-1] >= 4:
                    pulses.append(x)
            if pulses:
                fxd["pulses"] = {"frames": pulses, "amp": 70, "decay": [1, 0.5, 0.2], "blue": 0.25, "lift": 90}
            span = b - a
            motion.append({"f": [a, b], "dx": [[a + int(round(k * span / 46)), v] for k, v in g.SWAY], "ease": "linear"})
        elif grade == "bw":
            camera = {"drift": 0.0018}
            fxd["scratches"] = {"seed": 1000}
            wa = max(a + 4, b - int(round(4 * Ef)))
            cand = sorted({w["f"] for w in ws if w["f"] >= wa} |
                          {int(np.floor(t * FPS)) for t, _ in an["strong_hits"] if wa <= t * FPS <= b})
            peaks = []
            for x in cand + list(range(wa + 1, b + 1, 4)):
                if all(abs(x - p) >= 3 for p in peaks) and len(peaks) < len(g.STROBE_PEAKS):
                    peaks.append(x)
            peaks.sort()
            if peaks:
                fxd["strobe"] = {"f": [wa, b], "peaks": [[p, v] for p, v in zip(peaks, g.STROBE_PEAKS)], "soft": []}
        elif grade == "magenta":
            fxd["entry"] = {"frames": g.ENTRY_FRAMES}
            motion.append({"f": [a, b], "dy": g.keys_at(a, g.BOUNCE_UP)})
        elif grade == "lilac":
            fxd["entry"] = {"frames": g.ENTRY_FRAMES}
            camera = {"zoom": 1.3, "about": "subject"}
            motion.append({"f": [a, b], "dy": g.keys_at(a, g.BOUNCE_DOWN)})
        add_clip("verse", M.next(prefer="face" if grade == "red" else None), a, b, grade, camera=camera,
                 fx=fxd or None, section=f"verse B{idx}")
        if not ws:
            continue
        style = "diff" if grade in ("red", "bw") else "cursor" if grade in ("magenta", "lilac") else "plain"
        blocks, cur = [], []
        for w in ws:
            if cur and (len(" ".join(x["text"] for x in cur + [w])) > g.SUB_MAX_CHARS or w["line"] != cur[-1]["line"]):
                blocks.append(cur)
                cur = []
            cur.append(w)
        blocks.append(cur)
        for k, bl in enumerate(blocks):
            fa = a if k == 0 else bl[0]["f"]
            fb = blocks[k + 1][0]["f"] - 1 if k + 1 < len(blocks) else b
            B = {"f": [fa, fb], "style": style, "words": [[w["f"], w["text"]] for w in bl]}
            if style == "cursor":
                if grade == "lilac":
                    B["halo_from"] = fa
                if k:
                    B["slide_in"] = 6
            subs.append(B)
        if grade == "bw" and not outline_done:
            big = [w for w in ws if len(w["text"]) >= 3 and w["f"] + 7 <= b]
            if big:
                w = big[0]
                text.append({"kind": "word", "f": [w["f"], w["f"] + 7], "only": [w["f"] + o for o in g.OUTLINE_ON],
                             "text": w["text"].upper(), "font": "pop", "fit": [1010, 1000], "outline": 3, "at": [540, 540]})
                outline_done = True

    # ---------------------------------------------------------------- end card + whip
    if end_words and end_b - end_a >= 5:
        if end_card:
            parts = [p for p in end_card.split("/") if p]
            st = [(end_a + int(round(k * (end_b - end_a + 1) / len(parts))), p.upper()) for k, p in enumerate(parts)]
        else:
            st = [(max(end_a, w["f"]) if k else end_a, g.card_text(w["text"], latin)) for k, w in enumerate(end_words)]
        used.update(id(w) for w in end_words)
        mi = M.next()
        name, t0, spec, subj = window("end", mi, end_a, end_b)
        under = {"clip": name, "t": t0, "grade": "redmono", "camera": {"zoom": 1.2, "center": _clamp_center(subj, 1.2)}}
        under.update(spec)
        shots.append({"kind": "card", "f": [end_a, end_b], "font": "card", "fg": list(g.CRIMSON), "bg": 0,
                      "show": g.on_off(end_a, end_b, g.END_RUNS, [f + d for f, _ in st for d in (0, 1, 2)]),
                      "states": [{"from": f, "lines": [{"text": t, "fit": g.end_fit(t), "at": [540, 540]}]} for f, t in st],
                      "under": under})
        report_shots.append(dict(f=[end_a, end_b], kind="card", section="end", text="/".join(t for _, t in st),
                                 under_moment=mi))
    elif end_a <= end_b:
        add_clip("verse", M.next(), end_a, end_b, "redmono", section="end (no card)")
    left = [w for w in W_ if id(w) not in used]
    if left:
        warn.append("words not shown: " + " ".join(w["text"] for w in left))
    add_clip("outro", M.next(), end_whip, N - 1, "violet", section="whip")
    motion.append({"f": [end_whip, N - 1], "dx": {str(end_whip + k): v for k, v in enumerate(g.WHIP_OUT)}})

    # ---------------------------------------------------------------- inverts on the strongest 808s
    blocked = set()
    for s in shots:
        a, b = s["f"]
        blocked |= set(range(a - 3, a + 4)) | {b - 1, b, b + 1}
        ef = s.get("fx") or {}
        if "entry" in ef:
            blocked |= set(range(a, a + g.ENTRY_FRAMES + 1))
        if "strobe" in ef:
            blocked |= set(range(ef["strobe"]["f"][0] - 1, ef["strobe"]["f"][1] + 2))
        if "hue_cycle" in ef:
            blocked |= set(range(ef["hue_cycle"]["f"][0], ef["hue_cycle"]["f"][1] + 1))
    for s in shots:
        if s["kind"] != "clip" or s["f"][1] - s["f"][0] < 20 or s["grade"] in ("mauve", "amber", "khakih") \
                or s["f"][0] >= end_whip:
            continue
        a, b = s["f"]
        c = sorted(((st, int(np.floor(t * FPS))) for t, st in an["strong_hits"] if a <= t * FPS <= b), reverse=True)
        picked = []
        for _st, f in c:
            if f not in blocked and all(abs(f - p) >= 6 for p in picked) and len(picked) < g.INVERTS_PER_CLIP:
                picked.append(f)
        inverts.update(picked)

    shots.sort(key=lambda s: s["f"][0])
    fused_rep = None
    if edit_style == "fused":
        fused_rep = fuse(dict(shots=shots, text=text, subs=subs, inverts=inverts, W=W, lights=lights, N=N,
                              W_=W_, intro_w=intro_w, end_whip=end_whip, end_a=end_a, end_words=end_words,
                              vb0=(spans_b[0][0] if spans_b else None), strong=an["strong_hits"]), narrator)
    tl = {
        "about": f"card-strobe edit planned from {Path(audio).name} {start:.3f}-{start + dur:.3f}s: "
                 f"{an['tempo']} BPM, drop {an['drop']:.3f}s",
        "fps": FPS, "size": [SQ, 1920], "square": {"size": SQ, "y": 420, "margin": MARGIN},
        "frames": N,
        "audio": {"path": str(Path(audio).expanduser().resolve()), "start": start, "duration": round(N / FPS, 4),
                  "fade_out": 0.03},
        "clips": clips, "shots": shots, "text": text, "subtitles": subs, "motion": motion,
        "events": {"inverts": sorted(inverts), "bar_flash": [W - 1] if W >= 1 else [],
                   "mosaic": {"frames": mosaic, "block": g.MOSAIC_BLOCK}},
    }
    if fused_rep:
        tl["about"] = tl["about"].replace("card-strobe edit", "FUSED card-strobe edit")
        tl["events"]["invert_modes"] = fused_rep.pop("invert_modes")
        tl["fused"] = fused_rep.pop("fused")
    timeline.resolve(tl)              # validates coverage, clips and grades
    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(timeline.dumps(tl), encoding="utf-8")
    rep = dict(
        tempo=an["tempo"], beat_frames=round(P * FPS, 2), eighth_frames=round(Ef, 2), bar_frames=round(BARf, 2),
        frames=N, drop_s=round(an["drop"], 3), white_frame=W, card1=[c1a, c1b], first_cut=cut,
        gap_candidates=[[round(a, 3), round(b, 3), round(d, 1)] for a, b, d in an["gaps"]],
        burst=None if not burst else dict(frames=[burst["a"], burst["black"]], card2=[burst["c2a"], burst["c2b"]],
                                         return_frame=round(burst["ret"], 1)),
        end_card=[end_a, end_b] if end_words else None, whip=[end_whip, N - 1],
        shots=report_shots, inverts=sorted(inverts),
        text=[dict(f=L["f"], kind=L["kind"], text=L.get("text") or "/".join(s[1] for s in L.get("steps", [])))
              for L in text],
        subtitles=[dict(f=B["f"], style=B["style"], line=" ".join(w for _, w in B["words"])) for B in subs],
        notes=an["notes"], warnings=warn, fused=fused_rep)
    (out.parent / "plan_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return tl, rep


# ===================================================================== fused style
def fuse(P, narrator="serif"):
    """turn a planned Mastermind edit into the FUSED style (in place on the planner's lists) ->
    {"fused": block, "invert_modes": {...}, + report fields}. Every number comes from the two approved
    «mefedron master 4» edits (examples/fused_*.json)."""
    from ..fused import FACE_BANNED, accent_steps
    shots, text, subs, W, N = P["shots"], P["text"], P["subs"], P["W"], P["N"]
    fu = {"serif": {"layer": "canvas", "x": 540, "y": 800, "scale": 0.8, "sway": [[0, 1.0], [W, 0.4]],
                    "shade": 0.7, "shade_r": 16, "lines": []},
          "vhs": [], "captions": [], "glitch": {"bars": "keep", "context": "prev", "steps": {}}}
    steps = fu["glitch"]["steps"]

    def shot_at(f):
        return next((s for s in shots if s["f"][0] <= f <= s["f"][1]), None)

    # 1. intro: the serif lead-in under a VHS window replaces the typed glyphs and the band subtitle
    text[:] = [L for L in text if L.get("kind") != "typing"]
    subs[:] = [B for B in subs if B["f"][0] >= W]
    for s in shots:
        if s["kind"] == "clip" and s["grade"] == "mauve":
            s["grade"] = "dusk"
    if P["intro_w"] and W > 0:
        words = [[max(0, w["f"]), w["word"]] for w in P["intro_w"]]
        long_ = len(" ".join(w for _, w in words)) > 14
        fu["serif"]["lines"].append({"f": [0, W - 1], "words": words, "y": 540, "scale": 0.92 if long_ else 1.0,
                                     "layer": "square", "sway": 1.0})
    if W >= 4:
        fu["vhs"].append({"f": [0, W - 2], "vignette": 0.28, "grain": 2.3, "flicker": 1.0, "frame": 1440})
        # drop ramp: lift, grey wash, blown expo on the last three intro frames (the white follows)
        for f, st in ((W - 3, {"step": "wash=1.15,8", "jpeg": 0}), (W - 2, {"step": "wash=0.55,70", "jpeg": 0}),
                      (W - 1, {"step": "expo=2.6 botw=225,1 hs=30"})):
            s = shot_at(f)
            if s and s["kind"] == "clip":
                steps[str(f)] = dict(st, stage="pre")
    # 2. the exact sung words as a tiny caption under every card (Cyrillic under the Latin card)
    for s in shots:
        if s["kind"] != "card":
            continue
        a, b = s["f"]
        ws = [w for w in P["W_"] if a - 1 <= w["f"] <= b]
        if ws:
            fu["captions"].append({"f": [a, b], "words": [[max(a, w["f"]), w["word"]] for w in ws]})
    # 3. verse B narrator: the serif line instead of the tiny subtitles (it rides bounces and the whip)
    vb0 = P["vb0"]
    if narrator == "serif" and vb0 is not None:
        keep = []
        for B in subs:
            if B["f"][0] >= vb0 and B.get("style") in ("diff", "cursor", "plain") and B["words"]:
                fu["serif"]["lines"].append({"f": B["f"], "words": B["words"]})
            else:
                keep.append(B)
        subs[:] = keep
    # 4. glitch ACCENTS on the strong 808s of verse B: the hit frame and the next, never on a clip head,
    #    a strobe, an entry or an invert; INV family in the first half, plain steps after; face-safe ops
    if vb0 is not None:
        clipf, blocked = set(), set()
        for s in shots:
            if s["kind"] == "clip" and vb0 <= s["f"][0] and s["f"][1] < P["end_a"]:
                clipf |= set(range(s["f"][0], s["f"][1] + 1))
                blocked |= set(range(s["f"][0], s["f"][0] + 3))
                ef = s.get("fx") or {}
                if "strobe" in ef:
                    blocked |= set(range(ef["strobe"]["f"][0] - 1, ef["strobe"]["f"][1] + 1))
                if "entry" in ef:
                    blocked |= set(range(s["f"][0], s["f"][0] + g.ENTRY_FRAMES + 1))
        blocked |= set(P["inverts"])
        hits = sorted({int(np.floor(t * FPS)) for t, _ in P["strong"] if vb0 <= t * FPS < P["end_a"]})
        acc = accent_steps(hits, lambda f: f in clipf and f not in blocked, inv_until=(vb0 + P["end_a"]) // 2)
        if clipf:
            fu["glitch"]["base"] = {"frames": sorted(clipf), "luma_cap": 200, "invert": "duotone",
                                    "banned": list(FACE_BANNED)}
        for f, st in acc.items():
            steps[str(f)] = {"step": st, "seed": 9000 + f}
    # 5. inverts keep the hue on warm clips (a plain invert turns orange / red into cyan)
    from ..grade import WARM
    modes = {}
    for f in sorted(P["inverts"]):
        s = shot_at(f)
        if s and s["kind"] == "clip" and s["grade"] in WARM:
            modes[str(f)] = "hue"
    # 6. face-safe exposure strobes
    for s in shots:
        st = (s.get("fx") or {}).get("strobe")
        if st:
            st["curve"] = {"mode": "soft"}
    # 7. the crimson word rides the whip and fades out, so the loop lands clean
    end = next((s for s in shots if s["kind"] == "card" and s["f"][1] == P["end_whip"] - 1), None)
    if end:
        n = N - P["end_whip"]
        for ln in end["states"][-1]["lines"]:
            text.append({"kind": "word", "f": [P["end_whip"], N - 1], "text": ln["text"], "font": "card",
                         "fit": ln.get("fit") or g.end_fit(ln["text"]), "at": ln["at"], "color": list(g.CRIMSON),
                         "opacity": [0.6] * max(0, n - 2) + [0.35, 0.15][-min(2, n):]})
    fu["glitch"]["steps"] = dict(sorted(steps.items(), key=lambda kv: int(kv[0])))
    return {"fused": fu, "invert_modes": modes, "accents": {k: v["step"] for k, v in steps.items()},
            "serif_lines": [[L["f"], " ".join(w for _, w in L["words"])] for L in fu["serif"]["lines"]],
            "captions": [[C["f"], " ".join(w for _, w in C["words"])] for C in fu["captions"]]}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="card_strobe.tools.plan")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--words", required=True)
    ap.add_argument("--moments", required=True)
    ap.add_argument("--src", help="video for moments without their own 'src'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--drop", type=float, help="drop 1 (808) time, original-audio seconds")
    ap.add_argument("--break", dest="brk", help="808 gap A:B in original-audio seconds, or 'none'")
    ap.add_argument("--gap-db", type=float, default=g.GAP_DB)
    ap.add_argument("--card1", help="hero card text, states split by '/' (e.g. MASTER/MIND)")
    ap.add_argument("--card2", help="second card lines split by '/' (e.g. ZAE-/BAL)")
    ap.add_argument("--end-card", help="crimson end card states split by '/' (e.g. CALVIN/KLEIN)")
    ap.add_argument("--script-words", nargs="*", default=[], help="words drawn in the script face (money words)")
    ap.add_argument("--cyrillic-cards", action="store_true", help="keep Cyrillic on cards (default: Latin caps)")
    ap.add_argument("--style", choices=("mastermind", "fused"), default="mastermind")
    ap.add_argument("--narrator", choices=("serif", "subs"), default="serif", help="fused: verse B words as the "
                    "serif line (default) or as Mastermind's tiny subtitles")
    ap.add_argument("--track", help="beat analysis json (beat_period, grid_origin, low_hits) instead of the comb")
    ap.add_argument("--beat0", type=float, help="with --bpm: any beat time (original-audio s) fixes the grid phase")
    ap.add_argument("--top", type=int, help="use only the first N moments / curated picks")
    a = ap.parse_args(argv)
    brk = None
    if a.brk:
        brk = "none" if a.brk == "none" else tuple(float(x) for x in a.brk.split(":"))
    end = a.end
    words = load_words(a.words)
    if end is None:
        end = max(w["start"] for w in words) + 1.0
    _, rep = plan(a.audio, a.start, end, words, load_moments(a.moments, a.src, a.top), a.out, a.bpm, a.drop, brk,
                  a.card1, a.card2, a.end_card, a.script_words, not a.cyrillic_cards, a.gap_db, a.style, a.narrator,
                  a.track, a.beat0)
    print(f"{rep['tempo']} BPM (8th {rep['eighth_frames']} f, bar {rep['bar_frames']} f), {rep['frames']} frames")
    print(f"drop 808 {rep['drop_s']}s -> white f{rep['white_frame']}, card 1 f{rep['card1'][0]}-{rep['card1'][1]}, "
          f"first cut f{rep['first_cut']}")
    print("808 gaps:", rep["gap_candidates"] or "none", "-> burst", rep["burst"])
    print("end card:", rep["end_card"], "whip:", rep["whip"])
    for s in rep["shots"]:
        print(f"  f{s['f'][0]:>4}-{s['f'][1]:<4} {s['kind']:6} {s.get('section', ''):11} {s.get('grade', ''):8} "
              f"{s.get('text', '')}{s.get('src', '')} {s.get('t', '')} {s.get('desc', '')}")
    if rep.get("fused"):
        fr = rep["fused"]
        print("fused: serif lines", len(fr["serif_lines"]), "captions", len(fr["captions"]), "glitch steps",
              len(fr["accents"]))
    for w in rep["warnings"]:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
