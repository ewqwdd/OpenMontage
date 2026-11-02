---
name: glitch-drop-lyrics-edit
description: |
  Make a TikTok lyric edit in the user's approved "МАРШРУТКА" / IMG_2446 style for any song:
  thin dirty glowing serif words appear on their syllables over dark night clips with a VHS flicker,
  then at the drop the text turns CAPS and every frame gets a beat-locked glitch cell (strobes, invert,
  halftone, bars, datamosh, white/cyan flash on the 808), and the final punchline word is red.
  Use when the user sends a track / TikTok sound / audio and asks for "такой же эдит как маршрутка",
  "глитч на дропе", "эдит с красным словом в конце", "в стиле того лирик видео", or wants this
  style adapted to another song, or wants backgrounds / red word / drop moved in such an edit.
---

# Glitch-drop lyrics edit: the workflow

Everything runs locally and costs nothing (numpy, PIL, ffmpeg in `.venv`).

1. **Read** `skills/creative/glitch-drop-lyrics.md`. Part 0 is the workflow, Part 1 the grammar (when each effect fires, in beats), Part 2 the kit.
2. **Audio:** sound only, trimmed to the excerpt. Then run
   `.venv/bin/python -m lib.glitch_drop.tools.music <audio> [--start S --end S]`
   and tell the user the tempo and the drop candidate(s). The drop is the start of the fullest, brightest section. It is not the first bass entry.
3. **Ask the user for the lyrics**, one sung phrase per line. Never put ASR text on screen.
   - Word times come from `lib.vhs_lyrics.tools.audio align` if `.venv-audio` exists (its `words.json` fits as is).
   - Otherwise time them by hand: `[{"line", "word", "start"}]`.
4. **Clips.**
   - One dark night clip per calm line, chosen by meaning.
   - One clip for the drop (a bright lamp top over a dark floor works best).
   - The default pool is `~/Downloads/visuals`.
5. **Plan.**
   ```
   .venv/bin/python -m lib.glitch_drop.tools.plan --audio <a> [--start S --end S] --words words.json \
       --clips c1.mp4 c2.mp4 … --drop-clip d.mp4 --out ~/Downloads/<project>/timeline.json [--drop SEC] [--red WORD]
   ```
   Check `plan_report.json`: the line split, the red word (the last word by default, alone on its line) and the cell table.
6. **Preview** the drop and a few calm frames:
   `.venv/bin/python -m lib.glitch_drop <timeline.json> <out> --frames a:b`.
   Make a contact sheet and look at it.
7. **Render** `.venv/bin/python -m lib.glitch_drop <timeline.json> ~/Downloads/<project>/`, which writes `final.mp4`.
   - Send it with the telegram-send skill if asked.
   - Re-encode at crf 23 when the file is over 50 MB.

Regression check after touching the kit: render `lib/glitch_drop/examples/reference_marshrutka.json` with `--preview` and compare it against the approved v2 frames. The mean MAE must stay below 0.1.
