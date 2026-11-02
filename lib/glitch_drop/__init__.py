"""glitch_drop: thin dirty lyric edit with a glitch-storm drop and a red accent word.

The calm intro (one centred line growing word by word, measured flicker, tear, sway, grain) runs
over night clips. At the drop the text turns to CAPS and every frame gets a glitch step (strobes,
inversions, halftone, bars, datamosh...). The accent word is red. One timeline JSON describes an
edit; see timeline.py for the schema and glitch.py for the schedule language.

    .venv/bin/python -m lib.glitch_drop <timeline.json> <out_dir> [--preview] [--frames a:b]
"""
