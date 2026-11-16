"""preview/ from the renders. Run after: build_blender.py -- --smooth --views --head --turn 36 --walk 24,
then compare.py x, heads_check.py, head_ring.py (project .venv python; needs ffmpeg on PATH)."""
import shutil
import subprocess

from common import *

R = WORK / "render_smooth"
PV = HERE / "preview"
SEQ = WORK / "seq"
shutil.rmtree(SEQ, ignore_errors=True)
SEQ.mkdir()


def flat(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def video(pattern, fps, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(SEQ / pattern),
                    "-pix_fmt", "yuv420p", "-crf", "16", str(PV / out)], check=True)


turn = sorted(R.glob("turn_*.png"))
for k in range(3 * len(turn)):
    im = flat(turn[k % len(turn)])
    im.crop((144, 0, 624, 768)).save(SEQ / f"turn_{k:03d}.png")
    im.crop((264, 0, 504, 180)).resize((480, 360), Image.NEAREST).save(SEQ / f"head_{k:03d}.png")
video("turn_%03d.png", 12, "turntable.mp4")
video("head_%03d.png", 12, "head_turn.mp4")
n = len(list(R.glob("walk34_*.png")))
for k in range(5 * n):
    pair = Image.new("RGB", (960, 768), BG)
    pair.paste(flat(R / f"walk34_{k % n:03d}.png").crop((144, 0, 624, 768)), (0, 0))
    pair.paste(flat(R / f"walkside_{k % n:03d}.png").crop((144, 0, 624, 768)), (480, 0))
    pair.save(SEQ / f"walk_{k:03d}.png")
video("walk_%03d.png", 24, "walk_test.mp4")

sh = Image.new("RGB", (4 * 360, 300), BG)
for i, v in enumerate(["front", "front34", "side", "back34"]):
    sh.paste(flat(R / f"stand_{v}.png").crop((332, 140, 692, 440)), (i * 360, 0))
sh.save(PV / "shoulders.png")
for src, dst in (("compare_turnaround.png", "compare_turnaround.png"), ("compare_apose.png", "compare_apose.png"),
                 ("compare_angles.png", "angles_high_low.png"), ("heads.png", "compare_heads.png"),
                 ("head_ring.png", "head_ring.png")):
    shutil.copyfile(WORK / src, PV / dst)
print("preview:", sorted(p.name for p in PV.iterdir()))
