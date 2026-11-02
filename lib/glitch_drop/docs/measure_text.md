# Text look v2: measurements, discrepancies, implementation

All pixel values are at 480p (the reference grid). Multiply by S=2.25 for build.py's 1440 canvas.
Frame numbers are 0-based. Tools and raw data are in `work_text/`. The deliverable is `reports/text_v2.py`.

## 1. Measurements: reference vs v1

| property | reference | v1 | how measured |
|---|---|---|---|
| font family | Cormorant Garamond shapes (Λ-shaped л/Л, Δ-shaped д, swash б) | same family | glyph shapes; TNR/Tinos/PT Serif rejected (their л is flat-topped) |
| lowercase x-height | **35 px** (half-max 36-37 on every dark frame 131-335) | 27 | G-channel row profile, serif-to-serif |
| "на улице хочется сдохнуть" ink width | **527 px** (half-max 528-533) | 500 | G half-max extent, frames 317-329 |
| caps cap height | **55 px** (621: rows 186.5-241.5) | 40 | row profile of the clean frames 519/615/621 |
| "ЕСЛИ ПРЯМО СЕЙЧАС" width | **530 px** | 515 | 615/621 |
| МАРШРУТКА | cap height **85 px**, width **390 px**, heavy | 56 px tall, 380 px wide | red mask (R−max(G,B)>50), 672-699 |
| stroke weight | thin: stem G-FWHM **5.0-5.5 px** with peak below 255 (pointed profile) | 6.7-7.1 px, flat 250 plateau | mean stem cross-section over all stems in the x-height band |
| → font weight | **wght 430** (stem 2.75 px lower / 3.3 px caps); МАРШРУТКА **wght 700** | wght 700 at a lower x-height (stem 4.35) | rendered sweep 430/460/500, compared FWHM |
| core colour | p99 ≈ 245/245/255 (part 1), ≈ 215/215/250 (part 2); mean of the top 8 % ≈ 215/235/242 | 250/250/255 plateau | percentiles inside the text box |
| red core | mean 150/35/65, p90 ≈ 175/60/95 (dark crimson) | 230/75/99 (pink) | |
| chromatic aberration | **R +1.75, B −1.40, G 0**. Constant across x (left, middle and right thirds all agree) and on every frame | effectively R +0.4, B 0 (max() blend into a saturated core) | 1/8-px cross-correlation of the channel rows |
| fringe softness | R and B profiles about 1.5× wider than G (low-resolution chroma from the 480p yuv420 capture) | sharp | stem cross-sections |
| glow (excess above the bg at 60 px, G, frames 160/200/230) | 1:79 2:59 3:50 4:43 6:33 8:26 10:21 13:16 16:12 20:8.5 25:6 30:4 40:1.5 | 4:22 6:11 10:4, gone by 15 | ring profile by mask dilation |
| glow colour | lavender that turns bluer with distance: R:G:B 0.73:0.67:1 near, 0.4:0.5:1 at 20 px | saturated blue (R/G about 0) | |
| edge softness | rows rise over 2-3 px. The text is **not** blurred on onset frames | — | |

## 2. The "dirt" and the glitch on the text

### 2a. Scanline displacement (the main dirt)

- **One fixed per-scanline horizontal displacement profile D(y), in screen space.** It is applied to the **text layer only**. The background on the same rows does not move (checked on 120/387, x 480-640).
- When the text moves up 1 px, the pattern stays on the same screen rows. All three channels share it.
- The same profile holds across the whole of part 1: correlation 0.9-0.98 between every burst.
- **Shape of D.** Measured at rows 218-257 from 36 frames, residual 0.2-0.5 px:
  - Piecewise-constant runs of 2-5 rows with sharp steps. Std 1.5 px, range −2.8…+3.0 px at amplitude 1.
  - Examples: rows 218-223 ≈ +1.5…+2.3, rows 228-229 = +3.0/+2.1, rows 234-239 ≈ −2.
  - **No sine wave anywhere.** v1's `wave()` (sine λ=22, ±7 px, RGB split 6) does not exist in the reference.
- **Per-frame amplitude a(f) is signed.** It was measured on every part-1 frame, by projection with correlation |r| > 0.5. The table is `AMP` in text_v2. Patterns:
  - Beat-synced bursts that decay over about 5 frames: 31-36, 60-64, 120-125, 149-154, 209-214, 238-243, 298-303, 327-332, 387-393, 476-482. They start at 0.8-1.03 and drop to about 0.15.
  - Sustained plateaus: 4-14 ≈ 0.65, 93-103 ≈ 0.43, 182-192 ≈ 0.58, 271-281 ≈ 0.47, 360-370 ≈ 0.46, 449-458 ≈ 0.45.
  - **Negative-polarity ramps**, where the same profile is mirrored: 41-52, 69-74, 129-143, 158-163 (−0.07 → −0.53), 218-232, 307-322, 336-341, 396-409, 427-430, 485-494.
  - **Exact zeros** with perfectly clean text: e.g. 24-30, 75-88, 104-119, 164-181, 193-208, 282-297, 371-386, 431-448, 460-475.
- **What v1 got wrong.** v1's `WAVES` list is a partial, wrong-shaped guess at the a≈1 frames. Six of its twelve ranges are actually the baseline tear described next.

### 2b. Baseline tear

- A bell-shaped band at screen rows ~249-254 (row weights 0.22 / 0.78 / 1 / 0.95 / 0.38), shifted **left**, always at the same screen rows.
- Amplitude (row-chain dip): 37-39 −6, 126-128 −3…−5, 146-148 −4, 215-217 −4.7, 235-237 −4.5, 270-274 −2.8, 304-306 −6, 325-326 −3.3, 395 −2.9, 413-415 −3.5, 482-484 −4.5.
- Frames 437-439 have a small S-shaped tear instead: −2 px at rows 250-252 and +1.5 px at rows 254-256.

### 2c. Onset dimming

- On the frame before a new word, the line drops to about 0.77 of its peak. On the onset frame it drops to about 0.80. Measured on the dark lines 131-250; the next frame is back to normal.
- Stem width does not change, so this is **not** a smear. v1's pre-onset `hblur + blur` and its `soft=1.8` do not exist in part 1.

### 2d. Other effects

- **Other per-frame tearing.** None was found beyond D and the band. There was no interlacing, no row brightness modulation (frame 200 checked), and no noise inside the letters beyond the 480p compression.
- **Part 2.** No scanline jitter was detected; the measurement is swamped by the glitch preset. Part-2 text smear and echo are frame-level effects and belong to the glitch agent.

## 3. What is implemented (`reports/text_v2.py`)

- **`text_mask_v2(txt, caps=False, red=False)`**
  - Cormorant Garamond at wght 430 (red at 700).
  - Sized from the reference: x-height 35, cap 55, red cap 85. Widths are calibrated on the ink bbox: 527 / 530 / 390. Read-back: 524 / 526 / 388.
  - Same `(mask, ax, ay)` contract as v1. ay is the x-height centre (or cap centre for caps); ax is the ink centre.
- **`compose_text_v2(bg, m, f=None, caps=False, red=False, opacity=1.0, glitch=True, amp=None, band=None, look=None)`**, in order:
  1. gauss 0.9 px core, ×1.25 gain, clipped.
  2. Three-gaussian glow (r = 3 / 8 / 20 px; colours in `LOOK`).
  3. Then, **after the blur**, the scanline displacement a(f)·D(y) plus the baseline tear, applied to core and glow. Doing this after the blur keeps the steps sharp, as in the reference.
  4. Per-channel shift of core alpha and glow: R +2.35, B −2.10. Each channel is composited normally.
  5. Cb/Cr low-pass to 1/6.75 of the canvas, emulating the reference's 480p 4:2:0. This brings the measured split down to +1.75/−1.38 and widens the fringes as in the reference.
  - Only the text bbox plus the glow margin is processed: 0.24 s per frame.
- **`text_glitch_v2(layer, f, amp=None, band=None)`.** The same tearing as a standalone row-shift for any H×W(×C) layer. It is not needed when f is passed to compose.
- **`onset_dim(f, ONSETS)`.** Returns 0.87 (assuming flicker_v2's frame gain of about 0.92 is applied afterwards; use 0.80 without it).
- **Tables:** `D480` (480 rows: measured 218-257, synthetic outside with the same statistics), `AMP`, `AMP_SCALE = 1.32`, `BAND`, `BAND_PROFILE`, `BAND_S`, `LOOK`.

### Validation (flat-bg harness and full renders through a copy of build.py)

Values are reference / v2.

- **G stem FWHM:** 5.53/5.38, 5.03/5.04, 5.40/5.53, 5.26/5.35 (frames 160, 230, 325, 200). v1 was 6.7-7.1.
- **Stem peaks:** G 194/189, 168/192, 179/163, 188/192.
- **Chromatic aberration:** R−G +1.75 / +1.75 and B−G −1.40 / −1.38.
- **Glow ring profile:** matches within about 3/255 out to 20 px. It is about 4/255 low at 25-40 px.
- **Jitter (mean |row step| px):**

  | frame | 31 | 60 | 122 | 210 | 390 | 477 | 365 |
  |---|---|---|---|---|---|---|---|
  | ref | 0.86 | 0.29 | 0.59 | 0.93 | 0.51 | 0.72 | 0.33 |
  | v2 | 0.84 | 0.29 | 0.59 | 0.98 | 0.48 | 0.72 | 0.31 |

  The profile correlates with the reference at 0.98.
- **Tear profile on 38/216/305/483:** the 5-row shape matches within about 0.5 px.

**Comparison sheets.** These are in `reports/text_cmp_*.png` (ref / v1 / v2 rows, 2-3× nearest) and are copied to `~/Downloads/lyric-edit-text-v2/`:
- `part1_a`, `part1_b`, `part1_c`
- `waves`, `tear`
- `part2`, `red`
- `zoom_230`, `zoom_wave`, `zoom_part2` (4-5×)

## 4. Integration into build.py

The exact code is in the module docstring.

**Part 1.** Use `T2.text_mask_v2` and `place`, then `T2.compose_text_v2(bg, canvas, f=f, opacity=T2.onset_dim(f, ONSETS))`. Delete all of the following:
- the pre-onset `hblur(blur_np(...))`
- `soft`
- `compose_text`
- the `WAVES` / `wave()` call

**Part 2.** Use `T2.text_mask_v2(txt, caps=True, red=...)` and remove the 1.22× red resize. Use `compose_text_v2(..., caps=True, red=...)`. The pre-onset smear and `glitch_frame` remain as before.

A reference implementation is `work_text/build_t.py`. It is a copy of build.py with the v2 path enabled; pass `--v1` for the old path.

## 5. Remaining gaps and coordination notes

- **Placement is not mine and differs from the reference.**
  - The part-2 cap centre is about y 214 in the reference, against build's 222.
  - МАРШРУТКА jumps between y ≈ 174 and 208 (top edge).
  - Several part-1 lines sit 5-10 px higher than v1's sway.

  The baseline tear is screen-fixed at rows ~250-253, so it only cuts the letters where the text sits as in the reference. The glitch agent's `TPOS_TXT` should drive the positions.
- **Overlap with glitch_v2.** glitch_v2 also ships its own `text_mask_v2` / `compose_text_v2` for part 2, with wght 560 and a cap height of 58-62 from a scale search. My serif-to-serif row profile gives 55 px, and its stem width matches wght 430 better. Use one of the two for part 2, not both. If glitch_v2 renders part 2, its text sizes and weight should be reconciled with the numbers here.
- **D(y) coverage.** D is measured only on rows 218-257. Rows outside are synthetic with matching statistics: the б ascender, descenders, and part-2 caps rows 186-217 (part 2 has no jitter anyway).
- **Part 1 vs part 2 jitter.** Part-2 text jitter, smear, echo and pink/green recolouring are frame-level effects, left to glitch_v2. Part-2 core and glow are a scaled version of part 1. Its glow could not be fitted reliably because the backgrounds are bright.
- **Chroma low-pass scope.** The low-pass is applied only inside the text bbox. A global 480p 4:2:0 emulation of the whole frame would be more faithful, and it would make the bbox local pass redundant: set `chroma=0` in `LOOK` if a global one is added.
- **Onset dim and flicker.** The onset dim assumes flicker_v2's frame gain. If both are used without care, the dimming is counted twice.
