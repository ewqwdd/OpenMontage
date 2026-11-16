# @kit/pixel-lyrics

Hypit component of the dark pixel-game lyric edit: `<px:Edit variant="<edit>" accent="cold|warm">` with one
`<px:Word id text at>` child per sung word, in sung order. It outputs one visual track, 1080×1920.

- `client/engine.js` — camera shots, the shot sequencer, the pixel filter, lyrics, HUD. Pure function of the frame.
- `client/scenes/<edit>.js` — one scene set per edit; `variant` is the file name.
- `client/img/` — the prepared pictures (`tools/prep_img.py`), `client/font/` — DotGothic16 (OFL).
- `build.mjs` inlines all of `client/` into `src/generated.ts`; run `npm run build -w @kit/pixel-lyrics`
  after every change in `client/`.

Guide: `skills/creative/pixel-lyric-edit.md` (repo root).
