# VHS Kinetic Lyrics — editing grammar + component kit

A TikTok-style lyric edit: the song's words land one by one, in sync with the vocal, over
dark night footage, with a VHS/CRT finish. Reverse-engineered frame by frame from a
reference edit (project `projects/tupaya-tvar-remake`). The kit `lib/vhs_lyrics/` rebuilds
that edit pixel-identically from one timeline JSON (`lib/vhs_lyrics/examples/tupaya.json`),
so a new track only needs a new timeline.

```
python -m lib.vhs_lyrics <timeline.json> projects/<id> [--stages bg,html,render,post]
```
Output: `projects/<id>/renders/final.mp4` (raw HyperFrames render in `renders/raw.mp4`).
Cost: zero. Everything runs locally (ffmpeg, HyperFrames, numpy/PIL).

Worked examples:
- `lib/vhs_lyrics/examples/tupaya.json` — the reference remake (hand-measured boxes and grades).
- `projects/track2/` — **the first edit made from scratch on a new track with this skill; the user
  approved it as is.** Its `gen_timeline.py` (frozen copy:
  `lib/vhs_lyrics/examples/track2_gen_timeline.py`) is the template for the next track.
  Copy it and replace the word times, scenes and backgrounds.

---

## Part 0 — New track, end to end (the approved track2 workflow)

Two Python envs: `.venv` (kit, render) and `.venv-audio` (torch-CPU, demucs, faster-whisper,
librosa; models cached in the user profile). Both are free and local.

1. **Audio only.** When the user gives a TikTok/URL, take only its sound; the video is never used.
   ```
   .venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio prep <url|file> projects/<id>/analysis
   ```
   This writes stems, a whisper draft `asr.txt` (segments + words), and `grid.json` (tempo,
   beats, vocal onsets, vocal start/end). Copy `analysis/original.m4a` to `projects/<id>/assets/audio/`.
2. **Ask the user for the lyrics.** Whisper mishears slang, names and shouted parts (about a
   third of the words on track2), and every word goes on screen big. Use the whisper draft only
   for line windows. Trim the lyrics to what the clip actually contains (TikTok sounds cut off
   mid-song) → `analysis/lyrics.txt`, one sung line per line. Keep the user's spelling (they write
   Е, not Ё; Ё dots also squash the glyphs in a fixed box).
3. **Align.**
   ```
   .venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio align projects/<id>/analysis --chunks chunks.json
   ```
   - Whole-track alignment drifts when part of the vocal is distorted or shouted (track2's caps
     half scored about 0.00).
   - `chunks.json` = `[[[line indices], t0, t1], …]`, with windows taken from the `#SEG` lines
     of `asr.txt`. One chunk per 1–3 lines fixes the drift.
   - Words scored < 0.05 get the nearest vocal onset from `grid.json` (cross-check with the ASR
     word times).
   - Words < 3 frames apart are merged into one state.
4. **Trim dead intro.** If the vocal starts late (> about 0.5 s), start the audio on the beat
   just before the first syllable (`audio.offset`, `O` in the generator). This keeps text on
   screen from the start.
5. **Scenes** by the grammar below: rhyme couplets = scenes until the energy shift (drop / caps /
   drums return), then one line = one scene. A drum break right before the shift is the place
   for the background dim plus the big-shadow punch. A punch shorter than 1.5 beats is acceptable
   in the climax when the line itself is that short.
6. **Backgrounds by meaning.**
   - Pick clips that literally echo the line where possible (sea for "sea breeze", kittens for
     "won't play with you", a lone cat for "sat alone", a leaving train for "will leave").
   - Use a different clip for every scene.
   - Copy the clips into `projects/<id>/assets/bg/scene<N>.mp4` so the project is
     self-contained and a clip can be swapped by replacing a file.
   - Make a contact sheet first: `ffmpeg -i clip -vf "fps=1/1.5,scale=240:-2,tile=6x1"`.
7. **Brightness is automatic:** give each scene `bg.look` (median / p95 luma, saturation, tint)
   instead of a hand-written grade. The track2 targets are median 17–32 and p95 80–110:
   - calm or cold scenes darker and bluer;
   - the pen-lettering reset scene the brightest.
8. **Build:** a `make.py` in the project runs gen_timeline → kit (bg with auto-grade, html, render,
   post), with `--send` to Telegram. Check a snapshot grid at every punch frame before sending.
   Things to look for:
   - a glitch word must stay on for its whole length (the kit handles words longer than 15 frames);
   - small words in one row need box widths proportional to their letter count.

---

## Part 1 — Editing grammar (how to cut it)

Measured on the reference (136.6 BPM, 4/4, 16 bars + final hit, about 29 s, 10 scenes).

### Scene = a musical phrase, cut on the vocal
- **Cut on the first syllable of the line that opens the scene** (0…+5 frames). Vocal lines
  start on beat 1 or 3 of a bar, often a little late (median +0.4 beat), so the cuts land on
  the half-bar automatically. No cut is placed on the beat without a vocal, and no frame is
  ever left without text.
- **Length:** the first ~60% of the track uses **2 sung lines = 1 scene, 1.5–2.5 bars**. One
  long wall scene of about 3 bars sits mid second half. The climax (last ~4 bars) uses
  **1 line = 1 scene, about 1 bar**. The intensity comes from the cut rate.
- Each scene gets a different background clip, even when the text repeats.

### Word = a syllable, never quantised
- Each sung word becomes its own element at its onset (0…+4 frames). Function words (И, В,
  С) get one too. A long word can be split into syllables that appear together; the
  reference stacks them vertically.
- Words **accumulate** until the scene's cut. The screen is cleared inside a scene only for a
  full-screen hit or a change of device, and only on the half-bar.
- **No entrance animation at all.** A word hard-cuts in within 1 frame at its final size and
  place, then stays still. The motion comes from the cuts, the background flicker and the
  VHS layers.
- A melisma stretches the word: one letter added every about 6 frames (an eighth note).
- Minimum gap between appearances is 3 frames.

### Anatomy of a scene: setup → punch
- **Setup:** white or cold colour, narrow face (`cond/condb/roboto/thin`) or pen lettering,
  small (4–24% of frame height).
- **Punch:** red Impact-grunge (or a variant), 33–52% of frame height per row, full width.
  **It is always the last element of the scene and holds about 2 beats (0.7–1.0 s) before the cut.**
  A punch on the half-bar is used early; the climax puts punches on the downbeat.
- One main punch per scene. The first line may get at most one secondary hit: a red word
  over the setup, or a giant pronoun column.
- **Contrast of scale** inside a scene is the core (biggest/smallest word ratio up to ×25).

### Choosing the strong word (in order of weight)
1. Chorus or a repeated phrase.
2. Violence, threat, insult, taboo, strong emotion.
3. A concrete image that can be shown with a colour or texture (e.g. an army word in camo).
4. The last or rhyming word of the line.
5. A sung-out word: a candidate for letter-stretch or glitch.

Vocal loudness barely matters; meaning and position decide.

### Colour logic
- **Red** = aggression or punch. Its share grows in the second half.
- **Blue** = crying or sadness words.
- **White** = neutral setup and function words.
- **Green camo** = a literal illustration.
- **Pink / dark red** = a variant used to separate a punch from a neighbouring red.

### Layouts (6)
1. **Pair** of words in a row.
2. **Centred growing line** (subtitle-like build-up).
3. **Column + stack:** a giant pronoun column on the left, with words stacked on the right.
4. **Wall / collage:** words in the gaps, mixed sizes, syllables stacked.
5. **2 full-screen rows** for a 2-word punch.
6. **1 full-width row** for a 1–3-word punch.

### Alternation rules
- The punch design always differs from the previous scene's (layout / face / colour: at most
  one shared). **Exception:** identical lyrics get an identical design and only a new background
  (repeat line = copy scene; chorus = fixed "brand").
- **Signature effects are used at most once per video and only with a reason:**
  - background dim → the first chorus hit;
  - RGB glitch → a sung-out word at a cut, a bridge into the next scene, as long as the word;
  - letter stretch → a melisma;
  - camo → a concrete image;
  - brush / thin / lowercase → variety in the fast climax.
- **Base devices may repeat:** the centred line, red grunge, full-screen rows, white setup.
- **Structural devices are used 2–3 times:**
  - pen lettering at the start of each 8-bar half;
  - column + stack;
  - wall;
  - big shadow only on the chorus;
  - mid shadow on every climax punch;
  - blue for crying;
  - skew (crying / flying words).
- **Density alternates** dense ↔ sparse (screen coverage >60% → next <50%), except in the
  climax.

### Dramaturgy: two 8-bar waves
- **Wave 1:** loud opener (chorus + dim) → calm (small subtitles) → build (tiny → wall) → chorus.
- **Wave 2:**
  1. reset (pen lettering);
  2. the longest wall scene;
  3. 1-bar punch scenes with mid shadow, hits on the downbeat;
  4. **loop:** the opening line returns red and full-width on the final hit, as a thin red
     setup that is then replaced by the big row.

### Adapting to a new track — algorithm
1. **Timings (free, local).** Separate stems with demucs. Force-align the lyrics on the vocal
   stem (torchaudio MMS_FA). Whisper only as a draft, because it merges repeats.
   → `words = [(word, start, end)]`.
2. **Grid.** Tempo and phase from the drum-stem onset envelope (residual to the 16th grid
   should be <10 ms). Downbeat from the bass chroma cycle. Split into 8-bar sections and find
   the final hit. Express every timing as bar.beat.
3. **Lines.** Break at gaps ≥0.15 s, at lyric lines or at rhymes.
4. **Scenes.** Follow the length rules above. `cut = round(first_word_start × fps) + 0…3`,
   and it must fall within +1 beat after beat 1 or 3. A repeated line becomes a copied scene.
5. **Punch.** Score the words of the last line:
   - chorus +3;
   - threat / emotion +2;
   - image +2;
   - line-final / rhyme +1;
   - sung-out >0.5 s +1;
   - on a downbeat +1.

   Keep the best word or pair. It must appear ≥1.5 beats before the next cut; if it does
   not, pick an earlier word and leave the cut where it is.
6. **Design.** Setup layout ≠ previous scene's. Pen lettering at the first scene of each
   8-bar section. Punch per the alternation rules. Spend the signature effects once each.
   Mid shadow on the climax punches, big shadow on the chorus only.
7. **Finale.** Bring back the opening line, enlarged, on the final downbeat, and hold it to
   the end.
8. **Check.**
   - Every scene ends on its punch.
   - No two adjacent punches look the same (unless the lyrics repeat).
   - Each signature effect is used once.
   - Second-half scenes are about 2× shorter.

Typical boxes (% of the frame as seen on screen, `[x0, x1, y0, y1]`):

| Element | Box |
|---|---|
| Setup line | `[27, 73, 40, 57]` |
| Pair of words in a row | y 42–58 |
| Punch, 2 rows | `[5, 95, 0, 46]` + `[5, 95, 46, 96]` |
| Punch, 1 row | `[5, 96, 28, 65]` |
| Column | `[0, 40, 13, 90]` |
| Stack on the right | x 43–90, rows of about 23% |

---

## Part 2 — Components (`lib/vhs_lyrics/`)

| Module | What it does |
|---|---|
| `timeline.py` | Loads the timeline JSON (all times in **frames**) and flattens scenes → word clips. Item kinds: `text` and `grow` (a centred line growing word by word). |
| `styles.py` | Palette, the 11 text styles and shadows. Each style sets the font, variable instance, tracking, edge mode and edge amplitude. |
| `raster.py` | Turns each word into a PNG stretched into its measured box. Handles edges (`spiky` hair fringe / `torn` paper tear + holes / `wobble` brush), pen lettering, baked scanlines (period 8 px pre-lens, depth 0.14), the camo texture and the RGB glitch split. |
| `lens.py` | CRT barrel lens: the ffmpeg chain (zoom 1.17, effective k1 0.17) and `remap_box`, which maps on-screen boxes back to pre-lens coordinates. |
| `background.py` | Per-scene background segments: cover-crop, exact frame count, ffmpeg grade, concat with hard cuts. Also trims the audio and adds the fade-out. |
| `compose.py` | Writes the HyperFrames page. Layers: bg → veil → scene dims → words → scanlines 5% → dirt (overlay) → vignette 45%. Adds the glitch frame steps and writes the no-hold frames. |
| `post.py` | CRT lens → frame holds (every 4th frame repeats, except onsets) → VHS row wave (gaussian bumps ±2–7 px crawling up 40 px/frame). |
| `__main__.py` | CLI pipeline `bg,html,render,post`. |
| `grade.py` | Auto-grade from `bg.look`. |
| `tools/audio.py` | Run in `.venv-audio`. `prep` does download / stems / whisper draft / beat grid / vocal onsets; `align` does lyric forced alignment, optionally chunked. |

### Text styles

| Style | Face | Edge | Used for |
|---|---|---|---|
| `hand` | Bad Script with Е→E, У→Y, П→n, second pen pass, jitter | — | white pen setup; per-item `track` (em) |
| `grunge` | Impact | spiky hairs | main punch (red / white) |
| `torn` | Impact | paper tear + holes | giant single letter |
| `clean` | Impact | — | camo word |
| `rough` | Oswald Bold | wobble 3 px | giant blue pronoun column |
| `cond` / `condb` | Oswald SemiBold / Bold | — | setup lines, stacks, big clean rows |
| `thin` | Oswald Light | — | thin red pre-hit |
| `brush` | Oswald Regular | wobble 2.5 px | dark-red brush punch |
| `roboto` / `robotom` | Roboto Condensed Bold / Medium | — | lowercase setup / glitch word |

### Item keys
- `box` `[x0, x1, y0, y1]` in % of the frame as seen on screen.
- `color`: a palette name or `[r, g, b]`. Palette: white, red, darkred, hotred, tornred, pink,
  blue, lblue, dblue, green.
- `shadow`: `mid` | `big`.
- `fx`: `glitch` | `camo`.
- `skew` (deg).
- `amp`: spike amplitude override (cap it on tall white words).
- `dil`: thicken the glyph before resizing (MaxFilter size).
- `track`: letter spacing for pen lettering.
- `until`: frame where the item disappears (default = the scene's end).

### Scene keys
- `start` / `end` (frames).
- `bg`: `src` (relative to the timeline file), `offset` in seconds, and either an ffmpeg `grade`
  or `look` `{median, p95, sat, tint}`. With `look` the grade is fitted to the clip on every
  build (`grade.py`, curves through the clip's own median/p95) and logged to
  `hyperframes/assets/grades.json`. An offset past the clip's end slides back automatically;
  a clip shorter than the scene loops.
- `dim`: `{from, opacity}` — the backdrop drops before a big hit.

### Global effects
`effects`: `lens`, `frame_holds`, `vhs_wave`, `veil` (stepped bg flicker), `dirt`,
`scanlines`, `vignette`. Also `lens_k1` and `lens_zoom`.

### Grading backgrounds
Match each scene's **median and mean** luma to the reference (or to the target mood).
- The look is dark: median roughly 2–35 on a 0–255 scale.
- When a clip must be darkened but its lights kept, use `curves` (crush lows, keep highs)
  instead of a linear multiplier.
- Cut around lightning or flashes in the source clip.

### Notes
- Impact is read from `C:/Windows/Fonts` (it is not redistributable). The other fonts ship
  under OFL in `lib/vhs_lyrics/assets/fonts`.
- Verified: the example timeline reproduces the reference remake pixel-identically
  (mean abs diff 0.0 over 888 frames).
- Render: about 1 min for 30 s at 1440×1080 with 3 workers, plus about 1 min of post.
  It needs about 3 GB of free RAM.
