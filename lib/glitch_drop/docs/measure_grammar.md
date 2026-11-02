# Editing grammar of IMG_2446: when and why each effect fires

This report covers when each effect fires and why, measured against the music. Earlier reports (`text.md`, `motion.md`, `flicker.md`, `glitch.md`) cover what each effect looks like. Rules are written in musical units, so they can be re-applied to another song.

**Conventions**
- Frames are 0-based and the video runs at 30 fps. Frame f covers the time window [f/30, (f+1)/30).
- Beat index b: t = 0.100 s + 0.5108 s · b. The bar number is floor(b/4)+1, and the beat in the bar is b mod 4 + 1.
- Confidence: **H** means measured and unambiguous. **M** means measured but with only a few samples, or with another reading possible. **L** means inferred or proposed.

Scripts are in `work_grammar/`. Data is in `reports/grammar_timeline.json`, which has 310 events, each tagged with its beat, bar and beat-in-bar. The figures are `grammar_overview.png` and `grammar_p2_cycles.png`.

---

## 0. Verdict on the user's read

> "Some effects are always on and the text treatment is the same throughout. At the drop a lot of glitch combinations appear, and that's the whole trick. At the end the most accented word is red."

Mostly right. Four refinements, all backed by measurements:

1. **The always-on layers are part-1 only, and they are not tied to the music.**
   - These layers are the flicker, the text scanline tear, the text wiggle, the sway and the vignette.
   - Each one is a free-running loop: tear 89 fr, flicker ~179 fr, x-wiggle 20 fr, y-sway 66.7 fr.
   - None of these periods relates to the 15.32-frame beat.
   - They all switch off at the drop.
2. **The text treatment changes once, at the drop.**
   - Part 1: thin lowercase serif, gentle jerky wiggle.
   - Part 2: ALL CAPS, re-placed at random ±14 px every frame, smeared on about 65 % of frames.
   - Caps is a section switch, not emphasis on single words.
3. **The "glitch combinations" are one fixed 1-second (30-frame) preset, looped 7 times.**
   - The loop has three colour variants (white, cyan, pale) that form a 3-s super-loop.
   - An invert-strobe layer is on for the first 3 s, off for the next 3 s, and on again for the red word.
   - The 1-s loop is almost exactly 2 beats (30 vs 30.65 frames). As a result, the full-white flash lands on the big syncopated 808 hit of every 2-beat cell: 0–1 frame off in the first five cycles, drifting to 3 frames early by the end.
   - The drop itself is the strongest arrangement change in the song (bar 9 of 12). It is not the first bass entry (bar 5), which the edit ignores.
4. **The red word is the last word and the punchline (МАРШРУТКА), shown alone on its line.**
   - It is red, heavy and 1.55× bigger than the other caps.
   - It appears on its sung syllable, about 1 beat before the final glitch cycle.
   - It is held until the audio hard-cuts.
   - Its "accent" is semantic and positional. It is not acoustic: the mix energy is flat across bars 9–12.

---

## 1. Music analysis (numpy only, `work_grammar/*.py`)

### 1.1 Tempo and grid (H)

- The autocorrelation of spectral flux peaks at **0.510 s** in every band. The 1.02 s two-beat pattern is equally strong.
- A comb fit over the whole song gives **P = 0.5108 s = 117.46 BPM = 15.32 frames per beat**, with phase **0.100 s**.
- One bar is 2.043 s, or 61.3 frames.
- Folding the onsets of every band onto a 16-step bar puts the maxima on steps 0 and 8 (beats 1 and 3). This holds in both pre-drop sections.
- Two independent checks confirm the downbeat phase. The two structural changes fall exactly on bar lines:
  - the bass entry at 8.273 s is the bar-5 downbeat (grid 8.273 s);
  - the drop at 16.45 s is the bar-9 downbeat (grid 16.446 s).
- There is no tempo drift. In 4-s windows the local phase stays at 0.10 ± 0.01 s throughout 0–12 s.
- Late windows show a half-beat "phase" because the 808 pattern becomes syncopated, not because the tempo changes.

### 1.2 Sections (per-bar band means, `dropdet.py`) (H)

| bars | time | frames | sub <90 Hz | 2–5 kHz | 5–16 kHz | spectral flatness | what happens in the edit |
|---|---|---|---|---|---|---|---|
| 1–4 | 0–8.27 s | 0–247 | **−8 dB (absent)** | 22–27 | 10–17 | 0.15–0.25 | part 1 |
| 5–8 | 8.27–16.45 | 248–492 | **+25…33 dB** | 26–31 | 16–21 | 0.26–0.35 | part 1, unchanged. **The edit ignores this boundary.** |
| 9–12 | 16.45–23.29 | 493–699 | 35–39 | **35–36 (+5)** | **27–29 (+7)** | **0.44–0.48** | part 2 (glitch) |

- **Before the bass entry (bar 5) there is a gap.** Mid, presence and high bands dip 5–10 dB between 8.15 and 8.26 s (a classic "pre-drop cut"), then the 808 enters at 8.27 s.
- **Before the real drop (bar 9) there is no gap.** Bar 8 is a mild build: sub +4 dB and presence +3 dB over bar 7. Its loudest event is an 808 pickup at 16.20 s (frame 486, beat 31.5), half a beat before the drop. The last part-1 word, "что", sits on that pickup (frame 487).

### 1.3 How to find "the drop" automatically (M; rule proposed, validated on this song)

The drop is **not** the biggest low-end jump. In this song the biggest low-end jump is at bar 5 (+30 dB sub), and the editor did nothing there.

The bar-9 drop is the boundary with:
- the largest jump in the *bright/noisy* group: 2–5 kHz + 5–16 kHz energy, spectral flatness, and centroid. Its step score is 4.45, against 0.34 at bar 5;
- a full low end already present before it;
- the "fullest" section of the song after it. Every band is at its maximum and flatness is at its song maximum.

Algorithm:
1. Beat-track the song and build bars.
2. For each bar line b (prefer multiples of 4 bars), compute z-scored per-beat features: sub, low, 2–5k, 5–16k, flatness, centroid, flux. Then compute Δ = mean(next 4 beats) − mean(previous 4 beats).
3. Score = Σ Δ over {2–5k, 5–16k, flatness, centroid} + 0.5·Σ Δ over {sub, low}.
4. Accept only bars where the sub is already present before the boundary, or where the section after it is the loudest of the song.
5. Choose the highest score. In the last third of a TikTok excerpt this is usually the chorus.
6. Snap to the downbeat. The visual transition starts on the frame that contains the downbeat (§3).
7. Fallback: let the user or an LLM confirm. "The drop" is partly a taste decision.

### 1.4 Vocal onsets (L)

- Vocal-band flux, timbre novelty and spectral flux in bands 250–4000 Hz were tested against the 41 known word onsets. None of them correlates better than random onset trains.
- A mono, dense mix cannot be separated with numpy.
- Visual inspection of zoomed spectrograms (`work_grammar/zs_a.png`, `zs_b.png`) shows consonant and harmonic-segment onsets at the text onsets, within about ±2 frames.
- Word onsets are **not** quantised to the grid. Their offsets from the nearest 16th note are spread uniformly over ±1.9 frames, which is the maximum possible.
- → Words follow the sung syllable (forced alignment / ASR word timestamps), not the beat.

---

## 2. Part 1 grammar (frames 0–492, bars 1–8)

**R1. Segmentation: one screen = one sung breath-phrase. Two screens = one 2-bar couplet. (H)**
- The 8 lines pair up exactly into 4 couplets of 2 bars each: [я стою на остановке | и жду автобус], [я замарала все кроссовки | слякоть и холод], [на улице хочется сдохнуть | сажусь в автобус], [но когда я вижу тебя | мне кажется что].
- Lines alternate long and short within a couplet: 5.8 / 2.7, 5.3 / 2.5, 5.5 / 3.9, 4.0 / 2.6 beats.
- The first line starts at beat −0.2 (pickup); the others at 5.6, 8.4, 13.6, 16.2, 21.7, 25.5 and 29.6.
- Line starts sit on the vocal entry, which is typically a 16th or 8th after beat 1 or beat 2.5 of the bar. They are not on the downbeat.
- Size limit: 3–5 words and **≤ 25 characters** per line. That is about 527 px of 640 at x-height 35, i.e. about 82 % of the frame width.
- The line break falls where the singer breathes, even mid-sentence: "мне кажется что | Я НАБЛЮЮ НА | СВОЮ КУРТКУ".

**R2. Word reveal: cumulative, a hard cut on each sung syllable. (H for the cut and the cumulation, M for the timing)**
- Each word appears on its own onset frame and stays.
- The line remains complete through the vocal pause until the first word of the next line replaces it. There is no blank gap and no fade-out.
- Timing is syllable-locked, measured at ±2 frames; no beat quantisation.
- The onset micro-effect from motion.md/text.md is the only per-word event:
  - frames o−1 and o are horizontally echoed (equivalent to a ~4 px@480 box) and dimmed to ~0.8;
  - frame o+1 is sharp again.

**R3. No word-level emphasis in part 1. (H)**
- All words have the same size, weight and colour. Emphasis is reserved for the drop (caps) and the finale (red).

**R4. Background: one clip per line, crossfaded so that the new clip is fully in on the line's first syllable. (H for the placement, L for the length rule)**
- Clip changes happen at the line starts 89, 131, 212, 251, 394, 456 and 495.
- One exception, at **335**: a line change mid-couplet in bars 5–6 with no clip change (the same bus shot continues).
- Result: 7 clips for 8 lines. Clips last 39–143 frames (1.3–4.8 s, 2.5–9.3 beats).
- Every clip change is a linear **dissolve ending on the line start**:

  | line start | dissolve length | in beats | dissolve starts at beat |
  |---|---|---|---|
  | 89 | 12 fr | 0.78 | 4.83 |
  | 131 | 9 | 0.59 | 7.77 |
  | 212 | 7 | 0.46 | 13.18 |
  | 251 | 11 | 0.72 | 15.47 |
  | 394 | 9 | 0.59 | 24.93 |
  | 456 | 6 | 0.39 | 29.17 |

- The lengths do not correlate with anything measured: r = 0.22 with the vocal gap before the line, r = −0.01 with the previous line's length. Start positions are not on a grid either. This looks **hand-placed**.
- Generative rule: dissolve length ≈ 0.6 beat (0.4–0.8; 9 ± 3 frames at 117 BPM), ending on the first syllable of the new line. If there is a line change inside a couplet's second half, optionally keep the shot.
- The background has no beat-synced cut, zoom or shake anywhere in part 1.

**R5. Always-on layers (part 1): free-running loops that ignore the music. (H)**

| layer | period | vs beat (15.32 fr) | evidence |
|---|---|---|---|
| text scanline tear a(f) plus baseline tear | **89 fr (2.97 s)**, r = 0.96 at lag 89 and lag 178 | 5.81 beats, not locked | bursts at 31, 120, 209, 298, 387, 476 (and 60, 149, 238, 327); all ramps and zeros repeat |
| global flicker | sinusoids 3.18 Hz + 7.38 Hz (9.43 / 4.07 fr); whole pattern repeats at **~179 fr** (r = 0.74) | 1.62× and 3.77× the beat rate, not integer | flicker_table; corr with audio flux \|r\| < 0.05 at every lag |
| text x-wiggle (sawtooth) | **20 fr** (r = 0.72 at 20, 40, …, 180) | 1.31 beats | motion_table dx |
| text y-sway | **66.7 fr** (sub-period 33.3) (r = 0.93) | 4.35 beats / 1.09 bars, drifts 5 fr per bar | motion_table dy |
| text rotation wobble | ~50 / 100 fr | — | motion_table rot |
| vignette, grain, chroma split, glow | constant | — | text.md / flicker.md |

- These look like a stacked VHS/overlay preset with built-in loops, starting at frame 0.
- For another song: just loop them. Syncing to the beat is not part of the style. Keep them off in part 2.
- The bass entry at bar 5 (frame 248) has **no visual response** (luma 25 → 26, no event). The editor treats bars 1–8 as one "verse" mode.

---

## 3. The drop transition (H)

- Audio: the bar-9 downbeat is at 16.446 s (grid). The measured sub/presence step is at 16.44–16.47 s, which corresponds to frames 493.3–494.
- Video:
  - **493** (spans 16.433–16.467 s and contains the downbeat): a slight lift, p5 15 → 25.
  - **494**: grey wash, mean luma 49 → 113.
  - **495–497**: over-exposure ramps to white (158, 210, 230).
  - **498**: 175, then **499**: dark (62).
  - The first INV strobe is at 500.
- Rule: **the drop transition starts on the frame that contains the downbeat.** It is a 2-frame wash, then the white-out peaks about 3 frames (~0.2 beat) after the downbeat.
- The first caps word "Я" is on its sung syllable at 495, 1.9 fr after the beat.
- There is no pre-drop build visually: no zoom, speed ramp or blackout.
- The last part-1 line simply holds. The 89-frame tear loop happens to be in a negative ramp at 485–494.
- The background switches to one new clip for all of part 2; 494–495 is a 2-frame mix.
- Caveat: the mp4's AAC encoder delay is compensated by ffmpeg (audio start_time 0). A residual A/V offset of about 1 frame cannot be excluded.

---

## 4. Part 2 grammar (frames 495–699, bars 9–12)

**R6. One 30-frame glitch cell, looped. The period is fixed at 1.000 s ≈ 2 beats. (H)**
- The cycles begin at 495 + 30m. Their offsets from the nearest even beat are +1.9, +1.0, +0.3, −0.3, −1.0, −1.6 and −2.3 frames.
- So each cycle starts on beat 1 or beat 3 of the bar within about ±2 frames, and drifts by 0.65 frames per cycle (30 vs 30.65).
- That drift shows the preset is a fixed 1-s loop that is not beat-tracked. Started on the drop, it stays musically aligned for the 6.8 s it runs.
- **For another song:** time-warp the cell to 2 beats, or to the number of beats closest to 1 s. That keeps the alignment the reference only had by luck.

**R7. Cell anatomy in beats from the cycle start (p = frame in cycle; beat = p/15.32). (H)**

| p | beat in cell | effect | musical anchor |
|---|---|---|---|
| 0–3 | 0–0.2 | over-exposure / bottom white-out (A), grey wash (B), pale cyan (C) | the even beat; sub-bass peak at p29–p2 in most cycles (detected onsets 616, 647, 677) |
| 4–15 | 0.26–0.98 | **INV strobe**: frames with 1–3 frame spacing, about 12 Hz. Speck rows on p6–7. **Halftone top on p8, thick bar A on p9** (the "&"), lines on p10, iridescence on p11–14 | first beat of the cell |
| 15–18 | ~1.0–1.17 | **full-frame datamosh on p15, freeze box on p16**, mosh on the lower 60 % on p18 (cyan-INV over-exposure in B) | the odd beat |
| **19–21** | 1.24–1.37 | **FLASH**: 93 % white or cyan, then 2 frames of full white or cyan | **the strongest 808 hit of the cell** (sub +7–15 dB): hits at 513, 544, 574, 605, 635, 667, 697 = beat 2n+1.3 |
| 22 | 1.44 | grey wash / teal | — |
| 23–24 | 1.5–1.57 | clean frames, text readable | the "&" of the odd beat |
| 25–29 | 1.63–1.9 | bottom-of-frame fills: displaced blocks, speck grid, **halftone bottom (p27)**, **bar B (p28)**, lines (p29) | pickup into the next cell |

- **Flash vs 808 hit, per cycle:** +1, 0, 0, −1, −1, −3, −3 frames. The flash is on the hit in the first five cycles, then early because of the fixed-loop drift.
- So the strongest event (white-out) sits on the strongest kick. Smaller events sit on the beat (over-exposure, mosh) and on the 8th off-beats (halftone and bars on p8–9 and p27–28).

**R8. Variation comes from a 3-s super-loop of colour, plus an invert layer. It is not driven by audio energy. (H for the structure, L for the cause)**
- **Super-loop of three cells:**
  - A: white / over-exposed (m0, m3, m6);
  - B: cyan (m1, m4): cyan halftone, cyan bars, cyan flash, teal;
  - C: pale / black-white (m2, m5): pale-cyan inverted, white below 150, black frame 560 or white frame 650.
- **INV strobe layer** (22 frames): on in cycles 0–2 (495–584), off in 3–5 (585–674), and **on again in cycle 6 (675–699, the red word)**.
- Measured visual activity: mean |ΔL| per cycle is 84, 65, 75 | 44, 31, 40 | 86. Part 1 is 4.4.
- Audio energy is flat across bars 9–12: presence 35–36 dB, sub 37–39 dB.
- So the arc is **hit hard (3 s) → breathe (3 s) → hit hard for the punchline**. There is **no escalation** over time.
- This tracks the lyric (the INV-off stretch ≈ "ЕСЛИ ПРЯМО СЕЙЧАС НЕ ОСТАНОВИТЬСЯ") rather than the music.
- The on/off edges are snapped to cycle boundaries: 5 and 3 frames after the line starts at 580 and 672.

**R9. Part-2 text. (H)**
- ALL CAPS.
- Lines are shorter: 1–3 words, ≤ 17 characters. Caps are wider.
- Words are still cumulative and on their syllables. Onsets fall anywhere in the cell: p0, 18, 8, 22, 2, 25, 10, 24, 12, 23, 27.
  - 5 of 11 onsets land in p22–27, the readable stretch after the flash. This matches the singer's habit of entering on the "&" (beat 1.5–1.8 of the cell). It is coincidental, not scheduled (L).
- The text layer jumps to a new random position every frame: σ 14 px, mean +9 px low, lag-1 autocorrelation 0.22. The background does not shake.
- Motion smear on about 65 % of frames, median 14 px, with echo ghosts.
- On blown-out frames the text is dimmed (ta 0.2–0.6). On INV frames it is inverted with the frame.
- Line changes in part 2 come at beats 35.5, 37.65, 40.7 and 43.66, i.e. on vocal phrases. They are independent of the cells.

---

## 5. The red accent word (H for the facts, M for "why")

- **Which word:** МАРШРУТКА, the last word of the excerpt and the final noun of the sentence ("…if the marshrutka doesn't stop right now").
- **Why it counts as the most accented:**
  - it is the punchline that pays off the bus theme (автобус ×2 earlier → маршрутка);
  - it is alone on its line, the only single-word screen;
  - it is the last screen of the song.
- **It is not acoustically louder.** Per-beat RMS and band energies in beats 43–45 equal the part-2 mean (vocals cannot be separated, so "held note" cannot be confirmed).
- **When it appears:**
  - frame **672** (22.40 s), beat 43.66 = bar 11 beat 4.66, a pickup 1 beat before bar 12;
  - that is cell m5 p27 (halftone bottom);
  - it is the word's sung onset.
- **When it disappears:** it is held to the last edit frame, **699**: 28 frames, 1.8 beats, until the audio cuts at 23.29 s.
- **Style:**
  - crimson core ~(150,35,65);
  - weight 700 against 430;
  - cap height 85 px against 55 (×1.55), ink width 390 px;
  - same glow and chroma split as the other text;
  - vertical position jumps between y ≈ 174 and 208.
- **Around it:**
  - the INV layer comes back three frames later (675) for the last cycle;
  - the over-exposure frames 675–678 turn the word pink;
  - INV 679 makes it green on dark;
  - the final cell runs its full anatomy: mosh 690, box 691, flash 694–696 (3 frames before the 808 at 697), wash 697.

## 6. The ending (H)

- The song excerpt hard-cuts at **23.29 s**, about 60 ms after an 808 hit (frame 697, beat 45.3), mid-bar (bar 12 beat 2.4). There is no fade.
- The edit ends with it: frames 698–699 are the clean p23–24 frames of cell 6, showing the red word, and the TikTok outro follows.
- No end card, no hold and no fade to black. The last cell is cut off at p24.
- Rule: **end on the audio cut. The last word stays on screen until then, and the glitch loop is simply truncated.**

---

## 7. Component catalog

| # | component | class | where | trigger (musical) | key params (see the measurement reports) |
|---|---|---|---|---|---|
| C1 | lowercase serif lyric line | text treatment | part 1 | line = breath-phrase; word = syllable onset | Cormorant Garamond wght 430, x-height 35 px@480, ≤ 25 chars, lavender-white core, 3-gauss glow, R+1.75 / B−1.4 px split (text.md) |
| C2 | word-in echo + dim | event (per word) | part 1 | frames o−1 and o of each syllable onset | ~4 px h-box echo, ×0.8 brightness, o+1 sharp (motion.md §4) |
| C3 | text x-wiggle / y-sway / rotation | constant loop | part 1 | free-running: 20 fr / 66.7 fr / ~50 fr | x ±2.5 px jerky sawtooth, y ±3.7 px, rot ±0.5° (motion.md §1) |
| C4 | text scanline tear + baseline tear | constant loop | part 1 | free-running 89-fr loop from frame 0 | D(y) profile, AMP / BAND tables (text.md §2) |
| C5 | global flicker | constant loop | part 1 | free-running 3.18 + 7.38 Hz, ~179-fr repeat | 7 % std luma gain (flicker.md) |
| C6 | vignette, grain, softness | constant | part 1 (vignette only part 1) | — | flicker.md / build.py |
| C7 | background clip per line | structure | part 1 | clip changes on line starts (skip one mid-couplet) | 7 clips, 1.3–4.8 s |
| C8 | background dissolve | transition | part 1 | ends on the new line's first syllable | 6–12 fr (0.4–0.8 beat), linear |
| C9 | drop wash → white-out | transition | 493–498 | frame containing the drop downbeat | lift → grey wash → ×2–3.4 over-exposure peaking +3 fr |
| C10 | glitch cell (30 fr) | event loop | part 2 | cycle = 2 beats from the drop; anatomy table R7 | glitch.md §2 table, glitch_v2 SCHED |
| C10a | over-exposure / white bottom | sub-event | p0–3 | even beat | ×1.9–3.4 gain, blown lower frame |
| C10b | INV strobe | layer | p4–15, cycles 0–2 and 6 | first beat of the cell | 5–6 inverted frames, 1–3 fr spacing |
| C10c | halftone top / thick bar A | sub-event | p8 / p9 | 8th off-beat | grid 21×16 px top band y 0–190; bar y 211–240 |
| C10d | datamosh + freeze box | sub-event | p15 / p16 (+ p18) | odd beat | 8-px-grid streak blocks; box x 0–490, y 0–195 |
| C10e | flash white/cyan | sub-event | p19–21 | strongest 808 hit (~beat 1.25 of the cell) | 93 % then 100 % fill, 3 frames |
| C10f | wash, clean, bottom fills, halftone bottom, bar B | sub-events | p22–29 | the "&" and the pickup into the next cell | glitch.md |
| C11 | colour super-loop A/B/C | variation | part 2 | every 3 cells (≈ 6 beats) | white / cyan / pale |
| C12 | caps text + per-frame shake + smear | text treatment | part 2 | from the drop to the end | caps 55 px, σ 14 px random offset, smear median 14 px, ghost |
| C13 | red word | text emphasis | 672–699 | final word / punchline, on its syllable | crimson, wght 700, ×1.55 size, alone on its line |
| C14 | ending | structure | 699 | audio hard-cut | no fade, last cell truncated |

---

## 8. Not derivable from the music: needs a human or an LLM

1. **Which word is red.** Default rule: the last content word of the final line (the punchline, usually a noun). Put it on its own line.
2. **Where the drop is**, when several candidates score close (§1.3). Confirm the chorus or hook boundary.
3. **Line segmentation.** Breath phrases need lyrics plus word timestamps. The ≤ 25 / ≤ 17-character limits are mechanical; choosing the break point is linguistic.
4. **Where the INV layer is switched off in part 2.** In the reference it is off for the middle 3 s, i.e. the middle lyric lines. Proposed default: INV on for the first 3 cells after the drop and for the red-word cell, off otherwise.
5. **Clip choice and order:** dark night/transport footage, one per line, and one fast smeared clip for the whole drop. Also which line change keeps the same shot (335).
6. **Crossfade lengths.** These are hand-placed. Use 0.6 beat ± 0.2 unless told otherwise.
7. **Which cells get the cyan / pale variants.** Here the pattern is a fixed A-B-C rotation, which is fine as a default.

## 9. Transfer recipe for a new song (pseudo-code)

```
beats, bars   = beat_track(song)                      # tempo T, period Pb frames
drop_bar      = argmax_bar(bright_noisy_step, sub_present)    # §1.3, user-confirm
words         = asr_word_timestamps(song, lyrics)      # onsets in frames (round, no quantise)
lines         = split_breath_phrases(words, max_chars=25 before drop / 17 after)
red_word      = llm_pick_punchline(lines[-1])  -> own line
# part 1  (0 .. drop_frame-1)
for each line: clip_i; dissolve ending at line.start, length = round(0.6*Pb) frames
always-on: tear loop 89f, flicker 3.18+7.38 Hz, wiggle 20f, sway 66.7f  (free-running, not beat-synced)
word reveal: cumulative hard cut at onset; echo+dim on onset-1 and onset
# drop
drop_frame = frame containing the drop downbeat; frames +0 lift, +1 grey wash, +2..+4 white-out
# part 2  (drop_frame .. end)
cell_len = 2 beats (or the beat count nearest 1 s); time-warp the 30-frame schedule to cell_len
optionally nudge the cell so the flash (p19-21) lands on the strongest low hit of each cell
colour slots A,B,C,A,B,C,...; INV layer on for cells 0-2 and for the red-word cell
text: CAPS, random +/-14 px per frame, smear; red word: crimson, bold, 1.55x, held to the end
end at the audio end; truncate the cell
```

## 10. Evidence index

- `work_grammar/audio.py`, `tempo.py`, `grid*.py`, `phase.py`, `snare.py`: tempo, grid and phase.
- `perbeat.py`, `dropdet.py`, `steps.py`: section energies, the drop step score, and the 10-ms band levels at 8.27 s, 16.45 s and 23.29 s.
- `subhits.py`, `p2frames.py` (`p2frames.txt`): 808 hits per frame against the cell position.
- `words.py`, `vocal.py`, `xcorr.py`, `novelty.py`: word onsets against the grid and the vocal-onset attempts (negative result).
- `loops.py`, `loops2.py`, plus inline autocorrelation of `motion_table.json`: loop periods of the constant layers.
- `xfade.py`: crude dissolve check (camera motion confounds it; the XF values come from motion.md).
- `timeline.py` → `reports/grammar_timeline.json`.
- `plot_overview.py` → `grammar_overview.png`; `plot_cycles.py` → `grammar_p2_cycles.png`. Zoomed spectrograms: `work_grammar/zs_a.png`, `zs_b.png`, `zs_c.png`, `spec_overview.png`.
