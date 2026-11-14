# Card-Strobe Edit: editing grammar and component kit

A 9:16 TikTok edit built around a **1:1 picture in a black letterbox**. On the 808 drops the footage disappears behind a **giant ultra-condensed word card** that flips black/white every 2–3 frames, and the letterbox bars flip with it, so the whole phone strobes. Between the cards the footage runs:
- one hard **duotone** clip per bar, a different hue at every cut;
- words land on their syllables as pop words, clones and outline stacks, later as tiny subtitles;
- a flash-cut burst fills the 808 gap;
- the punchline is a **crimson card** alternating with footage;
- a whip ends the edit mid-motion, so the loop restarts cleanly.

The style comes from the user's favourite TikTok (kileeknow / madk1d «и без свечения», `ref3`), measured frame by frame in `~/Downloads/podnebesny-edits-v2/_analysis/ref3.md`. The user approved it as **"Mastermind"**: `01-mastermind-toilet-ref3`, Поднебесный in the RZD toilet under «так похуй» 47.265–59.398 s.

The kit `lib/card_strobe/` rebuilds that edit **byte-identically** from one timeline JSON (`lib/card_strobe/examples/mastermind_toilet.json`). The planner `lib/card_strobe/tools/plan.py` writes the same kind of timeline for any song and any footage.

**Two styles, one kit:**
- **Mastermind** (pure ref3): typed blocky intro, pop words, tiny subtitles. `--style mastermind` (default).
- **Fused** (Part 3, the user's current direction): the Mastermind skeleton plus the first edit («МАРШРУТКА», `lib/glitch_drop`). That adds a thin glowing serif lead-in and narrator, a VHS open, Cyrillic captions under the Latin cards, glitch accents on the 808s and a red punchline. Use `--style fused`. Approved on «mefedron master 4», and both edits are kit examples: `examples/fused_chorus_mefedron.json` and `examples/fused_verse_zvonit.json`.

```
~/.cache/card_strobe_align/bin/python -m lib.card_strobe.tools.align --audio song.mp3 --words words.json --demucs --out words_aligned.json
.venv/bin/python -m lib.card_strobe.tools.plan --audio … --start S --end S --words words_aligned.json --moments … \
    --out timeline.json [--bpm 160 | --track track.json] [--style fused]
.venv/bin/python -m lib.card_strobe <timeline.json> <out_dir> [--preview | --frames a:b] [--workers N]
.venv/bin/python -m lib.card_strobe.tools.sheet <final.mp4> <out_dir> --every 3       # numbered contact sheets
.venv/bin/python -m lib.card_strobe.tools.audit <final.mp4> --timeline timeline.json --track track.json   # QA numbers
```

- **Cost:** zero. numpy, PIL and ffmpeg in `.venv`.
- **Speed:** about 40 fps wall with 10 workers, so a 12 s edit renders in about 15 s.
- **Format:** 1080×1920, 30 fps. The square is 1080×1080 at y 420–1499. Footage is precut at 1210 px (65 px margin) as headroom for zoom, sway and whips.

---

## Part 0: a new song, end to end

1. **Audio.** Take the sound only, and pick the excerpt.
   - ref3's excerpt is 12 s.
   - The ideal excerpt starts **in a bass-less bar just before an 808 entry** (that entry is the drop).
   - It contains, if possible, **one 808 gap** (bass out ≥ 3 eighths) mid-way, for the burst and card 2.
   - It ends **in a bass-out moment after the punchline**, where the crimson card goes.
2. **Grid.** The planner reuses `lib.glitch_drop.tools.music` (comb tempo). Trap songs often get a dotted or half tempo. «так похуй» comes out as 106 instead of 160, «Династия» as 93 instead of 140, and «mefedron master 4» as 88 instead of 132 (the triplet hats fool it).
   - Check the tempo and pass `--bpm`. Add `--beat0 SEC` (any beat, original seconds) to pin the phase too.
   - Better, when a beat analysis exists, pass `--track track.json`. It takes `beat_period`, `grid_origin` and `low_hits: [{t, rel_db}]`, and replaces both the comb and the low-hit detector. «mefedron master 4» has one at `~/Downloads/podnebesny-edits-v3/_analysis/track.json`, made from 183 kick and 82 snare onsets of a demucs drum stem, with a median grid residual of 6 ms.
   - DROP 1 = the strongest low (808) hit in the first 45 % of the excerpt, snapped to the beat. If it is wrong, pass `--drop SEC`.
3. **Lyrics + word times.** The user sends their lyric-tool file, `{"words": [{"row", "start", "end", "text"}]}`. **Its text, rows and order are right, but its times are not.**
   - On «mefedron master 4» every word was late, by 0.30 s on average and up to 1.56 s. Only 1 of 111 words was within 40 ms.
   - Never put ASR text on screen. Only the times move.

   Align with `tools/align.py`. It needs torch, torchaudio and demucs in a separate venv; the setup line is in its docstring.
   ```
   ~/.cache/card_strobe_align/bin/python -m lib.card_strobe.tools.align --audio song.mp3 --words words.json \
       --demucs --out ~/Downloads/<project>/words_aligned.json        # or --stem vocals.wav
   ```
   **The method that worked** (`~/Downloads/podnebesny-edits-v3/_analysis/track.md`):
   1. **Vocal stem** with demucs htdemucs.
   2. **MMS_FA forced alignment** of the known text. This is torchaudio's multilingual uroman CTC model, with the Cyrillic romanised.
      - Pass 1 aligns the whole text at once, with a `*` star token between rows to absorb ad-libs, samples and untexted vocals (the extra «Я люблю…» lead-in at 12.30).
      - Pass 2 re-aligns each row in a window around its pass-1 position, chained so rows can't overlap.
   3. **Onset refinement** on the stem: a 5 ms energy-rise novelty in two bands. An onset within 40 ms of MMS → their mean. A late, unsure MMS with an onset up to 120 ms earlier → the onset (a short «Эй,» after a gap). Otherwise MMS alone (legato «Я люблю», «в потолок»).
   4. Words with 3+ vowels get `syllables`, for syllable-timed card swaps (MEFE-/DRON on «ме-фе-дрон»).
   5. **Check the flagged words by ear** (`<out>.report.json` → `stats.to_check`). These are a low MMS score or a move of more than 0.6 s. Fix them by hand in the output.

   Measured against the hand-checked times of «mefedron master 4»: **99 of 111 words are within 40 ms and 107 within 80 ms.** The 4 misses are hand-resolved words from track.md, and 3 of them are flagged.

   Faster-whisper word timestamps run about 32 ms late with a ±75 ms scatter, so they only work as a weak vote. They were not needed.

   The planner reads the aligned file as is (`row` → line, `text` → word). It also still takes `[{"line", "word", "start"}]`. One line = one sung phrase. The last line's last 1–2 words become the end card.
4. **Moments: curate the footage first.** The user asks for "the most stylish shots, where he looks great in the suit", and repeats are fine. Before planning:
   - **Skim every source.** Use 1 fps contact sheets, then 2–4 fps around candidates. Find the hard cuts inside a window by frame diff: a diff over ~25 is a cut, and a window must end before it.
   - **Rank the hero frames.** Suit, stares into the lens, profile turns, chugs, Dutch angles, a logo or star as a halo or crown. Drop frames with another person in them, or crop them out.
   - **Give each pick a 1080 square crop** in source px, a `best_t`, a `kind` (`hero_portrait` counts as a face) and an energy. Verify each crop rendered at t_in, best and t_out.
   - The result is a picks file: `{"picks": [{"src", "t_in", "t_out", "best_t", "square_crop": {"x", "size"}, "kind", "energy", "desc"}]}`. It feeds `--moments` directly, with `--top 24` to keep the hero set. The example is `examples/podnebesny_curated.json` (the full 59 picks: `~/Downloads/podnebesny-edits-v3/_analysis/CURATED.json` + `.md`).
   - The planner also takes plain moments, `[{"src", "t_in", "t_out", "subject_x", "subject_y", "kind", "energy", "desc"}]`. A `*_shots.json` source review works with `--src video.mp4`.
   - **moment 0 = the intro** (dark, face, static is fine).
   - The rest = verse clips, one per bar, cycled; repeats are fine.
   - The burst samples them all.
   - The red "home" clip prefers a `kind: "face"` moment.
   - Pick hero frames: the suit, stares, chugs, slams, a whip.
   - `subject_x/y` are 0..1 of the source frame. The planner crops and aims at them.
5. **Plan.** Read the planner printout and `plan_report.json`:
   - tempo;
   - white frame and card 1 frames and text;
   - 808 gap candidates, then burst and card 2;
   - end card and whip;
   - the shot table, text events and **warnings** (words not shown, short moments).
   
   Fix with flags (`--card1 MASTER/MIND`, `--card2 ZAE-/BAL`, `--end-card CALVIN/KLEIN`, `--break A:B | none`, `--script-words доллар падал`, `--cyrillic-cards`), or edit the JSON.
6. **Preview.** Run `--preview` (every 4th frame) or `--frames a:b`, which writes PNGs and numbered contact sheets in `<out>/preview/`. **Look at the sheets.** Check:
   - the card words;
   - that no two neighbouring clips share a hue;
   - that the subjects are framed;
   - that subtitles are readable on bright clips.
7. **Render** to `~/Downloads/<project>/final.mp4`. Make a contact sheet with `tools.sheet`. Send it with the telegram-send skill if the user asks.
8. **Audit.** `tools.audit final.mp4 --timeline timeline.json --track track.json [--cold a:b]` reports:
   - 808s with no visual event;
   - duplicated footage frames;
   - warm or rainbow leaks on cold sections;
   - the loop seam (Mastermind 44.8);
   - the brightest frames (the drop white should be the only full white).
   
   These numbers caught problems on the «mefedron master 4» edits that the contact sheets missed.

---

## Part 1: the grammar (what fires when, in musical units)

Units: **E = an 8th**, beat = 2E, half-note = 4E, bar = 8E. ref3 runs at 160 BPM, so E = 5.625 frames at 30 fps. All rules are in `lib/card_strobe/grammar.py`.

### Structure (ref3 §2–3)

| section | when | what is on screen |
|---|---|---|
| **intro** | start → DROP 1 (no 808) | ONE dark clip (mauve duotone, luma ≈ 7, p95 ≤ 55). An intro over 1 s gets one jump-cut on the half-note grid. The first sung word is typed in **blocky stencil glyphs**: cap 124 px (long word) or 167 px (short), +2 characters every 4 f. A translucent **band** (y 522–562, ×0.35) carries the tiny subtitle. **2 mosaic frames** (36 px) land 3 f after the first vocal onset. **Lights on** 1.6E before the drop: amber, luma ramp ×0.3 → ×0.68 → ×0.8. |
| **DROP 1** | the 808 | 808 frame: **bars alone go white** (254). Frame `round(t808·fps)+2`: **the whole phone is white 254**. Then the **hero card for 3E (16 f)**. |
| tail | 2–8 f | the face, amber, the whole line so far as a band subtitle |
| **verse A** | to the 808 gap | **one clip per bar**, cuts on the half-note grid (+1 f) — pop-word mode |
| **burst** | the 808 gap (bass ≥ 3E, ~4–5 dB under the body) | flash-cut montage, then **1 black frame** with only the subtitle |
| **DROP 2** | 1.67E before the 808 returns → next half-note after it | second card: line 1 alone for **5 f**, then two lines strobing across the return |
| **verse B** | to the punchline | one clip per bar, red "home" first — **subtitle mode** |
| **end card** | the last line's last words | crimson card / footage alternating |
| **whip** | last 5 f | the composite slides −60, −135, −225, −325, −425 px with motion blur. It ends mid-whip: **no fade, no end card**. |

### The hero card (ref3 #1, the loudest thing in the edit)
- Flat black square, **one word in white Impact**, no stroke, glow or shadow. Perfectly static.
- A card word of ≥ 5 letters is stretched to **1040 × 823** (cap 76 % of the square, glyph aspect ≈ 0.2). One of ≤ 4 letters is stretched to 829 × 932 (86 %).
- **Polarity runs 2, 3, 2, 3, 2, 3, 1 frames, starting white.** That is ≈ one flip per 16th (12 Hz). On white frames the type is black and **the letterbox bars turn white too**.
- Word swap on the syllable. A single long word is split at the consonant + vowel onset nearest its middle: MASTER|MIND, ZAE|BAL. Words sung before the white belong to the intro (typed), not the card.
- **Latin caps.** Cyrillic is transliterated (заебал → ZAE-/BAL), the ref3 trick. `--cyrillic-cards` keeps Cyrillic.
- Card 2 is two stacked lines at cap 431 (40 % each), left-aligned, gap ≈ 93 px. Its polarity runs are 3, 2, 2, 3, 3, 2.

### Clips (ref3 §3, §6)
- **One clip per bar.** Cuts sit on the half-note grid, 0 to +2 f after the grid point and never early. A remainder under 0.45 bar joins the previous clip.
- **Every clip is a duotone.** Luma is normalised by the clip's own p5/p95 (constant per clip, so there is no flicker) and mapped through colour stops. Blacks are crushed. Saturation is either ≈ 0 or near maximum.
- **Neighbours never share a hue.** Verse A rotates orange → violet → red → B&W. Verse B rotates red ("home") → B&W → magenta → lilac. The burst is khaki, the end card red-mono, the whip violet.
- Footage in the intro and the first verse clip is **conformed to 20 fps inside 30** (every 3rd frame repeats), for the stutter texture.
- **Entries:** zoom-blur ×1.25 → 1 + macroblocks + small white bars over 4 f, ease-out. These go on verse A clip 2+ and on magenta/lilac. Red and the first clip enter with a hard cut.
- **Holds:**
  - verse A clip 1: step **punch-ins on its words** ×1.3 → 1.7 → 2.0, plus a hue cycle;
  - verse A clip 2: **808 breathing zoom**, 0.97 + 0.11·e^(−Δf/4) after each 808, plus a ±2 % wobble;
  - red: **push-in ×1.5 over 44 f** about the face, a ×1.04 punch on a stressed word, and a sway of −48 → +12 → −32 px;
  - B&W: drift +0.18 %/f, plus scratches;
  - magenta: a **bounce** of −31 / +15 / −7 px;
  - lilac: a bounce of +55 / −17 / +16 / −5 px.
- **Exit into the burst:** a wind-up shake of +4, +16, +37, −8, +35, +81, +96, +170 px over the last 8 f, with motion blur when the move exceeds 8 px/f.

### Words (ref3 §2, §4 #12–19, §5)
- **Every word is an event at its vocal onset − 1 frame.**
- **Verse A, pop mode:**
  - Bold condensed caps (Helvetica Neue Condensed Black), cap 95 / 80 / 65 / 58 px by length.
  - Placed off-centre on 8 rotating slots.
  - Each enters with one of: 2-frame scale-down pop, ±10° tilt, rise from below, drop-in with a 5 px settle, slide from the right edge.
  - **When the next word lands, the previous one drops to 35 %**, and they pile up as a collage.
  - A word held ≥ 1.2E becomes **clones**: ≤ 3 letters, +1 copy per frame, up to 6, every 3rd at 55 %.
  - The clip's last long word becomes **solid 2 f → an outline stack** (3 px stroke, rows 2, 3, 5, 6, 7, 8, pitch 1.25 × cap) that survives 1 f into the next clip.
  - `--script-words` draws "money" words in Bad Script with a soft shadow (Доллар, падал).
  - The **hue cycle** runs −40°/f for 9 f (one full turn) on the word nearest the middle of verse A clip 1.
- **Verse B, subtitle mode:**
  - **Tiny subtitles**: Helvetica 41 px, centred at the square centre, built word by word, at most 30 characters per line or one lyric line per block.
  - On red and B&W clips they use a **difference blend at −3°**. On magenta and lilac they get a **block cursor**, a dark halo on lilac, and a 6-frame slide-up when a new line starts.
  - **At most one giant outline word** (3 px stroke, 1010 × 1000), flickering on frames +0, 1, 3, 4, 7, on the first B&W clip.
- The size hierarchy is extreme: cards are ≈ 40× the subtitle.

### Hits (ref3 §4 #2–4, #21)
- **1-frame full-screen inverts** (square and bars) land on the strongest 808s: at most 2 per clip, ≥ 6 f apart. They stay ≥ 3 f from cuts and out of entries, strobes and hue cycles.
- **B&W exposure strobe** covers the last half-bar of the B&W clip:
  - peaks 244, 214, 205, 196, 193, 171 on kicks and syllables, ≥ 3 f apart;
  - 1 f attack, decay ×0.55 / 0.22 / 0.05, troughs at half exposure.
- **Red light pulses**: R +70 and B +18, decaying over 2 f, with a highlight lift on the hit. They fire on the syllables and 808s of the red clip, ≥ 4 f apart.
- **Burst:**
  - Sub-shot runs are 1, 3, 2, 1, 3, 2, … frames (21 f = ref3 exactly). The 1st and 3rd sub-shots are **242 flashes**.
  - Every other clip sub-shot is **washed**: blacks lifted to 82–92, γ 0.55.
  - Zoom alternates 1.0 / 1.35 with a crash zoom of +11 %/f, and some sub-shots are flipped.
  - Every sub-shot uses a different moment. Grade khaki. The band and subtitle stay on.

### The end
- The crimson card (205, 30, 62) on black alternates **3 on / 2 off** with a red-mono clip. It is always on for 3 f at each word swap.
- It holds no white, so the drop stays the brightest event in the edit.
- Then the 5-frame whip.

### Never (ref3 §4 "not present"; the fused style adds the serif glow and VHS grain on purpose, Part 3)
Glow or bloom on text, RGB split, vignette, grain, light leaks, crossfades, random high-frequency shake. Every transition is a hard cut, a 1-frame flash or a glitch entry.

### Not derivable from the music (decide with the user)
1. The card words, when the word sung at the drop is weak. Brand names and swears transliterate best.
2. Which moments are the "money" shots, and their order.
3. Script words, symbol swaps (Доллар ↔ $ every 2–3 f) and literal gags (soap drop on «EU кидал»). These go into the JSON by hand.
4. Whether a shallow 808 dip is a real break (`--break`).

---

## Part 2: the kit (`lib/card_strobe/`)

| module | what |
|---|---|
| `timeline.py` | **The schema is in its docstring.** Loader, validation (shots must cover every frame once) and `dumps()` (one shot per line). **All event times are integer frames.** Square coordinates for text, canvas coordinates (1210) for the camera. |
| `render.py` | `frame(i)` is a pure function of i. It covers footage (camera → duotone → fx), text layers, band, subtitle, composite motion with blur, cards, flats, bar flash and inverts. It handles precut + grade levels once, chunked multiprocess encode (libx264 crf 16), audio mux, and preview PNGs with sheets. |
| `grammar.py` | **The rules as code**, constants measured on ref3 (see Part 1): strobe runs, card fits, syllable split, translit, pop slots and moves, burst runs, whips, bounces, gap finder. |
| `tools/plan.py` | audio + words + moments → `timeline.json` + `plan_report.json`. Tempo and low hits come from `lib.glitch_drop.tools.music`. |
| `tools/sheet.py` | numbered contact sheets (≤ 2400 px) from a video or a PNG folder |
| `tools/compare.py` | per-frame MAE between two videos (the regression check) |
| `tools/align.py` | the user's lyric file (correct text, rough times) → real word times + syllables: demucs, MMS_FA, onsets (separate torch venv) |
| `tools/audit.py` | QA numbers on the encoded video: 808 coverage, duplicate frames, warm leaks, loop seam, brightest frames |
| `fused.py` | **the fused style**: `FusedRenderer` (picked automatically when a timeline has a `fused` block). Schema in its docstring; Part 3 |
| `grade.py` | the 11 duotone palettes, hue rotate, wash, pulses, exposure strobe, scratches, colour keep |
| `fx.py` | camera affine, keyframes, 20 fps conform, ping-pong, mosaic, band, zoom-blur and macroblock entry, letterbox |
| `text.py` / `fonts.py` | masks and pastes (shadow, difference, outline stack, blocky). The font **roles** are `card` / `pop` / `sub` / `blocky` / `script`. |
| `footage.py` | precut (cover-crop at the subject, cached by hash), exact-frame reads, subject → canvas mapping |
| `examples/` | `mastermind_toilet.json` (the approved edit) + `mastermind_words.json` / `mastermind_moments.json` (its planner inputs); `fused_chorus_mefedron.json`, `fused_verse_zvonit.json` (the two approved fused edits) + `mefedron_words.json` (aligned lyrics, user schema) + `podnebesny_curated.json` (curated suit picks) |

### Timeline cheat sheet
```json
{"fps": 30, "size": [1080, 1920], "square": {"size": 1080, "y": 420, "margin": 65}, "frames": 364,
 "audio": {"path": "song.m4a", "start": 47.265, "duration": 12.133, "fade_out": 0.03},
 "clips": {"C": {"src": "video.mp4", "t0": 91.95, "dur": 1.5, "ax": 0.42}},
 "shots": [
  {"kind": "flat", "f": [26, 26], "value": 254},
  {"kind": "card", "f": [27, 42], "fg": 254, "bg": 0, "swap": [27, 28, 32, 33, 37, 38, 42],
   "states": [{"from": 27, "lines": [{"text": "MASTER", "fit": [1040, 823], "at": [543, 541.5]}]}]},
  {"kind": "clip", "f": [45, 86], "clip": "C", "t": 91.95, "grade": "orange", "conform": 20,
   "camera": {"zoom_steps": [[45, 1.3], [50, 1.7]], "center": [640, 880]}, "fx": {"hue_cycle": {"f": [75, 83], "deg": -40}}},
  {"kind": "card", "f": [338, 358], "fg": [205, 30, 62], "show": [338, 339, 340], "states": [...],
   "under": {"clip": "N", "t": 115.25, "grade": "redmono"}}],
 "text": [{"kind": "word", "f": [50, 86], "text": "EU", "cap": 65, "at": [390, 680], "dim_at": 61, "scale": [1.0, 0.75, 0.6]},
          {"kind": "clones", "f": [75, 86], "text": "HA", "cap": 95, "positions": [[540, 270], [250, 760]]},
          {"kind": "stack", "f": [81, 87], "text": "PAYPAL", "cap": 125, "at": [540, 540], "rows": [2, 3, 5, 8]}],
 "subtitles": [{"f": [182, 228], "style": "diff", "words": [[183, "бро"], [191, "так"]]}],
 "motion": [{"f": [359, 363], "dx": {"359": -60, "360": -135}}],
 "events": {"inverts": [205, 289], "bar_flash": [25], "mosaic": {"frames": [3, 4], "block": 36}}}
```

### Tweaks people ask for
- **Another card word / spelling:** `--card1 "BRE/ND"`, or edit `states[].lines[].text`. Set `fit` for the stretched hero look, or `cap` for natural proportions.
- **Harder or softer strobe:** card `swap` frames. Use `grammar.strobe_swaps(a, b, (2, 3))`, or `(1, 1)` for a 30 Hz flicker, which carries a photosensitivity risk.
- **More inverts:** add frames to `events.inverts` (808 frames, never inside a card).
- **Different colours:** a shot's `grade` (`mauve amber orange violet khaki khakih red bw magenta lilac redmono`), or a new `palettes` entry. `gain` brightens or darkens.
- **Reframe a clip:** `clips.X.ax` sets the crop. `camera.center` / `about` take canvas px, `zoom` sets the scale, `track.keys` take `[precut frame, x, y]`.
- **Money word in script / symbol swap:** a `word` layer with `"font": "script", "size": 128, "shadow": [12, 0.7, 6, 8]`, plus `"alt": {"frames": [...], "text": "$", "font": "pop", "cap": 170}`.
- **Slow motion without duplicate frames:** set `clips.X.fps: 60` (the precut keeps the source rate). The loader warns when `speed < 1` would repeat frames.
- **A face crushed into black by a bright window:** set `levels_roi: [x0, y0, x1, y1]` on the shot (canvas px of the face), or pin `levels: [25, 185]`.
- **808 breathing on top of a push or zoom steps:** `camera.kick: {"frames": [...], "amp": 0.10, "tau": 4}`.
- **An invert that shouldn't turn a warm clip cyan:** `events.invert_modes: {"222": "hue"}`, or `"duotone"` to go back through the shot's palette.
- **Fade a word out:** use a per-frame `opacity` list, e.g. `[0.6, 0.6, 0.6, 0.35, 0.15]`.
- **Clone cadence between 1 and 2 frames:** `every: 1.5`.
- **A syllable recolour on the crimson card** (green on «то», pink on «лок»): `fg_frames: {"460": [50, 225, 193]}`.
- **Strobe burns faces into white blobs:** add `"curve": {"mode": "soft"}` to the strobe. That caps the gain at 1.6x with a knee at 180 rolling off to 220 (`grade.SOFT_STROBE`).
- **Cards built syllable by syllable** (DOL → DOLBO- → DOLBO-/YOBKA): `grammar.syllable_card(states, widest)`. It applies one common squeeze, so a partial word keeps its final proportions. `grammar.show_ranges([[a, b], ...])` builds a card's `show` list.
- **Fonts on another machine:** without the macOS faces the bundled fallbacks render (Oswald for Impact and Helvetica Neue Condensed Black, Arimo for Helvetica, DejaVu Sans Mono for Menlo). To pin the look, set `"fonts": {"card": "/path/Anton.ttf"}`. Anton has no Cyrillic.

### Regression
Three approved edits are kit examples. After touching the kit, re-render them and compare with `tools.compare`. Then run `pytest tests/lib/test_card_strobe.py`.

| example | reference | result |
|---|---|---|
| `mastermind_toilet.json`, `--workers 3` | `~/Downloads/podnebesny-edits-v2/01-mastermind-toilet-ref3/final.mp4` | **byte-identical** (`cmp`). Default workers: MAE ≈ 0.3, encoder noise at chunk joins |
| `fused_chorus_mefedron.json` | `~/Downloads/podnebesny-edits-v3/01-chorus-mefedron-hammer/final.mp4` | encoded mean MAE 0.0007, max 0.11. Raw frames: 491/494 bit-identical; the 3 syllable-recolour frames differ by ≤ 2 levels on glyph edges |
| `fused_verse_zvonit.json` | `~/Downloads/podnebesny-edits-v3/02-verse-zvonit-konyunktivit/final.mp4` | encoded mean MAE 0.014, max 0.42. Raw frames: 446/450 bit-identical; 4 VHS frames have a few clipped highlight pixels |

The two fused examples render from the builders' precut caches when you pass `--cache ~/Downloads/podnebesny-edits-v3/<edit>/_work/precut`. Without it, they precut fresh from `~/Downloads/podnebesny-edits-v{2,3}/_inputs`.

### Known limits
- **Only 9:16 with a full-width square.** The 1080 square size is where every pixel number was measured.
- The planner covers the grammar. It does not do the hand gags of the approved edit:
  - soap-drop tracking, the Доллар ↔ $ swap, the green belt kept in lilac;
  - TOMMY/HILFIGER pops in verse B.
  
  For those, edit the JSON (the example shows every one).
- Tempo detection is the glitch_drop comb. Trap songs often need `--bpm`.
- 808-gap detection is a 4 dB sub-band dip. A song with a sustained sub under the gap may need `--break A:B`, or `--break none` to suppress a false one.
- Moments shorter than their shot are slowed (≥ 0.5×) or ping-ponged. The planner warns.
- `examples/*.json` use absolute paths to the user's `~/Downloads/podnebesny-edits-v{2,3}/_inputs`.
- The two fused examples were built by hand-written builders, not the planner. Their gags are hand-placed: syllable recolours, the DOHUYA/BABLA chug intercut, the burst steps and the red cell. `--style fused` plans the skeleton and the fused layer, not those gags (Part 3).
- **Tempo:** the comb still fails on trap songs. Use `--track` or `--bpm` with `--beat0`.
- **Gaps:** the 808-gap detector misses breaks that keep a sustained sub. «mefedron master 4» has no 808 gap in either hook, so the planner plans no burst or card 2 there (pass `--break`).
- **Alignment** needs a torch venv. It isn't in `.venv` or the tests.

---

## Part 3: the fused style (Mastermind × «МАРШРУТКА»)

**What the user asked for:** "продолжим в стиле первого эдита Mastermind и самого первого", that is, keep developing this look. It was approved on «mefedron master 4» as two edits:
- `01-chorus-mefedron-hammer`: «Я люблю мефедрон», the last hook hammered twice, 16.5 s.
- `02-verse-zvonit-konyunktivit`: «Эй, звонит долбоёбка…», the verse into the drum stop, 15 s.

Both are kit examples, and `--style fused` plans new ones.

### What is added to the Mastermind grammar
| ingredient | where | numbers (from the approved edits) |
|---|---|---|
| **serif lead-in** | the intro, instead of the typed glyphs and band subtitle | glitch_drop IntroText (Cormorant 430, lavender glow, chroma split, scanline tear, onset dim, word-in echo, measured hand-held sway). It sits on the face at y 540 with scale 0.92–1.0, square layer, under a VHS window: vignette 0.28, grain 2.3, measured flicker, laid out on the 1440 frame. The intro grade is `dusk` (a lifted mauve), so the face reads behind the line. |
| **drop ramp** | the last 3 intro frames | lift `wash=1.15,8` → grey wash `wash=0.55,70` → blown `expo=2.6 botw=225,1 hs=30`. Then the white, then the card. |
| **card captions** | under every giant Latin card | the exact Cyrillic sung word(s), 34 px Helvetica at y 1017–1022, in the card's type colour. They swap with the polarity. |
| **serif narrator** | the second half, instead of the tiny subtitles (`--narrator subs` keeps the subtitles) | canvas layer: it rides bounces and the whip, and mosaics with the picture. y 800, scale 0.8, shade 0.7 (a dark halo that keeps it readable on bright clips). The sway drops to 0.4 after the drop. |
| **black serif breath** | a flat black hold before a second pass | the line alone on black, scale 1.5–1.8, sway 0.4, no rotation, grain only |
| **glitch accents** | the strong 808s of the second half | a step on the hit frame and the next frame only. Never on the first 3 frames of a clip (a clean face first), on a strobe, an entry or an invert. The INV family comes first, then plain steps (`fused.ACCENT_INV` / `ACCENT_PLAIN`). Face-banned ops: `iri botw vs box tre`. INV runs back through the shot's own palette (`invert: duotone`), the bars stay black, and the square's mean luma is capped at 200. A JPEG-38 crush runs on every footage frame of that section. |
| **burst glitch** (verse) | the drum-stop burst | one glitch_drop step per frame from `reference_drop` p4–p15, with the band and serif drawn *over* the step (`over: true`) so they stay legible |
| **red cell** (verse) | over the crimson end card | `fused.RED_CELL` steps between the card's show frames, plus 2-frame inverts |
| **hue-safe inverts** | 1-frame inverts on warm clips | `invert_modes: hue`. A plain invert turns orange or red into a cyan negative. |
| **soft strobe** | every exposure strobe | `curve: soft` (1.6x cap, knee 180 → 220). The ref3 curve burns faces. |
| **red punchline + loop** | end | crimson card with syllable states (PO- / POTO- / POTOLOK). The word rides the whip at 60 % and fades out over the last 2 frames. The whip clip can be the opening shot, so the loop lands on him: seam 50.5 vs Mastermind 44.8. |
| **second pass in a new colour** (chorus) | a repeated hook | the same cards in cyan (30, 208, 245) instead of white, plus a cyan flat before the card |
| **808 camera kicks** (verse) | every clip | `camera.kick` amp 0.15, tau 4, on the 808 frames, on top of the push or zoom steps |

### Glitch steps (`fused.glitch`)
- **Syntax:** the step syntax is glitch_drop's (`lib/glitch_drop/glitch.py`), `fx | tx | meta`. Useful ops:
  - `inv`, `hs=N` (horizontal smear), `soft=4`, `expo=k`, `botw=y,1`, `wash=a,b`;
  - `ht=y0,y1,C,holes|grid|stripes` (halftone), `dust=y0,y1,C,dens`, `row=y,C`;
  - `barA=y0,y1,C` / `barB=y,C`, `hl=C`, `line=y,C`;
  - `mosh=y0,y1,dens` (datamosh), `lowblk2`, `fill=r,g,b`, `flash=C,a`, `cyaninv`.
  
  Colours: W white, K black, C cyan, R red. y is in px@480 of the 4:3 frame. The square is padded to 1440 for the step.
- **Options per step**, or as glitch-level defaults:
  - `jpeg` (38; 0 = off), `tone`;
  - `bars` (`follow`: the letterbox takes the step's polarity; `keep`);
  - `invert` (`rgb` / `duotone`), `luma_cap`, `banned`;
  - `over` (draw the serif, captions and band after the step);
  - `stage: pre` (before the serif and VHS, bars untouched: drop ramps);
  - `seed`.
- **`base`** gives many frames a default step (the crush) and options. A step on a base frame inherits them.
- **`runs`** lays a glitch_drop pattern over a frame range.
- **`context: prev`** lets `mosh` reuse frame i-1's glitched output, one frame of look-back, so frames stay pure.

### Recipes
- **A new fused edit:** align the words, curate the picks, then run `plan … --style fused --track track.json --drop SEC`.
  - Check the planned serif lines, captions and accents in `plan_report.json` → `fused`.
  - Then hand-place the gags the planner can't know: syllable recolours (`fg_frames`), card / chug intercuts (`show` + `grammar.show_ranges`), a burst `runs` entry, a red cell.
- **Planner test on the user's chorus:** `~/Downloads/podnebesny-edits-v3/_skill_test_fused/` holds `timeline.json`, `final.mp4` and the sheets. It is `--style fused` with no hand gags, built from `CURATED.json --top 24`, `track.json` and `--drop 58.298`.
- **More glitch:** more `accent_steps` per hit (`per_hit=3`), or plain steps on more hits. **Less glitch:** fewer hits, or `base` without `jpeg`.
- **A serif line that must stay put during a whip:** set `"layer": "square"` on that line.
- **Legibility over a glitch frame:** set `"over": true` on that step.
- **Reference:** `fused.py`'s docstring is the full schema. The examples show every option in use.
