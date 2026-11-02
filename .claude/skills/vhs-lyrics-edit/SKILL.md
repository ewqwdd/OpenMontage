---
name: vhs-lyrics-edit
description: |
  Make a TikTok VHS kinetic-lyrics edit (the user's approved "ТУПАЯ ТВАРЬ" / track2 style) for a new track:
  song words hard-cut in on their syllables over dark night footage, CRT lens, VHS wave, grunge punches.
  Use when the user sends a track / TikTok link / audio and asks for "такой же эдит / монтаж / как в прошлый раз",
  "наш монтаж под этот трек", or wants backgrounds of an existing VHS edit replaced.
---

# VHS lyrics edit — the approved workflow

Everything is local and free. Follow the spending policy in `CLAUDE.local.md`; no paid tools are needed here.

1. **Read** `skills/creative/vhs-kinetic-lyrics.md`: Part 0 is the step-by-step workflow, Part 1 the editing grammar,
   Part 2 the kit reference. The template to copy is `projects/track2/` (`gen_timeline.py`, `make.py`, `README.md`).
2. **Audio only** from the link. Prep it:
   `.venv-audio/Scripts/python -m lib.vhs_lyrics.tools.audio prep <url|file> projects/<id>/analysis`
   This gives stems, a whisper draft, the beat grid and the vocal onsets.
3. **Ask the user for the lyrics** and show the whisper draft quality as the reason. Never put whisper text on screen.
   If no backgrounds are named, use `C:\Users\m\Documents\snippet-generator\.local-out\snippet-api\vibe`. The format is 1440×1080 4:3.
4. **Align** chunked by the whisper segments (`... align projects/<id>/analysis --chunks chunks.json`).
   Fix low-score words using the vocal onsets.
5. **Write `projects/<id>/gen_timeline.py`** from the track2 template:
   - word times in seconds;
   - scenes per the grammar (couplets → one line per scene in the climax, punch last, signature effects once,
     identical lyrics = identical design);
   - backgrounds by meaning, copied to `assets/bg/scene<N>.mp4`;
   - `LOOK` brightness targets.
6. **Build:** `python projects/<id>/make.py`. Check a snapshot grid at the punch frames. Then
   `python projects/<id>/make.py --send` to Telegram (telegram-send skill; never ask for a token).
7. Once approved, keep the sent render as `renders/v1_sent.mp4`. Write the project `README.md`
   (scene table plus how to swap backgrounds).
