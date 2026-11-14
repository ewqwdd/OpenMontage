# UI-Lyric Edit: editing grammar and component kit

A square 1080×1080, 60 fps lyric edit where **every line is acted out by a fake interface**. A dating
swipe, a pulse widget, a wallet, a chat: the UI object does on screen what the line says, exactly on
the sung words. There is no footage. Everything is code animation, rendered locally with Hypit.

The style comes from two TikToks the user sent on 2026-11-14 (@ezarrr_3 — the one that went viral — and
@zxchugirane). The user approved the adaptation on «mefedron master 4» ("найс"): chorus 13.95–28.67 s
and verse 28.65–43.25 s. Both edits are the kit example `lib/ui_lyrics/examples/mefedron/`.

```
.venv/Scripts/python -m lib.ui_lyrics init projects/<id> [--example mefedron]
node tools/gen_source.mjs                      # words.final.json -> audio cuts + Hypit Sources
npm run build -w @kit/ui-lyrics                # after every change in client/
hypit build productions/<edit>/main.svrun --follow
```

---

## Part 0 — Workflow

Run project commands from `projects/<id>/`. Everything is free and local (spending policy: fine).

1. **Init.** `.venv/Scripts/python -m lib.ui_lyrics init projects/<id>` copies the template, runs
   `npm install`, selects the local runtime and prepares the render browser. Put the track at
   `assets/audio/master.wav`.
2. **Pick the excerpts.** One edit ≈ 14–15 s ≈ 4 lyric lines. Tell the user the tempo and the windows.
   - librosa reports 2/3 of the real tempo on trap (88 for 132 BPM). Check it against a repeated
     line: on «mefedron» the chorus repeats every 7.25 s = 16 beats.
   - Lines often start a pickup early (0.1–0.2 s before the downbeat), so cut by words, not by bars.
3. **Align the words. Always.** The user's `words.json` has the right text and rough times; on
   «mefedron» it was off by up to 0.5 s, sometimes by a whole word.
   - Cut the excerpt ± 3 s, then stems + whisper draft + grid:
     `.venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio prep <excerpt.wav> analysis`
   - `analysis/lyrics.txt`: one sung line per line, lowercase, no punctuation, `е` for `ё`.
     `analysis/lyrics_display.txt`: the same lines as they must look on screen.
   - `analysis/chunks.json`: one chunk per line, `[[[line], t0, t1], …]` in excerpt time, windows
     from the `#SEG` lines of `analysis/asr.txt`, overlapping the neighbours by ~0.1 s.
   - `PYTHONIOENCODING=utf-8 .venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio align analysis --chunks analysis/chunks.json`
     (without `PYTHONIOENCODING` the Cyrillic print crashes on Windows).
   - `node tools/words_from_fa.mjs --offset <excerpt start> --edits '{"chorus":[0,1,2,3]}' --label "ARTIST // EDIT"`
     writes `productions/words.final.json`.
   - **Verify on spectrograms**: `.venv-audio/Scripts/python tools/plot_align.py analysis --offset <s> --final productions/words.final.json`,
     then look at every `analysis/plots/line*.png`. A word start sits on the rise of its first
     syllable or on its leading consonant noise. MMS_FA scores of 0.1–0.3 are normal for sung
     vocals; trust the picture. Typical fix: a line-opening "Эй" or "Да" is 30–50 ms late.
     A repeated line is a free cross-check: its word offsets must repeat.
   - Set each edit's `start` (about 0.15 s before its first word, but after the previous line's
     last syllable) and `frames` (end before the next line's first word) by hand.
4. **Write the treatment** (`productions/TREATMENT.md`): one table row per scene — words, interface,
   what happens on which word. Follow Part 1. Tell the user the scene list before building if the
   reading of a line is not obvious.
5. **Write the scenes** in `packages/ui-lyrics/client/scenes/<edit>.js` (+ `.css`). The file name is
   the edit name in `words.final.json`. Copy scene types from the example (Part 2 has the list).
6. **Preview without rendering.** Serve the project root statically and open `dev/index.html`:
   `?edit=<edit>&sheet=230,236,250&cols=5&cell=254` for contact sheets, `&play` for sound.
   Check every scene, every transition frame by frame, and the big frames at `cell=810`.
7. **Render.** `node tools/gen_source.mjs && npm run build -w @kit/ui-lyrics && hypit build productions/<edit>/main.svrun --follow`
   (about 3 minutes per edit). Export: `hypit get <build-id> --output final.video --to renders/<name>.mp4`.
8. **Verify the file.**
   - `hypit media tiles renders/<name>.mp4 --at … --columns 4 --rows 3 --cell 420 --to renders/review/<x>` and look.
   - `.venv-audio/Scripts/python tools/check_sync.py renders/<name>.mp4 assets/audio/<edit>.wav` must print 0 ms.
   - Every-frame tiles around two word onsets: the word is visible 1 frame before its onset.
9. Give the user the paths; send with telegram-send if asked.

---

## Part 1 — Grammar

### Why it works
1. **Recognised in 0.2 s.** Search, wallet, chat, call screen: forms the viewer knows without
   reading. That is why a 1.5 s scene lands.
2. **A hit is a state change of the same object**, not a new picture. On the punch word the same
   card flips colour and its content breaks (green chart → red crash; wallet up → wallet 0,00).
3. **Nothing stands still inside a scene.** A counter rolls, rows arrive one by one, something types.
4. **Cuts have no exit.** The old scene is never animated out.
5. **The frame never changes.** HUD, timecode and progress bar hold the edit together.
6. **One hero object.** It takes 65–75 % of the width; the caption sits strictly above or below;
   only dust (chips, blurred glyphs, particles) lives at the edges.

### Rules
- **Scene length**: half a line to a line, 1.2–2 s; a list line or a chat may hold 3–3.6 s.
  6–7 scenes per 14.5 s.
- **Scene start** = first word of the scene − 3 frames. The flash lands on the cut, the word lands
  on its own frame while the scene is still pulling focus.
- **Transition**: one pre-frame of the next accent at 60 % over the old scene → one solid frame →
  the new scene with blur 30 → 0 px in 15 frames and scale 1.075 → 1 in 18.
- **Caption**: Inter 900, 58–70 px, one or two lines, laid out in final positions. A word appears on
  its frame: opacity in 3 frames, blur 12 → 0 and y +20 → 0 in 9. One pill per scene, on the word
  the UI acts on hardest; swear words always get the pill. Chat scenes have no caption: the bubble
  carries the words.
- **Word lead**: a word is on screen 1 frame before its vocal onset.
- **Colour**: near-black base, one accent per scene, the accent names the mood: pink = love,
  red = body / error / declined, lime or mint = money / top, ice white = emptiness, violet = chat.
  Neighbouring scenes never share an accent.
- **Hits**: `hit(frame, amp, rgb)` on the punch words — shake always, RGB split only on the hard
  ones (2–3 per edit).
- **Repeated line** (a chorus sung twice): never copy the scene. Same meaning, another interface,
  higher stakes (swipe → year-in-review top-4; pulse → error cascade; stream → stream going dark).
- **Object continuity**: when two lines argue with each other, the second one reuses the first
  one's card in a new state (wallet at 4.8M → the same wallet at 0,00 «ОТКАЗАНО»).
- **Lists fill progressively**; if a card would stand half-empty for more than ~0.5 s, show
  skeleton rows that lock in on their words.
- **Chats** are bottom-anchored: a new message pushes the older ones up (`stack()` in the example).
- **Ending**: the last scene resolves into black (or dims to ~20 %) over the last 14–16 frames, so
  the loop restarts cleanly.
- **Tone**: the UI text is sardonic, never an ad. No doses, prices of substances, or how-to detail.

### What must be reviewed in the preview
- Is the object recognisable in the first 0.3 s of its scene? (The first ceiling was a grey strip
  until it got a ceiling fan and later eyelids.)
- Does anything stand empty or static for more than half a second?
- Do particles cover the number or the button they celebrate? Move the burst to a card corner.
- Is every caption line inside 1000 px?

---

## Part 2 — The kit

`lib/ui_lyrics/template/` is a Hypit project; `init` copies it.

| Path | What |
| --- | --- |
| `packages/ui-lyrics/client/engine.js` | `setupEdit(root, data) → render(frame)`. Scenes, transitions, captions, HUD, camera shake / RGB, grain. Pure function of the frame. |
| `packages/ui-lyrics/client/engine.css` | Base, HUD, caption, particles, shared atoms (`.card`, `.row`, `.banner`, `.stamp`, `.ring`, `.live`, `.roll`, `.ava`, `.ticker`). |
| `packages/ui-lyrics/client/scenes/<edit>.js/.css` | One scene set per edit. Registers `SCENE_SETS.<edit> = function (A) { … }`. |
| `packages/ui-lyrics/build.mjs` | Inlines `client/` into `src/generated.ts`; then `tsc`. |
| `packages/ui-lyrics/src/*.ts` | Hypit Surface `<ui:Edit variant=… ><ui:Word text at/>…`, Producers, VisualTrack. Fonts arrive as four FontStacks through hidden probe slots. |
| `tools/gen_source.mjs` | `words.final.json` → `assets/audio/<edit>.wav` + `productions/<edit>/main.svml/.svrun`. |
| `tools/words_from_fa.mjs`, `plot_align.py`, `check_sync.py` | Alignment merge, spectrogram check, A/V offset check. |
| `dev/index.html` | Preview page; loads every file in `client/scenes/` from the server's directory listing. |

### Scene API

```js
SCENE_SETS.chorus = function (A) {
  const { wf, scene, hit, burst, roller, popIn, slam, pose, tapRing, eo3, eo5, back, lerp, clamp, fmt, I, SH } = A;
  const start = wf(6) - 3;                    // wf(i) = frame of the i-th word of this edit
  hit(wf(8), 16, 14);                         // shake 16 px, RGB split 14 px
  scene({
    start, accent: '#ff2d3a', bg: '#150406', side: 'HEALTH // 02 // BPM',
    glyphs: [['!', 90, 240, 380]],            // big blurred background glyphs: text, x, y, size
    chips: [['тахикардия', 716, 262, 5]],     // small mono tags: text, x, y, rotation
    cap: { pos: 'top', size: 66, lines: [[6], [7, 8]], pills: [6] },   // word indices
    build(el, s) {                            // el = scene content layer, 1080×1080
      el.innerHTML = `<div class="card pulse">…</div>`;
      return lf => { … };                     // lf = frame since scene start; set the COMPLETE state
    },
  });
};
```

- Scenes must be registered in time order. A scene ends where the next one starts.
- `update(lf)` must compute everything from `lf`: the renderer seeks to arbitrary frames with
  several workers. No state carried between calls, no `Math.random()` (use `A.rng(seed)` / `A.hash`).
- Optional scene fields: `flash` (flash colour), `pill` / `pillInk`, `zoomIn`, `blackout: lf => 0..1`.
- `s.el.style.setProperty('--a', colour)` recolours a scene mid-way (state flip); `s.glowEl` is the
  background glow.
- Helpers: `pose(lf, seed)` hero-card 3D settle + idle drift; `popIn(el, age, opts)` rows and chips;
  `slam(el, age, rot, from)` stamps and banners; `roller(el, value(lf), format)` counter with a
  ghost trail; `burst(host, opts)` particles (`dt => …`); `tapRing(el, age)`.
- Query scene elements with scoped selectors (`.ecg path`, not `path`): icons contain paths too.
- Text that appears later must not need a font subset nothing else uses; `display:none` text does
  not load fonts. Inter covers Latin, Cyrillic and ₽; arrows and hearts fall back to a system font.

### Scene types in the example (copy and adapt)

`examples/mefedron/scenes/chorus.js`: dating swipe deck with stamps and a match counter · pulse
widget with ECG, load gauge and a banner · live stream with eyelids (and its closing variant) ·
year-in-review top-N with skeleton rows · cascading error dialogs.
`examples/mefedron/scenes/verse.js`: incoming call with decline and in-scene state flip · chat with
word-by-word bubbles and a block pill · cart with a tap, SOLD OUT stamps and a rolling total ·
wallet (two states: rolling up with coins and a ticker; crashing to 0,00 with «ОТКАЗАНО») · tile
grid that fills · chat with an attachment (bloodshot eyes) and the dim-out ending.

### Limits
- The canvas is fixed at 1080×1080. A 9:16 version needs a reflow of the engine and scenes.
- `words.final.json` word order and count are bound to the scene code through word indices.
- Changing a word time: edit `start` in `words.final.json`, run `gen_source.mjs`, rebuild.

### Regression
`python -m lib.ui_lyrics init projects/<tmp> --example mefedron`, copy the track to
`assets/audio/master.wav`, `node tools/gen_source.mjs`, build the package and both edits, then compare
with the approved renders in `projects/mefedron-snippets/renders/`:
`ffmpeg -i new.mp4 -i approved.mp4 -lavfi psnr=stats_file=psnr.log -f null -`.

Measured on 2026-11-14 when the kit was extracted:
- verse: identical (PSNR `inf`);
- chorus: average 51.9 dB, worst frame 38.5 dB. The differing frames are the error cascade with the
  RGB split and what follows it; amplified ×6 the difference is barely visible. Treat an average
  above 48 dB and a worst frame above 35 dB as a pass, and look at the worst frame if it is lower.

Before deleting a temporary project run `hypit runtime down` inside it: its worker keeps
`.hypit/runtimes/local/runtime.sqlite` open, and on Windows the folder cannot be removed until it stops.

`pytest tests/lib/test_ui_lyrics.py` checks the template, the example data and `init` (9 tests, no npm).
