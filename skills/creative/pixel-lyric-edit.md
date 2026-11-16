# Pixel-Lyric Edit: editing grammar and component kit

A vertical 1080×1920, 30 fps lyric edit that looks like a **grim old Japanese PC game**: one hero, one
world, every lyric line acted out literally in one drawn shot. The camera lives inside the drawing, the
sung words drive what happens, a game HUD keeps score, and the whole picture is crushed into a 270×480
dithered pixel grid. Lyrics are hard-cut pixel type in the centre; drug names (or whatever the user picks)
grow syllable by syllable and flip their colours on each one.

The pictures are drawn by Gemini image (**paid**, ≈ $0.039 each); everything else is code and FFmpeg.

Approved by the user on 2026-11-15 on «mefedron master 4» (chorus 13.95–28.67 s, verse 28.65–43.25 s).
The finish the user picked: **cold accent + `ice` grade at 0.5**. Both edits are the kit example
`lib/pixel_lyrics/examples/mefedron/`; the look itself is kept as pictures in `lib/pixel_lyrics/style/`.

```
.venv/Scripts/python -m lib.pixel_lyrics init projects/<id> [--example mefedron]
.venv/Scripts/python tools/gen_img.py assets/gen/specs/00_hero.json --budget <usd>   # PAID, after the user's yes
.venv/Scripts/python tools/prep_img.py                 # assets/gen -> client/img
node tools/gen_source.mjs                              # words.final.json -> audio cuts + Hypit Sources
npm run build -w @kit/pixel-lyrics                     # after every change in client/
hypit build productions/<edit>/main.svrun --follow
node tools/grade.mjs renders/<edit>.mp4 renders/<edit>_ice50.mp4 ice <edit> 0.5
```

Where each idea came from (one reference = one role; take nothing else from it):

| Reference | Role |
| --- | --- |
| @zlgmari, @idkidksc | the grammar: line = scene, word = event, one hero, motivated transitions |
| @ps1h022 | **only** the pixelation. Its photo cut-outs, font and montage were tried first and rejected |
| @warden9943 | how lyrics appear and change: centred line, chunks on hard cuts, one smeared frame |
| @not_demiv («ПРОВОДА») | syllable flicker: the word grows by syllables and inverts its colours on each |

---

## Part 0 — Workflow

Run project commands from `projects/<id>/` (the folder is git-ignored: anything worth keeping goes back
into the kit).

1. **Init.** `.venv/Scripts/python -m lib.pixel_lyrics init projects/<id>`; put the track at
   `assets/audio/master.wav`. Add `--example mefedron` to start from the approved scenes.
2. **Excerpts and words.** Exactly as in `skills/creative/ui-lyric-edit.md` Part 0, steps 2–3 (stems,
   forced alignment, `tools/words_from_fa.mjs`, check every line on `analysis/plots`). Differences:
   30 fps, `"lead": 0.35`, `"accent": "cold"` in `productions/words.final.json`. The user's word file has
   the right text and rough times: always re-align. About 14–15 s and four lines per edit.
3. **Money first.** One edit pair needs about 18 pictures ≈ $0.70 (hero sheet, anchor room, 12 scenes,
   3 alternates, 1–2 retakes). Tell the user the number and get an explicit yes with a cap **before**
   the first call; pass the cap to every run as `--budget`. The Google project of `GOOGLE_API_KEY` must
   have billing on (free-tier image quota is 0 → HTTP 429 `limit: 0`; only the user can fix that).
4. **Treatment** (`productions/TREATMENT.md`): hero, world, then one row per shot — words, what the
   picture shows, what happens on which word, how we get to the next shot. Follow Part 1.
5. **Draw** (Part 1 «Pictures»). Hero sheet → look at it → anchor room → look at it → the scene batch →
   look at all → alternates and retakes. Then `tools/prep_img.py`.
6. **Syllables.** For each word the user wants to flicker: `tools/syllables.py <vocals.wav> --offset <s>
   --edit <edit> --word <i>` and read the syllable starts off the envelope (Part 1 «Lyrics»).
7. **Scenes.** `packages/pixel-lyrics/client/scenes/<edit>.js`; the file name is the edit name. Copy
   the structure of the example. Measure positions in the pictures before placing anything (Part 2).
8. **Preview without rendering.** `node tools/shot.mjs <edit> drafts/a.jpg frames=0-440-8 cols=10 cell=200`
   for the whole edit, `frames=30-54-1` for a passage frame by frame, `f=120` for one full frame.
   Fix what stands empty, static, hidden behind the lyrics, or unreadable.
9. **Render.** `node tools/gen_source.mjs && npm run build -w @kit/pixel-lyrics`, then
   `hypit build productions/<edit>/main.svrun --follow` (≈ 1 min per edit) and
   `hypit get <build-id> --output final.video --to renders/<edit>.mp4`.
10. **Grade.** `node tools/shot.mjs <edit> cuts` once (writes `productions/cuts.json`), then
    `node tools/grade.mjs renders/<edit>.mp4 renders/<edit>_ice50.mp4 ice <edit> 0.5`. Develop a look on
    stills first: append `still` and write a `.jpg`.
11. **Verify the files.** `tools/check_sync.py <mp4> assets/audio/<edit>.wav` prints 0 ms; pull a frame
    grid with ffmpeg and read it. Say what you could not check (you cannot listen or watch motion).
    Files over 30 MiB do not reach the user's phone: send a copy made with `--crf=20 --maxrate=11M`.

---

## Part 1 — Grammar

### The idea

- **One hero, one world.** The viewer follows a person through a night, not a slideshow. Every shot
  shows the same hero in places that belong together (his room, the yard kiosk, the stairwell).
- **A line is a shot, and the shot is literal.** «звонит долбоёбка» → a phone ringing on the floor with
  the caller's name on a game window. Metaphors become objects; that is where the humour is.
- **Words are events.** Inside a shot every sung word moves something: the camera hops to an object,
  an item pops up and gets swallowed, a counter rolls, a price tag flies off.
- **Dark and deadpan, never cartoonish.** The joke is in the HUD and the windows, the drawing stays grim.
- 6–7 shots per 15 s edit. A repeated line gets a new shot with higher stakes, never a copy
  (round 1: items pop over his head; round 2: the stash on the carpet, the cursor hops between items).

### Pictures (Gemini image, `tools/gen_img.py`)

Every prompt ends with the same style block and every hero prompt starts with the same hero block
(copy both from `examples/mefedron/gen/*.json`):

- **Style block:** 1990s PC-98 Japanese adventure game pixel art, low resolution, limited 16-colour
  palette, checkerboard dithering, hard dark outlines; grim night palette (near-black violet, dusty
  purple, teal shadows, sickly orange lamp light, bone white, blood-red accents); vertical frame;
  **keep the top third dark and uncluttered** (the lyrics live there); no text, no letters, no brand
  names, no UI, no watermark.
- **Hero block:** a short, fixed list of recognisable things (hat, hair, clothes, one accessory).
- **Reference chain.** `hero_sheet` (1:1: front, side, close-up; no refs) → the anchor room (ref: hero
  sheet) → every scene (refs: hero sheet + anchor). That is what keeps the hero and the palette the
  same across 15 pictures. For a new track with a new hero, pass `assets/style/*.jpg` as refs and say
  "same drawing style and palette as the attached picture".
- **Ready heroes** live in `lib/pixel_lyrics/characters/<name>/`: the approved sheet, crops and
  `character.md` (hard rules of the look, the hero block, how to add angles). Use the sheet as the
  hero reference instead of drawing a new one. First one: `hollow`.
- **A reference pulls the composition with it.** A bird's-eye shot asked with the room as reference
  came back as the room again. When the angle must change, reference a picture that already has that
  angle (the top-down flat-lay), not the anchor.
- **Alternates** for a pose change inside a shot: reference the finished scene and ask to "redraw this
  exact picture… only change …". They come back almost registered, never exactly: measure the hero's
  head in both and swap with a small kick, or treat the alternate as its own shot.
- **Sprites:** a 2×2 sheet of item icons on pure black, 1:1 → `prep.json` `sprites` cuts and keys them.
- **Look at every picture before the next batch.** Reject wrong angle, wrong hero, duplicated limbs,
  drawn text. A real brand name the model drew gets a `mosaic` box in `prep.json`.
- Never draw anything paid without the user's yes; move rejected pictures to `assets/gen/rejected/`.

### Camera and shots

- A shot is one picture under a camera track: start wide, push in, hop to the detail the word names.
  Fast hops take 4–6 frames with `eo5` and ride on a slow drift in between; nothing ever stands still
  (the sequencer adds a tiny breathing drift itself).
- **Transitions are motivated and land on the first word of the line**:
  push into a face → the close-up; tilt up (`slide` with `dy: -1`) → the ceiling; spin and zoom into a
  spiral → fall onto the carpet; a flashlight → white flash. Every cut gets motion blur and a mosaic
  burst; hard cuts with no reason are not used.
- Keep the hero's face out of the lyric band (top 300 px of 960) at rest.

### HUD and windows

- A persistent top row (y ≈ 142–162): a bar on the left, a counter on the right. They tell a small
  story across the edit: HP drains with every item and hits zero on the last one; ₽ jumps to 999 999
  «(ТИПО)» at the kiosk and burns down on the clothes.
- RPG windows (`boxed` in the example) hang on objects: caller name over the phone, «ВЫЗОВ ОТКЛОНЁН»,
  «ТЕМА ×ВСЯ», shop refusal. Text is sardonic and short, never an ad, no how-to detail.
- Selection cursor (four blinking corners) for "this one"; pixel heart for love; item sprites pop
  with `back()` and get swallowed.

### Lyrics

- One centred line at a time, DotGothic16 caps, 36 px, black outline. A phrase is 1–3 words and
  must fit 524 px; split longer lines into phrases at the breath.
- Words are appended on **hard cuts** and the line re-centres each time. The frame before every
  addition and the first frame of a new phrase are torn into a horizontal smear. The old phrase
  vanishes the instant the next begins. No fades, no slides.
- One key word per phrase in the accent colour.
- **Syllable words** (only the ones the user names; on «mefedron»: МЕФЕДРОН, ОКСИКОДОН): alone in their
  phrase, 72 px, accent colour, grown syllable by syllable; each syllable flips fill and outline, and
  the last state is always the normal one. Offsets come from the vocal stem, not from dividing the
  word evenly — they were 0/5/12 frames in one chorus and 0/4/10 in its repeat.
- Accent: `cold` = ice blue `#5ad0ff` (approved), `warm` = orange `#ffb23e`.

### Filter, glitch, grade

- The crush is always on: 270×480 grid, Bayer dither, fixed 30-colour palette, soft vignette.
- Glitch (`rows`, `rgb`, `smear`, `red`, 1-bit `levels`) only where the lyric says the body is
  breaking, growing with each word, and dead calm right after it. End every edit with `crt`.
- Grade after render, on the finished file: `ice` (steel-teal, neutral whites, hard contrast, blur on
  cuts), `halo` (violet neon, anamorphic streaks, chroma, grain, sideways whip on cuts), `dream`
  (blue night, mist, light trails — they also trail the lyrics —, punch-in flash on cuts).
  Approved: `ice` at 0.5. The strength mixes the look over the source; cut effects stay full.

---

## Part 2 — Kit

`lib/pixel_lyrics/template/` is the project; `packages/pixel-lyrics` is the Hypit component
(`<px:Edit variant="<edit>" accent="cold|warm">` with one `<px:Word>` per sung word).
`build.mjs` inlines `client/engine.js`, every `client/scenes/*.js`, `client/img/*` and the font.

### A scene set

```js
(window.PIXEL_SCENES = window.PIXEL_SCENES || {}).chorus = A => {
  const { wf: W, track, seq, kick, shake, P, back, heart, spr, tvnoise, TOTAL } = A;
  const cam = track([{ f: 0, x: .5, y: .56, z: 1.05 }, { f: W(2), x: .43, y: .5, z: 1.26, e: 'eio' }]);
  const S = seq([
    { img: 'c1_room', from: 0, cam, over: (ctx, f, iw, ih) => { /* picture-space extras */ } },
    { img: 'c2_face', from: W(6), cam: cam2, in: { mosaic: 9, mw: 4, blur: 1.5, bw: 5 } },
    { img: 'c2_ceiling', from: W(9) - 3, cam: cam3, hud: (ctx, f) => {}, in: { slide: 1, dy: -1, h: 4, blur: 1.6 } },
  ]);
  return {
    lines: [{ from: 0, to: 1, key: [1] }, { from: 2, to: 2, syl: { 2: [['МЕ', 0], ['ФЕ', 5], ['ДРОН', 12]] } }],
    cuts: S.cuts, draw: (ctx, f) => S.draw(ctx, f), blur: f => S.blur(f),
    labels: f => [/* HUD on the text layer */],
    fx: f => ({ block: S.block(f), flash: .2 * kick(f, [W(1)], 6), crt: P(f, TOTAL - 8, 7) }),
  };
};
```

Everything is a pure function of the frame: no `Math.random`, no state between frames.

- `W(i)` — frame of word *i* (index inside the edit). Tie every event to `W(i)`, never to a beat grid.
- `track([{f, x, y, z, r, e}])` — camera keys. `x, y` are 0..1 in the picture, `z = 1` covers the frame,
  `e` eases the segment arriving at the key (`eo`, `eo5`, `ei`, `eio`, `back`, `lin`).
  The camera is clamped inside the picture; with rotation `r` it needs
  `z ≥ (270·|cos r| + 480·|sin r|) / 274` or the corners go black. `free: true` lifts the clamp.
- `seq(shots)` — `img` (name or `f => name`), `from` (cut frame), `cam(f)`, `over(ctx, f, iw, ih)` drawn
  in the picture's pixels (moves with the camera), `hud(ctx, f)` in 540×960 screen space,
  `in: {mosaic, mw, blur, bw}` or `{slide: 1, dx, dy, h, blur}`. Gives `draw`, `blur`, `block`, `cuts`,
  and `pos(shotIndex, f, nx, ny)` → where a picture point is on screen (to hang a label on an object).
- Drawing: `heart(ctx, x, y, px, col)`, `spr(ctx, name, x, y, w, {s, r})`, `tvnoise(ctx, x, y, w, h, f)`,
  `box(...)`, `shake(f, hits, amp, dur)`, `kick(f, hits, dur)`, `hash`, `vnoise`.
- `lines` — phrases: `{from, to, key: [wordIdx], syl: {wordIdx: [[text, frameOffset], …]}}`.
- `labels(f)` — text `{t, x, y, size, col, align, bold, blink, from, to}` or box
  `{box: [x, y, w, h], fill, edge}` in 540-space. Sizes 16 (use `bold: 0`) and 32 are clean; colours are
  `bone`, `ink`, `key`, `red`, `green`. `₽` is drawn as `Р` with a crossbar (the font has no ruble).
  `A.tw(text, size)` measures.
- `fx(f)` — `flash, bri, sat, rows, rgb, block, smear, red, white, vig, levels (<4 = 1-bit), crt`.

### Measuring a picture

Positions are guessed wrong from thumbnails. Crop the picture with a 100 px grid (PIL) and read the
numbers, or render a contact sheet and correct. Alternates: put both side by side at the same scale.

### Tools

| Tool | What |
| --- | --- |
| `tools/gen_img.py <spec> --budget N` | Gemini pictures, logs cost to `assets/gen/_log.jsonl`, stops at the cap |
| `tools/prep_img.py` | `assets/gen/*.png` → `client/img` (+ sprites, brand mosaic, manifest) |
| `tools/syllables.py` | vocal envelope of a word with frame offsets |
| `tools/gen_source.mjs [--accent warm]` | audio cuts + Hypit Sources (`productions/<edit>[-warm]/`) |
| `tools/shot.mjs` | preview captures; `<edit> cuts` → `productions/cuts.json` |
| `tools/grade.mjs` | the three looks, strength, `still` mode |
| `tools/plot_align.py`, `tools/check_sync.py` | alignment plots, audio offset of a render |

### Traps that cost time

- ffmpeg `blend` with inputs in different pixel formats tints the whole frame violet. `grade.mjs`
  forces `format=gbrp` on every branch; keep that when adding a look.
- Git Bash heredocs break on long JS with quotes: write files with the Write tool.
- `drawtext` crashes this ffmpeg build (fontconfig); label frames another way.
- Python on Windows: `PYTHONIOENCODING=utf-8` or Cyrillic prints crash.

### Regression (after touching the kit)

```
.venv/Scripts/python -m pytest tests/lib/test_pixel_lyrics.py
.venv/Scripts/python -m lib.pixel_lyrics init <tmp>/kitcheck --example mefedron
# copy chorus.wav / verse.wav into <tmp>/kitcheck/assets/audio, then from there:
node tools/gen_source.mjs --no-audio && node tools/shot.mjs chorus cuts      # 118,168,225,335,386
node tools/shot.mjs chorus drafts/sheet.jpg frames=0-440-20 cols=12 cell=160  # look at it
npm run build -w @kit/pixel-lyrics && hypit build productions/chorus/main.svrun --follow
```

The chorus words must land on frames 4, 13, 34, 61, 73, 85, 118, 142, 156, 171, 195, 198, …
