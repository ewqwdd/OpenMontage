---
name: ui-lyrics-edit
description: |
  Make a TikTok lyric edit in the user's approved "UI-lyric" style (approved on «mefedron master 4», after the
  @ezarrr_3 / @zxchugirane references): a square 1080x1080 60 fps code animation with no footage, where every
  lyric line is acted out by a fake interface (dating swipe, pulse widget, live stream, wallet, cart, call
  screen, chat), every sung word lands on its own frame, scenes change with a one-frame accent flash and a
  focus pull out of blur, a HUD with REC timecode holds the frame.
  Use when the user sends a track (and usually a words.json) and asks for "эдит с интерфейсами", "UI-эдит",
  "как эдит с мефедроном / как у ezarrr", "иллюстрация текста интерфейсами", "такой же сниппет под этот трек",
  "ещё один сниппет в этом стиле", or wants scenes, words, timings, colours or transitions changed in such an
  edit. Not for footage-based edits (vhs-lyrics-edit, glitch-drop-lyrics-edit, card-strobe-edit).
---

# UI-lyric edit: the workflow

Everything is local and free: Hypit renders HTML/JS scenes with a headless browser and FFmpeg. No paid
generation. The kit is `lib/ui_lyrics/` (a Hypit project template plus the approved example).

1. **Read** `skills/creative/ui-lyric-edit.md`: Part 0 is the workflow, Part 1 the grammar, Part 2 the kit and
   the scene API. Look at `lib/ui_lyrics/examples/mefedron/scenes/*.js` before writing scenes.
2. **Init.** `.venv/Scripts/python -m lib.ui_lyrics init projects/<id>`; put the track at
   `projects/<id>/assets/audio/master.wav`. Run everything else from `projects/<id>/`.
3. **Excerpts.** About 14–15 s and four lines per edit. Cut by words (lines start a pickup early). Tell the
   user the windows and the tempo; librosa gives 2/3 of the real tempo on trap.
4. **Align the words — always.** The user's word file has the right text and rough times (off by up to 0.5 s
   on «mefedron»). Demucs stem + chunked forced alignment (`lib.vhs_lyrics.tools.audio prep` / `align`, one
   chunk per line), `tools/words_from_fa.mjs`, then **look at every line** in `analysis/plots/` from
   `tools/plot_align.py`. Fix late line openers by hand. Never put ASR text on screen.
5. **Treatment.** One row per scene: words, interface, what happens on which word.
   - A scene is half a line to a line; 6–7 scenes per edit.
   - The punch word changes the state of the same object.
   - A repeated line gets a different interface with higher stakes, never a copy.
   - Swear words go on the accent pill. UI text is sardonic, never an ad, no how-to detail.
6. **Scenes.** Write `packages/ui-lyrics/client/scenes/<edit>.js` and `.css`; the file name is the edit name
   in `productions/words.final.json`. Every `update(lf)` sets the complete state from the frame.
7. **Preview** with `dev/index.html` (static server on the project root): contact sheets of every scene,
   every transition frame by frame, big frames at `cell=810`. Fix what stands empty, static or unreadable.
8. **Render.** `node tools/gen_source.mjs && npm run build -w @kit/ui-lyrics`, then
   `hypit build productions/<edit>/main.svrun --follow` for each edit (about 3 min each), then
   `hypit get <build-id> --output final.video --to renders/<name>.mp4`.
9. **Verify the files**: review tiles, `tools/check_sync.py` prints 0 ms, a word is visible one frame before
   its onset. Say what you could not check (you cannot listen). Send with telegram-send if asked.

**After touching the kit**: run the regression in Part 2 ("Regression") and `pytest tests/lib/test_ui_lyrics.py`.
