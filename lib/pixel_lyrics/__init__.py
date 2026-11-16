"""pixel_lyrics: the "dark pixel-game" lyric edit as a reusable kit.

One hero, one world, every lyric line acted out literally in one drawn shot; the camera lives inside the
drawing, words drive events, a game HUD keeps score. The pictures are drawn by Gemini image in a grim
PC-98 style (PAID, about $0.039 each, ~18 per pair of edits), everything else is code: a 270x480 dithered
pixel filter, hard-cut centred lyrics with smear frames and syllable flicker, and an ffmpeg grade.
1080x1920, 30 fps, rendered locally with Hypit.

The kit is a Hypit project template, not a Python renderer:

    template/packages/pixel-lyrics  the component: client/engine.js (camera shots, sequencer, pixel filter, lyrics,
                                    HUD) + client/scenes/<edit>.js (one scene set per edit, written for each track)
                                    + client/img (prepared pictures) + client/font (DotGothic16)
    template/tools                  gen_img.py (Gemini, budget-capped), prep_img.py, gen_source.mjs, words_from_fa.mjs,
                                    syllables.py, shot.mjs (preview captures, cut frames), grade.mjs, plot_align.py,
                                    check_sync.py
    template/dev/index.html         instant preview without rendering
    style/                          the approved look as reference pictures for new generations
    characters/<name>/              approved reusable heroes: sheet, crops, character.md (rules + prompt block)
    examples/mefedron               the approved edits (chorus + verse of "mefedron master 4"): scenes, pictures,
                                    prompts, words

    python -m lib.pixel_lyrics init projects/<id> [--example mefedron]     # copy template, npm install, select runtime

Guide: skills/creative/pixel-lyric-edit.md. Skill: .claude/skills/pixel-lyrics-edit.
"""
