"""The FUSED style: the Mastermind card-strobe skeleton + the first edit's («МАРШРУТКА», lib.glitch_drop)
ingredients, as one renderer.

Approved on «mefedron master 4» (examples/fused_chorus_mefedron.json, examples/fused_verse_zvonit.json):
- the thin glowing serif line (glitch_drop IntroText: Cormorant 430, lavender glow, chroma split, scanline
  tear, onset dim, word-in echo, measured hand-held sway) as the narrator / lead-in / breath;
- VHS windows (480p soften, measured flicker gain, vignette, grain) on the calm open;
- the exact Cyrillic word as a tiny caption under every giant Latin card, in the card's colour;
- glitch cells from the glitch_drop pattern language (`inv hs=8`, `ht=290,480,C,holes`, `mosh=…`) on single
  frames: accents on the 808s, a burst, a "red cell" over the crimson end card;
- dissolves (the calm lead-in only), pre-drop ramps (lift / wash / expo) and hue-safe inverts.

Every frame is still a pure function of i (glitch context = one frame of look-back, grain seeded by i), so
any chunking of the render gives the same frames.

timeline["fused"] = {
  "serif": {                                     # defaults for every line (SERIF)
    "x": 540, "y": 540, "scale": 1.0,            # square px of the line's centre / x-height
    "sway": [[0, 1.0], [18, 0.4]],               # measured hand-held sway, scaled per frame (keys)
    "rot": null,                                 # rotation scale (null = the sway scale)
    "tear_scale": 1.32, "tear_follow": true,     # scanline tear; follow = the tear rows move with the line
    "shade": 0.0, "shade_r": 14,                 # dark halo under the glow (0.7 on bright footage)
    "resample": "bilinear" | "lanczos",          # how a scaled line is resampled
    "layer": "canvas" | "square",                # canvas: moves with the composite (whips, bounces) and is
                                                 # pixelated by mosaic frames; square: fixed on top
    "lines": [{"f": [a, b], "words": [[f, "Эй,"], [f2, "звонит"]], "x": .., "y": .., "scale": ..,
               "sway": k, "rot": k, "layer": .., "on_cards": false}]},   # flats always, cards if on_cards
  "vhs": [{"f": [0, 17], "soften": 2.2, "vignette": 0.28, "grain": 2.3, "flicker": 1.0,
           "frame": 1080 | 1440}],               # 1440 = vignette + grain laid out on the 4:3 first-edit frame
  "captions": [{"f": [a, b], "words": [[f, "нахуй,"]] | "text": "люблю", "size": 34, "x": 540, "y": 1017}],
  "caption": {"size": 34, "x": 540, "y": 1017},  # caption defaults (colour = the card's type colour)
  "dissolve": [{"f": [28, 35], "under": {"clip": "A1", "t": 21.0, "from": 0, "grade": "dusk", "speed": 0.85}}],
  "glitch": {                                    # defaults for every step (GLITCH)
    "jpeg": 38, "tone": 0.0, "context": "fresh" | "prev",   # prev: `mosh` reuses frame i-1's glitched output
    "bars": "follow" | "keep",                   # follow: the letterbox bars take the step's polarity
    "invert": "rgb" | "duotone",                 # duotone: inv / cyaninv / palecyan stay in the shot's hue
    "luma_cap": null, "banned": [],              # cap the square's mean luma; drop these ops (FACE_BANNED)
    "over": false,                               # true: serif, captions and the band are drawn AFTER the step
    "stage": "post",                             # pre: before the serif/VHS, bars untouched (drop ramps)
    "base": {"frames": [313, ...], "step": "", "luma_cap": 200, ...},   # a default step on many frames
    "runs": [{"f": [395, 405], "pattern": "reference_drop", "from": 4}],  # pattern slices, one step per frame
    "steps": {"396": "inv hs=26", "409": {"step": "dust=20,70,K,60", "jpeg": 0, "over": true}}}
}
Step syntax = lib/glitch_drop/glitch.py (fx | tx | meta); ops used here: inv expo botw hs vs soft wash tint
cyaninv palecyan flash fill mosh lowblk lowblk2 ht dust row barA barB hl line iri box tre.
"""
import copy

import numpy as np
from PIL import Image, ImageFilter

from ..glitch_drop import glitch as gl
from ..glitch_drop import motion as gmotion
from ..glitch_drop import text as gtext
from ..glitch_drop.timeline import DEFAULT_LOOK as GD_LOOK
from ..glitch_drop.util import place
from . import fx, grade, render
from . import text as tx
from .timeline import merge

GW, GH = 1440, 1080                       # the glitch_drop canvas (4:3); the square sits at x 180
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
COLD = {"inv", "cyaninv", "palecyan"}
FACE_BANNED = ["iri", "botw", "vs", "box", "tre", "tre_"]     # rainbow / blow-out / smear / frozen box: never on faces

SERIF = {"x": 540, "y": 540, "scale": 1.0, "sway": [[0, 1.0]], "rot": None, "tear_scale": 1.32,
         "tear_follow": True, "shade": 0.0, "shade_r": 14, "resample": "bilinear", "layer": "canvas", "lines": []}
VHS = {"soften": 0.0, "vignette": 0.28, "grain": 2.3, "flicker": 1.0, "frame": 1080}
CAPTION = {"size": 34, "x": 540, "y": 1017}
GLITCH = {"jpeg": 38, "tone": 0.0, "context": "fresh", "bars": "follow", "invert": "rgb", "luma_cap": None,
          "banned": [], "over": False, "stage": "post"}
_STEP_KEYS = set(GLITCH) - {"context"} | {"step", "seed", "_step"}

# accent vocabularies that passed review on hero faces (chorus v2): INV family first, plain steps after
ACCENT_INV = ["inv hs=8", "ht=290,480,C,holes", "inv mosh=40,480,0.85 line=160,C", "barB=240,C",
              "inv ht=0,190,C,stripes row=425,C", "dust=290,480,C,grid lowblk2"]
ACCENT_PLAIN = ["hs=20 hl=C", "dust=290,480,C,grid lowblk2", "ht=290,480,C,holes", "barB=240,C", "soft=4 hs=12",
                "row=425,C"]
# a red cell over the crimson end card (verse v2, f409-435)
RED_CELL = ["dust=20,70,K,60", "hl=K", "lowblk2", "barB=240,R", "row=297,W", "dust=15,70,K,90",
            "ht=290,480,R,holes", "mosh=40,480,0.5", "hl=W"]


# ===================================================================== resolve
def resolve_fused(tl):
    """validate + normalise tl["fused"] in place (called by timeline.resolve)"""
    fu = tl["fused"]
    se = fu["serif"] = merge(SERIF, fu.get("serif"))
    for L in se["lines"]:
        if "f" not in L or "words" not in L:
            raise ValueError("fused.serif.lines need f and words")
        if L.get("layer", se["layer"]) not in ("canvas", "square"):
            raise ValueError(f"fused serif line {L['f']}: layer must be canvas or square")
    vh = fu.get("vhs") or []
    if isinstance(vh, dict):                       # {"until": 18, ...} shorthand
        vh = [dict(vh, f=[0, vh.pop("until") - 1])] if "until" in vh else [vh]
    fu["vhs"] = [merge(VHS, w) for w in vh]
    fu["caption"] = merge(CAPTION, fu.get("caption"))
    caps = []
    for C in fu.get("captions") or []:
        C = dict(C)
        if "words" not in C:
            C["words"] = [[C["f"][0], C["text"]]]
        caps.append(C)
    fu["captions"] = caps
    for d in fu.setdefault("dissolve", []):
        u = d["under"]
        u.setdefault("from", d["f"][0])
        u["f"] = [u["from"], d["f"][1]]
        u["kind"] = "clip"
        if u.get("clip") not in tl["clips"] or u.get("grade") not in tl["_palettes"]:
            raise ValueError(f"fused.dissolve {d['f']}: unknown clip or grade")
    g = fu.get("glitch") or {}
    defaults = merge(GLITCH, {k: v for k, v in g.items() if k in GLITCH})
    if defaults["context"] not in ("fresh", "prev"):
        raise ValueError("fused.glitch.context must be fresh or prev")
    steps = {}
    base = g.get("base") or {}
    base_opts = {k: v for k, v in base.items() if k in _STEP_KEYS}
    base_frames = {int(f) for f in base.get("frames", [])}
    for f in base_frames:
        steps[f] = {**defaults, "step": "", **base_opts}

    def opts_at(f):                       # a step on a base frame inherits the base options
        return {**defaults, **(base_opts if f in base_frames else {})}

    for r in g.get("runs") or []:
        pat = gl.load_pattern(r["pattern"])
        a, b = r["f"]
        k0 = r.get("from", 0)
        ro = {k: v for k, v in r.items() if k in _STEP_KEYS}
        for j, f in enumerate(range(a, b + 1)):
            steps[f] = {**opts_at(f), "step": "", **ro, "_step": copy.deepcopy(pat[(k0 + j) % len(pat)])}
    for k, v in (g.get("steps") or {}).items():
        v = {"step": v} if isinstance(v, str) else dict(v)
        f = int(k)
        steps[f] = {**opts_at(f), **v}
    for f, s in steps.items():
        if s["stage"] not in ("pre", "post") or s["bars"] not in ("follow", "keep") \
                or s["invert"] not in ("rgb", "duotone"):
            raise ValueError(f"fused.glitch step {f}: bad stage / bars / invert")
    fu["_steps"] = steps
    fu["_context"] = defaults["context"]


def level_frames(tl):
    """(spec, frame) pairs whose grade levels the renderer needs beyond the shots: dissolve unders"""
    return [(d["under"], i) for d in tl["fused"].get("dissolve", []) for i in range(d["f"][0], d["f"][1] + 1)]


# ===================================================================== helpers for builders / the planner
def accent_steps(hits, ok, inv_until=None, per_hit=2, skip=(), inv=ACCENT_INV, plain=ACCENT_PLAIN):
    """glitch ACCENTS (not a carpet): a step on each 808 hit frame and the `per_hit - 1` frames after it,
    only where ok(f) (a footage frame, not a clip head, not a clean face); the INV family before
    `inv_until`, plain steps after. -> {frame: step}"""
    out, ki, kp = {}, 0, 0
    for h in sorted(hits):
        for f in range(h, h + per_hit):
            if f in out or f in skip or not ok(f):
                continue
            if inv_until is None or f < inv_until:
                out[f] = inv[ki % len(inv)]
                ki += 1
            else:
                out[f] = plain[kp % len(plain)]
                kp += 1
    return out


def clip_heads(tl, n=3):
    """the first n frames of every clip shot (glitch accents keep a clean face first)"""
    return {s["f"][0] + d for s in tl["shots"] if s["kind"] == "clip" for d in range(n)}


# ===================================================================== renderer
class _Tear(gtext.IntroText):
    """IntroText whose scanline tear rows can be shifted to follow the line's y"""
    shift = 0

    def displacement_rows(self, f):
        d = super().displacement_rows(f)
        return np.roll(d, self.shift) if self.shift else d


class FusedRenderer(render.Renderer):
    def __init__(self, tl, precuts, levels):
        super().__init__(tl, precuts, levels)
        fu = self.fu = tl["fused"]
        look = copy.deepcopy(GD_LOOK)
        se = self.se = fu["serif"]
        look["text"]["tear_scale"] = se["tear_scale"]
        self.gm = gmotion.IntroMotion(look)
        self.it = _Tear(look, self.gm.tex)
        self.lines = se["lines"]
        self.onsets = {w[0] for L in self.lines for w in L["words"]}
        self.vhs = fu["vhs"]
        self._vig = {}
        self.steps = {}
        for f, s in fu["_steps"].items():
            st = s.get("_step") or gl.parse_step(s["step"], s.get("seed", 7000 + f))
            if st.seed is None:
                st.seed = s.get("seed", 7000 + f)
            if s["banned"]:
                st = gl.Step([(n, a) for n, a in st.fx if n not in set(s["banned"])], st.tx, st.tone, st.pos, st.seed)
            self.steps[f] = (st, s)
        self.dissolves = fu.get("dissolve", [])
        self._ctx = {}                      # frame -> glitch context of a step run with an empty context
        self.capped = []

    # ------------------------------------------------------------ footage (shots + dissolve unders + look-back)
    def prepare(self, i0, i1):
        a0 = max(0, i0 - 1) if self.fu["_context"] == "prev" else i0
        need = {}
        for i in range(a0, i1):
            k, s = render.frame_spec(self.tl, i)
            if k == "clip":
                need.setdefault(s["clip"], []).append(render.source_index(self.tl, s, i)[0])
            for d in self.dissolves:
                if d["f"][0] <= i <= d["f"][1]:
                    u = d["under"]
                    need.setdefault(u["clip"], []).append(render.source_index(self.tl, u, i)[0])
        from . import footage
        for c, ns in need.items():
            a = min(ns)
            self.src[c] = (a, footage.read_range(self.precuts[c], a, max(ns) + 1))

    # ------------------------------------------------------------ serif narrator
    def _sway(self, i, L):
        if "sway" in L:
            return L["sway"]
        keys = self.se["sway"]
        cur = [v for f, v in keys if f <= i]
        return cur[-1] if cur else keys[0][1]

    def serif_line(self, i, kind, layer=None):
        for L in self.lines:
            if not L["f"][0] <= i <= L["f"][1]:
                continue
            if kind == "card" and not L.get("on_cards"):
                continue
            if layer and kind == "clip" and L.get("layer", self.se["layer"]) != layer:
                continue
            words = [w for f, w in L["words"] if f <= i]
            if words:
                return L, " ".join(words)
        return None, None

    def serif(self, rows, i, L, txt):
        """draw `txt` with line L's look on rows (1080 x w x 3, the square centred in w) -> float32"""
        se = self.se
        h, w = rows.shape[:2]
        pad = (GW - w) // 2
        bg = np.pad(rows.astype(np.float32), ((0, 0), (pad, GW - w - pad), (0, 0)), mode="reflect")
        sc = L.get("scale", se["scale"])
        m, ax, ay = self.it.mask(txt)
        if sc != 1:
            im = Image.fromarray(m.astype(np.float32), "F")
            if se["resample"] == "lanczos":
                m = np.asarray(im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS),
                               np.float32).clip(0, 1)
            else:
                m = np.asarray(im.resize((max(1, int(round(m.shape[1] * sc))), max(1, int(round(m.shape[0] * sc)))),
                                         Image.BILINEAR), np.float32)
            ax, ay = ax * sc, ay * sc
        k = self._sway(i, L)
        rot = L.get("rot", se["rot"] if se["rot"] is not None else k)
        sx, sy = self.gm.text_offset(i)
        x0 = pad + (w - self.S) / 2 + L.get("x", se["x"])
        cx, cy = x0 + sx * k, L.get("y", se["y"]) + sy * k
        can = place(m, ax, ay, cx, cy)
        self.gm.rot = rot
        can = self.gm.rotate(can, i, cx, cy)
        ph = -1 if (i + 1) in self.onsets else (0 if i in self.onsets and i != 0 else None)
        if ph is not None:
            can = self.gm.word_in(can, ph)
        self.it.shift = int(round(cy - 524)) if se["tear_follow"] else 0
        if se["shade"]:
            ys, xs = np.where(can > 0.02)
            if len(ys):
                r = se["shade_r"]
                y0, y1 = max(0, ys.min() - 4 * r), min(GH, ys.max() + 4 * r)
                xa, xb = max(0, xs.min() - 4 * r), min(GW, xs.max() + 4 * r)
                sh = gtext.gauss(np.clip(can[y0:y1, xa:xb] * 3, 0, 1), r)
                bg[y0:y1, xa:xb] *= (1 - se["shade"] * np.clip(sh * 2.2, 0, 1))[..., None]
        out = self.it.compose(bg, can, i, opacity=self.it.onset_dim(i, self.onsets))
        return out[:, pad:pad + w]

    def _serif_u8(self, rows, i, kind, layer=None):
        L, txt = self.serif_line(i, kind, layer)
        if L is None:
            return rows
        return np.clip(self.serif(rows, i, L, txt), 0, 255).astype(np.uint8)

    # ------------------------------------------------------------ captions
    def caption(self, sq, i, color):
        cd = self.fu["caption"]
        for C in self.fu["captions"]:
            if C["f"][0] <= i <= C["f"][1]:
                cur = [w for f, w in C["words"] if f <= i]
                if cur:
                    m = tx.text_mask(cur[-1], "sub", C.get("size", cd["size"]))
                    tx.paste(sq, m, tuple(int(c) for c in color), C.get("x", cd["x"]), C.get("y", cd["y"]))
        return sq

    # ------------------------------------------------------------ VHS window
    def vhs_at(self, i):
        return next((w for w in self.vhs if w["f"][0] <= i <= w["f"][1]), None)

    def vignette(self, strength, frame):
        key = (strength, frame)
        if key not in self._vig:
            S = self.S
            yy, xx = np.mgrid[0:S, 0:frame]
            d = ((xx - frame / 2) / (frame / 2)) ** 2 + ((yy - S / 2) / (S / 2)) ** 2
            v = np.clip(1 - strength * d, 0.55, 1)[..., None].astype(np.float32)
            o = (frame - S) // 2
            self._vig[key] = np.ascontiguousarray(v[:, o:o + S])
        return self._vig[key]

    @staticmethod
    def soften(canvas, r):
        h, w = canvas.shape[:2]
        im = Image.fromarray(canvas).resize((int(w / 2.25), int(h / 2.25)), Image.BILINEAR)
        im = im.filter(ImageFilter.GaussianBlur(r * 0.45))
        return np.array(im.resize((w, h), Image.BICUBIC))

    def vhs_post(self, x, i, v):
        if v["vignette"]:
            x = x * self.vignette(v["vignette"], v["frame"])
        if v["flicker"]:
            lg = self.gm.tex["flicker_log_gain"]
            x = x * np.float32(np.exp(lg[i % len(lg)] * v["flicker"]))
        x = np.clip(x, 0, 255)
        if v["grain"]:
            o = (v["frame"] - self.S) // 2
            n = np.random.default_rng(5000 + i).normal(0, v["grain"], (self.S, v["frame"], 1)).astype(np.float32)
            x = np.clip(x + n[:, o:o + self.S], 0, 255)
        return x

    # ------------------------------------------------------------ glitch steps
    def card_mask(self, s, i):
        m, _ = render.Renderer.card(self, dict(s, fg=255, bg=0, swap=[], fg_frames={}), i)
        return m[..., 0].astype(np.float32) / 255

    def _cold(self, x, st, grade_name):
        """duotone invert: luma reversed through the shot's palette, so an ice / violet shot stays ice /
        violet on INV frames (a plain RGB invert turns it orange / green)"""
        stops, gamma = self.pal[grade_name]
        lut = grade._lut(tuple((float(a), tuple(b)) for a, b in stops), float(gamma)).astype(np.float32)
        y = np.clip(x.astype(np.float32) @ LUMA, 0, 255).astype(np.uint8)
        x = lut[255 - y]
        out = []
        for t in st.fx:
            if t[0] == "inv":
                continue
            if t[0] == "cyaninv":          # inverted + exposed cyan-white, from the cold negative
                out += [("expo", [1.25]), ("tint", [0.84, 0.95, 1.0])]
            elif t[0] == "palecyan":
                out += [("expo", [1.5]), ("tint", [0.8, 0.94, 0.98])]
            else:
                out.append(t)
        st2 = gl.Step(out, st.tx, st.tone, st.pos, st.seed)
        if "cyaninv" in st.names and "box" in st2.names:     # keep the cyan border of the frozen box
            st2.fx = [("tint", [1, 1, 1])] + st2.fx
        return x, st2

    def _uses_ctx(self, st):
        return "mosh" in st.names and "cyaninv" not in st.names

    def run_step(self, x, i, kind, s, tmask=None, ctx=None):
        """apply frame i's step to the square x (float32) -> (float32 square, ctx after the step)"""
        st, spec = self.steps[i]
        if spec["invert"] == "duotone" and kind == "clip" and COLD & set(st.names):
            x, st = self._cold(x, st, s["grade"])
        pad = (GW - self.S) // 2
        img = np.pad(np.asarray(x, np.float32), ((0, 0), (pad, GW - self.S - pad), (0, 0)), mode="reflect")
        tm = None
        if tmask is not None:
            tm = np.zeros((GH, GW), np.float32)
            tm[:, pad:pad + self.S] = tmask
        c = {} if ctx is None else dict(ctx)
        out = gl.apply(img, st, tm, c, spec["tone"], spec["jpeg"])[:, pad:pad + self.S]
        if spec["luma_cap"]:
            with np.errstate(all="ignore"):      # spurious Accelerate matmul warnings
                ml = float((out.reshape(-1, 3) @ LUMA).mean())
            if ml > spec["luma_cap"]:
                out = out * (spec["luma_cap"] / ml)
                self.capped.append((i, round(ml, 1)))
        return out, c

    def context_for(self, i):
        """glitch context "prev": the glitched output of frame i-1, run with an empty context itself
        (one frame of look-back keeps frame(i) a pure function of i)"""
        st, _ = self.steps[i]
        if self.fu["_context"] != "prev" or not self._uses_ctx(st) or (i - 1) not in self.steps \
                or self.steps[i - 1][1]["stage"] != "post":
            return None
        if (i - 1) not in self._ctx:
            x, _, kind, s, tmask = self._pre(i - 1)
            _, c = self.run_step(x.astype(np.float32), i - 1, kind, s, tmask, {})
            self._ctx[i - 1] = c
        return self._ctx[i - 1]

    def step_bars(self, bar, st):
        b = np.array(bar, np.float32)
        for n, a in st.fx:
            if n == "inv":
                b = 255 - b
            elif n == "fill":
                b = np.array(a[:3], np.float32)
            elif n == "flash":
                b = b * (1 - a[1]) + gl.colv(a[0]) * a[1]
            elif n == "wash":
                b = b * a[0] + a[1]
            elif n == "expo":
                b = np.clip(b * a[0] + 18 * (a[0] - 1), 0, 255)
            elif n == "cyaninv":
                b = gl.op_cyaninv(b[None, None])[0, 0]
        b = np.clip(b, 0, 255)
        if max(b) < 24:                     # dark steps keep pure black bars (format rule)
            b = np.zeros(3, np.float32)
        return tuple(int(round(v)) for v in b)

    # ------------------------------------------------------------ frame
    def _over(self, i):
        st = self.steps.get(i)
        return bool(st and st[1]["stage"] == "post" and st[1]["over"])

    def _pre(self, i):
        """everything before the post-stage glitch step -> (uint8 square, bar, kind, spec, card mask)"""
        kind, s = render.frame_spec(self.tl, i)
        S, M = self.S, self.M
        over = self._over(i)
        bar, tmask, serif_done = (0, 0, 0), None, False
        if kind == "flat":
            bar = render._rgb(s["value"])
            sq = np.empty((S, S, 3), np.uint8)
            sq[:] = bar
            if s.get("subs", sum(bar) < 3 * 128):
                self.subtitle(sq, i, canvas=False)
        elif kind == "card":
            sq, bar = self.card(s, i)
            if not over:
                self.caption(sq, i, self.card_colors(s, i)[0])
                sq = self._serif_u8(sq, i, "card")
            serif_done = True
            if i in self.steps:
                tmask = self.card_mask(s, i)
        else:
            canvas = np.array(self.footage(s, i))
            v = self.vhs_at(i)
            if v and v["soften"]:
                canvas = self.soften(canvas, v["soften"])
            self.text(canvas, i)
            if self.in_band(i) and not over:
                b = self.look["band"]
                fx.band(canvas, b["y"][0] + M, b["y"][1] + M, b["k"])
            self.subtitle(canvas, i)
            if not over:
                canvas[M:M + S] = self._serif_u8(canvas[M:M + S], i, "clip", "canvas")
            sq = self.composite(canvas, i)
            if i in self.ev["mosaic"]["frames"]:
                sq = fx.mosaic(sq, self.ev["mosaic"].get("block", 36))

        # float stage: dissolve -> pre step -> serif on the square -> VHS window
        x = None
        for d in self.dissolves:
            if d["f"][0] <= i <= d["f"][1]:
                t = (i - d["f"][0] + 1) / (d["f"][1] - d["f"][0] + 2)
                under = self.footage(d["under"], i)[M:M + S, M:M + S].astype(np.float32)
                x = under * (1 - t) + sq.astype(np.float32) * t
        st = self.steps.get(i)
        if st and st[1]["stage"] == "pre":
            x, _ = self.run_step(sq if x is None else x, i, kind, s, None, {})
        if not serif_done and not over:
            L, txt = self.serif_line(i, kind, "square")
            if L is not None:
                x = self.serif(sq if x is None else x, i, L, txt)
        v = self.vhs_at(i)
        if v:
            x = self.vhs_post(sq.astype(np.float32) if x is None else x, i, v)
        if x is not None:
            sq = np.clip(x, 0, 255).astype(np.uint8)
        if i in self.ev["bar_flash"]:
            bar = (self.W,) * 3
        if i in self.ev["inverts"]:
            sq, bar = self.invert(sq, bar, i, kind, s)
        return sq, bar, kind, s, tmask

    def frame(self, i):
        sq, bar, kind, s, tmask = self._pre(i)
        st = self.steps.get(i)
        if st and st[1]["stage"] == "post":
            ctx = self.context_for(i)
            out, c = self.run_step(sq.astype(np.float32), i, kind, s, tmask, ctx)
            if ctx is None or not self._uses_ctx(st[0]):
                self._ctx[i] = c            # = the empty-context run, reusable as frame i+1's look-back
            sq = np.clip(out, 0, 255).astype(np.uint8)
            if st[1]["bars"] == "follow":
                bar = self.step_bars(bar, st[0])
            if st[1]["over"]:
                sq = np.ascontiguousarray(sq)
                if kind == "card":
                    self.caption(sq, i, self.card_colors(s, i)[0])
                    sq = self._serif_u8(sq, i, "card")
                else:
                    if kind == "clip" and self.in_band(i):
                        b = self.look["band"]
                        fx.band(sq, b["y"][0], b["y"][1], b["k"])
                    L, txt = self.serif_line(i, kind)
                    if L is not None:
                        sq = np.clip(self.serif(sq, i, L, txt), 0, 255).astype(np.uint8)
        if len(self._ctx) > 4:
            for k in sorted(self._ctx)[:-2]:
                del self._ctx[k]
        return fx.letterbox(sq, self.tl["size"], self.tl["square"]["y"], bar)
