# Glitch-Drop Lyrics: editing grammar and component kit

A TikTok lyric edit in two modes.
- **Calm part (the song before the drop).** One thin, dirty, glowing serif line grows word by word on the sung syllables. It sits over dark night clips, with free-running VHS layers (flicker, tear, sway, grain).
- **The drop.** The text switches to CAPS. Every frame gets a glitch step from a 2-beat cell: over-exposure, invert strobe, halftone, bars, datamosh, freeze box, white or cyan flash. The cells loop until the end. The last word, the punchline, is red.

The style was reverse-engineered frame by frame from `IMG_2446.MP4` ("я стою на остановке … МАРШРУТКА"). The kit `lib/glitch_drop/` rebuilds that edit pixel-identically from one timeline JSON (`lib/glitch_drop/examples/reference_marshrutka.json`, mean MAE 0.016 against the approved v2). The planner `lib/glitch_drop/tools/plan.py` writes the same kind of timeline for any other song.

```
.venv/bin/python -m lib.glitch_drop.tools.music <audio>              # tempo, beat grid, drop candidates
.venv/bin/python -m lib.glitch_drop.tools.plan  --audio … --words … --clips … --drop-clip … --out timeline.json
.venv/bin/python -m lib.glitch_drop <timeline.json> <out_dir> [--preview | --frames a:b]
```

- **Cost:** zero. It needs numpy, PIL and ffmpeg in `.venv`.
- **Speed:** on this Mac, about 300 frames render in 45 s, so a full 23 s edit takes about 2 min.
- **Format:** 1440×1080 (4:3), 30 fps. The kit refuses other sizes, because every measurement is 480p × 2.25.

---

## Part 0: a new song, end to end

1. **Audio.**
   - Take only the sound of the link or file. The video is never used.
   - Trim to the excerpt the edit should cover (`--start/--end`). TikTok sounds usually run about 15–25 s, with the drop in the last third.
2. **Structure.** Run `tools.music` on the excerpt.
   - Read the tempo and the drop candidates.
   - Show the user the top one or two: "дроп на 16.4 с (такт 9), второй кандидат 15.9 с".
   - The drop is partly taste. If the user names another moment, pass `--drop SEC`.
3. **Lyrics + word times.**
   - Ask the user for the lyrics. Every word goes on screen, and ASR mishears slang and names.
   - Write one sung breath-phrase per line, keep the user's spelling, and include only what the excerpt contains.
   - Word times:
     - If `.venv-audio` exists, run `python -m lib.vhs_lyrics.tools.audio prep <file> <wd>` and then `align <wd> --chunks …` (see `skills/creative/vhs-kinetic-lyrics.md` Part 0). Its `words.json` is the planner's input as is.
     - Without the audio env, time the words by hand from the onsets: `[{"line": 0, "word": "я", "start": 0.0}, …]` in seconds of the original audio.
4. **Backgrounds.**
   - One dark night clip per calm line: street, stop, rain, wet asphalt, transport, lamps. Pick them by meaning where possible.
   - One clip for the whole drop: a lamp or headlight top over a dark floor reads best, because the regrade pushes the top bright and the bottom dark.
   - The user's default pool is `~/Downloads/visuals`.
5. **Plan.** Run `tools.plan`. It writes `timeline.json` and `plan_report.json`: lines, red word, cell table, crossfade length.
   - Check the line split and the red word against the lyrics.
   - Edit the JSON for anything else: a clip offset, a `grade.target`, or the same clip on two lines.
6. **Preview.** Run `--frames <drop-30>:<end>`, build a contact sheet of the drop and look at it. Look at a few calm frames too: the text must be readable and the clip dark.
7. **Render** to `~/Downloads/<project>/final.mp4`. Send it via the telegram-send skill if the user wants it there. Use a crf 23 copy when the file is over 50 MB.

---

## Part 1: the grammar (what fires when, in musical units)

Measured on the reference. The full evidence is in `lib/glitch_drop/docs/measure_grammar.md`, and every one of its 310 events is in `docs/reference_events.json`.

### Song structure
- **Tempo / grid.** A comb fit of the spectral flux. Reference: 117.46 BPM, so one beat = 15.32 frames and one bar = 61.3 frames.
- **The drop is NOT the first or the biggest bass entry.**
  - In the reference the sub goes up 30 dB at bar 5, and the edit ignores it completely.
  - The drop is the beat boundary with the largest step in the **bright/noisy** group (2–5 kHz, 5–16 kHz, spectral flatness, centroid) + 0.5× the low group, with the low end already present before it.
  - It is the start of the fullest section. Reference: bar 9, 16.446 s.
- **The edit has two modes only.** There is no third section, no build-up visual and no escalation inside the drop.

### Calm part (before the drop)
| rule | measured |
|---|---|
| **One screen = one sung breath-phrase**; two screens ≈ one 2-bar couplet. Lines alternate long and short. | 8 lines = 4 couplets, ≤ 25 characters (~82 % of the width) |
| **Words appear cumulatively, a hard cut on their own syllable.** They are not snapped to the beat. The line stays complete until the next line replaces it: no fade, no blank gap. | onsets ±2 frames from the vocal, spread uniformly against the 16th grid |
| **Word-in micro-event.** Frames onset−1 and onset get a ~4 px horizontal echo and ×0.8 brightness; onset+1 is sharp. | the only per-word event |
| **No word emphasis.** All words have the same size, weight (430) and colour. Emphasis is saved for the drop (caps) and the end (red). | |
| **One background clip per line.** It changes through a linear dissolve that **ends on the new line's first syllable**, ≈ 0.6 beat long (6–12 frames). A line inside a couplet may keep the same shot. | 7 clips for 8 lines; dissolve lengths hand-placed (r ≈ 0 with anything) |
| **Always-on layers are free-running loops that ignore the music**, and they all stop at the drop. Never beat-sync them. | text scanline tear 89 frames, flicker 3.18 + 7.38 Hz (≈ 179-frame repeat, ±7 %), x-wiggle 20 frames, y-sway 66.7 frames, rotation ±0.5°, vignette, grain σ 2.3, soft chroma split |
| The bass entry or any mid-song change before the drop gets **no** visual response. | |

### The drop moment
- **The frame that contains the downbeat** (drop frame D): a slight lift.
- **D+1:** a grey wash.
- **D+2:** the glitch section starts. Over-exposure ramps to white at D+4 (×1.9 → 2.6 → 3.4), then D+5 goes back to the image and D+6 is dark.
- The first caps word lands on its own syllable. There is no zoom, speed ramp or blackout before it, and the last calm line just holds.
- The background switches to the single drop clip.

### The drop: the glitch cell
- **One 2-beat cell, looped to the end.** The reference cell was a fixed 1 s; at 117 BPM that is 2 beats. The kit locks every cell to the beat grid, so there is no drift.
- **Cell length:** k ∈ {1, 2, 4} beats, whichever is closest to 1 s. That gives 2 beats at 85–170 BPM.
- **Anatomy** (p = step of the 30-step template, warped onto the real cell):

| p | beat in cell | effect | anchor |
|---|---|---|---|
| 0–3 | 0–0.2 | over-exposure / bottom white-out (A), grey wash (B), pale cyan (C) | the even beat |
| 4–15 | 0.25–1.0 | **INV strobe** (inverted frames 1–3 frames apart, ~12 Hz); specks; **halftone top on p8, thick bar on p9**; lines; iridescence | first beat and its "&" |
| 15–18 | 1.0–1.2 | **full-frame datamosh p15, freeze box p16**, mosh lower 60 % | the odd beat |
| **19–21** | ~1.25 | **FLASH**: 93 % → 100 % white/cyan, 3 frames | **the strongest 808/kick hit of the cell** (the planner nudges it ±3 frames onto the detected hit) |
| 22 | 1.45 | grey wash / teal | |
| 23–24 | 1.5 | clean frames, the text is readable | |
| 25–29 | 1.65–1.95 | bottom fills: displaced blocks, speck grid, **halftone bottom p27, bar B p28**, lines | pickup into the next cell |

- **Variation without escalation.**
  - Colour rotates A (white) → B (cyan) → C (pale) every cell.
  - The **INV strobe layer** is on for the first 3 cells, off for the middle ones (the song "breathes" on the middle lines), and **on again for the red-word cell**.
  - The audio energy is flat across the drop, and so is the visual energy: hit, then breathe, then hit for the punchline.
- **Drop text.**
  - CAPS (a section switch, not emphasis), ≤ 17 characters per line, 1–3 words.
  - Still cumulative on syllables.
  - The text jumps to a new random position every frame (σ ≈ 14 px), with motion smear on about 65 % of frames and a ghost of the previous position.
  - It is dimmed on blown-out frames and inverted with the frame.
  - The background does not shake much (jitter 9/6 px).
  - No grain or vignette in the drop; JPEG-style dirt instead.

### The red accent word
- **Which word:** the punchline, the last content word of the excerpt, put **alone on its own line** as the last screen. It is not acoustically louder. The choice is semantic (the payoff of the theme: автобус → маршрутка). When the last word is a filler, ask the user or pick the last strong noun or verb (`--red WORD`).
- **When:** on its sung syllable. The cell it lands in, or the next one if it lands in the second half of a cell, switches the INV layer back on. That cell is the red template m6: the over-exposure frames turn the word pink, and INV turns it green on dark.
- **Style:** crimson core (205, 30, 62), same glow and chroma split as the other text.
  - The reference measures weight 700 and ×1.55 cap height.
  - The approved v2 (the kit default) keeps the caps weight 560 and scales the word ×1.28 / ×1.27 (`look.drop_text.red_scale`), so it is the biggest word on screen and still fits the width.
- **Held to the end.**

### The ending
- **End on the audio cut:** no fade, no end card. The last glitch cell is simply truncated, and a tail shorter than half a cell joins the previous cell.

### Not derivable from the music (decide with the user / by meaning)
1. Which word is red, and whether it goes on its own line (default: the last word).
2. The drop, when two candidates score close.
3. Line breaks: breath phrases.
4. Clip choice, and which line keeps the previous shot.
5. Exact crossfade lengths (default 0.6 beat).
6. Where INV is off (default: the cells between the first 3 and the red cell).

---

## Part 2: the kit (`lib/glitch_drop/`)

| module | what |
|---|---|
| `timeline.py` | JSON loader and defaults; the schema is in its docstring. All times are in seconds; frame = round(t·fps). Lines starting at or after `drop.time` are drop lines (CAPS). |
| `grammar.py` | **the rules as code**: cell length, grid-locked cells, piecewise-linear warp of the reference cells with the flash anchored to the low hits, A/B/C × INV template choice, the red cell, short-tail merge, line splitting, crossfade length. |
| `tools/music.py` | numpy-only tempo / beat grid / drop detection / low (808) hits. |
| `tools/plan.py` | audio + words + clips → `timeline.json` + `plan_report.json`. |
| `glitch.py` | operators and the schedule engine. **The token language is documented in its docstring** (inv, expo, botw, hs, vs, soft, wash, tint, teal, cyaninv, palecyan, whitetop, black, flash, fill, mosh, box, lowblk, ht, dust, row, barA, barB, hl, line, iri, tre; text tv/th/td/tg/ta/tslice; meta tone/pos). |
| `text.py` | `IntroText` (thin glowing serif with chroma split, scanline tear, onset dim) and `DropText` (caps, smears, ghost, red). |
| `motion.py` / `flicker.py` | the measured intro loops (texture `assets/textures/reference_intro.json`, tiled), flicker, own-footage deflicker, per-line exposure, the 2-frame pre-drop lift. |
| `background.py` | clip load, grading (`{"target": luma}` or measured pct/rgb), dissolves, vignette, the drop regrade (bright top / dark bottom). |
| `render.py` | frames → `final.mp4` with the trimmed audio, or 640×480 preview PNGs. |
| `assets/patterns/reference_drop.txt` | the reference drop, 205 steps = 7 cells. Cells m0–m5 are the templates; m6 is the red cell. |
| `docs/measure_*.md` | the measurement reports: text, motion, flicker, glitch, grammar. |

### Timeline cheat sheet
```json
{"fps": 30, "size": [1440, 1080], "duration": 23.3,
 "audio": {"path": "song.m4a", "start": 0.0, "duration": 23.29, "fade_out": 0.03},
 "drop": {"time": 16.5, "schedule": "reference" | [ "seed: fx | tx | tone=… pos=…", {"pattern": "reference", "from": 0, "to": 30, "repeat": 2}, … ],
          "bg": {"clip": "drop.mp4", "offset": 0, "stretch": 1.37}},
 "lines": [{"words": [[0.0, "я"], [0.8, "стою"]], "clip": "street.mp4", "offset": 2.0, "xf": 0, "grade": {"target": 45}},
           {"words": [[16.5, "Я"], [17.1, "НАБЛЮЮ"]]},
           {"words": [[22.4, "МАРШРУТКА"]], "red": true}],
 "look": {"flicker": {"strength": 1.0, "pre_drop": true}, "grain": 2.3, "vignette": 0.28, "text": {"weight": 430}}}
```

### Tweaks people ask for
- **Weaker or stronger flicker:** `look.flicker.strength` (0 = off). `look.flicker.mode: "off"` disables the gain loop.
- **Darker or brighter calm clips:** `lines[i].grade.target` (median luma; the reference averages 45–55, the darkest shots 15–20).
- **Hand-placed glitch:** replace `drop.schedule` with your own list. Slices of the reference keep its exact look (`{"pattern": "reference", "from": 150, "to": 180}`), and single steps use the token language.
- **More glitch on a longer drop:** the planner simply keeps looping cells. Escalation is not part of this style; say so if asked, and do it only on request.

### Known limits
- Only 1440×1080.
- The intro tear and sway are the reference texture, tiled. They are free-running by design, which is the grammar.
- The pre-drop lift LUT was calibrated on the reference. On very different footage it can look slightly green; `look.flicker.pre_drop: false` turns it off.
- `examples/reference_marshrutka.json` uses absolute paths to `~/Downloads` (the reference and `visuals/`).
