"""ui_lyrics: the "UI-lyric edit" style as a reusable kit.

Every lyric line is acted out by a fake interface (dating swipe, pulse widget, wallet, chat...), every
sung word lands on its own frame, scenes change with a one-frame accent flash and a focus pull out of
blur. 1080x1080, 60 fps, pure code animation rendered locally with Hypit: no paid generation.

The kit is a Hypit project template, not a Python renderer:

    template/packages/ui-lyrics   the component: client/engine.js (transitions, captions, HUD, particles,
                                  counters) + client/scenes/<edit>.js (one scene set per edit, written
                                  for each track)
    template/tools                gen_source.mjs (words -> audio cuts + Hypit Sources), words_from_fa.mjs,
                                  plot_align.py, check_sync.py
    template/dev/index.html       instant preview without rendering
    examples/mefedron             the approved edits (chorus + verse of "mefedron master 4"): 13 scenes
                                  to copy from, their words and alignment inputs

    python -m lib.ui_lyrics init projects/<id> [--example mefedron]     # copy template, npm install, select runtime

Guide: skills/creative/ui-lyric-edit.md. Skill: .claude/skills/ui-lyrics-edit.
"""
