# Segment C: frames 437–646 (ПОЛ ЛИТРА КОНЬЯКА / ГОЛОВА КРУЖИТСЯ / ЗАНИЖЕНАЯ ШАХА / ДЕВЧАТА МУТЯТСЯ)

The machine-readable version is in `segC.json`. Coordinates are in reference pixels (960×720).

## Word timeline (hard cuts throughout, no dissolves)

| frame | event |
|---|---|
| 437–440 | Near-black empty frame |
| 441 | **ПОЛ** cuts in with a 1-frame glitch |
| 451 | **ЛИТРА** cuts in with a 1-frame glitch. ПОЛ stays where it is: the line is laid out in its final position, x 128–854. |
| 460 | Slice glitch on ПОЛ ЛИТРА |
| 463–493 | **КОНЬЯКА** strobe against ghost frames of ПОЛ ЛИТРА |
| 494–496 | Cut to the road/trees background, no text |
| 498 | **ГОЛОВА** (a different font) strobes on/off |
| 514/515 | **КРУЖИТСЯ** appears below it; both lines flicker independently until 540 |
| 541 | Cut to the street-lamp background + **ЗАНИЖЕНАЯ** (serif), ramping up to full brightness by 545 |
| 569 | **ШАХА** in red Oswald, cut in over the middle of ЗАНИЖЕНАЯ. The middle letters are hidden; ЗА…АЯ show at the sides. Navy shadow. |
| 598 | Both dim to about 60% |
| 599 | Cut to a dark background + **ДЕВЧАТА**, centred |
| 619 | **МУТЯТСЯ** arrives with a heavy glitch. The **line re-centres**: ДЕВЧАТА jumps from x 337 to 174. |
| 645 | Cut to ДАВАЙ (segment D) |

## Fonts

All measured by IoU fits against the mask.

- **Oswald Bold (700)**, squeezed horizontally:
  - ПОЛ ЛИТРА: cap 226, xscale 0.52. IoU 0.87 on ПОЛ, the best of Oswald 500/600/700, Anton, Fjalla and Bebas.
  - КОНЬЯКА: cap 300, xscale 0.50.
  - ШАХА: cap 251, xscale 0.42.
  - ДЕВЧАТА МУТЯТСЯ: cap 124, xscale 0.60.
  - Tracking is slightly tight, −4 px.
- **ГОЛОВА / КРУЖИТСЯ:** a bold, medium-width geometric grotesque. The closest free font with Cyrillic is **Montserrat Bold/ExtraBold at xscale ~0.72**. This is uncertain: the fringes keep the IoU at about 0.3. Rubik Bold or Golos Bold are alternatives. Caps are 160 and 62.
- **ЗАНИЖЕНАЯ:** a Times-like regular serif. **PT Serif Regular** at xscale ~0.92 is the best of those tested; Tinos was worse. Cap 64.

## Effect rules (when and why)

1. **Hard cut on the syllable.** Each new word appears on a hard cut. Most word entries carry a **1-frame glitch-in**: a scanline-striped ghost of the whole line offset −45…−60 px left, with a 12–13 px stripe period and 50% duty, plus 1 px mono dither noise in rectangular blocks. Seen at 441, 451, 619–621 and 615.
2. **Held frames are almost clean.**
   - A very faint ghost sits dx −48 px left, luma ~27 against a background of 15.
   - Black dust specks are static.
   - The text bbox is steady to 1 px: no shake.
3. **Occasional 1-frame slice glitch while a word is held.** It happens about every 8–20 frames: 460, 550, 615, 640. The frame splits into 2–3 horizontal bands with different dx (up to −56 px), with 13 px stripes.
4. **The strong word strobes.** КОНЬЯКА and ГОЛОВА alternate with ghost or off frames at roughly 2 on : 1 off, irregularly.
   - КОНЬЯКА ghost frames show the previous line dim and smeared. The exact sequence is in the json `strobe_pattern`.
   - ГОЛОВА ghost frames are empty background. ГОЛОВА also gets right-crop frames ("ГОЛО", "ГОЛОР").
5. **Prism/RGB split only on the strobe words.** It applies to КОНЬЯКА and ГОЛОВА/КРУЖИТСЯ. R is +6…7 px, B is −8…−10 px against G, each blurred 6–8 px, which reads as a continuous rainbow (violet→cyan→white→yellow→orange). On the calm words (ПОЛ ЛИТРА, ЗАНИЖЕНАЯ, ДЕВЧАТА) the channels are at 0.
6. **Accent word.** ШАХА is the red accent, (170,42,50), with a navy shadow (30,22,60) at dx +8, about 4 px blur and a 6 px halo. It sits over the knocked-out middle of the calm line.
7. **Mirror/wide ghost on ЗАНИЖЕНАЯ.** It is intermittent (frames listed in the json): a dim copy 1.1–1.2× wider whose glyphs read mirrored at the ends (Ɛ…R).
8. **Vignette is applied over the text.** Letters near the frame edges are darker: ПОЛ's left stem is 150, centre letters 235.

## Texture: pixel level

Crops are in `spec/`:

- `segC_x4_456.png`: clean Oswald with faint vertical streaks.
- `segC_x4_441.png`: glitch-in with dither noise and a block step.
- `segC_x4_470.png`: КОНЬЯКА prism bands.
- `segC_x4_585.png`: ШАХА with navy shadow and checker dither.
- `segC_x4_626.png`: ДЕВЧАТА with dark vertical drips.
- `segC_x6_529_halftone.png`: halftone, 4 px pitch, 45°.
- `segC_x6_619_ditherghost.png`
- `segC_x6_467_scanband.png`
- `segC_x6_615_blocks.png`
- `segC_x2_511_golova.png`
- `segC_x2_545_zanizhenaya.png`

Texture measurements:

- **(a) Vertical streaks.**
  - Clean Oswald: 2–3 px wide, 8–16 px long, contrast 3–5 levels.
  - ДЕВЧАТА: strong dark drips from the top edge, 1–2 px wide, 16–30 px long, contrast 20–30 levels.
- **(b) Block steps.** They appear only on glitch frames: bands 8–90 px tall, steps 3–56 px, changing every frame.
- **(c) Grain.** Mono, 1 px, std 2–6 over the whole frame. The glitch-in blocks have strong 1 px dither, std ~28.
- **(d) Halftone and dither.**
  - Halftone dots at 4 px pitch, 45°: ГОЛОВА 529, the КОНЬЯКА 484 blob, faint inside КОНЬЯКА.
  - 2–3 px checker on ШАХА's lower part.
  - Sparse dot/cross dither at 3–4 px on the ghosts at 619/631/644.
- **(e) Prism.** 3 blurred channels at R +7 / B −10 make 5–6 visible hue bands, about 17 px of fringe per edge.
- **(f) Navy shadow.** It is only on ШАХА, as above.
- **(g) Softness.**
  - Edge ramp is about 2 px. The whole thing looks like roughly 540p upscaled, with faint 8 px compression blocks.
  - The prism words are softer, about 480p.

## Backgrounds

| frames | background |
|---|---|
| 437–493 | Near-black warm grunge |
| 494–540 | Night path between trees with block lights upper-left. Violet-blue tint (22,18,23), slow drift. |
| 541–598 | Street lamp with bloom top-centre, neutral dark. The lamp rises slowly, then about 5 px/frame from 590. |
| 599–644 | Very dark, teal sky patches at the top |

All backgrounds have a strong vignette.

## Unsure

- The ГОЛОВА font. No good fit was possible through the fringes.
- The exact mirror logic of the ЗАНИЖЕНАЯ ghost: per-glyph mirroring versus a wide copy.
- Background motion is unmeasurable on these dark plates; the phase correlation was noise-dominated.
- Ghost-frame content at 463/469… is the previous line heavily processed. It may actually be a darkened, inverted-luma copy.
