# шАхА remake (CUPSIZE edit, 960x720, 30 fps, 853 frames)

A frame-by-frame recreation of a reference TikTok edit. Segment A (reference frames 0-234, the first 7.8 s)
is tuned against the reference by measurement. Segments B-D (`build_B/C/D.py`) are the earlier v1 builders:
`fx_D.py` was not recovered, so `build_D.py` does not import.

## Pipeline (segment A)

`python -I render_A.py 0:235 out/final` runs these steps for each frame:

1. **Clean frame** (`build_A.frame`): the background clip, graded and exposure-matched to the reference
   (`bgs.py`), with the text layers on top (`fx_A.py`, half-res composition in `look2.py`).
2. **Edge jitter** (`crunch.edge_jitter`): a displacement field on the 8 px block-row grid. Its density is set
   per word to match the reference frame-to-frame diff.
3. **Codec pass** (`crunch.codec_pass`): MPEG-2 at q 6, g 12, bf 2, then decoded back. This gives the
   mosquito noise and block edges.
4. **Post-codec layers**, the parts that are crisp in the reference:
   - text grain: vertical streaks on white, fine grain on red;
   - the dot ghost of ТОРЧАТ ИЗ ПУЗА;
   - the small front line;
   - 16 px speckle blocks at positions measured on the reference (`spec/speckle_A.json`).

## Measured data in `spec/`

- `backgrounds.json`: background shots. The clips are expected in `~/Downloads/visuals/`.
- `ghost_vis_A.json`: the dot-ghost geometry and the visibility per 20 px cell for frames 76-82. The ghost is
  transparent in the middle and visible at the ends.
- `speckle_A.json`: speckle block positions and strengths, 98 frames.
- `seg*.md`: the per-segment specs.

## Not in the repo

- **Reference frames** `full/0001.png ...`. `bgs._match_ref` needs them for the per-frame exposure match.
- **Background clips.**
- **Reference audio.**

## Compare tools

`tools/cmp6`, `tools/cmp7` measure reference and render side by side, from a folder that holds `full/` and the
render:

| Tool | What it compares |
|---|---|
| `pair.py` | crop pairs (`MD=<render dir>`) |
| `wstat.py` | white fill texture and glow rings |
| `rstat.py` | red fill texture |
| `edge.py` | edge rise width |
| `tdiff.py` | temporal diff |
| `dotprof.py` | dot-ghost density |
| `gvis.py` | ghost visibility extraction |
