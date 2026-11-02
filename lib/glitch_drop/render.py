"""Render a resolved timeline frame by frame -> frames (preview PNGs) or final.mp4.

intro frame: graded clip (+ crossfade into the next line) -> 480p soften -> thin text with glow,
             chroma split, scanline tear, onset dim, word-in box, measured sway/rotation
             -> vignette -> flicker (deflicker + gain + exposure + pre-drop lift) -> grain
drop frame:  clip (stretched) graded, bloomed, softened, regraded (bright top / dark bottom)
             -> caps text at the step position with its smears -> glitch Step -> no grain
"""
import subprocess

import numpy as np
from PIL import Image

from . import background as bgm
from . import flicker as flk
from . import glitch, motion, text
from .timeline import current_words
from .util import BH, BW, H, S, W, place


class Renderer:
    def __init__(self, tl):
        self.tl, self.look, self.fps = tl, tl["look"], tl["fps"]
        self.N, self.G = tl["n"], tl["G"]
        self.motion = motion.IntroMotion(self.look)
        self.itext = text.IntroText(self.look, self.motion.tex)
        self.dtext = text.DropText(self.look)
        self.vig = bgm.vignette(self.look["vignette"])
        self.onsets = set(tl["onsets"])
        self.intro_onsets = {w["f"] for L in tl["intro"] for w in L["words"]}
        self.word_box = {w["f"]: w["in_box"] for L in tl["intro"] for w in L["words"] if w["in_box"]}
        self.flicker = flk.Flicker(self.look, self.motion.tex, self.fps, self.G,
                                   [(L["s"], L["e"]) for L in tl["intro"]],
                                   [L.get("exposure") for L in tl["intro"]])
        self.schedule = glitch.build(tl["drop"]["schedule"], self.N - self.G)

    # ------------------------------------------------------------ intro
    def _prepare_intro(self, only):
        for L in self.tl["intro"]:
            L.pop("_fr", None)
            if only and (L["e"] <= only[0] - 8 or L["s"] - L["xf"] >= only[1]):
                continue
            L["_fr"] = bgm.load_clip(L["clip"], L["offset"], L["e"] - L["s"] + L["xf"], self.fps, L["stretch"], L["ay"])
            g = L["grade"]
            L["_grade"] = bgm.make_grader(L["_fr"], g["pct"], g["rgb"], sat=g["sat"], tint_amt=g["tint"])
        if self.look["flicker"]["deflicker"]:
            self.flicker.own_gain = self._own_gain()

    def _bg(self, li, f, sub=None):
        lines = self.tl["intro"]
        L = lines[li]
        crop = lambda M, k: (lambda c: c if sub is None else c[::sub, ::sub])(self.motion.crop_bg(M["_fr"][k], f, M["jitter"]))
        bg = L["_grade"](crop(L, f - L["s"] + L["xf"]))
        if li + 1 < len(lines):
            Nx = lines[li + 1]
            if Nx["xf"] and f >= Nx["s"] - Nx["xf"] and "_fr" in Nx:
                j = f - (Nx["s"] - Nx["xf"])
                t = (j + 1) / (Nx["xf"] + 1)
                bg = bg * (1 - t) + Nx["_grade"](crop(Nx, j)) * t
        return bg

    def _own_gain(self):
        lines = self.tl["intro"]
        thumbs = np.zeros((self.G, 60, 80), np.float32)
        for li, L in enumerate(lines):
            if "_fr" not in L:
                continue
            for f in range(L["s"], L["e"]):
                bg = self._bg(li, f, sub=9)
                thumbs[f] = flk.thumb_luma(np.asarray(bg, np.float32)[:120, :160], 60, 80)
        segs = []
        for i, L in enumerate(lines):
            e = L["e"]
            if i + 1 < len(lines) and lines[i + 1]["xf"]:
                e = lines[i + 1]["s"] - lines[i + 1]["xf"]
            segs.append((max(0, L["s"]), min(self.G, e)))
        return flk.own_gain(thumbs, segs)

    def _word_phase(self, f):
        if f + 1 in self.intro_onsets or f + 1 == self.G:
            return -1, self.word_box.get(f + 1)
        if f in self.intro_onsets and f != 0:
            return 0, self.word_box.get(f)
        return None, None

    def intro_frame(self, li, f):
        L = self.tl["intro"][li]
        bg = bgm.soften(self._bg(li, f), self.look["soften"])
        m, ax, ay = self.itext.mask(current_words(L, f))
        sx, sy = self.motion.text_offset(f)
        cx, cy = W / 2 + sx, self.look["text"]["y"] * S + sy
        canvas = self.motion.rotate(place(m, ax, ay, cx, cy), f, cx, cy)
        ph, box = self._word_phase(f)
        if ph is not None:
            canvas = self.motion.word_in(canvas, ph, box)
        return self.itext.compose(bg, canvas, f, opacity=self.itext.onset_dim(f, self.onsets))

    # ------------------------------------------------------------ drop
    def _prepare_drop(self):
        b = self.tl["drop"]["bg"]
        self._dfr = bgm.load_clip(b["clip"], b["offset"], self.N - self.G, self.fps, b["stretch"], b["ay"])
        g = b["grade"]
        self._dgrade = bgm.make_grader(self._dfr, g["pct"], g["rgb"], sat=g["sat"], tint_amt=g["tint"])
        self._regrade = bgm.DropRegrade(b["shift_up"])
        self._dctx = {}

    def drop_frame(self, f):
        b, k = self.tl["drop"]["bg"], f - self.G
        step = self.schedule[k]
        GL = next(L for L in self.tl["drops"] if L["s"] <= f < L["e"])
        txt, red = current_words(GL, f).upper(), bool(GL.get("red"))
        rng = np.random.default_rng(900 + step.seed)
        jx, jy = rng.normal(0, b["jitter"][0]), rng.normal(0, b["jitter"][1])
        ox = int(np.clip((BW - W) / 2 + jx, 0, BW - W))
        oy = int(np.clip((BH - H) / 2 + jy, 0, BH - H))
        bg = self._dgrade(self._dfr[k][oy:oy + H, ox:ox + W])
        if b["bloom"]:
            bg = bgm.bloom(bg)
        bg = self._regrade(bgm.soften(bg, b["soften"]))
        can = self.dtext.canvas(step, txt, red, self._dctx)
        img = self.dtext.compose(bg, can, red)
        return glitch.apply(img, step, can, self._dctx, self.tl["drop"]["tone"], self.tl["drop"]["jpeg"])

    # ------------------------------------------------------------ driver
    def frames(self, only=None):
        """yield (f, uint8 frame) in order; only=(a, b) renders a range (grain stays frame-exact)."""
        self._prepare_intro(only)
        grain = np.random.default_rng(3)
        gs = self.look["grain"]
        for li, L in enumerate(self.tl["intro"]):
            for f in range(L["s"], L["e"]):
                g = grain.normal(0, gs, (H, W, 1)).astype(np.float32) if gs else 0
                if only and not (only[0] <= f < only[1]):
                    continue
                img = self.flicker.apply(self.intro_frame(li, f) * self.vig, f) + g
                yield f, np.clip(img, 0, 255).astype(np.uint8)
        if only and only[1] <= self.G:
            return
        self._prepare_drop()
        for f in range(self.G, self.N):
            if only and not (only[0] - 1 <= f < only[1]):
                continue
            img = self.drop_frame(f)
            if only and f < only[0]:
                continue          # warm-up frame: fills the datamosh / ghost context
            yield f, np.clip(img, 0, 255).astype(np.uint8)


def preview(tl, out_dir, only=None, size=(640, 480)):
    d = out_dir / "preview"
    d.mkdir(parents=True, exist_ok=True)
    for f, img in Renderer(tl).frames(only):
        Image.fromarray(img).resize(size).save(d / f"{f:04d}.png")
    return d


def video(tl, out_dir, crf=15, log=print):
    out_dir.mkdir(parents=True, exist_ok=True)
    au, fps, n = tl["audio"], tl["fps"], tl["n"]
    audio, silent, final = out_dir / "audio.wav", out_dir / "video_noaudio.mp4", out_dir / "final.mp4"
    d, fo = float(au["duration"]), float(au["fade_out"])
    af = f"atrim=0:{d},afade=t=out:st={max(0.0, d - fo):.3f}:d={fo},apad=whole_dur={n / fps + 0.001:.4f}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{au['start']:.3f}", "-i", str(au["path"]), "-vn",
                    "-af", af, "-ar", "44100", str(audio)], check=True)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    want = 0
    for f, img in Renderer(tl).frames():
        assert f == want, (f, want)
        enc.stdin.write(img.tobytes())
        want += 1
        if f % 50 == 0:
            log(f"frame {f}/{n}")
    enc.stdin.close()
    enc.wait()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(audio), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    silent.unlink()
    audio.unlink()
    return final
