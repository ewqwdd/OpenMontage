"""Render a resolved timeline: frame(i) is a PURE function of i, so the edit can be split across
processes in any way and still gives identical frames.

footage frame:  precut canvas frame -> camera (zoom / about / center / track, flip, kick) -> sharpen ->
                [glitch entry] -> duotone (+gain) -> colour keep -> hue cycle -> wash -> pulses ->
                exposure strobe -> scratches -> text layers -> band -> subtitle -> composite crop
                (sway / bounce / whip, motion blur on fast moves) -> mosaic
card frame:     flat bg + giant type (polarity swapped on `swap` frames), or the `under` clip
flat frame:     one colour (white 254 / flash 242 / black 0 + subtitle)
every frame:    bar flash -> 1-frame invert (square AND bars; rgb / hue / duotone) -> 9:16 letterbox

A timeline with a "fused" block renders through fused.FusedRenderer instead (the Mastermind skeleton plus
the first edit's serif narrator, VHS windows, card captions and glitch cells); renderer_for() picks it.
"""
import bisect
import json
import os
import subprocess
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from . import fonts, footage, fx, grade
from . import text as tx


# ===================================================================== source time
def source_index(tl, spec, i):
    """-> (precut frame n, source time t, precut frame as float for `track`) of clip-shot `spec` at frame i.
    The tracking position is (shot t - clip t0) * fps + mapped index; camera.track.by = "time" uses
    (t - clip t0) * fps instead (the two differ only by float rounding). A clip with its own "fps"
    (precut at the source rate, e.g. 60) is indexed at that rate, so a slow `speed` shows new frames."""
    fps = tl["fps"]
    j = i - spec.get("from", spec["f"][0])
    if spec.get("conform"):
        j = fx.conform(j, fps, spec["conform"])
    if spec.get("pingpong"):
        j = fx.pingpong(j, *spec["pingpong"])
    if spec.get("speed", 1) != 1:
        j = j * spec["speed"]
    c = tl["clips"][spec["clip"]]
    t = spec["t"] + j / fps
    by_time = ((spec.get("camera") or {}).get("track") or {}).get("by") == "time"
    cf = c.get("fps") or fps
    if cf == fps:
        nf = (t - c["t0"]) * fps if by_time else (spec["t"] - c["t0"]) * fps + j
        return int(round((t - c["t0"]) * fps)), t, nf
    nf = (t - c["t0"]) * cf if by_time else (spec["t"] - c["t0"]) * cf + j * cf / fps
    return int(round((t - c["t0"]) * cf)), t, nf


def frame_spec(tl, i):
    """-> (kind, spec) shown at frame i; a card's non-`show` frames resolve to its `under` clip"""
    s = tl["shots"][bisect.bisect_right(tl["_starts"], i) - 1]
    if s["kind"] == "card" and "show" in s and i not in s["_show"]:
        return "clip", s["_under"]
    return s["kind"], s


def prepare_shots(tl):
    for s in tl["shots"]:
        if s["kind"] == "card" and "show" in s:
            s["_show"] = set(s["show"])
            s["_under"] = dict(s["under"], f=s["f"])


def levels_key(s):
    """grade levels are shared by every shot with the same clip, grade, ROI and percentiles"""
    k = f"{s['clip']}|{s['grade']}"
    if "levels_roi" in s or "levels_pct" in s:
        k += f"|{s.get('levels_roi')}|{s.get('levels_pct')}"
    return k


def compute_levels(tl, precuts, extra=()):
    """p5/p95 per (clip, grade) over exactly the source frames that pairing shows: a stable grade.
    `levels_roi` [x0, y0, x1, y1] (canvas px) measures inside a box only (a face in front of a bright
    window); `levels_pct` [lo, hi] changes the percentiles. `extra` = more (spec, frame) pairs (a fused
    dissolve); they only add keys that no shot measures, so they never shift an existing grade."""
    need, spec_of = {}, {}
    for i in range(tl["frames"]):
        k, s = frame_spec(tl, i)
        if k == "clip" and "levels" not in s:
            key = levels_key(s)
            spec_of[key] = s
            need.setdefault(key, set()).add(source_index(tl, s, i)[0])
    shot_keys = set(need)
    for s, i in extra:
        if "levels" not in s and levels_key(s) not in shot_keys:
            spec_of[levels_key(s)] = s
            need.setdefault(levels_key(s), set()).add(source_index(tl, s, i)[0])
    levels = {}
    for key, ns in need.items():
        s = spec_of[key]
        a = min(ns)
        fr = footage.read_range(precuts[s["clip"]], a, max(ns) + 1)
        sel = [n - a for n in sorted(ns) if n - a < len(fr)]
        fr = fr[sel]
        if "levels_roi" in s:
            x0, y0, x1, y1 = (int(v) for v in s["levels_roi"])
            fr = fr[:, y0:y1, x0:x1]
        lo, hi = s.get("levels_pct", (5, 95))
        levels[key] = grade.clip_levels(fr, lo, hi)
    return levels


# ===================================================================== renderer
class Renderer:
    def __init__(self, tl, precuts, levels):
        self.tl, self.precuts, self.levels = tl, precuts, levels
        self.fps = tl["fps"]
        self.S = tl["square"]["size"]
        self.M = tl["square"]["margin"]
        self.CV = self.S + 2 * self.M
        self.look = tl["look"]
        self.W = self.look["white"]
        self.pal = tl["_palettes"]
        self.ev = tl["events"]
        fonts.set_overrides(tl.get("fonts"))
        prepare_shots(tl)
        self.src = {}

    # ------------------------------------------------------------ footage
    def prepare(self, i0, i1):
        need = {}
        for i in range(i0, i1):
            k, s = frame_spec(self.tl, i)
            if k == "clip":
                need.setdefault(s["clip"], []).append(source_index(self.tl, s, i)[0])
        for c, ns in need.items():
            a = min(ns)
            self.src[c] = (a, footage.read_range(self.precuts[c], a, max(ns) + 1))

    def get(self, clip, n):
        a, fr = self.src[clip]
        return fr[min(max(n - a, 0), len(fr) - 1)]

    def zoom_at(self, cam, i, f0):
        if "zoom_steps" in cam:
            z = [v for f, v in cam["zoom_steps"] if f <= i]
            zoom = z[-1] if z else cam["zoom_steps"][0][1]
        elif "push" in cam:
            p = cam["push"]
            u = min(1.0, (i - f0) / p["frames"])
            zoom = 1.0 + (p["to"] - 1.0) * (1 - (1 - u) ** 2)
        elif "drift" in cam:
            zoom = 1.0 + cam["drift"] * (i - f0)
        elif "pulse" in cam:
            p = cam["pulse"]
            zoom = p.get("base", 0.97)
            hs = [x for x in p.get("hits", []) if x <= i]
            if hs:
                zoom = zoom + p.get("amp", 0.11) * np.exp(-(i - max(hs)) / p.get("tau", 4.0))
            w = p.get("wobble")
            if w:
                zoom = zoom + w[0] * np.sin(2 * np.pi * (i - f0) / w[1])
        else:
            zoom = cam.get("zoom", 1.0)
        if "min_zoom" in cam and i >= cam["min_zoom"][0]:
            zoom = max(zoom, cam["min_zoom"][1])
        if "punch" in cam and i in cam["punch"]["frames"]:
            zoom *= cam["punch"]["k"]
        if cam.get("crash"):
            zoom *= 1 + cam["crash"] * (i - f0)
        if "kick" in cam:                    # 808 kick, multiplied on top of any mode above
            k = cam["kick"]
            hs = [h for h in k["frames"] if h <= i]
            if hs:
                zoom *= 1 + k.get("amp", 0.10) * float(np.exp(-(i - max(hs)) / k.get("tau", 4.0)))
        return zoom

    def footage(self, s, i):
        n, t, nf = source_index(self.tl, s, i)
        img = self.get(s["clip"], n)
        cam, ef = s.get("camera") or {}, s.get("fx") or {}
        f0, CV = s["f"][0], self.CV
        zoom = self.zoom_at(cam, i, f0)
        dx = dy = 0.0
        P, Q = cam.get("about"), cam.get("center")
        if "track" in cam:
            keys = cam["track"]["keys"]
            Q = (np.interp(nf, [k[0] for k in keys], [k[1] for k in keys]),
                 np.interp(nf, [k[0] for k in keys], [k[2] for k in keys]))
            if cam["track"].get("keep_inside"):
                lo, hi = self.S / 2 / zoom + 2, CV - self.S / 2 / zoom - 2
                Q = (min(max(Q[0], lo), hi), min(max(Q[1], lo), hi))
        if P is not None:
            dx, dy = (P[0] - CV / 2) * (1 - zoom), (P[1] - CV / 2) * (1 - zoom)
        if Q is not None:
            dx, dy = -(Q[0] - CV / 2) * zoom, -(Q[1] - CV / 2) * zoom
        if zoom != 1.0 or dx or dy:
            img = fx.camera(img, zoom, dx, dy, 0, size=(CV, CV))
        else:
            img = img.copy()
        if cam.get("flip"):
            img = np.ascontiguousarray(img[:, ::-1])
        if "sharpen" in ef:
            img = np.asarray(Image.fromarray(img).filter(ImageFilter.UnsharpMask(*ef["sharpen"])))
        keep = None
        if "keep_colour" in ef:
            kc = ef["keep_colour"]
            keep = grade.green_mask(img, kc.get("thr", 6), kc.get("soft", 22.0))
        if "entry" in ef:
            e0 = ef["entry"].get("at", f0)
            k = ef["entry"].get("frames", 4)
            if e0 <= i < e0 + k:
                img = fx.glitch_entry(img, i, e0, k)
        if "levels" in s:
            p5, p95 = s["levels"]
        else:
            p5, p95 = self.levels[levels_key(s)]
        gain = s.get("gain", 1.0)
        gain = (s.get("gain_frames") or {}).get(str(i), gain)
        stops, gamma = self.pal[s["grade"]]
        img = grade.duotone(img, stops, p5, p95, gamma, gain)
        if keep is not None:
            img = grade.restore_colour(img, keep, ef["keep_colour"].get("rgb", (70, 235, 95)),
                                       ef["keep_colour"].get("blur", 3))
        if "hue_cycle" in ef:
            h = ef["hue_cycle"]
            if h["f"][0] <= i <= h["f"][1]:
                img = grade.hue_rotate(img, h.get("deg", -40) * (i - h["f"][0] + 1))
        if "wash" in ef:
            w = ef["wash"]
            img = grade.washed(img, w.get("first", 92) if i == f0 else w.get("rest", 82), w.get("gamma", 0.55))
        if "pulses" in ef:
            p = ef["pulses"]
            img = grade.pulse(img, i, p["frames"], p.get("amp", 70), tuple(p.get("decay", (1, 0.5, 0.2))),
                              p.get("blue", 0.25), p.get("lift", 90))
        if "strobe" in ef:
            st = ef["strobe"]
            args = (img, i, st["f"], [tuple(p) for p in st["peaks"]], set(st.get("soft", [])),
                    tuple(st.get("decay", (1.0, 0.55, 0.22, 0.05))))
            img = grade.exposure_strobe(*args, curve=st["curve"]) if st.get("curve") else grade.exposure_strobe(*args)
        if "scratches" in ef:
            img = grade.scratches(img, ef["scratches"].get("seed", 1000) + i)
        return img

    # ------------------------------------------------------------ text layers (canvas = square + margin)
    def _word(self, img, L, i, op, j):
        role = L.get("font", "pop")
        sc = _anim(L.get("scale"), j, 1.0)
        if "fit" in L:
            m = tx.fitted_mask(L["text"], role, L["fit"][0], L["fit"][1], L.get("outline", 0))
        elif "size" in L:
            m = tx.text_mask(L["text"], role, L["size"])
        else:
            m = tx.text_mask(L["text"], role, round(tx.cap_size(role, L["cap"] * sc), 1))
        if L.get("rot"):
            m = tx.rotated(m, L["rot"])
        cx = L["at"][0] + _anim(L.get("dx"), j, 0) + self.M
        cy = L["at"][1] + _anim(L.get("dy"), j, 0) + self.M
        sh = L.get("shadow")
        if sh:
            b, k, ox, oy = self.look["word_shadow"] if sh is True else sh
            tx.paste_shadow(img, m, cx, cy, b, k * op, (ox, oy))
        tx.paste(img, m, tuple(L.get("color", (255, 255, 255))), cx, cy, op)

    def text(self, img, i):
        for L in self.tl["text"]:
            a, b = L["f"]
            if not a <= i <= b or ("only" in L and i not in L["only"]):
                continue
            j = i - a
            kind = L.get("kind", "word")
            dim = 1.0 if "dim_at" not in L or i < L["dim_at"] else L.get("dim", self.look["dim"])
            op = _anim(L.get("opacity"), j, 1.0) * dim
            if kind == "word":
                alt = L.get("alt")
                if alt and i in alt["frames"]:
                    L2 = dict(L)
                    L2.update({k: v for k, v in alt.items() if k != "frames"})
                    for x, y in (("cap", "size"), ("size", "cap"), ("cap", "fit"), ("size", "fit")):
                        if x in alt:
                            L2.pop(y, None)
                    self._word(img, L2, i, op, j)
                else:
                    self._word(img, L, i, op, j)
            elif kind == "typing":
                self._typing(img, L, i)
            elif kind == "clones":
                every, faint = L.get("every", 1), L.get("faint", {"every": 3, "opacity": 0.55})
                n = min(len(L["positions"]), 1 + int(j / every))       # `every` may be fractional (1.5)
                for k in range(n):
                    o = (1.0 if k % faint["every"] != faint["every"] - 1 else faint["opacity"]) * op
                    self._word(img, dict(L, at=L["positions"][k]), i, o, j)
            elif kind == "stack":
                rows = _anim(L["rows"], j, 1)
                tx.outline_stack(img, L["text"], L.get("font", "pop"), L["cap"], rows, L["at"][0] + self.M,
                                 L["at"][1] + self.M, L.get("pitch", 156), L.get("stroke", 3),
                                 tuple(L.get("color", (255, 255, 255))))

    def _typing(self, img, L, i):
        steps = L["steps"]
        cur = [(f, t, c) for f, t, c in steps if f <= i]
        if not cur:
            return
        k = len(cur) - 1
        s, cap = cur[-1][1], cur[-1][2]
        full = s
        for _, t, c in steps[k + 1:]:          # the word this step is a prefix of (left-aligned typing)
            if c == cap and t.startswith(full):
                full = t
            else:
                break
        block = L.get("block", 6)
        role = L.get("font", "blocky")
        fm, m = tx.blocky_mask(full, cap, block, role), tx.blocky_mask(s, cap, block, role)
        cx, cy = L.get("at", (self.S / 2, self.S / 2))
        cx, cy = cx + self.M, cy + self.M
        x0 = cx - fm.shape[1] / 2 + m.shape[1] / 2
        tx.paste(img, m, tuple(L.get("color", (250, 250, 250))), x0, cy)

    # ------------------------------------------------------------ subtitles
    def subtitle(self, img, i, canvas=True):
        o = self.M if canvas else 0
        sl = self.look["sub"]
        W = (255, 255, 255)
        x = sl["x"] + o
        for B in self.tl["subtitles"]:
            f0, f1 = B["f"]
            if not f0 <= i <= f1:
                continue
            cur = [(f, w) for f, w in B["words"] if f <= i]
            if not cur:
                return img
            txt = " ".join(w for _, w in cur)
            style = B.get("style", "plain")
            if style == "diff":
                m = tx.rotated(tx.subtitle_mask(txt, size=sl["size"], max_w=sl["max_w"]), B.get("rot", sl["rot"]))
                tx.paste_shadow(img, m, x, sl["y"] + o, 4, 0.75, (0, 0))
                return tx.paste_difference(img, m, x, sl["y"] + o)
            if style == "cursor":
                last = max(f for f, _ in cur)
                m = tx.subtitle_mask(txt, cursor=(i // 4) % 2 == 0 or i - last < 3, size=sl["size"], max_w=sl["max_w"])
                if "halo_from" in B and i >= B["halo_from"]:
                    tx.paste_shadow(img, m, x, sl["y"] + o, 5, 1.0, (0, 0))
                    tx.paste_shadow(img, m, x, sl["y"] + o, 2, 0.8, (0, 0))
                y = sl["y"]
                sli = B.get("slide_in")
                if sli and i <= f0 + sli:
                    u = (i - f0) / sli
                    y = sl["y"] + 70 * (1 - u) ** 2
                    for k in range(1, 4):
                        tx.paste(img, m, W, x, y + o + 10 * k * (1 - u), 0.35 / k)
                return tx.paste(img, m, W, x, y + o)
            m = tx.subtitle_mask(txt, size=sl["size"], max_w=sl["max_w"])
            return tx.paste(img, m, W, x, sl["band_y"] + o)
        return img

    def in_band(self, i):
        return any(B.get("style") == "band" and B["f"][0] <= i <= B["f"][1] for B in self.tl["subtitles"])

    # ------------------------------------------------------------ composite motion
    def offset(self, i):
        for seg in self.tl["motion"]:
            if seg["f"][0] <= i <= seg["f"][1]:
                return _channel(seg.get("dx"), i, seg.get("ease", "cosine")), _channel(seg.get("dy"), i, seg.get("ease", "cosine"))
        return 0.0, 0.0

    def crop(self, canvas, dx, dy):
        M, S = self.M, self.S
        cx = int(round(np.clip(dx, -M, M)))
        cy = int(round(np.clip(dy, -M, M)))
        sq = canvas[M - cy:M - cy + S, M - cx:M - cx + S]
        rx = int(round(dx)) - cx
        if rx:
            sq = np.roll(sq, rx, 1)
        return sq

    def composite(self, canvas, i):
        dx1, dy1 = self.offset(i)
        dx0, dy0 = self.offset(i - 1)
        if abs(dx1 - dx0) + abs(dy1 - dy0) > self.look["blur_threshold"]:
            n = self.look["blur_samples"]
            acc = np.zeros((self.S, self.S, 3), np.float32)
            for k in range(n):
                u = k / (n - 1)
                acc += self.crop(canvas, dx0 + (dx1 - dx0) * u, dy0 + (dy1 - dy0) * u)
            return (acc / n).astype(np.uint8)
        return np.ascontiguousarray(self.crop(canvas, dx1, dy1))

    # ------------------------------------------------------------ cards
    def card_colors(self, s, i):
        """(type colour, background) of card `s` at frame i: polarity `swap` frames exchange them;
        `fg_frames` {"460": [50, 225, 193]} recolours the type on single frames (a syllable gag)"""
        fg, bg = _rgb((s.get("fg_frames") or {}).get(str(i), s.get("fg", self.W))), _rgb(s.get("bg", 0))
        if i in s.get("swap", ()):
            fg, bg = bg, fg
        return fg, bg

    def card(self, s, i):
        S = self.S
        fg, bg = self.card_colors(s, i)
        sq = np.empty((S, S, 3), np.uint8)
        sq[:] = bg
        st = [x for x in s["states"] if x["from"] <= i] or s["states"][:1]
        st = st[-1]
        role = s.get("font", "card")
        masks = []
        for ln in st["lines"]:
            if "fit" in ln:
                masks.append(tx.fitted_mask(ln["text"], role, ln["fit"][0], ln["fit"][1], ln.get("outline", 0)))
            else:
                masks.append(tx.text_mask(ln["text"], role, round(tx.cap_size(role, ln["cap"]), 1)))
        x0 = st["lines"][0]["at"][0]
        for k, (ln, m) in enumerate(zip(st["lines"], masks)):
            x = ln["at"][0]
            if k and st.get("align") == "left":
                x = x0 - (masks[0].shape[1] - m.shape[1]) / 2
            tx.paste(sq, m, fg, x, ln["at"][1])
        return sq, bg

    # ------------------------------------------------------------ frame
    def frame(self, i):
        kind, s = frame_spec(self.tl, i)
        S, M = self.S, self.M
        bar = (0, 0, 0)
        if kind == "flat":
            bar = _rgb(s["value"])
            sq = np.empty((S, S, 3), np.uint8)
            sq[:] = bar
            if s.get("subs", sum(bar) < 3 * 128):
                self.subtitle(sq, i, canvas=False)
        elif kind == "card":
            sq, bar = self.card(s, i)
        else:
            canvas = self.footage(s, i)
            self.text(canvas, i)
            if self.in_band(i):
                b = self.look["band"]
                fx.band(canvas, b["y"][0] + M, b["y"][1] + M, b["k"])
            self.subtitle(canvas, i)
            sq = self.composite(canvas, i)
            if i in self.ev["mosaic"]["frames"]:
                sq = fx.mosaic(sq, self.ev["mosaic"].get("block", 36))
        if i in self.ev["bar_flash"]:
            bar = (self.W,) * 3
        if i in self.ev["inverts"]:
            sq, bar = self.invert(sq, bar, i, kind, s)
        return fx.letterbox(sq, self.tl["size"], self.tl["square"]["y"], bar)

    def invert(self, sq, bar, i, kind, s):
        """1-frame invert of the square and the bars. events.invert_modes {"222": "hue"} picks the mode:
        rgb (default, a warm duotone turns cyan), hue (the luma flips, the hue stays) or duotone (the
        luma runs back through the shot's own palette; clip frames only, others fall back to rgb)"""
        mode = self.ev.get("invert_modes", {}).get(i, "rgb")
        pal = self.pal[s["grade"]] if mode == "duotone" and kind == "clip" else None
        return grade.invert(sq, mode, pal), tuple(255 - v for v in bar)


def _rgb(v):
    return tuple(int(c) for c in v) if isinstance(v, (list, tuple)) else (int(v),) * 3


def _anim(seq, j, default):
    if seq is None:
        return default
    if not isinstance(seq, (list, tuple)):
        return seq
    return seq[min(j, len(seq) - 1)]


def _channel(spec, i, ease):
    if not spec:
        return 0.0
    if isinstance(spec, dict):
        return spec.get(str(i), spec.get(i, 0.0))
    return fx.keyframes(i, spec, ease)


# ===================================================================== drivers
def setup(tl, cache_dir, log=print):
    """precut the clip windows and measure the grade levels once (parent process)"""
    log("fonts: " + ", ".join(f"{k}={Path(v).name}" for k, v in fonts.report().items()))
    sq = tl["square"]
    precuts = footage.precut_all(tl["clips"], cache_dir, tl["fps"], sq["size"],
                                 (sq["size"] + 2 * sq["margin"]) / sq["size"], log)
    prepare_shots(tl)
    extra = ()
    if tl.get("fused"):
        from .fused import level_frames
        extra = level_frames(tl)
    for w in tl.get("_warnings", ()):
        log("WARNING: " + w)
    return precuts, compute_levels(tl, precuts, extra)


def _encoder(path, size, fps, crf):
    return subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
                             "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", str(path)],
                            stdin=subprocess.PIPE)


def renderer_for(tl):
    """the Renderer class a timeline needs: FusedRenderer when it has a "fused" block"""
    if tl.get("fused"):
        from .fused import FusedRenderer
        return FusedRenderer
    return Renderer


def _run_chunk(args):
    tl, precuts, levels, i0, i1, path, crf = args
    r = renderer_for(tl)(tl, precuts, levels)
    t = time.time()
    r.prepare(i0, i1)
    enc = _encoder(path, tl["size"], tl["fps"], crf)
    for i in range(i0, i1):
        enc.stdin.write(np.ascontiguousarray(r.frame(i), np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    return i0, i1, round(time.time() - t, 2)


def video(tl, out_dir, workers=None, crf=16, cache_dir=None, log=print, edges=None):
    """-> out_dir/final.mp4 (+ render_report.json). Chunks render in parallel, then concat + audio.
    `edges` [0, a, b, ..., frames] sets the chunk boundaries (default: equal chunks, one per worker).
    Frames are pure functions of i, so the chunking only changes encoder noise at the joins."""
    out_dir = Path(out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    T = time.time()
    precuts, levels = setup(tl, cache_dir or out_dir / "_work" / "precut", log)
    n, fps = tl["frames"], tl["fps"]
    workers = max(1, workers or os.cpu_count() or 1)
    chunk = int(np.ceil(n / workers))
    tmp = out_dir / "_work" / "chunks"
    tmp.mkdir(parents=True, exist_ok=True)
    edges = edges or (tl.get("render") or {}).get("edges")
    if edges:
        edges = sorted({0, n} | {int(e) for e in edges if 0 < int(e) < n})
        tasks = [(tl, precuts, levels, a, b, str(tmp / f"c{a:05d}.mp4"), crf) for a, b in zip(edges, edges[1:])]
        chunk = max(b - a for a, b in zip(edges, edges[1:]))
    else:
        tasks = [(tl, precuts, levels, a, min(n, a + chunk), str(tmp / f"c{a:05d}.mp4"), crf)
                 for a in range(0, n, chunk)]
    log(f"render {n} frames, {len(tasks)} chunks x {chunk}, {workers} workers")
    t = time.time()
    if len(tasks) == 1:
        stats = [_run_chunk(tasks[0])]
    else:
        with get_context("spawn").Pool(min(workers, len(tasks))) as pool:
            stats = pool.map(_run_chunk, tasks)
    t_frames = time.time() - t
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{x[5]}'\n" for x in tasks))
    silent = tmp / "silent.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(silent)], check=True)
    au, dur = tl["audio"], n / fps
    final = out_dir / "final.mp4"
    af = f"afade=t=out:st={max(0, dur - au['fade_out']):.4f}:d={au['fade_out']}"
    if au.get("fade_in"):                 # an in-point inside a word: a 10 ms fade-in kills the click
        af = f"afade=t=in:st=0:d={au['fade_in']}," + af
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(silent), "-ss", f"{au['start']:.4f}",
                    "-t", f"{dur:.4f}", "-i", au["path"], "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-af", af, "-shortest",
                    "-movflags", "+faststart", str(final)], check=True)
    rep = dict(frames=n, workers=workers, chunks=len(tasks), wall_s=round(time.time() - T, 1),
               frames_s=round(t_frames, 1), fps_wall=round(n / t_frames, 1), fonts=fonts.report(),
               per_chunk=[dict(i0=a, i1=b, s=s) for a, b, s in stats])
    (out_dir / "render_report.json").write_text(json.dumps(rep, indent=1))
    return final, rep


def frames(tl, a, b, cache_dir, log=print):
    """yield (i, uint8 frame) for i in a..b-1 in this process"""
    precuts, levels = setup(tl, cache_dir, log)
    r = renderer_for(tl)(tl, precuts, levels)
    r.prepare(a, b)
    for i in range(a, b):
        yield i, r.frame(i)


def preview(tl, out_dir, a=0, b=None, step=1, scale=0.5, cache_dir=None, log=print):
    """PNG frames (scaled) in out_dir/preview/ + numbered contact sheets; -> list of sheet paths"""
    from .tools.sheet import contact_sheet
    out_dir = Path(out_dir).expanduser().resolve()
    d = out_dir / "preview"
    d.mkdir(parents=True, exist_ok=True)
    b = tl["frames"] if b is None else min(b, tl["frames"])
    keep = set(range(a, b, step))
    paths = []
    for i, img in frames(tl, a, b, cache_dir or out_dir / "_work" / "precut", log):
        if i not in keep:
            continue
        im = Image.fromarray(img)
        if scale != 1:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        p = d / f"f{i:04d}.png"
        im.save(p)
        paths.append((i, p))
    return contact_sheet(paths, d, tl["fps"])
