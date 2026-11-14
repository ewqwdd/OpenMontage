"""card_strobe: the "Mastermind" / ref3 edit style as a reusable kit.

A 1:1 picture in a black 9:16 letterbox. On the 808 drops the footage is replaced by giant
ultra-condensed type cards that flip polarity every 2-3 frames, and the letterbox bars flip with
them. Between the cards: one duotone clip per bar (hard cuts on the half-note grid), word pops on the
syllables, a flash-cut burst in the 808 gap, tiny subtitles in the second half, a crimson card at the
end and a whip that loops. One timeline JSON describes an edit (schema: timeline.py).

A "fused" block in the timeline adds the first edit's ingredients (lib/glitch_drop): a glowing serif
lead-in / narrator, VHS windows, Cyrillic card captions and glitch cells (fused.py).

    ~/.cache/card_strobe_align/bin/python -m lib.card_strobe.tools.align ...   # rough lyric times -> real ones
    .venv/bin/python -m lib.card_strobe.tools.audit <final.mp4> ...            # QA numbers

    .venv/bin/python -m lib.card_strobe.tools.plan ...                # audio + words + moments -> timeline.json
    .venv/bin/python -m lib.card_strobe <timeline.json> <out_dir> [--preview | --frames a:b]

Guide: skills/creative/card-strobe.md. Rules as code: grammar.py.
"""
