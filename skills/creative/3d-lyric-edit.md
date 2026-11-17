# 3D lyric edit: grammar and kit

A TikTok lyric snippet shot as a low-poly horror video game: the user's 3D hero in one dim room, one shot per sung
line, the head glitching all the time, glitch text. Approved by the user on the chorus of «mefedron master 4»,
2026-11-17 (`projects/mefedron-3d/renders/chorus_3d_v5_hardpixel.mp4`, also saved as `chorus_3d_approved.mp4`).

Everything is local and free: Blender (EEVEE), numpy, PIL, ffmpeg. No paid generation anywhere in this style.

## Part 0. Workflow

1. **Inputs.**
   - The track excerpt and its words. Re-align the words even when the user sends times
     (`skills/creative/ui-lyric-edit.md` Part 0; 30 fps). `words.json` keeps the same format as the pixel-lyric kit.
   - **The scenario comes from the user**: which shot goes with which line, what the hero does, what appears on
     which word. Ask for it when it is missing. Do not invent the shot list.
   - Only the chorus exists so far. A verse needs its own scenario.
2. **Init.** `.venv/Scripts/python -m lib.lyrics3d init projects/<id>` copies the approved example
   (`shots.py`, `edit.json`, `words.json`). Put the excerpt's sound at the path in `edit.json` (`audio`); it must be
   exactly `frames / fps` long and start at `words.json → edits.<edit>.start`.
3. **`edit.json`**: frame count, the shots (cut on the first word of each line), the lyric screens, the glitch
   schedule. Fields are in Part 2.
4. **`shots.py`**: for every shot the pose, the camera, the props and the head motion, as code. Part 2 has the API.
5. **Look before the full render.**
   - `python -m lib.lyrics3d stills projects/<id> 60 150 290 400` renders and grades a few frames.
   - `--dbg side|front|back|top` shows the pose from outside the shot (bright, no haze).
   - When the room, a pose or a camera is new, show a graded frame per shot to the user first.
6. **Render and finish.**
   - `python -m lib.lyrics3d render projects/<id>` (two Blender jobs; 442 frames take about 4 minutes on an RTX 3050).
   - `python -m lib.lyrics3d post projects/<id> --small` writes `renders/<edit>_3d.mp4` and a copy under 30 MiB.
   - Re-render only the shots that changed: `render … --frames A B`, then `post`.
7. **Verify.** Sound offset 0 ms (`projects/mefedron-hollow/tools/check_sync.py <mp4> <wav>`), 442 frames, a contact
   sheet of the whole edit, strips of the head for the head motion. Say plainly that motion and sound were not
   watched or heard.

## Part 1. Grammar

### The look
- **Reference role.** The reference short (a paper-bag-head character in a Soviet flat) gave the **look only**:
  a dim room, one pool of light, chunky low-res textures on big surfaces, haze, a heavy vignette, a wide lens, a
  hand-held camera. Its warm brown palette was **not** taken: the user asked for colder, bluer colours.
- **Pixels ×3 on everything.** The frame is rendered at 360×640 and enlarged ×3 with no smoothing. Text and glitch
  are drawn in the same 360×640 grid. Then a 4×4 ordered dither to 5 bits per channel.
- **Hard pixel edges.** Blender renders with the pixel filter at 0 (`scene.py`, `--filter`), so outlines are
  stairs, as in the hero's `viewer.html` (`antialias: false`). With the old filter of 0.8 the outlines were
  smoothed and the user saw no pixels at all ("графика как будто не пикселизированная").
- **Tried and not taken on 2026-11-17:** pixels ×6 (180×320 picture, 16 levels per channel, the text left at ×3).
  The user looked at it and kept the ×3 hard-edge version ("v5 оставим").
- **Colour.** Cold: navy shadows, pale ice highlights, a few wine-red and cardboard accents. Saturation 0.86,
  channel gains (0.93, 1.0, 1.09), blue lifted in the dark, an S-curve, vignette 0.62.
- **Light.** A bare bulb as a spot from above (the pool on the rug), a CRT with blue static as the key light on the
  face in the close shot, a window with blinds as a cyan rim, a weak fill, haze (world volume 0.012).
- **The hero's paint** is darkened to 0.5 and gets 0.07 of its own light. Without that the pale face burns out
  under the lamp. It still reads nearly white from above (known, the user has not objected).

### The room
A post-Soviet room at night: an ornament rug on the floor and another on the wall behind him, wallpaper, a
mattress with a plaid, a CRT on a stand, a console and a pad, a window with blinds over a radiator, a door, a
wardrobe, posters. The mess on the floor is part of the brief: syringes, pills, blisters, bottles, cans, pizza
boxes, a tipped pill bottle, an ashtray, a lighter, a spoon, a phone, crumpled paper.
All textures are drawn by `lib/lyrics3d/textures.py` at 24–128 px. Low texel density is the point.

### Shots
- **One shot per sung line, cut on the first word** (or up to 3 frames before it).
- **The shots are literal.** In the approved chorus:

  | Line | Shot |
  | --- | --- |
  | Я люблю мефедрон, марки, ксан, оксикодон | Bust "right in front of the screen": head, shoulders, a little of the body. The camera stands where the TV is. The four things pop up one by one in an arc over his head. |
  | Пидорасит слишком сильно, залипаю в потолок | From the ceiling, straight down. He sits on the floor, legs straight and slightly apart, torso 60° from the floor, leaning on his arms behind him, and looks into the lens. The camera pulls up and turns. |
  | the first line again | A low flight over the floor: the four things lie in a row, the camera is over each on its word, then lifts its look to him. |
  | the second line again | The ceiling shot again, turning the other way, harder. |
- **A repeated line gets the same shot with higher stakes**, not a new idea.
- **The camera is hand-held**: a slow wobble on position and roll, a push-in on the close shot, lenses 19–22 mm
  (on a 36 mm tall sensor).
- **Things named in the lyrics** appear on the first frame of their word: scale 1.55 → 1 over 4 frames, a 2-frame
  flash, then they hang like game pickups (sway ±32°, a slow bob). The arc hangs over where the head rests and
  does not follow its tilt. Later the same things lie on the floor, turned so that the flying camera reads them
  upright.

### Head motion (the user's rules, in their words)
- **Close shot: "меньше покачиваний и сделать их плавными".** One slow cosine tilt per hook word, two on a long
  word (five in the line, not one per syllable), 11° split over head, neck and chest.
- **From above: "резко дергать".** Sharp throws with no in-betweens **for as long as the camera is up there**.
  First time: a throw on every syllable, held 3 frames, then back. Second time: side to side every 2 frames,
  bigger. The head never freezes there.
- A smooth sway from above was tried and rejected ("качать головой плавно только в начале, когда камера сверху
  то резко дергать как раньше").
- From above the head is first aimed at the camera (`aim_head`), the throw goes on top.

### Glitch on the head
On through the whole edit, in the render grid, round the head's place on screen: slices thrown sideways, colour
channels pulled apart, blocks copied to the wrong place (some inverted or tinted), pixel smears. The level per
frame comes from `edit.json`: random 3-frame bursts per shot, a tick on every hook syllable, a hit on every head
throw. The last shot is `hard` (bigger area, a ghost head, whole-frame row tears), builds to the end and never
drops below 0.75 in its last line.

### Text
- The grammar of the glitch-drop kit (`skills/creative/glitch-drop-lyrics.md`): **CAPS in Cormorant Garamond**,
  one centred line that grows word by word, lavender glow, split chroma, a scanline tear on its own clock, a dim
  on every word onset; on glitch frames the line jumps, smears, leaves a ghost and is cut into slices.
- **One accent word is crimson** and bigger («ПИДОРАСИТ», both times).
- Screens of 1–3 words; a thing named in the lyrics gets a screen of its own.
- The line sits low (0.80–0.845 of the height); on the floor flight it sits at 0.15 so that it does not cover
  the things.
- The line is torn less than the head (level × 0.62, every third frame nearly clean).
- **Rejected on 2026-11-17, do not offer again:** a white bitmap font (Fixedsys) and yellow Oswald Bold with a
  black outline. The user compared both with the Cormorant line and kept it ("старый короче топ оставляем").

### Known weak spots
- The face is nearly white in the close shot and from above; the bags under the sockets are lost.
- From above the hands barely read, only the spread sleeves do.
- The first half second of the floor flight is dark (the camera comes in from the edge of the rug).
- Only sitting poses exist (`pose_sit`). The hands-in-lap pose is made for the bust framing and looks wrong
  in a wider shot.

## Part 2. The kit: `lib/lyrics3d/`

| File | What it is |
| --- | --- |
| `scene.py` | The Blender engine: materials, mesh helpers, the room, the mess, the hero, lights, posing and camera helpers, the render loop. Executes the project's `shots.py`. |
| `post.py` | `Post`: glitch on the head, grade, text, dither, ×3, mux. |
| `lyrics.py` | The approved text. |
| `textures.py` | Draws `assets/tex/*.png`. Run it after changing a texture. |
| `__main__.py` | `init`, `stills`, `render`, `post`. |
| `examples/mefedron/` | The approved chorus: `shots.py`, `edit.json`, `words.json`. |

The hero is `lib/pixel_lyrics/characters/hollow/model3d/hollow_smooth.blend` (`edit.json → hero_blend` overrides
it; the rig must be called `hollow_rig` with the same bone names).
A project texture in `projects/<id>/assets/tex/<name>.png` wins over the kit's texture of that name.

### `edit.json`
```json
{"fps": 30, "frames": 442, "edit": "chorus", "words": "words.json", "audio": "assets/audio/chorus.wav",
 "shots": [{"name": "A", "from": 0,   "glitch": [0.20, 0.45], "text_y": 0.845},
           {"name": "B", "from": 118, "glitch": [0.42, 0.70], "text_y": 0.80, "calm": {"from": 171, "k": 0.6}},
           {"name": "D", "from": 335, "glitch": [0.80, 1.0],  "text_y": 0.80, "hard": true,
            "build": [0.35, 0.5], "hold": {"from": 389, "min": 0.75, "rand": 0.25}}],
 "ticks": [34, 39, 46], "hits": [118, 124, 130],
 "screens": [[0, 1, false], [2, 2, false], [6, 6, true]]}
```
- `glitch: [p, k]`: how often a burst starts and how strong it is. `calm`, `build`, `hold`, `hard` are optional.
- `ticks`: frames of the hook syllables. `hits`: frames of the head throws.
- `screens`: `[first word, last word, accent]` by word index inside the edit; every word on exactly one screen.
- A word's frame is `round((start − edits.<edit>.start) × fps)`.

### `shots.py`
It is executed with every name of `scene.py` in scope, builds its own props at load time and defines
`apply(f) → shot name`. Every frame starts from a clean pose; nothing is keyframed. World: metres, Z up, the
hero sits at the origin and faces −Y, +X is his left (screen right when the camera looks at him).

| Name | Use |
| --- | --- |
| `EDIT`, `NFRAMES`, `FPS` | the project's `edit.json` and its numbers |
| `set_pose(list)`, `pose_sit(lean, arms="back"\|"lap", legs_open=8)` | the pose; `lean` is degrees back from upright (30 = torso 60° from the floor) |
| `turn(bone, deg, axis)` | rotate a bone round a world axis (`"X"`, `"Y"`, `"Z"`) through its head; `"ROLL"`, `"CURL"`, `"SPREAD"` are bone-local. He faces −Y, so `"Y"` tilts the head to a shoulder and a negative `"X"` swings a hanging limb forward |
| `head_centre()`, `head_world()`, `aim_head(point)` | where the head is; turn neck and head so that the face looks at a point |
| `swing(f, keys)` | smooth −1..1 through `[(frame, value)]` |
| `jerk(f, frames, amp, hold, wild)`, `throw_head(roll, lean)` | sharp head throws and applying them |
| `camera_at(pos, target, up, roll, lens)` | the camera; for a straight-down shot give `up` in the floor plane |
| `ease`, `ease_out`, `hsh(i, salt)`, `wob(f, salt, speed)` | easing, per-integer noise, hand-held wobble |
| `box`, `cyl`, `blob`, `empty`, `mtex(name, emit=…)`, `mflat(name, rgb, emit=…)` | props and materials (`face_mats={"+z": mat}` puts a texture on one face of a box) |
| `L_BULB`, `L_TV`, `L_WIN`, `L_FILL`, `BULB`, `WIRE`, `CEIL` | lights and the objects to hide when the camera is at the lamp |
| `RX0`, `RX1`, `RY0`, `RY1`, `RZ`, `TV_Y`, `SIT_DZ` | the room's box (4.3 × 4.25 × 2.6 m), the TV's place, the rig's drop for sitting |

Bones: `pelvis`, `spine`, `chest`, `neck`, `head`, `upper_arm.L/R`, `forearm.L/R`, `hand.L/R`, `thigh.L/R`,
`shin.L/R`, `foot.L/R`, fingers `thumb|f_index|f_middle|f_ring|f_pinky.01–03.L/R` (`fingers(side, curl)`).
Sides are the hero's.

`scene.py` writes the head's place on screen for every frame to `renders/seq/meta_*.json`; `post` needs it.
Where two meta files cover a frame, the newer one wins, so partial re-renders are safe.

### Regression after touching the kit
- `.venv/Scripts/python -m pytest tests/lib/test_lyrics3d.py`
- Render the example and compare with the approved frames: `init` a scratch project, `stills` at
  60 100 121 180 290 325 350 430, and the raw frames in `renders/test/` must match
  `projects/mefedron-3d/renders/seq/` (mean difference 0.000 at the time of writing). `seq/` holds the hard-edge
  frames of v5; the smoothed frames of v1–v4 are in `seq_soft_v3/` and match `stills … --filter 0.8` only.

## History of the user's corrections (mefedron chorus, 2026-11-17)

| Version | What the user said | What changed |
| --- | --- | --- |
| v1 | fewer sways at the start and smooth; the head must move all the time from above; add glitch text from a skill | 10 syllable tilts → 5 smooth ones; text from the glitch-drop kit |
| v2 | smooth only at the start; from above jerk sharply as before | sharp throws back, now for the whole shot |
| v3 | the text is hard to read, try another font and colour | two variants made (white bitmap, yellow bold) |
| v4 | "старый короче топ оставляем" | v3 stays: the Cormorant line |
| v3 again | the picture does not look pixelated, do it like the hero viewer's pixel button | edge smoothing off (v5) |
| v5 | try an even stronger version | pixels ×6 with a visible dither (v6) |
| v6 | "v5 оставим" | v5 is the approved file; hard edges are the kit's default |
