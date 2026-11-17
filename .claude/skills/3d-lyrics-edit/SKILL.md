---
name: 3d-lyrics-edit
description: |
  Make a TikTok lyric snippet in the user's approved "3D horror-game" style (approved on the chorus of
  «mefedron master 4», 2026-11-17): a vertical 1080x1920 30 fps edit rendered in Blender, where the user's 3D
  hero (the "hollow" model) sits in one dim post-Soviet room and every sung line is one literal shot — a bust
  in front of the screen with the things from the lyrics popping up in an arc over his head, a view from the
  ceiling pulling up while he stares into the lens and throws his head, a low flight over the things on the
  floor. Low-poly, low-res textures, cold blue light, everything in x3 pixels with a 15-bit dither, a glitch
  on the head through the whole edit, glitch text in Cormorant caps with one red word.
  Use when the user sends a track (and usually words) and asks for "3д эдит", "3д анимация", "как 3д мефедрон",
  "эдит с 3д моделькой", "в стиле хоррор-игры", "ещё один в этом 3д стиле", or wants shots, camera, head motion,
  props, room, glitch or text changed in such an edit. Not for the drawn pixel edit with the same hero
  (pixel-lyrics-edit), not for footage edits (vhs-lyrics-edit, glitch-drop-lyrics-edit, card-strobe-edit) and
  not for the fake-interface edit (ui-lyrics-edit).
---

# 3D lyric edit: the workflow

The kit is `lib/lyrics3d/` (Blender scene engine, post pass, text, the approved example). Everything is local
and free: no paid generation in this style.

1. **Read** `skills/creative/3d-lyric-edit.md`: Part 0 is the workflow, Part 1 the grammar (look, shots, head
   motion, glitch, text, what the user rejected), Part 2 the kit and the `shots.py` API. Read
   `lib/lyrics3d/examples/mefedron/shots.py` before writing shots.
2. **The scenario is the user's.** They say which shot goes with which line and what happens on which word.
   Ask for it when it is missing; do not invent the shot list. Only a chorus exists so far.
3. **Init.** `.venv/Scripts/python -m lib.lyrics3d init projects/<id>`; put the excerpt's sound at the path in
   `edit.json`. Re-align the words even when the user sends times (`skills/creative/ui-lyric-edit.md` Part 0).
4. **Write `edit.json`** (frames, shots cut on the first word of each line, lyric screens with one accent word,
   glitch schedule) **and `shots.py`** (pose, camera, props, head motion per shot).
5. **Look first.** `python -m lib.lyrics3d stills projects/<id> <frames…>`, and `--dbg side|front|back|top`
   for poses. When a room, pose or camera is new, show the user one graded frame per shot before the full render.
6. **Render and finish.** `python -m lib.lyrics3d render projects/<id>` (run it in the background; about
   4 minutes for 442 frames), then `python -m lib.lyrics3d post projects/<id> --small`. Re-render only changed
   shots with `--frames A B`.
7. **Verify the file**: sound offset 0 ms, frame count, a contact sheet, head strips for the head motion. Say
   what you could not check — you cannot watch motion or listen. Send the `_small` copy to the user's phone.

Rules the user set on this style, keep them unless told otherwise:

- **Head motion.** Close shot: few, smooth tilts (one per hook word). From above: sharp throws with no
  in-betweens for as long as the camera is up there. Never a smooth sway from above, never a frozen head there.
- **Text.** The glitch-drop Cormorant line stays. A white bitmap font and a yellow bold font were tried and
  turned down; do not offer them again.
- **Pixels x3 on everything, with hard edges** (no edge smoothing in Blender; the kit's default). Bigger pixels
  (x6) were tried and turned down. Colder and bluer than the reference, glitch on the head in every shot.

**After touching the kit**: `pytest tests/lib/test_lyrics3d.py` and the frame comparison in Part 2 of the guide.
