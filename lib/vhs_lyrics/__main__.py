"""python -m lib.vhs_lyrics <timeline.json> <project_dir> [--stages bg,html,render,post] [--workers 3]

project_dir gets: hyperframes/ (index.html + assets), renders/raw.mp4, renders/final.mp4.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import background, compose, post, timeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vhs_lyrics")
    ap.add_argument("timeline")
    ap.add_argument("project")
    ap.add_argument("--stages", default="bg,html,render,post")
    ap.add_argument("--workers", default="3")
    a = ap.parse_args(argv)
    stages = set(a.stages.split(","))
    tl = timeline.load(a.timeline)
    proj = Path(a.project)
    ws = proj / "hyperframes"
    (ws / "assets").mkdir(parents=True, exist_ok=True)
    (proj / "renders").mkdir(parents=True, exist_ok=True)
    raw, final = proj / "renders" / "raw.mp4", proj / "renders" / "final.mp4"

    if "bg" in stages:
        background.build(tl, ws / "assets")
    if "html" in stages:
        compose.build(tl, ws)
    if "render" in stages:
        r = subprocess.run(f'npx hyperframes render . -w {a.workers} -o "{raw.resolve()}"',
                           shell=True, cwd=ws)
        if r.returncode:
            sys.exit(r.returncode)
    if "post" in stages:
        fx = tl.get("effects", {})
        noholds = json.loads((ws / "assets" / "noholds.json").read_text())
        post.run(raw, final, tl["width"], tl["height"], tl["fps"], noholds,
                 lens=fx.get("lens", True), holds=fx.get("frame_holds", True), wave=fx.get("vhs_wave", True),
                 k1=tl.get("lens_k1", 0.17), zoom=tl.get("lens_zoom", 1.17))


if __name__ == "__main__":
    main()
