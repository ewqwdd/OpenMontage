---
name: card-strobe-edit
description: |
  Make a TikTok edit in the user's approved "Mastermind" / ref3 (kileeknow «и без свечения») style, or its
  FUSED variant (Mastermind + the first «МАРШРУТКА» edit, approved on «mefedron master 4»), for any song and
  footage: a square picture in a black 9:16 letterbox; on the 808 drop a giant ultra-condensed word card
  (MASTER/MIND, MEFE-/DRON) strobes black/white every 2-3 frames with the bars flipping too; then one hard
  duotone clip per bar, words on their syllables, a flash-cut burst in the 808 gap, 1-frame inverts on the
  808s, a crimson end card and a looping whip. Fused adds a thin glowing serif lead-in / narrator, a VHS open,
  Cyrillic captions under the cards and glitch accents on the 808s.
  Use when the user asks for "эдит как Mastermind", "как первый эдит / как мастермайнд", "в стиле первого
  эдита и мефедрона", "карточки и стробы", "большие буквы в квадрате", "в стиле третьего тиктока / kileeknow",
  "такой же эдит под этот трек", "продолжим этот визуальный стиль", or wants this style on another song /
  other footage, or wants cards, clips, colours, glitches or the serif line changed in such an edit.
---

# Card-strobe edit: the workflow

Everything runs locally for free: numpy, PIL and ffmpeg in `.venv`. Only the lyric alignment needs a separate torch venv.

1. **Read** `skills/creative/card-strobe.md`:
   - Part 0 is the workflow.
   - Part 1 is the Mastermind grammar.
   - Part 2 is the kit.
   - Part 3 is the fused style.
   
   Default to **fused** when the user says "как первый эдит / мефедрон / продолжим стиль". Use **mastermind** when they name ref3 / Mastermind alone.
2. **Audio + excerpt.**
   - The excerpt starts in a bass-less bar before an 808 entry, contains an 808 gap if possible, and ends in a bass-out after the punchline. 15–17 s is fine.
   - Get the grid right:
     - the comb tempo is wrong on trap (it gave 88 instead of 132);
     - pass `--track track.json` (beat analysis) or `--bpm B --beat0 SEC`, and `--drop SEC`.
   - Tell the user the tempo and the drop.
3. **Lyrics.** The user's file has the right text and rough times.
   - Align it:
     ```
     ~/.cache/card_strobe_align/bin/python -m lib.card_strobe.tools.align --audio <a> --words <words.json> \
         --demucs --out ~/Downloads/<project>/words_aligned.json
     ```
     The venv setup is in `tools/align.py`'s docstring.
   - Listen-check the words in `report.json` → `stats.to_check`.
   - Never put ASR text on screen.
4. **Curate the footage** (Part 0 step 4).
   - Pick the most stylish frames: suit, stares, profile turns, chugs, Dutch angles, logo halos or crowns. Repeats are fine.
   - Give each one a 1080 square crop and a `best_t`, and check for hard cuts inside each window.
   - Write `{"picks": [...]}`, with `examples/podnebesny_curated.json` as the model.
5. **Plan.**
   ```
   .venv/bin/python -m lib.card_strobe.tools.plan --audio <a> --start S --end S --words words_aligned.json \
       --moments picks.json --top 24 --out ~/Downloads/<project>/timeline.json --style fused \
       [--track track.json | --bpm B --beat0 SEC] [--drop SEC] [--break A:B|none] \
       [--card1 MEFE-/DRON] [--card2 ZAE-/BAL] [--end-card PO-/POTOLOK] [--narrator serif|subs]
   ```
   - Check the printout and `plan_report.json`: card words, burst/gap, shot table, `fused` (serif lines, captions, accents) and warnings.
   - Then hand-place the gags. The two fused examples show every one: syllable recolours `fg_frames`, card/clip intercuts `show`, a burst `runs`, a red cell.
6. **Preview.** `.venv/bin/python -m lib.card_strobe <timeline.json> <out> --preview` (or `--frames a:b`) writes numbered sheets to `<out>/preview/`. Look at them:
   - card text;
   - no two neighbouring clips share a hue;
   - faces framed and not burnt;
   - serif and captions readable.
7. **Render.** `.venv/bin/python -m lib.card_strobe <timeline.json> ~/Downloads/<project>/` writes `final.mp4`.
   - Make a sheet: `.venv/bin/python -m lib.card_strobe.tools.sheet final.mp4 <dir> --every 4`.
   - Get the QA numbers: `.venv/bin/python -m lib.card_strobe.tools.audit final.mp4 --timeline timeline.json --track track.json`.
   - Give the user the path. Send it with telegram-send if asked.

**Regression check after touching the kit** (Part 2, "Regression"):
- `examples/mastermind_toilet.json --workers 3` must be byte-identical to `~/Downloads/podnebesny-edits-v2/01-mastermind-toilet-ref3/final.mp4`.
- `examples/fused_chorus_mefedron.json` and `examples/fused_verse_zvonit.json` must match `~/Downloads/podnebesny-edits-v3/0{1,2}-*/final.mp4` with `tools.compare` mean MAE < 0.05.
- `pytest tests/lib/test_card_strobe.py` must pass.
