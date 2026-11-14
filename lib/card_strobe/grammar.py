"""The card-strobe editing grammar as code. Units: E = an 8th note, beat = 2E, half-note = 4E,
bar = 8E (4/4). Every number here was measured frame by frame on the reference (ref3 / kileeknow,
160 BPM, so E = 5.625 frames at 30 fps) and is written in musical units so it transfers to any tempo.
The guide is skills/creative/card-strobe.md, Part 1.

What fires on what
- 808 DROP (the first 808 after the intro):  bars alone go white on the 808 frame (+0), the whole
  phone is white 254 one frame later, then the HERO CARD for 3E: black square, one giant word,
  polarity flipping in runs of 2,3,2,3... frames starting white; the bars follow the polarity.
- Verse: ONE CLIP PER BAR, hard cuts on the half-note grid (0..+2 f late, never early), each clip
  one duotone, neighbours never share a hue. Every word lands on its syllable (onset - 1 frame).
- 808 GAP (bass out >= 2E): a FLASH-CUT BURST of 1,3,2,... frame sub-shots, first frame a 242 flash,
  every other sub-shot washed out, a translucent band with a tiny subtitle; 1 black frame with only
  the subtitle; then the SECOND CARD ~1.7E before the 808 returns: line 1 alone for 5 frames, then
  two lines strobing across the return; hard cut to the red "home" clip on the next half-note.
- Second half: smaller events. Tiny subtitles (difference blend on red/B&W, block cursor on purple),
  at most one giant outline word, an exposure strobe on the kicks in the B&W clip's last half-bar,
  red light pulses on the syllables of the red clip, 1-frame full-screen inverts on 808s.
- End: the punchline as a CRIMSON card alternating with footage (3 on / 2 off), then a 5-frame whip
  that ends mid-motion so the loop restarts cleanly. No fade, no end card.
"""
import numpy as np

# ---------------------------------------------------------------- drop 1 / hero card
DROP_LAG = 2               # white frame = round(808 time * fps) + 2   (ref3: 808 f24.4 -> white f26)
CARD1_E = 3.0              # white + card last 3 eighths (17 f at 160 BPM)
STROBE_RUNS = (2, 3)       # polarity runs: W2 B3 W2 B3 W2 B3 W1 (≈ one flip per 16th, 12 Hz)
WORD_LEAD = 1              # text appears 1 frame before the vocal onset (ref3: 0-2 f early)
CARD_SPLIT_MIN = 7         # a single card word this long is split into two syllable states
FIT_LONG = (173, 823)      # hero-card px per letter / height for words of >= 5 letters (MASTER 1040x823)
FIT_SHORT = (207, 932)     # ... and for <= 4 letters (MIND 829x932)
FIT_MAX_W = 1040

# ---------------------------------------------------------------- intro
TYPE_EVERY = 4             # blocky glyphs: one more character every 4 frames
TYPE_CAP = (124, 167)      # cap px: long word (>= 6 letters) / short word
LIGHTS_ON_E = 1.6          # the intro clip turns amber this long before the white (ref3 f17 of 26)
LIGHTS_GAIN = (0.3, 0.68, 0.8)   # luma ramp of the lights-on frames (9 -> 35 -> 53)
MOSAIC_AT = 3              # 2 mosaic frames starting this many frames after the first vocal onset
MOSAIC_BLOCK = 36

# ---------------------------------------------------------------- verse
CUT_LAG = 1                # cuts land 0..+2 f after the grid point; we use +1
CLIP_BARS = 1.0            # one clip per bar
MIN_CLIP_BARS = 0.45       # a shorter remainder joins the previous clip (ref3 I: 25 f = 0.55 bar)
TAIL_MAX = 8               # frames of "after-card" footage before the first verse cut (ref3: 2)
ROTATION_A = ("orange", "violet", "red", "bw")          # first half (pop words)
ROTATION_B = ("red", "bw", "magenta", "lilac")          # second half (subtitles); red = home colour
GAIN = {"orange": 0.82, "red": 1.2, "magenta": 1.35, "amber": 0.8}   # tuned on flat grey phone footage
ENTRY_FRAMES = 4           # zoom-blur + macroblock entry
WHIP_IN = (4, 16, 37, -8, 35, 81, 96, 170)       # wind-up shake into the burst (px, last 8 frames)
WHIP_OUT = (-60, -135, -225, -325, -425)         # loop whip (last 5 frames)
SWAY = ((0, 0), (12, -48), (24, 12), (46, -32))  # red clip sway, (frame offset, px), linear
BOUNCE_UP = ((0, 0), (4, -18), (8, -31), (10.5, 0), (13, 15), (16, 0), (19, -7), (24, 0))      # magenta clip
BOUNCE_DOWN = ((0, 0), (3, 0), (8, 38), (13, 55), (15, 18), (17, -17), (20, 0), (23, 16), (26, -5))  # lilac clip

# ---------------------------------------------------------------- word events
POP_SLOTS = ((390, 680), (655, 420), (230, 900), (740, 123), (700, 330), (540, 760), (300, 190), (780, 640))
POP_MOVES = ("shrink", "rot", "rise", "drop", "slide")
CLONE_SLOTS = ((540, 270), (250, 760), (780, 640), (300, 190), (720, 860), (470, 930))
HOLD_E = 1.2               # a word held this long (to the next word / the cut) gets clones or a stack
STACK_ROWS = (2, 3, 5, 6, 7, 8)
HUE_FRAMES = 9             # hue cycle: -40 deg / frame for 9 frames (one full turn)
SUB_MAX_CHARS = 30
OUTLINE_ON = (0, 1, 3, 4, 7)     # giant outline word: visible on these frames after its onset (flicker)
STROBE_PEAKS = (244, 214, 205, 196, 193, 171)
INVERTS_PER_CLIP = 2

# ---------------------------------------------------------------- break / drop 2 / end
GAP_DB = 4.0               # 808 gap: sub band (20-90 Hz) this many dB under the body median ...
GAP_MIN_E = 3.0            # ... for at least 3 eighths (Mastermind: -5 dB for 4E; the 808 hits stop,
                           #     the sub tail does not, so the dip is shallow)
DROP_SEARCH = 0.45         # drop 1 = the strongest low hit in the first 45 % of the excerpt
BURST_RUNS = (1, 3, 2)     # sub-shot lengths
BURST_FLASH = 242
CARD2_LEAD_E = 1.67        # card 2 starts this long before the 808 returns (ref3: 9.4 f)
CARD2_SOLO = 5             # line 1 alone for 5 frames
CARD2_RUNS = (3, 2, 2, 3, 3, 2)   # its polarity runs (ref3 ZAE-/BAL)
CRIMSON = (205, 30, 62)
END_RUNS = (3, 2)          # end card on / footage off
END_FIT_H = 600


def eighth(period, fps):
    return period / 2 * fps


def strobe_swaps(a, b, runs=STROBE_RUNS):
    """frames a..b with swapped (white) polarity: runs alternate white, black, white... from a"""
    out, f, k, white = [], a, 0, True
    while f <= b:
        n = runs[k % len(runs)]
        if white:
            out += [x for x in range(f, f + n) if x <= b]
        f += n
        k += 1
        white = not white
    return out


def on_off(a, b, runs=END_RUNS, force_on=()):
    """frames of a..b that show the card (on runs), plus every frame in force_on"""
    on = set(strobe_swaps(a, b, runs)) | {f for f in force_on if a <= f <= b}
    return sorted(on)


TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "yo", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r",
                     "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))
VOWELS = set("AEIOUYАЕЁИОУЫЭЮЯ")


def card_text(word, latin=True):
    """card spelling: caps, punctuation stripped, Cyrillic transliterated to Latin (ref3: ZAE-/BAL)"""
    w = "".join(ch for ch in word if ch.isalnum() or ch == "-").strip("-")
    if latin:
        w = "".join(TRANSLIT.get(ch, TRANSLIT.get(ch.lower(), ch)) for ch in w)
    return w.upper()


def split_syllables(w):
    """split a word in two at the consonant+vowel onset closest to the middle (MASTER|MIND, ZAE|BAL)"""
    if len(w) < 4:
        return w, ""
    best = None
    for k in range(2, len(w) - 1):
        onset = w[k] not in VOWELS and w[k + 1] in VOWELS
        # a stop + R/L cluster opens a syllable too: MEFE|DRON, not MEFED|RON
        cluster = k + 2 < len(w) and w[k] not in VOWELS and w[k + 1] in "RLРЛ" and w[k + 2] in VOWELS \
            and w[k - 1] in VOWELS
        if (onset or cluster) and w[k - 1] != "-":
            d = abs(k - len(w) / 2)
            if best is None or d < best[0]:
                best = (d, k)
    k = best[1] if best else len(w) // 2
    return w[:k], w[k:]


def hero_fit(text):
    """stretched box of a hero-card word: glyph aspect ~0.2 (ultra condensed), 76-86 % of the square"""
    px, h = FIT_LONG if len(text) >= 5 else FIT_SHORT
    return [int(min(FIT_MAX_W, px * max(1, len(text)))), h]


def end_fit(text):
    return [int(min(1000, 150 + 145 * len(text))), END_FIT_H]


def pop_cap(text):
    n = len(text)
    return 95 if n <= 3 else 80 if n <= 5 else 65 if n <= 7 else 58


def pop_move(kind):
    """per-frame animation of a pop word's first frames (ref3 #12/#17)"""
    return {"shrink": {"scale": [1.0, 0.75, 0.6]},     # 2-frame scale-down pop (EU)
            "rot": {"rot": 10},                          # tilted (КИДАЛ)
            "rise": {"dy": [60, 30, 0]},                 # rises from below (СЕГОДНЯ)
            "drop": {"dy": [-45, -20, 5, 0]},            # drops in, 5 px settle (СНОВА)
            "slide": {"dx": [640, 80, 0]}}[kind]         # slides in from the right edge (падал)


def show_ranges(runs):
    """[[a, b], ...] -> every frame a..b of each run: the `show` list of a card that intercuts footage in
    state blocks and single stabs (DOHUYA f180-192 | chug | BABLA f201-212 | chug | stab 215-216)"""
    return sorted({f for a, b in runs for f in range(int(a), int(b) + 1)})


def _nat_w(text, height, role="card"):
    from . import text as tx
    m = tx.text_mask(text, role, 400)
    return m.shape[1] * height / m.shape[0]


def squeezed_lines(parts, widest, height=400, box_w=1000, left=40, ys=(300, 760), role="card"):
    """card lines built from syllables (DOLBO- / YOB / YOBKA): ONE horizontal squeeze for all of them,
    fixed by the widest final part filling box_w, so a partial word keeps the proportions it will have
    when complete; left-aligned at `left`. ys = line centres (one entry per part)."""
    k = box_w / _nat_w(widest, height, role)
    out = []
    for t, y in zip(parts, ys):
        w = _nat_w(t, height, role) * k
        out.append({"text": t, "fit": [round(w), height], "at": [round(left + w / 2, 1), y]})
    return out


def syllable_card(states, widest, height=400, box_w=1000, left=40, y1=300, y2=760, y_alone=540, role="card"):
    """card states that build a word syllable by syllable: [(frame, ["DOLBO-"]), (frame, ["DOLBO-", "YOBKA"])]
    -> kit states (one line alone sits at y_alone, two lines at y1 / y2), all with one common squeeze"""
    return [{"from": f, "lines": squeezed_lines(parts, widest, height, box_w, left,
                                                [y_alone] if len(parts) == 1 else [y1, y2], role)}
            for f, parts in states]


def burst_runs(n):
    out, k = [], 0
    while sum(out) < n:
        out.append(BURST_RUNS[k % len(BURST_RUNS)])
        k += 1
    out[-1] -= sum(out) - n
    return [x for x in out if x > 0]


def whip_in(end):
    """{frame: dx} wind-up shake ending on frame `end` (inclusive)"""
    n = len(WHIP_IN)
    return {str(end - n + 1 + k): v for k, v in enumerate(WHIP_IN)}


def keys_at(f0, keys, length=None):
    """relative keyframes -> absolute; stretched to `length` frames when given"""
    span = keys[-1][0]
    s = 1.0 if not length or not span else min(1.0, length / span) if length < span else length / span
    return [[f0 + k * s, v] for k, v in keys]


def grid_points(origin, step, a, b):
    """grid frames origin + k*step inside [a, b]"""
    k0 = int(np.ceil((a - origin) / step))
    return [origin + k * step for k in range(k0, int(np.floor((b - origin) / step)) + 1)]


def find_gaps(t, e_sub, origin, t0, t1, eighth_s, db=GAP_DB, min_e=GAP_MIN_E):
    """808 gaps in [t0, t1) on the 8th grid from `origin`: runs of eighths whose mean sub-band energy
    (dB) is `db` under the median of the span, at least `min_e` eighths long.
    -> [(gap start s, 808 return s, depth dB)], in time order"""
    k0 = int(np.ceil((t0 - origin) / eighth_s))
    k1 = int(np.floor((t1 - origin) / eighth_s))
    starts = [origin + k * eighth_s for k in range(k0, k1)]
    if len(starts) < 4:
        return []
    v = np.array([np.mean(e_sub[(t >= a) & (t < a + eighth_s)]) if ((t >= a) & (t < a + eighth_s)).any() else np.nan
                  for a in starts])
    med = np.nanmedian(v)
    low = np.nan_to_num(v, nan=med) < med - db
    out, i = [], 0
    while i < len(v):
        if low[i]:
            j = i
            while j < len(v) and low[j]:
                j += 1
            if j - i >= min_e:
                out.append((float(starts[i]), float(starts[i] + (j - i) * eighth_s), float(med - np.mean(v[i:j]))))
            i = j
        else:
            i += 1
    return out
