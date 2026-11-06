# Segment B — frames 235–436 (ref.mp4, 960x720 @30)

Frames 437–440 are already the next shot (dark ground, no text) and 441 = «ПОЛ» → segment C.
Full per-frame data: `segB.json` (`letters_per_frame` for the A-line, `state_per_frame` for ЮРА/ХОЙ/ЗА УПОКОЙ, `frames` notes).

## Word timeline (frame of appearance)

| frame | event |
|---|---|
| 235 | cut to BG1 (night sky, tree, lamp). «МНЕ» (A-line, cap top y=308, centred x=480) |
| 241 | + «КАЖЕТСЯ,» |
| 255 | cut to BG2 (cloudy sky + cable). + «МНОЮ» — 7-frame entry glitch 255–261 |
| 270 | + «ГОРДИСЯ» (spelled without Л) — smear, sandy grain, 12 px scanlines 271–273 |
| 287 | + «БЫ» (line squeezed to 129–812) |
| 297 | line jumps UP to y=228; red «САМ» below (cap 160, x 386–568) |
| 300 | «ЮРА» huge (cap 294, top 192, x 129–479) – first as dark silhouette, white from 301 |
| 313 | «ХОЙ» (x ~520–831) – silhouette 313–314, white 315 |
| 336 | hard cut to BG3 (black + lit windows). «НАДЕЮСЬ» (C-line cap 72, top 428) |
| 359 | + «ВСЕ» · 364 + «МОИ» · 377 + «КЕНТЫ» · 392 + «ВЫПЬЮТ» |
| 413 | «ЗА» (cap 179, top ~232, x ~136–235) wipes in top-down; 414 full, 415 dim, 416 off |
| 417 | «ЗА УПОКОЙ» (centred x~500) – flickering prism word until 435 |
| 436 | ЗА УПОКОЙ off, C-line sliced; 437 cut |

## Font
- Oswald 700, horizontally squeezed to **xscale ≈ 0.49–0.53**. Tracking is about 0.005 em (0.02 em for ЮРА ХОЙ).
- The A-line is squeezed further to fit a maximum width of about 685 px: 0.53 → 0.46 → 0.41 as words are added.
- The reference Д has a shorter descender than Oswald, so the original is probably a Bebas-Cyrillic-like face. Oswald is the closest one we have.
- Cap heights: A-line 89, САМ 160, ЮРА/ХОЙ 294, C-line 72, ЗА УПОКОЙ 179.
- Colours:
  - A-line (220,219,221)
  - C-line (229,225,224)
  - ЮРА (221,221,219)
  - ЗА УПОКОЙ (230,232,216), cream
  - САМ (167,37,40), p90 (197,52,56)

## Effect rules (when / why)

1. **A-line glyph dropout** (235–335). Every glyph is randomly on or off, chosen afresh every frame, with 30–55% of glyphs off. There is no hold. This is the whole look of the "мне кажется…" phrase. From 297 on, the first word МНЕ is mostly off.
2. **A-line is always soft and glowing.**
   - Horizontal edge width 6–10 px, vertical 6–10 px.
   - Bloom σ ≈ 18 px at about 25% strength.
   - Grain is 1 px, monochrome, std 8–17, regenerated every frame. It covers only the text and its halo (a rectangle about the phrase bbox + 25–60 px). The background has no grain.
3. **Word-entry glitch on the A-line.**
   - On 255–261 (МНОЮ): smear, 6 px quincunx halftone blocks and h-slices, and the box stretches vertically about 1.3×.
   - On 270–273 (ГОРДИСЯ): smear, the densest grain, and 12 px scanlines.
   - Extra strong-smear single frames: 238–239, 247, 250, 252–253, 266, 274, 280–281, 284, 291, 306–307, 325, 330.
4. **The red САМ** sits under the line and is also hit by dropout ('СА', then 'С М'). From 301 it is mostly covered by ЮРА, and only its red М peeks out between ЮРА and ХОЙ.
5. **The big words ЮРА / ХОЙ** each flicker independently, with four states:
   - **W**: white with a spectral prism split, 5–6 tinted copies. Red/orange sits on the left of each edge and cyan/blue on the right, with a spread of 12–16 px.
   - **S**: the fill is off and only an opaque, glyph-shaped dark plate (21,15,17) remains, so the word reads as a black silhouette knocking out the back line.
   - **B**: about 35% opacity, navy/cyan tint, halftone.
   - **M**: dim and sliced.
   - The sequences are in the JSON. ЮРА is about 65% W.
   - Extra glitches: white solid blocks left of ЮРА on 303–304; thin red lines on 312 and 327; RGB-split bottom slices on 319, 325 and 334.
6. **The C-line is clean and sharp.**
   - Edges are 2 px. The texture is a static grunge: grain std about 7, held between frames (correlation 0.8–0.99), plus vertical streaks.
   - Glitches come only from these sources:
     - entry smear+halftone frames on new words: 359, 362–363, 376–377, 392;
     - a scale pop of 1.25× on 345–346;
     - echo/slices on 344 and 347–350;
     - **a zoomed ghost copy** (1.20×/1.30×, top-anchored, 25–35% opacity, halftone, letters sticking out at x≈82 and ≈879) on 370, 378, 388–392, 395–400, 406–411, 422, 428, 430 and 434–436;
     - a pink light-leak ellipse behind the left half on 388–392;
     - a white scratch on 386–387.
7. **ЗА УПОКОЙ** has a rainbow prism of about 6 copies spread about 30 px, with a navy fringe (38,85,156) and edges 16–22 px soft. It flickers on and off:
   - ON: 417, 418, 420, 421, 423, 425, 427–430, 432, 434, 435.
   - DIM: 419.
   - OFF: 422 (only RGB bokeh specks), 424, 426, 431, 433, 436.
   - On 425 and 435 it is enlarged with halftone and scanlines (5.5 px); 434 has white block slices.

## Backgrounds
- **BG1, 235–254.** Navy foggy sky with a tree and a warm lamp at about (625,385). Corners about 6, top about (20,20,25).
- **BG2, 255–335.** Cloudy sky with a power cable. The camera tilts handheld, so the lamp travels from (648,455) to (561,540) and then up to (487,431). Top about (25,27,34).
- **BG3, 336–436.** Warm-magenta black with pixel-blocky lit windows in the lower half. Locked off, drifting ±1 px/frame.
- All three have a strong vignette (corner/centre about 0.2).

## Texture (4× NN crops in this folder)
- `B270_dither_x4.png`: the sandy 1 px grain on the A-line.
- `B255_halftone_x4.png`: 6 px quincunx dot dither on the entry glitch.
- `B280_blocks_x4.png`: slices and halftone blocks.
- `B301_prism_x4.png`: the ЮРА prism fringes.
- `B418_zaupokoy_x4.png`: the rainbow prism.
- `B340_clean_shadow_x4.png`: clean C-line, with static specks and sharp 2 px edges.
- `B396_ghost_x4.png`: the zoomed ghost copy.
- `B362_smear_x4.png`: entry smear.
- `B241_reveal_x4.png`: dropout reveal.

## Unsure
- The exact font. Oswald is an approximation, and the IoU of only about 0.36–0.58 is partly due to blur.
- The positions of the first-word glyphs late in the A-line (the dropout map for МНЕ after 287 may be biased by fit drift).
- The prism copy count and offsets are estimated from edge colour sequences, not decomposed exactly.
- Whether the C-line ghost is a separate layer or a scaled duplicate with an echo.
- The S-state plate opacity (about 0.85) is inferred.
