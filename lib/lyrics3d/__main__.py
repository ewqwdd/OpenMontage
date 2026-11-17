"""3D horror-game lyric edit: project commands.

    python -m lib.lyrics3d init   projects/<id> [--example mefedron]
    python -m lib.lyrics3d stills projects/<id> 60 150 290 [--dbg side|front|back|top] [--raw]
    python -m lib.lyrics3d render projects/<id> [--frames A B] [--jobs 2]
    python -m lib.lyrics3d post   projects/<id> [--out renders/<edit>_3d.mp4] [--notext] [--small]

Blender is taken from .runtime/blender/*/ in the repo, else from PATH. Everything is local and free.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPO = KIT.parents[1]


def blender() -> str:
    for name in ("blender.exe", "blender"):
        for p in sorted((REPO / ".runtime" / "blender").glob(f"*/{name}"), reverse=True):
            if p.is_file():
                return str(p)
    exe = shutil.which("blender")
    if not exe:
        raise SystemExit("Blender not found: put it in .runtime/blender/<version>/ or on PATH")
    return exe


def scene_cmd(project: Path, out: Path, extra: list[str]) -> list[str]:
    return [blender(), "-b", "-P", str(KIT / "scene.py"), "--", "--project", str(project), "--out", str(out), *extra]


def run_scene(cmds: list[list[str]]) -> None:
    """Run Blender jobs side by side; show only the errors and a line per job."""
    procs = [subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace") for c in cmds]
    failed = False
    for c, p in zip(cmds, procs):
        text = p.communicate()[0]
        bad = [ln for ln in text.splitlines() if "Traceback" in ln or "Error" in ln or ln.startswith("  File ")]
        n = sum(1 for ln in text.splitlines() if ln.startswith("frame "))
        print(f"  blender {' '.join(c[c.index('--out') + 2:])}: {n} frames" + (" FAILED" if p.returncode or bad else ""))
        if p.returncode or bad:
            failed = True
            print("\n".join(text.splitlines()[-25:]))
    if failed:
        raise SystemExit(1)


def init(project: Path, example: str | None) -> None:
    if project.exists() and any(project.iterdir()):
        raise SystemExit(f"{project} already exists and is not empty")
    for sub in ("assets/audio", "assets/tex", "renders"):
        (project / sub).mkdir(parents=True, exist_ok=True)
    ex = KIT / "examples" / (example or "mefedron")
    if not ex.is_dir():
        raise SystemExit(f"no example {example!r}; have: {[p.name for p in (KIT / 'examples').iterdir()]}")
    for f in ex.iterdir():
        if f.is_file():
            shutil.copy2(f, project / f.name)
    edit = json.loads((project / "edit.json").read_text(encoding="utf-8"))
    print(f"created {project} from the example {ex.name!r}")
    print(f"next: put the excerpt's sound at {edit['audio']} (exactly {edit['frames']} frames at {edit['fps']} fps), "
          "then rewrite words.json, edit.json and shots.py for the new lines  (guide: skills/creative/3d-lyric-edit.md)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="lib.lyrics3d")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init", help="create a project from an example")
    a.add_argument("project")
    a.add_argument("--example", default="mefedron")
    a = sub.add_parser("stills", help="render a few frames and grade them: the style-frame / pose check")
    a.add_argument("project")
    a.add_argument("frames", type=int, nargs="+")
    a.add_argument("--dbg", choices=["side", "front", "back", "top"], help="look at the pose from outside the shot")
    a.add_argument("--raw", action="store_true", help="stop after Blender: no glitch, grade or text")
    a.add_argument("--notext", action="store_true")
    a = sub.add_parser("render", help="render the frame sequence to renders/seq")
    a.add_argument("project")
    a.add_argument("--frames", type=int, nargs=2, metavar=("A", "B"))
    a.add_argument("--jobs", type=int, default=2)
    a = sub.add_parser("post", help="glitch, grade, text, x3, sound -> mp4")
    a.add_argument("project")
    a.add_argument("--out")
    a.add_argument("--notext", action="store_true")
    a.add_argument("--crf", default="18")
    a.add_argument("--small", action="store_true", help="also write a copy under 30 MiB for a phone")
    args = ap.parse_args(argv)
    project = Path(args.project).resolve()
    if args.cmd == "init":
        init(project, args.example)
        return
    edit = json.loads((project / "edit.json").read_text(encoding="utf-8"))
    if args.cmd == "stills":
        tag = f"{args.dbg}_" if args.dbg else ""
        seq = project / "renders" / "test"
        extra = ["--tag", tag, "--stills", *map(str, args.frames)]
        if args.dbg:
            extra = ["--dbg", args.dbg, "--nofog", "--bulb", "600", *extra]      # bright and clear: it is a pose check
        run_scene([scene_cmd(project, seq, extra)])
        if args.raw or args.dbg:
            print("frames ->", seq)
            return
        from .post import Post
        print("stills ->", Post(project, text=not args.notext).stills(args.frames, seq, tag=tag))
    elif args.cmd == "render":
        a0, b0 = args.frames or (0, edit["frames"] - 1)
        n = max(1, min(args.jobs, b0 - a0 + 1))
        step = -(-(b0 - a0 + 1) // n)
        seq = project / "renders" / "seq"
        cmds = [scene_cmd(project, seq, ["--frames", str(a), str(min(b0, a + step - 1))]) for a in range(a0, b0 + 1, step)]
        run_scene(cmds)
        print("frames ->", seq)
    elif args.cmd == "post":
        from .post import Post
        dst = project / (args.out or f"renders/{edit['edit']}_3d.mp4")
        out, n = Post(project, text=not args.notext).video(dst, crf=args.crf)
        print(f"video -> {out}  ({n} frames, {out.stat().st_size / 2 ** 20:.1f} MiB)")
        if args.small:
            small = out.with_name(out.stem + "_small.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-c:v", "libx264", "-preset", "slow", "-b:v", "9500k",
                            "-maxrate", "12000k", "-bufsize", "20000k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-movflags", "+faststart", str(small)], check=True)
            print(f"small -> {small}  ({small.stat().st_size / 2 ** 20:.1f} MiB)")


if __name__ == "__main__":
    main(sys.argv[1:])
