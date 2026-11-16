---
name: pixel-lyrics-edit
description: |
  Make a TikTok lyric snippet in the user's approved "dark pixel-game" style (approved on «mefedron master 4»,
  2026-11-15): a vertical 1080x1920 30 fps edit where one drawn hero lives through the lyrics in one world —
  every line is one literal shot drawn by Gemini image in a grim PC-98 style, the camera moves inside the
  drawing, sung words trigger events and a game HUD (HP bar, ₽ counter, RPG windows), the picture is crushed
  into a dithered 270x480 pixel grid, lyrics are hard-cut centred pixel type with smear frames and syllable
  flicker on chosen words, finished with a cold grade (ice at 0.5, ice-blue accent).
  Use when the user sends a track (and usually a words.json) and asks for "пиксельный сниппет", "пиксельная
  анимация", "как эдит с героем в ушанке", "как пиксельный мефедрон", "сниппет в стиле старой игры",
  "иллюстрация текста с героем", "ещё один сниппет в этом стиле", or wants shots, hero, text, colours,
  accent or grade changed in such an edit. Not for footage edits (vhs-lyrics-edit, glitch-drop-lyrics-edit,
  card-strobe-edit) and not for the square fake-interface edit (ui-lyrics-edit).
---

# Pixel-lyric edit: the workflow

The kit is `lib/pixel_lyrics/` (a Hypit project template, the approved example, and the look as reference
pictures). Rendering is local and free; **the pictures are paid** (Gemini image ≈ $0.039 each, about 18 per
pair of edits ≈ $0.70).

1. **Read** `skills/creative/pixel-lyric-edit.md`: Part 0 is the workflow, Part 1 the grammar, Part 2 the
   scene API. Look at `lib/pixel_lyrics/examples/mefedron/scenes/*.js` and `gen/*.json` before writing.
2. **Init.** `.venv/Scripts/python -m lib.pixel_lyrics init projects/<id>`; track at
   `projects/<id>/assets/audio/master.wav`. Run everything else from `projects/<id>/`.
3. **Words — always re-align.** The user's word file has the right text and rough times. Stems + forced
   alignment + a look at every line, as in `skills/creative/ui-lyric-edit.md` Part 0 (30 fps, lead 0.35).
4. **Ask for the money before drawing.** Say how many pictures and how much; get an explicit yes and a
   cap; pass it as `--budget` to every `tools/gen_img.py` run. If Google answers 429 `limit: 0`, billing
   is off on the key's project — only the user can turn it on.
5. **Treatment.** Hero, world, one row per shot: words, the literal picture, the event on each word, the
   way into the next shot. A repeated line gets a new shot with higher stakes.
6. **Draw in order and look at every picture**: hero sheet → anchor room → scene batch → alternates and
   retakes. Same style block and hero block in every prompt; hero sheet + anchor as references.
   For a new hero keep the look by referencing `assets/style/*.jpg`. Then `tools/prep_img.py`.
7. **Scenes.** `packages/pixel-lyrics/client/scenes/<edit>.js`: shots with camera tracks, word events,
   HUD story, motivated transitions on the first word of each line. Measure positions in the pictures.
8. **Lyrics.** Phrases of 1–3 words, one key word each. Words the user wants to flicker get syllable
   offsets from `tools/syllables.py` (vocal stem), not an even split.
9. **Preview** with `tools/shot.mjs` (whole-edit sheets, passages frame by frame, full frames). Fix what
   stands still, hides behind the lyrics or cannot be read.
10. **Render** (`gen_source.mjs`, `npm run build -w @kit/pixel-lyrics`, `hypit build`, `hypit get`), then
    **grade**: `node tools/shot.mjs <edit> cuts`, `node tools/grade.mjs <in> <out> ice <edit> 0.5`.
    Default finish is cold accent + `ice 0.5`; `halo` and `dream` and the warm accent are the alternatives.
11. **Verify the files** (`tools/check_sync.py` = 0 ms, frame grids) and say what you could not check — you
    cannot listen or watch motion. Files over 30 MiB need a smaller copy to reach the user's phone.

One reference has one role: the pixelation reference gave only the pixelation, the text references only
the text animation. A style frame or contact sheet before a full build saves a rejected version.

**After touching the kit**: run the regression in Part 2 and `pytest tests/lib/test_pixel_lyrics.py`.
