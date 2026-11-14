# Reference drawing → low-poly comic-ink 3D character (creative skill)

> Engine: Blender 5.2 headless (`.runtime/blender/blender-5.2.3-windows-x64/blender.exe -b -P script.py -- args`)
> Working example: `projects/ps1-char-falling/head_spec/` (head of the crying kid — spec, agents' analyses, builders)

Goal: a model whose FRONT matches the drawing 1:1 and that still looks clean when turned (3/4, profile).
The reference is 2D: copying it literally as decals reads fine head-on and falls apart in 3D. Copy → verify → ADAPT.

## Pipeline — two stages + an edit loop (do them in order, never skip stage 1)

### Stage 1 — DECOMPOSE (разбивка на части). Output: a verified 2D spec, no 3D yet.
1. **Component agents (parallel).** List the components (face mass, hair mass, hair details, ears, lenses/eyes, frame,
   tears, small marks, style). One independent agent per component + one **audit** agent that inventories everything
   visible and flags what nobody owns. Each agent reports per part: shape, outline points, corner count, sampled colours,
   ink, layering, 3D recipe. Shared brief: `head_spec/components/BRIEF.md` (frame = origin between the eyes,
   unit H = face width; raw reference pixels always given; colours sampled with `sample.sh`, never guessed).
2. **Merge to one spec in reference pixels** (`make_spec.py` → `head_spec.json`): every shape = id, poly/line, fill key,
   layer, ink width. The shape **ids are the vocabulary for the rest of the pipeline** (builder objects, edits).
   Convert each agent's numbers back to raw pixels with *its own* origin/H — agents disagree on H by ±5%.
3. **2D check** (`render_2d.py`): outlines over the reference + flat layered reconstruction.
   If the flat version doesn't read as the drawing, fix the spec — 3D will not fix it.

### Stage 2 — ASSEMBLE (сборка). Output: the 3D model + renders.
4. **Adapt and build** (`build_head3d_v2.py`) by the rules below. Every Blender object is named by its spec id
   (masses: `skull`→`face`, `hair`→`hair_cap`; ink ribbons `<id>_ink` belong to `<id>`).
5. **Review in 3/4 and profile first**, then front. Zoom 2–4× on contours before showing the user.

### Edit loop — per-part notes in the browser
6. `export_glb.py` (Blender) → `editor/model.glb` with each object tagged `part`/`comp`/`color`;
   `python editor/serve.py` → http://localhost:8765. The user orbits the model, clicks a part (or picks it in the list),
   writes a note, optionally sketches over the model / on a blank sheet (✎) or attaches files (📎, drag-drop, Ctrl+V);
   notes land in `editor/edits.json` with camera, clicked point, screenshot incl. sketch (`editor/shots/`), files (`editor/attachments/`).
7. Read `edits.json`, fix by part id (spec for shape/colour, builder for 3D form), rebuild, re-export, mark notes `done`.

## Adaptation rules (hard — each one came from a rejected result)

- **Smooth every outline** (Chaikin 2–3 passes) before building. Hand jitter and corner noise become ugly facets in 3D.
- **Big masses are real volumes, not decals.** Hair = helmet lofted so each horizontal slice spans the drawn outline
  (front silhouette exact, shell clean and round), forehead cut along the *smoothed* hairline with boundary verts snapped
  onto it, solidified for a lip. Skull = loft from a section table. Never a front-projected card for a mass.
- **Small parts on a surface = pillows**: grid-diced polygon projected onto the host + sqrt bulge toward the middle.
- **Parts that cross curvature changes (tears over cheek/jaw/collar) = petals bent along their length only**:
  depth = front-most host point across the part's width at that height (`min` over x samples), clear the collar by ≥0.05.
  Per-vertex projection there crumples the card and tears its outline.
- **Side features (sideburns) = flat at their centre depth**; front projection stretches them into dark blobs on the cheek.
- **Ears = plates hinged at the face and swung back ~40°**, else they vanish in profile.
- **Hair needs visible thickness**: after cutting the hairline, add a separate *rim strip* from the hairline toward
  the skull and ~0.035 down (consistent winding!) in a darker hair colour — two ink lines along the fringe = chunky mass.
  Push the helmet front ~0.06 off the forehead. A solidify lip faces down and is invisible head-on.
- **Skull must stay under the hair**: pull every crown vertex that pierces the helmet back inside it (ray from the head centre).
- **Drop-shaped features the user calls "volumetric" (tears) = lofted cone→bulb volumes** following the petal depth,
  mirrored left/right, streak lines as strips on the surface. Flat cards read as stickers.
- **Eyes = shallow domes** (UV sphere scaled ~0.5 in depth) set into the face, symmetric centres/radius, glares as strips on the dome.
- **Ears**: same material as the face; hinge at the innermost edge, ~30° off the head side; right ear = mirror of the left.
  The face/ear seam is a *half line*: Freestyle face marks on the skull faces behind the lower half of the ear +
  lineset `select_by_face_marks`, `EXCLUSIVE`, `ONE` (Blender 5: bool FACE attribute `freestyle_face`).
- **Drop near-coplanar shading patches** (cheek shade) — they flicker; put gradients in the material instead.

## Ink rules (hard)

- **Freestyle only for silhouettes of volumes** (skull, hair, ears, collar): silhouette + border + external contour,
  `select_crease = False`, geometry modifiers `SAMPLING 2` + `BEZIER_CURVE error≈8`, mild along-stroke taper (0.8 ends).
- **NO** `SPATIAL_NOISE`, **NO** `BACKBONE_STRETCHER` on finished models: noise = crooked lines, stretcher turns every
  broken stroke fragment into a spike.
- **Decal outlines (tears, fringe, lenses, sideburns) = geometry ribbons**: offset the smoothed outline ±w/2, project with
  the *same* depth function as the card, 0.006 in front. Freestyle on thin cards near a surface breaks into dashes and spurs.
- Ink colour from the reference (here red-brown `#4e0b00`, not black); cream halo via alpha dilation in ffmpeg (`halo.sh`).
- Emission-only materials + `view_transform = Standard` so rendered pixels equal the sampled hex.

## Known open items

- Profile depth is invented (no side reference) — ask the user for a side view or accept the guess.
- Triangle count ~12k from the dicing grid; for strict PS1 budget raise `STEP` or decimate after the look is approved.
