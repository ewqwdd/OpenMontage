"""Zoomed heads: the drawings (top row) against the model. Run after build_blender.py -- --views --smooth."""
from common import *
R = WORK / "render_smooth"
def shot(n, box=(372, 10, 652, 220)):
    im = Image.open(R / f"{n}.png").convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,)); bg.alpha_composite(im)
    return bg.convert("RGB").crop(box).resize((420, 315), Image.NEAREST)
row = Image.new("RGB", (420 * 4, 315 * 3), BG)
for i, n in enumerate(["front", "front34", "side", "back34"]):
    r = Image.open(CH / "views" / f"{n}.png").convert("RGB")
    a = np.array(r).astype(int); m = silhouette(a); xs = np.nonzero(m[:200].any(axis=0))[0]; cx = (xs.min() + xs.max()) // 2
    row.paste(r.crop((cx - 140, 10, cx + 140, 220)).resize((420, 315), Image.NEAREST), (i * 420, 0))
    row.paste(shot(f"stand_{n}"), (i * 420, 315))
for i, (n, box) in enumerate([("stand_f65", (372, 10, 652, 220)), ("stand_r60", (372, 10, 652, 220)),
                              ("stand_top", (372, 250, 652, 460)), ("stand_low", (372, 0, 652, 210))]):
    row.paste(shot(n, box), (i * 420, 630))
row.save(WORK / "heads.png")
