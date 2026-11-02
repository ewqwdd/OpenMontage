# Motion: text sway, camera/background, word appearance, transitions (v2)

Feedback on v1: "the animation of the text and of all transitions, movement and swaying is too smooth".
Every number here was measured on `IMG_2446.MP4` (640x480, 30 fps, frames 0–699, 0-based) and on the v1
render with the **same** trackers. Units are px @480 unless noted (×2.25 for build.py).

Deliverables:
- `reports/motion_v2.py`: the module build.py calls.
- `reports/motion_table.json`: per-frame tables, 700 rows of text and 700 rows of frame data, plus transitions and word-in.
- `reports/motion_plot_*.png`: ref (red), v1 (blue) and v2 (green), re-tracked from the rendered v2.
- `reports/motion_sbs_*.png`: side-by-side frames, ref | v1 | v2.
- `reports/motion_validation.txt`: the validation numbers.
- `work_motion/`: all trackers, plus `build_v2.py`, the patched copy of build.py used for validation.

## 0. How it was measured (and how accurate it is)

| quantity | method | accuracy (checked on v1, where the truth is known) |
|---|---|---|
| part-1 text x,y | Per lyric segment (text constant): a template is built iteratively (median, then 25th percentile of the aligned frames), then FFT-NCC with sub-pixel peak. The anchor comes from the template: ink-extent centre in x, and the centre of the x-height band (rows ≥50 % of peak ink density) in y. That is the same anchor build.py uses. | x error std 0.65 px (per-segment bias ≤2 px). y error std 0.32 px. |
| rotation / scale | The left and right halves of the template are tracked separately: scale = Δx spread, rotation = Δy / distance. Segments ≥150 px wide only. | rotation noise 0.02°. scale noise 0.04 % |
| part-2 text | Hand-checked seed box per segment, then a text-colour map (lavender, or red for МАРШРУТКА, inverted frames tried too). NCC over translation and scale 0.86–1.20, accepted only if template ink lands on text pixels. | 86/205 frames valid. They agree with glitch_v2's independent TPOS (x MAD 2 px, y MAD 4 px). |
| part-2 blur | The seed template is convolved with a line kernel (L 0–36 px, 6 angles) and the best NCC kept. | coarse: L in steps of 3–8 px, angle ±15° |
| background | Phase correlation between consecutive frames on 4 regions outside the text band (sub-pixel), with a high-passed luminance. | — |
| word-in | Gradient energy of the G channel in the text box, normalised by text contrast, versus the median of o+2..o+6. Calibrated against box blurs applied to sharp ref frames. | — |
| crossfades | Each frame fitted as (1−t)·old + t·new on 32-px block means (text band excluded), then a linear ramp fitted. | v1's programmed xf (5, 0, 4, 7, 0) recovered as 5, 0, 4, 8, 0 |

## 1. Text motion, part 1 (0–494)

**Verdict: x is a fast, jerky, sawtooth-like wiggle. y is a slow, irregular wave with steps at word
onsets. There is a small rotation wobble. There is no scale change.**
v1 is the opposite on x: a smooth two-sine sway.

| | ref | v1 |
|---|---|---|
| x std | 2.46 px | 2.27 px |
| x mean \|Δx\| per frame | **1.60 px** | 0.44 px |
| x mean \|Δ²x\| (jerk) | **1.84** | 0.42 (4.4× smoother) |
| x spectrum | 76 % of power in **2–5 Hz** (peaks 3.0 and 4.5 Hz), 10 % at 6–8 Hz | 79 % at 0.6–0.7 Hz (the 47-frame sine) |
| x shape | ramps of about +2 px/frame for 3–5 frames, then snaps of −4 px/frame for 2–3 frames. Extrema every 2–3 frames (median 2) | smooth |
| y std | 3.70 px | 3.94 px |
| y spectrum | 91 % at 0.5–1 Hz (peak 0.9 Hz, a period of about 33 frames), **irregular**: half-periods 12–21 frames, asymmetric rise and fall | pure 32-frame sine |
| y smoothness \|Δ²y\| | 0.35 (as smooth as a sine) | 0.38 |
| y steps at onsets | real, up to −5.4 px in one frame (172 −5.4, 145 +0.8, 356 −0.4…). First-word tracking across each onset agrees within 1 px. | none |
| rotation | **±0.5° (p5/p95), std 0.30°**, smooth, period about 15–20 frames (spectral peak 1.8 Hz), lag-1 autocorrelation 0.84 | 0 |
| scale | 1.000 ± 0.0015 (none) | 1 |
| mean anchor y | 237.6 (4.6 px below build's 233; text_v2 makes the font taller, so treat this as the text agent's call) | 233 |

The text jitter is **not a whole-frame shake**. In the static "dark" shot (130–150) the background moves
exactly 0 px while the text keeps jittering by ±4 px.

## 2. Background / camera

- **No editor-added camera move in part 1.** There is no slow push-in, no zoom pulses on onsets or beats,
  and no smooth pan: the static shot 130–150 has bg Δ=0. Zoom per frame is 0.0019 ± 0.008 (noise level,
  the same as v1, which has none). So v1's `bg_sway` sine (±6 px over 90/120 frames) is **not in the
  reference** and is removed.
- The reference background motion is the source footage's own hand-held shake: 9-frame high-passed
  jitter of **2–4.5 px rms in x and 0.4–2.4 px in y**, depending on the line. Our clips are much
  calmer for street/street/dark (0.36/0.86/0.51 px rms), similar for storm/train/lamp, and close for
  field. The table includes the ref's high-passed camera track (`frame[f].jx/jy`). motion_v2 adds it
  per line with a gain of √(ref²−ours²)/ref: lines 0/89/131 at 1.0, 212 at 0.75, 456 at 0.2, the
  others at 0. This option makes the background "feel" as hand-held as the reference.
- **Part 2:** the text shake is a **text-layer** shake. The background does not follow it (lamp-blob
  tracking, e.g. 655→656: text +24 px y, bg +1 px), which matches glitch.md §1.6. The ref part-2
  background is a different, very fast and smeared train clip. Its motion is content and cannot be
  transferred one to one.

## 3. Text motion, part 2 (495–699)

| | ref | v1 |
|---|---|---|
| offset std x / y | **14.3 / 14.5 px** | ≈3 / 4 px |
| mean offset vs (320, 222) | (+0.6, **+9.3**): sits lower | (0, 0) |
| p5/p95 | x −21/+23, y −10/+34 | ±5 |
| frame-to-frame jump (median) | 7.6 / 9.7 px | 2.7 / 2.6 px |
| temporal correlation | lag-1 0.22 (almost white, a new random position every frame) | −0.16 |
| text motion blur | **69 % of frames ≥10 px**, median 14 px, up to ≥36 px; directions 0°, 60° and 90° most common; weakly tied to the jump direction (median angle error 35°) | median 3 px |
| scale | 1.00 (88/119 frames exactly 1.00; the rest are tracker noise) | 1 |

**Ownership.** glitch_v2.py (`TPOS_TXT` plus its smear and ghost schedule) already reproduces this part-2
text motion from its own measurement, and it agrees with this table (x MAD 2 px, y MAD 4 px; blur
corr 0.39, smeared-frame share 64 % vs 69 %). If `glitch_v2.render_part2_v2` is adopted, use it for the
part-2 text and do **not** also apply `MV.p2_offset` or `MV.motion_blur`. They are for the plain
build.py part 2 and serve as an independent cross-check.

## 4. Word appearance (every onset, part 1)

**Verdict: a hard cut with no scale pop, no slide and no flash.** The frame before the new word (o−1) and
the onset frame (o) are both horizontally **smeared/doubled** (an echo about 3–6 px to the side) and
slightly dimmed. o+1 is sharp again. v1 smears only o−1 and does it far too strongly (equivalent to a
10+ px box plus a gaussian), while v1's o is sharp.

Median over 27 onsets (horizontal sharpness normalised by text contrast, relative to o+2..o+6):

| frame | ref gx/contrast | ref contrast | v1 gx/contrast |
|---|---|---|---|
| o−2 | 0.99 | 1.01 | 1.01 |
| **o−1** | **0.82** | 0.96 | 0.57 |
| **o** | **0.82** | 0.96 | 0.97 |
| o+1 | 0.97 | 0.99 | 1.00 |

0.82 corresponds to a 4 px@480 horizontal box blur (calibration: hbox2 0.93, hbox3 0.88, hbox4 0.82,
hbox6 0.67). Zoomed frames (417/418, 181/182) show a doubled image, not a gaussian blur. text_v2's
`onset_dim` (×0.82 / ×0.80) measures the dimming half of the same event.

Per-onset event table (hbox = equivalent horizontal box @480 on o−1 / o; dX, dY = text jump o−1→o;
W = falls inside a scanline-glitch run, median used; L = line start):

| onset | word | L | o−1 sharp → hbox | o sharp → hbox | dX | dY |
|---|---|---|---|---|---|---|
| 24 | стою | | 0.92 → 2.3 | 0.74 → 5.0 | −2.9 | +1.0 |
| 43 | на | | 0.89 → 2.8 | 0.76 → 4.8 | −0.1 | −0.7 |
| 53 | остановке | | 0.84 → 3.6 | 0.89 → 2.9 | −0.3 | −0.6 |
| 89 | и | L | 0.56 → 8.0 | 0.56 → 7.9 | +0.4 | +0.1 |
| 96 | жду | | 1.05 → 0 | 0.82 → 4.0 | +1.0 | +1.1 |
| 107 | автобус | | 0.93 → 2.0 | 0.82 → 3.9 | +4.3 | +0.4 |
| 131 | я | L | 0.76 → 4.8 | 0.78 → 4.6 | +1.0 | +1.5 |
| 145 | замарала | | 0.76 → 4.8 | 0.63 → 6.8 | −3.7 | +0.8 |
| 172 | все | | 0.59 → 7.4 | 0.56 → 7.9 | −0.4 | **−5.4** |
| 182 | кроссовки | | 0.75 → 4.9 | 0.71 → 5.5 | +1.4 | −1.4 |
| 212 | слякоть | L | W → 4 | 0.86 → 3.3 | +0.2 | −0.3 |
| 228 | и | | 0.72 → 5.4 | 0.70 → 5.6 | +0.5 | +0.8 |
| 238 | холод | | W → 4 | W → 4 | −2.0 | +0.6 |
| 251 | на | L | W → 4 | 0.73 → 5.2 | +1.1 | −0.6 |
| 264 | улице | | 0.99 → 0.4 | 0.78 → 4.6 | −1.5 | +0.3 |
| 290 | хочется | | 1.06 → 0 | 0.90 → 2.6 | −2.8 | −0.1 |
| 313 | сдохнуть | | 0.88 → 3.0 | 0.88 → 3.1 | +4.8 | −1.5 |
| 335 | сажусь | L | 0.94 → 1.8 | 1.02 → 0 | −0.6 | 0.0 |
| 347 | в | | 0.86 → 3.3 | 0.90 → 2.6 | +3.3 | −0.6 |
| 356 | автобус | | 0.66 → 6.2 | 0.86 → 3.3 | −2.1 | −0.4 |
| 394 | но | L | W → 4 | 0.94 → 1.8 | +2.9 | +2.0 |
| 405 | когда | | 0.95 → 1.4 | 0.89 → 2.8 | −7.1 | +0.8 |
| 418 | я | | 0.54 → 8.3 | 0.56 → 8.0 | +0.9 | −1.1 |
| 427 | вижу | | 0.84 → 3.6 | 0.83 → 3.8 | +2.3 | +0.3 |
| 440 | тебя | | W → 4 | 0.81 → 4.2 | −0.4 | −1.4 |
| 456 | мне | L | W → 4 | 0.65 → 6.3 | −1.3 | +0.6 |
| 465 | кажется | | 0.87 → 3.1 | 0.75 → 4.9 | −4.9 | +0.5 |
| 487 | что | | W → 4 | W → 4 | +2.9 | −0.3 |

(dX/dY at an onset are part of the ordinary wiggle. The larger y steps of 4–5.6 px span o−2→o+1, as
measured by first-word tracking: 172 −4.4, 182 −4.2, 313 −4.9, 356 −4.1, 440 −5.6.)

Part 2 onsets: every frame is already heavily motion-blurred (§3). There is no separate word-in effect
beyond v1's `f+1 in ONSETS` smear, which was left as is.

## 5. Line transitions (background crossfades)

The text **hard-cuts** at the line start, with the §4 softness on s−1 and s. The **background crossfades
at every clip change** with a linear ramp that ends at s (or s+1). v1 hard-cuts at 212 and 456 and uses
fades that are too short elsewhere.

| line start | ref blended frames (t ramp 0→1) | fit rms | → `XF` (build convention s−xf..s−1) | v1 xf |
|---|---|---|---|---|
| 89 | 78..89 (12) | 0.02 | **12** | 5 |
| 131 | 122..128/130 (7–9) | 0.09 | **9** | 5 |
| 212 | 205..211 (7) | 0.07 | **7** | 0 |
| 251 | 242..252 (11, reaches 1 at s+1) | 0.04 | **10** | 4 |
| 335 | no clip change in the ref (same bus shot) | — | **8** (median) | 0 |
| 394 | 387..395 (9) | 0.05 | **8** | 7 |
| 456 | 451..456 (6) | 0.04 | **6** | 0 |
| 495 → part 2 | 494..495 (2) | 0.03 | `XF_INTO_PART2 = 2` (glitch pass) | 0 |

There are no zoom or whip transitions. The flash at 495 belongs to the glitch domain.

## 6. What motion_v2 implements

| function | replaces | what |
|---|---|---|
| `text_offset(f)` | `sway(f)` | measured (dx, dy)·S from the table (part 1). Low-score frames (14: glitch/onset) are interpolated, nothing smoothed (tracker noise 0.3 px is far below the 1.6 px/frame signal) |
| `rotate_text(canvas, f, cx, cy)` | — | measured rotation about the anchor (measured on 70 % of frames, the rest interpolated or faded to 0) |
| `word_in_effect(canvas, f)` | o−1 smear + `soft=1.8` | per-onset horizontal box on o−1 and o (`mask_hbox_px480`, calibrated through the renderer, ≤10 px@480) × measured dimming; `use_gain=False` if `text_v2.onset_dim` is used |
| `crop_bg(fr, f)` | `crop_bg` / `bg_sway` | no sine; optional ref hand-held jitter × per-line gain |
| `XF[line_start]` | `LINES[i]['xf']` | measured crossfade lengths |
| `p2_offset(f)` | `rng.normal(0,7/6)` text jitter | measured part-2 text shake (86 frames measured, the rest bootstrapped per segment) |
| `motion_blur(canvas, f)` | — | measured part-2 text motion blur (length, angle) |

## 7. Integration (build.py)

```python
import sys; sys.path.insert(0, SCR + '/reports'); import motion_v2 as MV

# after LINES is defined
for L in LINES:
    if L['s'] in MV.XF: L['xf'] = MV.XF[L['s']]

def sway(f):            return MV.text_offset(f)          # (px @1440)
def crop_bg(fr, f):     return MV.crop_bg(fr, f)          # no sine pan; MV.crop_bg(fr, f, gain=0) = static centre

# render_part1, text block:
canvas = place(m, ax, ay, W / 2 + sx, 233 * S + sy)
canvas = MV.rotate_text(canvas, f, W / 2 + sx, 233 * S + sy)
soft = 0.9                                                 # no soft=1.5/1.8 any more
canvas = MV.word_in_effect(canvas, f)                      # replaces the `nxt[0]-f == 1` smear block
# (if text_v2 is used: canvas = MV.word_in_effect(canvas, f, use_gain=False) and keep T2.onset_dim)

# render_part2 (only if glitch_v2.render_part2_v2 is NOT used; it has its own TPOS/smear for the text):
_sx, _sy = MV.p2_offset(f)
tx = W / 2 + _sx; ty = 222 * S + _sy                       # replaces rng.normal(0,7)/(0,6)
canvas = place(m, ax, ay, tx, ty)
canvas = MV.motion_blur(canvas, f)                         # before compose_text
# keep the bg crop on its own (v1 jitter or glitch_v2): the ref bg is NOT shaken with the text.
```

`work_motion/build_v2.py` is exactly build.py with these edits. It was used for the validation below.

Notes:
- A larger `xf` makes the next clip start `xf` frames earlier in its source (build loads
  `e-s+xf` frames from `off`). Shift `off` by −(new xf − old xf)/30 s if the exact content timing matters.
- The word-in hbox values are @480 and are multiplied by S inside the module.

## 8. Validation (v2 re-tracked with the same tools)

`work_motion/build_v2.py --frames 0:700` was rendered to `work_motion/v2f/` and then re-tracked by
exactly the trackers used on the ref and on v1 (`work_motion/validate.py`). Full numbers are in
`motion_validation.txt`.

| metric | v1 vs ref | **v2 vs ref** |
|---|---|---|
| part-1 text x, per frame | rmse 3.79 px, corr −0.00 | **rmse 0.80 px, corr 0.96** |
| part-1 text y, per frame | rmse 5.69, corr −0.11 | **rmse 0.25, corr 1.00** |
| part-1 rotation | rmse 0.30°, corr 0.09 | **rmse 0.07°, corr 0.97** |
| part-1 jerk \|Δ²x\| (ref 1.84) | 0.42 | **1.93** |
| part-1 mean \|Δx\| per frame (ref 1.62) | 0.46 | **1.65** |
| part-2 text x / y, per frame (85 frames valid in both) | rmse 16.2 / 17.2, corr 0.04 / −0.12 | **rmse 5.5 / 7.1, corr 0.92 / 0.88** |
| part-2 shake std x / y (ref 14.3 / 14.5) | 9.0* / 4.1 | **13.9 / 14.9** |
| word-in sharpness at o−1 / o (ref 0.82 / 0.82) | 0.57 / 0.97 | **0.85 / 0.83** |
| bg crossfade at 89/131/212/251/394/456 (ref 12/9/7/11/9/6) | 5/5/0/4/8/0 | 9/9/7/10/10/7 (the 89 fit is biased: both lines are the same clip in our version) |

\*v1's part-2 x std is inflated by mis-tracks on one segment. Its true jitter is σ = 3.1 px.

Part-2 rmse of 5–7 px is measurement noise on the heavily blurred v2 frames: the v2 text **is** placed
exactly at the table values, and the table itself agrees with glitch_v2's TPOS within 2–4 px MAD.

Word-in calibration: the table's `hbox_px480` is the box equivalent on the *final* 480p frame. Applied to
the text **mask** (before glow, CA, softening and the 1440→480 downscale), small boxes vanish and large
ones overshoot. `work_motion/calib_wordin.py` therefore renders every onset at 1× and 2× the box,
inverts the measured sharpness per onset, and stores `mask_hbox_px480`, which the module uses. The
result is a per-onset error with a median of 0.013 (of 1.0). The mask box is capped at 10 px@480
(affects 405 and 418, which calibrate to 9–14 px and then look heavier than the ref's double image).

Plots: `motion_plot_text_x.png`, `motion_plot_text_y.png`, `motion_plot_rot.png`,
`motion_plot_p2_x.png`, `motion_plot_p2_y.png`.
Sheets (ref | v1 | v2): `motion_sbs_sway_56_68.png`, `motion_sbs_wordin_180_185.png`,
`motion_sbs_wordin_416_420.png`, `motion_sbs_xfade_200_214.png`, `motion_sbs_p2_548_560.png`,
`motion_sbs_p2_638_652.png`.

Rebuild the table: `cd work_motion && python build_table.py`. It keeps the calibration.
Re-run `calib_wordin.py pass` only if the text compositor changes (for example if text_v2 is adopted,
because its thinner, taller font changes the mask→frame relation).

## 9. Remaining gaps

- Part-1 x anchor: per-segment absolute bias of ±1–2 px (ink centre vs advance centre, different font
  in the ref). The wiggle itself is exact.
- Rotation is measured only on text ≥150 px wide (70 % of part 1). Elsewhere it is interpolated or faded.
- Part 2: only 86/205 frames are measurable (the rest are white, cyan or glitch frames). Unmeasured
  frames are bootstrapped from the same lyric segment. The blur angle is quantised to 30° and the
  length to 3–8 px steps.
- The word-in "echo" is modelled as an equivalent box blur. The ref looks like 2–3 superimposed
  copies about 3–6 px apart, so a true echo would be closer but differs by under 0.05 in the sharpness
  metric.
- The ref part-2 background is a very fast, smeared clip. Its camera motion is content and is not
  reproduced; only the text shake and blur are.
- Background hand-held jitter transfer is opt-in by gain. It adds ref camera motion on top of our clips'
  own motion, so where our clip already moves (storm, train, lamp) the gain is 0.
- 335: the ref has no clip change there, so the crossfade length (8) is a median, not a measurement.
