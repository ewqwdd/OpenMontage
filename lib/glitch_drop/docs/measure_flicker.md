# Screen flicker / luminance dynamics: reference vs v1, and the v2 implementation

All frame numbers are 0-based reference frames at 30 fps. "Gain" is the per-frame multiplicative brightness factor that remains after the content is predicted from neighbouring frames. It is extracted per shot from 60x80 luma thumbnails, with the text band and the TikTok watermarks masked out. The estimator is `fit_gain` in `flicker_v2.py`: an iterative fit of X_f = a_f * S_f, where S_f is a leave-one-out Gaussian (sigma 1.5 frames) temporal prediction. The same estimator is used on the reference, on v1 and on v2, so all comparisons are like for like.

## 1. Findings in the reference

### Part 1 (frames 0–494): a constant, deterministic, global brightness flicker

* **What kind.** The flicker is multiplicative and affects luma only. The per-channel gains correlate at 0.997 (R), 0.999 (G) and 0.993 (B) with the luma gain, and the R/G and B/G gain ratios vary by only about 1 % (std). So there is no colour-temperature flicker.
* **Tonal response.** Testing the gain against tone bins gives slopes of log(ratio) against log(gain) of 1.19, 1.10 and 1.04 in the midtones (L 15–100). The slopes are 0.79 in the deep shadows and 0.84 in the highlights, which is explained by the black floor and clipping. That makes it a plain gain on the encoded RGB values, not an offset: a gain-only fit always beats an offset-only fit.
* **Amplitude.** The measured gain has a std of **7.0 %**, with p5–p95 of 0.884–1.117 and p1–p99 of 0.849–1.17. The amplitude is the same in every shot, from dark (mean luma 19) to bright (mean luma 67). Per-shot std is 6.8, 7.5, 7.2, 7.0, 7.4, 6.5 and 7.1 %. A constant relative amplitude across 7 unrelated clips means this is an added effect, not the source footage.
* **Spatial uniformity.** Top, middle and bottom bands correlate at 0.81–0.96. The edge-ring and centre gains correlate at 0.97, and the std of their ratio is 1.7 %. So the vignette does not breathe. After removing the gain, the row residuals show no travelling structure: the correlation peaks at a 0-row shift. That rules out rolling bars and scanline flicker.
* **Periodicity.** The flicker is periodic and phase-locked, not random. It is two sinusoids in log-gain whose phases stay constant over the whole part (checked in 60-frame windows):
  * f1 = **3.180 Hz** (a period of 9.43 frames), amplitude **7.3 %**, phase -1.18 rad (±0.2 across windows);
  * f2 = **7.380 Hz** (a period of 4.07 frames), amplitude **4.5 %**, phase +0.84 rad (±0.1).
  * This two-sine model explains R² = 0.75 of the measured gain overall, and 0.92 in the steadiest window. In frames 0–40 the model and the measured gain agree to within about 0.02.
  * The flicker is **not tied to the music.** The song is about 117 BPM, with a beat of 15.4 frames. Gain against audio spectral flux correlates at |r| < 0.05 at every lag, and gain against the low-band (kick) energy at |r| < 0.1.
* **Onsets and beats.** Word onsets carry no exposure pumps. The residual at onset+0 is -0.012 ± 0.010, against a null std of 0.010.
* **Text.** The flicker is applied after the text. The text glow follows the gain with slope 0.90 (r = 0.81). The text core follows it with slope 0.63 (r = 0.48); the lower figures come from saturation and sway.
* **Grain.** No grain-intensity flicker beyond brightness: grain HP std is 5 %, and its correlation with gain is 0.22. The reference's high-frequency noise is 0.5–1.0 (σ of luma minus a 5x5 box blur), against **1.5–2.0 in v1**. The reference is TikTok-recompressed, so some of its grain is gone, but v1's grain is visibly heavier.
* **Frame timing.** No held, duplicated or low-fps frames. After gain correction, frame-to-frame motion is never below 1.1, against a median of 3.4. There is no stutter.
* **Shot changes.** Most line changes are hard cuts. The exceptions are a **16-frame dissolve at 122–140** (street to dark) and a 3-frame mix at 392–394.
* **Pre-flash wash at 493–494.** Frame 493 is slightly lifted (p5 15 → 25). Frame 494 is washed to grey: percentiles go from 15/47/106 (p5/p50/p95) to 69/114/144. This is the ramp into the white flash at 495.
* **Exposure level and contrast are not flicker, but they differ a lot.** The reference is brighter on every line. Its black floor is raised (p2 of 5–22 against 0–13 in v1), and its highlights are much brighter (p98 higher by 40–80). Background mean luma per line, reference / v1:
  * 55 / 49, 58 / 51, 19 / 12, 20 / 14;
  * 22 / 20, 28 / 23, **67 / 40**, 55 / 45.

### v1 in part 1

* There is no added flicker. The 3.18 Hz component has 0.3 % amplitude (reference 7.3 %) and the 7.38 Hz component 0.6 % (reference 4.5 %). Correlation with the reference gain is -0.05.
* What frame-level variation v1 does have comes from the user's own footage, and it is uneven:
  * the dark and rain shots are almost frozen (0.6 % std);
  * the storm clip has lightning (11 % std, with spikes at 250–253 and 320–334);
  * the train clip has 6.6 % std.

### Part 2 (frames 495–699)

* The part-1 oscillator does **not** continue. In the same leave-one-out test, the model correlates at 0.06 with part-2 "normal" frames, against 0.89 in part 1.
* The global luminance pattern is the flash and strobe sequence. v1 follows it with a mean-luma correlation of 0.83 (MAE 32 levels) and a frame-delta correlation of 0.77.
* Systematic differences:
  * v1's quiet frames are too bright: mean 93 against 76; p5/p50/p95 of 12/67/251 against 9/56/214. The white snow at the bottom of v1's frame is the main cause.
  * v1's flash frames are not bright enough: about 190 against about 230 (for example 541–542, 557–558, 586–587 and 631–632).
  * About 90 frames differ by more than 35 levels. The list is in the validation section of `work_flicker/validate.py` output. These are mostly structural differences (inversion and strobe content), which belong to the glitch agent.

## 2. What is implemented

### `reports/flicker_v2.py`

`flicker_apply(img, f, ctx=None)` takes float RGB at any resolution and returns a clipped float. Its options and defaults:

| ctx key | default | effect |
|---|---|---|
| `mode` | `'measured'` | per-frame gain = the reference's measured gain (`measured_log_gain`). Frames dominated by shot changes or content (118–141, 249–254, 390–396, 489–494) are replaced by the two-sine model. `'model'` uses the clean two-sine model everywhere. `'off'` disables it. |
| `strength` | 1.0 | scales the log-gain |
| `own_gain` / `deflicker` | from the prepass / True | divides out the frame-level flicker already present in the user's footage (lightning and so on), so that only the reference's modulation remains |
| `events` | True | frames 493 and 494: a relative tone LUT measured from the reference (the lift and the grey wash) |
| `exposure` | False | per-line slow luma LUT that maps the background percentiles of the calibrated render (v1) to the reference's. **Recommended on for v2.** It is valid as long as the grading in build.py is unchanged; otherwise re-run `flicker_extract.py <new_frames_dir>` |
| `p2_match` | False | part 2: per-frame 3-point (p5/p50/p95) luma match to the reference. This is a safety net only (see the gaps) |

The module also provides:
* `prepass_part1(LINES, crop_bg)`, which estimates the own-footage flicker in the pipeline from 1/9-scale graded backgrounds. Crossfade windows get own gain 1.
* `postprocess(in_dir, out_dir)`, also available from the command line as `python flicker_v2.py post IN OUT [a b ctx_json]`, which runs the full two-pass process on rendered PNGs.

### `reports/flicker_extract.py` → `reports/flicker_table.json`

Regenerates everything from `ref/f`:
* the model terms;
* the measured series (hybrid and raw);
* the event LUTs;
* the per-line exposure LUTs;
* the reference per-frame mean, p5, p50, p95, R, G, B and background mean for all 700 frames.

## 3. Integration into build.py (tested in `work_flicker/build_v2.py`)

```python
# top of file
sys.path.insert(0, '<SP>/reports'); import flicker_v2
FLK_CTX = dict(exposure=True)             # mode='measured', deflicker+events on by default

# render_part1: right after the `prepared` loop (clips + graders loaded)
FLK_CTX.update(flicker_v2.prepass_part1(LINES, crop_bg))

# BOTH writers in main(): wrap the vignetted image, BEFORE grain is added
# (= on the finished composite: after compose_text / wave / glitch_frame, after VIG, before grain)
def writer(f, img):
    g = grain_seed.normal(0, 4, (H, W, 1)).astype(np.float32)
    out = np.clip(flicker_v2.flicker_apply(img * (VIG if f < G0 else 1), f, FLK_CTX) + g, 0, 255).astype(np.uint8)
```

Why it goes there:
* **After the text:** in the reference the text glow flickers with the frame (slope 0.9).
* **Before the grain:** the reference's grain does not pulse.
* **After the vignette:** the gain commutes with the vignette, but the `exposure` LUT was calibrated on final, vignetted frames. Applying the LUT before the vignette overshoots the background level by 5–10 %: line means came out 59/62/18/22/24/30/68/61 against the reference's 55/57/20/20/22/29/67/55.

For part 2 the call does nothing unless `p2_match` is set, so the glitch agent's output passes through unchanged.

## 4. Validation (part 1; same estimator on every set; `reports/flicker_validation.txt`)

| | gain std | corr with ref gain | 3.18 Hz amp / phase | 7.38 Hz amp / phase | bg-mean HP corr with ref |
|---|---|---|---|---|---|
| reference | 7.04 % | 1.000 | 7.35 % / -1.18 | 4.57 % / +0.84 | 1.000 |
| v1 | 5.57 % | **-0.046** | 0.33 % / +2.28 | 0.63 % / +3.03 | -0.016 |
| v2 (post-process on v1, default) | 7.21 % | **+0.885** | 7.29 % / -1.18 | 4.32 % / +0.86 | +0.823 |
| v2 + exposure | 7.12 % | +0.886 | 7.14 % / -1.18 | 4.39 % / +0.85 | +0.832 |
| v2, mode='model' | 6.71 % | +0.776 | 7.16 % / -1.19 | 4.29 % / +0.87 | +0.753 |

Per-shot correlation of v2 with the reference gain:

| shot (frames) | 0–118 | 142–212 | 212–249 | 255–335 (storm) | 335–390 | 397–456 | 456–489 |
|---|---|---|---|---|---|---|---|
| corr | 0.95 | 0.97 | 0.95 | 0.73 | 0.88 | 0.94 | 0.97 |

Per-shot gain std of v2, in % (reference in brackets):

| shot (frames) | 0–118 | 142–212 | 212–249 | 255–335 (storm) | 335–390 | 397–456 | 456–489 |
|---|---|---|---|---|---|---|---|
| std | 6.4 (6.8) | 6.6 (7.5) | 6.7 (7.2) | 9.2 (7.0) | 7.2 (7.4) | 6.7 (6.5) | 7.3 (7.1) |

With `exposure=True`, the per-line background mean (reference / v2) becomes:
* 55 / 55, 57 / 57, 20 / 17, 20 / 20;
* 22 / 21, 29 / 28, 67 / 66, 55 / 54.

Part 2 with `p2_match=True` (percentile mode): mean-luma correlation 0.826 → 0.984, MAE 32.4 → 12.7, delta correlation 0.770 → 0.979.

**In-pipeline render** (`work_flicker/build_v2.py --frames 0:700`, the real 1440x1080 path with `prepass_part1`, `exposure=True`, and the call placed after the vignette):
* gain std 7.15 %; **correlation with the reference gain +0.893**;
* 3.18 Hz component 7.19 % / -1.19 rad; 7.38 Hz component 4.45 % / +0.85 rad (the reference's are 7.35 % / -1.18 and 4.57 % / +0.84);
* background-mean HP correlation with the reference +0.847.

| shot (frames) | 0–118 | 142–212 | 212–249 | 255–335 (storm) | 335–390 | 397–456 | 456–489 |
|---|---|---|---|---|---|---|---|
| corr with ref gain | 0.92 | 0.96 | 0.95 | 0.79 | 0.83 | 0.94 | 0.96 |

Line background means, reference / v2 in-pipeline:
* 55 / 56, 57 / 59, 20 / 19, 20 / 22;
* 22 / 23, 29 / 30, 67 / 69, 55 / 56.

Part 2 passes through unchanged (correlation 0.825). The frames are in `work_flicker/preview_v2/`. A side-by-side reference | v1 | v2 video is at `~/Downloads/flicker-v2-check/01_ref_v1_v2_side_by_side.mp4`.

Plots:
* reference against v1: `flicker_plot_overview.png`, `flicker_plot_p1a.png`, `flicker_plot_p1b.png`, `flicker_plot_p2.png`;
* the extracted gain for ref / v1 / v2: `flicker_plot_gain_a.png`, `flicker_plot_gain_b.png`, `flicker_plot_gain_c.png`;
* `flicker_plot_v2_overview.png` and `flicker_plot_v2_part2.png`.

## 5. Remaining gaps

1. **The storm clip (frames 251–334) has its own lightning.** It includes a multi-frame decay at 320–334 that the frame-level deflicker cannot, and should not, remove. That is why this shot's correlation is 0.73 rather than about 0.95. For 1:1, pick a clip offset without lightning, or accept it.
2. **Crossfades.** v1 crossfades are 4–7 frames; the reference has a 16-frame dissolve at 122–140 and hard cuts elsewhere (a 3-frame mix at 392–394). This is a compositing and timing issue in `render_part1`, not flicker, and it changes the luminance envelope around line changes.
3. **Exposure and contrast.** `exposure=True` fixes the level, but it is calibrated on the v1 grading. A cleaner fix is to raise each line's `pct` in build.py: the reference has a lifted black floor and brighter highlights (p98 +40–80). After that, recalibrate with `python flicker_extract.py <new_render_dir>`.
4. **Part 2.** The luminance mismatch is structural (missed inversions and strobes) plus the base grade:
   * the snow clip is too bright in quiet frames: target p5/p50/p95 of about 9/56/214 against v1's 12/67/251, so scale the part-2 `make_grader` targets by about 0.85, roughly (10,58,228) → (8,49,194);
   * the flashes need to be brighter (about 230).
   `p2_match` forces the per-frame statistics, but it dims low-luma red text (e.g. 685) and greys out halftone frames (522, 612). Leave it off unless the glitch agent's output is structurally right.
5. **Grain.** v1's grain (σ 4 at 1080p) gives 1.5–2× the reference's high-frequency noise at 480p. Consider σ of about 2–2.5, or noise that is already softened.
