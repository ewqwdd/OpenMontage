"""The editing grammar as code: music + words -> drop schedule, lines and crossfades.

The rules were measured on the reference (skills/creative/glitch-drop-lyrics.md, Part 1). Here they
are written in beats, so they transfer to any tempo.

Drop schedule (R6-R8)
- The reference drop is one 30-frame glitch CELL (= 2 beats at 117 BPM) looped 7 times. Its colour
  rotates A (white) / B (cyan) / C (pale) every cell. The INV strobe layer is on for cells 0-2, off
  for the middle ones, and on again for the red-word cell.
- The reference cells are the templates: m0..m5 = pattern steps 30k..30k+29, m6 = the red cell (25
  steps, red text shows through its over-exposure).
- New song: cell = k beats, where k in {1, 2, 4} makes the cell closest to 1 s (2 at 85-170 BPM).
  Cells are locked to the beat grid (no drift): cell m starts on the frame that contains beat
  drop_beat + k*m, plus DROP_LAG frames.
- Every template is time-warped piecewise-linearly onto its cell, with anchors p0 -> 0,
  p19 (the white flash) -> the strongest low (808/kick) hit within +-3 frames of its warped place,
  and p30 -> cell end. Compressed cells keep the strongest step per frame (PRIORITY). Stretched cells
  fill the gaps with clean steps that carry the cell's clean tone and text position.
"""
import numpy as np

CELL = 30                 # reference cell length (steps)
FLASH_P = 19              # template step of the flash (mosh+flash -> fill, fill)
DROP_LAG = 2              # reference: downbeat inside frame 493, lift 493, wash 494, cell p0 at 495
INV_HEAD = 3              # cells with the INV layer at the start of the drop
TEMPLATES = {("A", 1): 0, ("B", 1): 1, ("C", 1): 2, ("A", 0): 3, ("B", 0): 4, ("C", 0): 5}
COLOURS = "ABC"
PRIORITY = ["fill", "flash", "mosh", "box", "inv", "expo", "cyaninv", "palecyan", "whitetop", "black",
            "wash", "ht", "barA", "barB", "lowblk", "lowblk2", "iri", "dust", "hl", "row", "line"]
INTRO_XF_BEATS = 0.6      # dissolve into a new line, ends on its first syllable (6-12 frames)
MAX_CHARS = (25, 17)      # intro (lowercase) / drop (caps) line length


# ---------------------------------------------------------------- pattern lines (text level)
def _split(line):
    seed, rest = line.split(":", 1)
    fx, tx, meta = (rest.split("|") + ["", ""])[:3]
    return int(seed), fx.split(), tx.split(), meta.split()


def _join(seed, fx, tx, meta):
    return f"{seed}: {' '.join(fx)} | {' '.join(tx)} | {' '.join(meta)}"


def _rank(fx):
    names = [t.split("=")[0] for t in fx]
    r = [PRIORITY.index(n) for n in names if n in PRIORITY]
    return min(r) if r else len(PRIORITY) + (0 if fx else 1)


def reference_cells(pattern_path):
    lines = [l.strip() for l in open(pattern_path, encoding="utf-8") if l.strip() and not l.startswith("#")]
    cells = [lines[i:i + CELL] for i in range(0, len(lines), CELL)]
    red = cells[6] + cells[0][len(cells[6]):]          # m6 is cut at p24 by the song end
    return cells[:6], red


def _clean_meta(cell):
    """tone/pos of the cell's clean frames (no fx): what an inserted gap frame looks like."""
    for l in cell:
        seed, fx, tx, meta = _split(l)
        if not fx:
            return meta
    return _split(cell[-1])[3]


def warp_cell(cell, n, flash_at=None, seed_shift=0):
    """time-warp a 30-step template onto n frames; flash_at = target frame of template step 19."""
    fa = FLASH_P * n / CELL if flash_at is None else flash_at
    fa = float(np.clip(fa, 0.45 * n, n - 4))
    q = np.interp(np.arange(CELL), [0, FLASH_P, CELL], [0, fa, n])
    out = [None] * n
    for p, l in enumerate(cell):
        i = min(n - 1, int(round(q[p])))
        if out[i] is None or _rank(_split(l)[1]) < _rank(_split(out[i])[1]):
            out[i] = l
    meta = _clean_meta(cell)
    for i in range(n):
        if out[i] is None:
            out[i] = _join(0, [], [], meta)
    res = []
    for i, l in enumerate(out):
        seed, fx, tx, mt = _split(l)
        res.append(_join(seed + seed_shift if seed else 5000 + seed_shift + i, fx, tx, mt))
    return res


def cell_beats(period):
    return min((1, 2, 4), key=lambda k: (abs(k * period - 1.0), k != 2))


def drop_schedule(pattern_path, fps, drop_time, period, n_frames, red_time=None, low_hits=(),
                  inv_head=INV_HEAD):
    """-> (G, steps, cells). G = first drop frame, steps = one pattern line per frame G..n_frames-1,
    cells = [(start, length, colour, inv, template)] for the report."""
    base, red_cell = reference_cells(pattern_path)
    k = cell_beats(period)
    G = int(np.floor(drop_time * fps)) + DROP_LAG
    starts = []
    m = 0
    while True:
        s = G if m == 0 else int(np.floor((drop_time + k * m * period) * fps)) + DROP_LAG
        if s >= n_frames:
            break
        starts.append(s)
        m += 1
    if len(starts) > 1 and n_frames - starts[-1] < 0.5 * (starts[-1] - starts[-2]):
        starts.pop()                    # a short tail joins the last full cell (it is cut by the song end)
    starts.append(n_frames)
    red_cell_i = None
    if red_time is not None:
        # the cell of the red word; the next one when the word lands in the second half of its cell
        # (reference: МАРШРУТКА at p27 of cell 5 -> cell 6 carries it) and that cell is not a stub
        rf = red_time * fps
        i = max(0, max(j for j, s in enumerate(starts[:-1]) if s <= rf + 3) if starts[0] <= rf + 3 else 0)
        L = starts[i + 1] - starts[i]
        if rf - starts[i] > 0.5 * L and i + 2 < len(starts) and starts[i + 2] - starts[i + 1] >= 0.5 * L:
            i += 1
        red_cell_i = i
    n_cells = len(starts) - 1
    hits = [(t * fps, s) for t, s in low_hits]
    steps, cells = [], []
    for i in range(n_cells):
        s, e = starts[i], starts[i + 1]
        L = e - s
        colour = COLOURS[i % 3]
        inv = 1 if (n_cells <= inv_head + 1 or i < inv_head or (red_cell_i is not None and i >= red_cell_i)) else 0
        if i == red_cell_i:
            tpl, name = red_cell, "m6(red)"
        else:
            j = TEMPLATES[(colour, inv)]
            tpl, name = base[j], f"m{j}"
        nominal = s + FLASH_P * L / CELL
        near = [(st, ft) for ft, st in hits if abs(ft - nominal) <= 3]
        flash_at = (max(near)[1] - s) if near else None
        steps += warp_cell(tpl, L, flash_at, seed_shift=10000 * (i // 7))
        cells.append(dict(start=s, frames=L, colour=colour, inv=inv, template=name,
                          flash=round(s + (flash_at if flash_at is not None else FLASH_P * L / CELL), 1)))
    return G, steps, cells


# ---------------------------------------------------------------- lines
def split_line(words, limit):
    """split a line (list of (t, text)) at the biggest time gap until every piece fits the limit."""
    def length(ws):
        return len(" ".join(w for _, w in ws))
    if length(words) <= limit or len(words) < 2:
        return [words]
    gaps = [(words[i][0] - words[i - 1][0]) * (1 - abs(i / len(words) - 0.5)) for i in range(1, len(words))]
    i = int(np.argmax(gaps)) + 1
    return split_line(words[:i], limit) + split_line(words[i:], limit)


def crossfade(period, fps):
    return int(np.clip(round(INTRO_XF_BEATS * period * fps), 6, 12))
