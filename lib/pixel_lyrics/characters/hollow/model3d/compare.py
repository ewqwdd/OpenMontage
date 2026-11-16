"""Reference views (top) against the model renders (bottom). Run with the project's .venv python."""
import sys

from common import *

RD = WORK / "render_smooth"        # renders of the smoothed-dither variant (build_blender.py -- --views --smooth)
ORDER = ["front", "front34", "side", "back34", "back"]
W = 340


def render(name):
    im = Image.open(RD / name).convert("RGBA")
    if im.width < 1024:
        im = im.resize((1024, 1024), Image.NEAREST)
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def centred(im, w=W):
    """Crop / pad a figure picture to width w around its silhouette centre."""
    a = np.array(im).astype(int)
    m = silhouette(a)
    xs = np.nonzero(m.any(axis=0))[0]
    cx = (xs.min() + xs.max()) // 2 if len(xs) else im.width // 2
    out = Image.new("RGB", (w, im.height), BG)
    out.paste(im, (w // 2 - cx, 0))
    return out


sheet = Image.new("RGB", (W * len(ORDER), 2048), BG)
for i, n in enumerate(ORDER):
    sheet.paste(centred(Image.open(CH / "views" / f"{n}.png").convert("RGB")), (i * W, 0))
    sheet.paste(centred(render(f"stand_{n}.png")), (i * W, 1024))
sheet.save(WORK / "compare_turnaround.png")
small = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
small.save(WORK / "compare_turnaround_small.png")

ap = Image.open(CH / "puppet/front/apose_source.png").convert("RGB")
pair = Image.new("RGB", (2048, 1024), BG)
pair.paste(ap, (0, 0))
pair.paste(render("apose_front.png"), (1024, 0))
pair.save(WORK / "compare_apose.png")
pair.resize((1024, 512), Image.LANCZOS).save(WORK / "compare_apose_small.png")
if len(sys.argv) > 1:
    extra = Image.new("RGB", (1024, 1024), BG)
    extra.paste(centred(render("stand_high.png"), 512), (0, 0))
    extra.paste(centred(render("stand_low.png"), 512), (512, 0))
    extra.save(WORK / "compare_angles.png")
