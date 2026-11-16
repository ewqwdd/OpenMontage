"""Close shots round the head on one sheet. Run after build_blender.py -- --smooth --head."""
import sys

from common import *

R = WORK / (sys.argv[1] if len(sys.argv) > 1 else "render_smooth")
OUT = sys.argv[2] if len(sys.argv) > 2 else "head_ring.png"


def shot(n):
    im = Image.open(R / n).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB").crop((60, 40, 500, 420))


rows = [[f"head_{az:+04d}.png" for az in (0, -30, -60, -90, -120, -150)],
        [f"head_{az:+04d}.png" for az in (180, 150, 120, 90, 60, 30)],
        [f"head_low_{az:+04d}.png" for az in (-60, -30, 30, 60)] + [f"head_high_{az:+04d}.png" for az in (-60, 60)]]
sheet = Image.new("RGB", (440 * 6, 380 * 3), BG)
for j, row in enumerate(rows):
    for i, n in enumerate(row):
        sheet.paste(shot(n), (i * 440, j * 380))
sheet.save(WORK / OUT)
sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(WORK / OUT.replace(".png", "_small.png"))
