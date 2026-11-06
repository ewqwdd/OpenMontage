# Segment A: frames 0–234 (frame 235 is already segment B)

Coordinates are in 960×720 pixels at 30 fps. The machine-readable spec is `segA.json`.

## Background

| Frames | Clip | Notes |
|---|---|---|
| 0–126 | **bg1**: night city from a height. A lit apartment block sits left of centre, there are car lights on the road, and the sky is black. | Fades in from black, linear over frames 0–14. Hand-held micro-jitter of ±1–3 px, no zoom. |
| 127–234 | **bg2**: dark foliage lit from below, with a pole in the lower middle. | Hard cut at 127, together with МОЯ. Slow pan: about +0.5 px/frame to the right (134–158), then −0.5…−1 px/frame (172–205), then still. |

Both clips have the same grade:
- very dark (mean of the lower band 7–10/255);
- strong vignette, with the edges at about 0.3 of the centre;
- almost no grain on the background (residual std 1–1.8).

## Word timeline

Each word appears on its sung syllable. The audio has flux onsets every 13.2 frames (≈136 BPM), starting at 20.5.

| Frame | Text | Colour | Cap (px) | Layout |
|---|---|---|---|---|
| 28 | КОГДА | white (224,223,232) | 257 | single, centre (481,340) |
| 33 | КИШКИ (replaces) | dim red (130,38,50), ×0.78 | 251 | single |
| 47 | ТОРЧАТ (replaces) | red (168,41,53) | 256 | single |
| 65 | + ИЗ | red | 256 | line re-centred, so ТОРЧАТ jumps left |
| 70 | + ПУЗА | red (155,38,49); brightness ramps 0.9→1 over 4 frames | 256 | re-centred |
| 83 | ОЧЕНЬ (replaces) | white | 216 | single |
| 95 | + СИЛЬНО | white, soft entry | 216 | re-centred |
| 109 | ХОЛОДНО (replaces) | cyan (119,197,200) | 397 | single, big emphasis word |
| 127 | МОЯ, with the background cut | red (159,37,47) | 323 | back layer |
| 138 | + ЛЮБОВЬ | red; brightness ramps 0.9→1 over 5 frames | 323 | re-centred |
| 151 | я | small white (241,231,229) | x-height 50 | front layer, centred over the back line |
| 155 | разделил | small white | 50 | cumulative, re-centred |
| 177 | бы | small white | 50 | cumulative, re-centred |
| 184 | этот | small white | 50 | cumulative, re-centred |
| 197 | холод | small cyan (140,199,189) | 50 | cumulative, re-centred |
| 216 | ПОРОВНУ (replaces) | teal (53,178,177) | 446 | single, biggest |

**Rules:**
- Within one sung phrase, words accumulate, and the line is re-centred on x=480 every time a word is added.
- A new phrase replaces the line with a hard cut.
- The phrase-final key word (ХОЛОДНО, ПОРОВНУ) is shown alone, larger (cap 400–450 instead of 220–320) and in cyan.
- From МОЯ ЛЮБОВЬ onward there are two layers: a big red back line and a small white lowercase front line on top of it.

## Font

The font fits Oswald Bold (wght 700, or 600 for МОЯ ЛЮБОВЬ), with IoU 0.51–0.64.
- **Big caps:** squeezed horizontally to x-scale 0.29–0.34 (≈0.31), with tracking about −4…+4 px.
- **Small lowercase:** x-scale about 0.6, weight about 500.

## Texture (pixel structure)

Crops at 4× nearest-neighbour are saved in `spec/`:
- `segA_x4_f030_kogda_topleft.png` (white)
- `segA_x4_f054_torchat_bottom.png` (red)
- `segA_x4_f036_kishki.png` (dim)
- `segA_x4_f112_holodno.png` and `segA_x4_f225_porovnu.png` (cyan)
- `segA_x4_f145_moya.png`
- `segA_x4_f160_small.png` (front small text)
- `segA_x4_f078_dotghost_left.png` and `segA_x4_f078_dotghost_right.png` (dot ghost)
- `segA_x4_f125_scanghost.png` (scan ghost)

### White and cyan words

- **(a) Vertical streaks** inside the glyphs:
  - about 2 px wide with a 4 px period;
  - running the full glyph height (vertical autocorrelation still 0.5 at 40 px);
  - contrast std 9–11 levels on white, 6–7 on cyan.
- **(b) Edge steps:**
  - rows move in bands of 20–70 px by ±1–2 px, re-randomised every frame on white words;
  - on glitch frames the bands are 8–30 px and the shifts 2–6 px;
  - rows always move in 2-row pairs.
- **(c) Grain:** 1 px, monochrome, vertically elongated, std 10–13. It is on the text only; the background is clean.
- **(d) Dither:** none on clean frames.
- **(e) RGB or prism split:** none (≤1 px).
- **(f) Navy halo:** symmetric, no offset.
  - Cyan words: (24,34,66), 99 % opaque to 8 px, 55 % at 16 px, about 0 at 24 px.
  - White words: (34,31,59), 85 % at 4 px, 50 % at 12 px.
- **(g) Softness:** edges are 5 px from 10 % to 90 %. The effective resolution is about 480×360, upscaled.

### Red words

- **(a) Vertical streaks:** weak and short.
- **(b) Edge steps:** nearly static, ≤1.5 px.
- **(c) Grain:** 1 px monochrome speckle.
  - std 9.5–10 on КИШКИ and ТОРЧАТ;
  - std 5.5 on the long lines;
  - std 4 on МОЯ.
- **(f) Ring:** dark maroon-navy (32,19,40), peaking at 50–57 % at 6–8 px from the edge and gone by 24 px.
- **(g) Softness:** edges are 7–8 px (10 px on КИШКИ), so the red text is softer than the white and cyan text.

### Small front text

- crisper (edge about 4 px), with slight ringing;
- a dark soft shadow of 4–6 px;
- low grain.

## Effects, and when they fire

| Effect | Frames | What it looks like |
|---|---|---|
| **dot_ghost** (on red lines) | 76–82, 164–171, 190 | See below. |
| **scan_ghost** (on white and cyan words) | 100–101, 107–108, 109–110 (entry), 122–126 (exit), 216–217 (entry) | See below. |
| **text_echo** (on the small line) | 164–166, 170, 190, 214 | A duplicate of the first letter or last word, offset −19…−47 px or to the right, about 1.1× bigger, sometimes dotted. It always coincides with a dot_ghost or a pre-cut. |
| **Entry frame of a new phrase** | entry frame, recovering over 1–2 frames (4–5 frames on multi-word lines) | Brightness 0.88–0.95 with a soft blur, plus a band shift or smear. |
| **Exit / pre-cut frame** | 126, 215, 234 | Dim to 0.85–0.9 and/or the top rows shift by −6 px. |
| **scratch_line** | 27–28 (dark, thin, diagonal over КОГДА's entry); 116–117 (white, dashed, about 6 px thick, curved diagonal from (135,495) to the upper right) | A film-scratch overlay lasting 2 frames. |
| **dim** | КИШКИ for its whole duration (×0.78); 181–183 (small line ×0.93–0.95); 191–198 (red ×0.88–0.95) | The text gets darker. |
| **dirt_blob** | 36–38, 43, 222 | Dark specks or blotches over letters. On 222 it comes with a light cross-dot patch on the upper right of ПОРОВНУ (x 516–833, y 118–322). |
| **fade_in_from_black** | 0–14 | Linear. |

**dot_ghost** (red lines):
- A desaturated grey copy of the whole line, made of small X/cross dots on a 45° lattice with a 6 px pitch, grey 60–150.
- It is scaled 1.07–1.3 about the line centre: at frames 78–81 it spans x 90–950 against the red 160–800.
- The red text under it dims to 0.75–0.9 and picks up dot texture.
- It starts on beat-grid onsets (73.3, 165.7, 192.1), lasting about half a beat (7 frames) or a single frame.

**scan_ghost** (white and cyan words):
- A grey, horizontally striped copy (stripe period about 12.8 px), scaled 1.08–1.3 about the centre or offset ±30–40 px.
- On the exit (122–126) it grows, and stripes appear inside the cyan letters too.
- It fires on entries and exits of the big white and cyan words.

## Unsure

- The dot_ghost scale is estimated from the bounding box of the grey mask: about 1.07 at 76–77, about 1.3 at 78–81, and about 1.17×1.24 at 165–170. The ghost may be a zoom-blur trail rather than one scaled copy.
- The exact scratch-line paths are approximate.
- The background lights in bg1 inflate some of the measured text bounding boxes (frames 61, 62, 67, 85, 87 and 90 are car lights, not text).
- Font identity: Oswald is the closest available fit (IoU ≤0.64, partly lowered by the rough edges). The real font could be a different condensed grotesk such as Bebas or Druk.
