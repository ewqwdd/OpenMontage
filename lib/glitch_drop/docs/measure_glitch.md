# Ending glitch section (frames 490–699): analysis and v2

All coordinates are in **480p px** (ref frame 640x480). Multiply by S=2.25 for the 1440x1080 render.
`p = (f-495) % 30`, `m = (f-495) // 30`. Ref file for frame f is `ref/f/{f+1:04d}.png`.

## 1. What the ref actually is (key findings)

1. **v1 already has the timing right.** v1's 30-frame cycle and its INV set match the ref: every
   inverted frame (500 502 503 505 507 510 / 529 531 534 536 538 539 / 562 563 565 567 570 /
   679 681 684 686 689) and every flash frame lands on the right frame. The difference is in what
   each effect looks like, plus the base frame. That is why v1 reads as "clean".
2. **The tonal layout is upside down.** In ref normal frames the top is bright and the bottom
   nearly black. Mean luma per 48-px row band, averaged over 40 normal frames:

   | y | 0 | 48 | 96 | 144 | 192 | 240 | 288 | 336 | 384 | 432 |
   |---|---|---|---|---|---|---|---|---|---|---|
   | ref | 114 | 128 | 125 | 101 | 93 | 65 | 28 | 26 | 24 | 28 |
   | v1 | 38 | 47 | 55 | 58 | 92 | 79 | 79 | 161 | 218 | 213 |

   The ref has a lit train ceiling and lamp at the top and a dark floor. v1 has dark trees at the
   top and a white snow road at the bottom. As a result every **inverted** frame is wrong in v1:
   the ref goes white with a dark "bird" blob at the top (mean about 190, bottom about 235), while
   v1 has a dark green bottom (bottom about 30–80).
   Band-luma error, ref vs v1: **67.5** on average, with 184 of 205 frames off by more than 25.
3. **The ref is very soft and compressed.** Mean |dx| sharpness is **1.32** for the ref and 2.95
   for v1. There is no crisp detail at all: everything is smeared along x, has TikTok
   macroblocking, and there are no visible snow particles.
4. **The text is a different shape.** Template search over scale (corr 0.6–0.78) gives the **same
   width as v1 but cap height ×1.45**: about 58–62 px against v1's 41. The text is tall,
   condensed and thin-stroked. Its colour is dim lavender: p99 = **(189,207,226)**, where v1 is
   (250,251,252) with a strong blue glow. The red word peaks at about **(160,30,65)**, where v1
   is (248,207,229).
   RGB split on the text only: R about +2 px, B about −1.5 px. The background has **0 px**
   channel offset, measured by phase correlation on 22 frames.
5. **The text moves a lot.** Measured text centre in good frames: x 300–347, y 204–262 (mean
   about 320, 228). This is an elliptical shake with a period of roughly 9–10 frames
   (…212,212,234,246… repeats). v1 jitter is σ≈3 px, against roughly ±22 px in the ref.
   Text is also often motion-smeared (vertical 10–26 px, horizontal 8–20 px, or diagonal) and
   ghosted by an echo of the previous frame's position.
6. **No mirroring, zoom punch or global shake.** Correlating normal and h-flipped templates gives
   0.59 vs 0.31, so the text is never flipped. Phase correlation finds no whole-frame
   displacement. The background motion is the original clip's own camera move.

## 2. Per-frame event table (compact)

`INV` = inverted, `HT` = halftone, `bar A` = p9 thick bar, `bar B` = p28 line+teeth, `mosh` = macroblock datamosh.
Mean ref RGB and top/mid/bottom luma for every frame are embedded in `glitch_v2.py` as `REF_TONE_TXT`.
Text centre per frame is embedded as `TPOS_TXT`.

| p | m0 (495–524) | m1 (525–554) | m2 (555–584) | m3 (585–614) | m4 (615–644) | m5 (645–674) | m6 (675–699) |
|---|---|---|---|---|---|---|---|
| 0 | over-exposure ×1.9, lower-left blown, x-smear 26 px (mean 155) | text sliced/torn | bottom white from y≈320 | over-exposure (227) | text ghost, v-smear | bottom white | over-exposed white, **pink text** |
| 1 | over-exp ×2.6, below y≈225 white (206) | clean | bottom white from y≈305 (bot 254) | over-exp | ghost | bottom white | over-exp pink |
| 2 | over-exp ×3.4, almost all white (226) | **gray wash** 87 (98/91/71), soft | **pale cyan inverted** (180,222,239), dark teal band y<115 | over-exp | gray wash 112 | pale cyan | over-exp pink |
| 3 | blue-tinted over-exp (160,172,193), v-smear | gray wash 102, text v-stretched | pale cyan, band y<118 | blue over-exp | gray wash 116 | pale cyan | over-exp pink |
| 4 | dark, very soft (58) | **INV** (212) | **white below y≈150**, lamp band on top, faint lavender text | dark soft | dark | white below 150 | **INV of over-exposed** = dark brown (60,55,34), green text |
| 5 | **INV** + x-smear | v/diag text echo | **BLACK** (4,3,1), olive text | normal | dark | **WHITE** 252, faint text | normal |
| 6 | white specks row y 150–195 | **INV** + dark specks | soft | normal | normal | normal | **INV** + dark specks |
| 7 | **INV** + column v-smear + dark speck rows y 35–70 / 160–185 | cyan speck rows | **INV** + dark speck rows | white specks | cyan specks | white specks | white specks |
| 8 | **INV** + **HT top** y 0–190 (dark stripes/light beads) + dash row y 425 | **cyan HT top** 0–188 + cyan dashes | **INV** + HT top | HT top (white stripes) | cyan HT top | HT top | HT top |
| 9 | **bar A** white y 211–240 + column v-smear above + lines below | **INV** + **red bar** y 210–241 (209,74,40) | bar A white 210–242 | bar A white | **cyan bar A** | bar A white 191–245 | **INV** + dark bar (48,65,61) |
| 10 | **INV** + thin lines + slices through text | cyan lines through text | **INV** + lines | white lines | cyan lines | white lines | white lines |
| 11 | **iridescent** lamp (oil-slick) | **INV** + heavy x-blur | normal | iri | normal | normal | **INV** |
| 12 | **INV** + iri (green/brown fringes) + soft | x-blur | **INV** | iri | normal | normal | iri |
| 13 | iri, text v-stretched | **INV** + x-blur | normal | iri | normal | normal | iri |
| 14 | iri strong, soft | **INV** + blur | normal | iri strong top-left | normal | normal | **INV** + iri |
| 15 | **INV + full-frame mosh**, dark line y 160 | **cyan-white INV over-exposed** + mosh + cyan line y 163 | **INV** + full mosh | mosh + iri | cyan INV over-exp + mosh | mosh | mosh + iri |
| 16 | **top-left frozen box** x 0–490 y 0–195 + inner box | cyan INV + box | box | box | cyan INV + box | box | box |
| 17 | dark, soft | cyan INV whiter | normal | normal | cyan INV | normal | normal |
| 18 | mosh lower 60% (text intact) | cyan INV + mosh | mosh | mosh | cyan INV + mosh | mosh | mosh |
| 19 | white flash 93% with faint blocky structure | **cyan flash** (24,199,235) | white flash | white flash | cyan flash | white flash | white flash |
| 20–21 | full white (254) | full cyan (21,211,249) | white | white | cyan | white | white |
| 22 | gray wash 158 (187/156/131), lower half v-stretched | **teal** image (43,136,159) | gray wash | gray wash | teal | gray wash | gray wash |
| 23–24 | clean (68), text crisp | text echo, h-smear | text v-smear echo | clean | dark clean | clean | – |
| 25 | lower displaced rectangles + speck row y≈297, diagonal text smear | teal + lower blocks + cyan specks | lower blocks | lower blocks | teal + blocks | lower blocks | |
| 26 | lower sparse speck grid (21×16 px) + blocks | cyan speck grid + iri | speck grid | speck grid | cyan grid | speck grid | |
| 27 | **HT bottom** y 290–480: bright field, dark holes | cyan HT bottom | HT bottom | HT bottom | cyan HT bottom | HT bottom (red text) | |
| 28 | **bar B** line y 240 + dash teeth 248–262, dark below | cyan bar B | bar B | bar B (+ line 212) | cyan bar B | bar B | |
| 29 | thin lines + slices through text | bottom white y>330 + cyan lines + iri | lines, faint text | lines, ghost | bottom white + cyan lines | lines | |

490–493 belong to part 1 (normal). **494** is a washed transition frame (mean 111, very soft).
v1 leaves 494 untouched, but it lives in part 1, so `glitch_v2` does not handle it.

Effect geometry measured in the ref:
- **Halftone grid**: period 21 px (x) × 16 px (y), holes about 10 px. Top band is y 0–190,
  bottom band y 290–480.
- **Bar A**: y 211–240. A solid band about 24 px thick with a scalloped top edge (16-px period).
  Below it is a dark band 40 px tall with thin light lines at +13 and +27 px.
- **Bar B**: a 5-px line at y 240–242, then a row of 11-px dashes 248–262.
- **Box**: x 0–490, y 0–195, posterised and edge-enhanced. Light 2-px border on the bottom and
  right. Inner box at x 335–480, y 32–150.
- **Mosh**: rectangles snapped to an 8-px grid, 8–64 px wide and up to about 96 px tall. Each is
  filled with the vertical pixel-stretch of its top row, which gives the ref's vertical streak
  columns. Some are stale or shifted copies.

## 3. Discrepancies v1 → ref, most impactful first

1. **Base tonal layout inverted.** Bright snow road at the bottom, dark top. This wrecks all 22
   INV frames, every "bottom white" frame and the overall look. Error 67 against 5.5 after v2.
2. **v1 is far too clean.** Sharpness 2.95 vs 1.32, crisp snow flakes, no compression blocking,
   no x-smear.
3. **Text style.** v1 uses bold, short, bright white-blue text with a heavy glow. The ref text is
   tall (×1.45), thin, dim lavender with an RGB split. The red word is also far too bright and
   pink in v1.
4. **Text motion.** No big shake, motion smear or echo ghost in v1. The ref moves the text
   ±22 px and smears it on about 60% of frames.
5. **Over-exposure frames** (495–498, 585–588, 675–678). v1 draws a fake blurred purple blob. The
   ref is the real image pushed ×2–3.4 with the lower part blown out along content edges. On
   675–678 the text turns pink.
6. **Mosh.** v1 draws 48-px gray mosaic squares in the lower half only. The ref has
   vertical-streak blocks over the full frame on p15 and the lower 60% on p18, with stale copies
   of earlier frames.
7. **Halftone.** v1 draws white dots on black (an LED look). The ref has a bright field with dark
   holes (bottom), or bright stripes with dark gaps (top), modulated by the image.
8. **Bars.** v1's bar is 7 px; the ref's is 29 px with scalloped teeth. v1 has no bar B
   (line + dash row).
9. **Box.** v1's threshold rectangle sits top-right at 0.56–0.86 W. The ref box is top-left
   (0–0.77 W, 0–0.41 H), a posterised copy with a nested inner box.
10. **Iridescence.** v1 shifts the channels ±10 px over the whole frame. The ref has no channel
    shift on the background, only oil-slick hue bands on the highlights.
11. **Specks.** v1 scatters random white dots. The ref specks are snapped to the 21-px grid
    columns in a few rows. They are dark on INV frames, cyan in m1/m4, and include the dash row
    at y≈425.
12. **Wrong special frames.** 560 should be black with olive text, 650 white with faint text.
    557/558 should be pale cyan *inverted* with a dark teal top band. 559 should be white below
    y≈150. 619/620 should not be gray-washed (v1 washes them to 169; the ref is 59/56). 679 is
    inverted over-exposure (dark brown), not a light INV.

## 4. What v2 implements (`reports/glitch_v2.py`)

- `SCHED_TXT` is the per-frame schedule (495–699), written from the table above. Each line looks
  like `f: <frame ops> | <text ops>`. The ops are: `inv, expo, botw, hs, vs, soft, wash, tint,
  teal, cyaninv, palecyan, whitetop, black, flash, fill, mosh, box, lowblk, ht, dust, row, barA,
  barB, hl, line, iri, tre`. The text ops are `tv, th, td` (smear), `tg` (echo ghost), `ta`
  (alpha) and `tslice`.
- `REF_TONE_TXT` holds the measured ref mean RGB plus top/mid/bottom luma per frame.
  `tone_match()` pulls each frame toward those values at strength 0.85. This keeps the
  brightness and tint rhythm exact even though the footage differs.
- `TPOS_TXT` holds the measured text centre per frame. Frames with corr < 0.40 are filled by
  interpolation.
- `grade_bg_v2()` regrades the background for part 2. It shifts the background up 55 px so the
  lamp sits higher, applies softness 1/4 plus an x-smear, a soft-knee on the lamp, a row
  gain/lift to the ref layout, and an anisotropic horizontal glare.
- `text_mask_v2` / `text_canvas_v2` / `compose_text_v2` build the tall thin text (weight 560,
  sx 1.02, sy 1.45), place it at the ref position, then apply smear, ghost, dim colour and the
  text-only RGB split.
- `glitch_frame_v2(base, f, tmask=None, red=False, ctx=None)` has the same convention as v1. It
  applies the schedule, then `tone_match`, then a 720×540 JPEG q38 round trip (TikTok blocking).
  `ctx['prev']` feeds the datamosh stale blocks.
- `render_part2_v2(writer, B, ctx=None)` is a drop-in replacement for `render_part2`.

## 5. Integration into build.py

```python
# top of build.py
sys.path.insert(0, SCR + '/reports')
import glitch_v2

# in main(): replace both calls  render_part2(writer)  with
glitch_v2.render_part2_v2(writer, sys.modules[__name__])
```

- Keep part 1 untouched. `render_part2_v2` does its own background crop and jitter (per-frame
  seeded), its own text, and the glitch.
- **Grain:** the writer adds `normal(0,4)` grain to every frame. The ref glitch section has none,
  because TikTok compression smooths it. Recommended: use `g *= 0 if f >= G0 else 1`, or σ≈1.5,
  for f >= G0.
- When previewing with `--frames a:b`, the function also renders frame a−1 as a warm-up so the
  datamosh has a previous frame. It does not write that frame.
- If you only want the effect layer, call `glitch_frame_v2(img, f, tmask, red, ctx)` with
  `ctx = {}` kept across frames. The full look, however, also needs `grade_bg_v2` and the v2
  text (`text_canvas_v2` + `compose_text_v2`). Those are the biggest wins.
- Cost: about 0.45 s per frame (205 frames ≈ 1.5 min).

## 6. Results

Comparison sheets (ref on top, v2 below) are `reports/glitch_cmp_*.png`.

All 205 frames (495–699) were rendered with `work_glitch/render.py`, which uses build.py's own
machinery (`load_clip`, `make_grader`, `bloom`, `soften`, `GLINES`) on a copy, plus the same
grain writer. Output is in `work_glitch/out/`.

| metric (480p) | v1 | v2 | ref |
|---|---|---|---|
| mean abs error of top/mid/bottom band luma vs ref | 67.5 | **5.5** | – |
| frames with band error > 25 | 184 / 205 | **3** | – |
| sharpness mean abs dx, frames 517–531, no grain | 3.31 | **1.67** | 1.71 |
| sharpness with build's σ4 grain | 2.95 | 2.55 | 1.32 (all 205) |

Sheet coverage:

| Sheet | Contents |
|---|---|
| `glitch_cmp_1.png` | Over-exposure, INV, halftone top, bar A, iridescence, mosh, box |
| `glitch_cmp_2.png` | Flash, gray wash, lower blocks, speck grid, halftone bottom, bar B, slices |
| `glitch_cmp_3.png` | Cyan cycle: cyan halftone, red bar on INV, cyan-INV over-exposure, cyan flash, teal |
| `glitch_cmp_4.png` | Bottom-white, pale cyan, white-top, black frame, INV specks/halftone |
| `glitch_cmp_5.png` | m3/m4 repeats |
| `glitch_cmp_6.png` | Cyan repeats, white 650, МАРШРУТКА halftone/bar, pink over-exposure |
| `glitch_cmp_7.png` | Ending: 679 dark INV, INV bar, iridescence, mosh, box, final frames |

## 7. Remaining gaps

- The footage is different. The ref has a lit train interior with a ceiling lamp and rays; we
  have a street lamp in snow. The lamp is still a tall bright cone rather than the ref's
  ceiling glare, and the inverted frames show a round dark blob where the ref shows a winged
  shape.
- Over-exposure frames (495–497, 585–587) look more uniform than the ref, where real highlights
  blow out in irregular shapes.
- Datamosh "stale" blocks come only from the previous frame. The ref sometimes shows blocks from
  much older frames.
- The text ghost is an echo of the previous frame's position. In some ref frames (530, 579) there
  are two or three echoes.
- 494, the part-1 transition wash, is not handled (it is outside part 2).
- Tone matching is data-driven from the ref. If the background clip changes, the gains adapt but
  are clipped to [0.3, 3].
