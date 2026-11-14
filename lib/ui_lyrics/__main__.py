"""python -m lib.ui_lyrics init <project_dir> [--example NAME] [--no-install]"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path) -> None:
    exe = shutil.which(cmd[0])
    if exe is None:
        raise SystemExit(f"{cmd[0]} not found on PATH")
    print("  $", " ".join(cmd))
    subprocess.run([exe, *cmd[1:]], cwd=cwd, check=True)


def init(project: Path, example: str | None, install: bool) -> None:
    if project.exists() and any(project.iterdir()):
        raise SystemExit(f"{project} already exists and is not empty")
    shutil.copytree(KIT / "template", project, dirs_exist_ok=True)
    name = re.sub(r"[^a-z0-9-]+", "-", project.name.lower()).strip("-") or "ui-lyrics-project"
    (project / "package.json").write_text(json.dumps({
        "name": name, "version": "0.0.0", "private": True, "type": "module",
        "hypit": {"project": True}, "workspaces": ["packages/*"],
        "dependencies": {
            "@hypit/hypit": "0.3.1", "@hypit/fontsource": "^0.2.0",
            "@fontsource-variable/inter": "^5.2.5", "@fontsource-variable/jetbrains-mono": "^5.2.5",
            "@kit/ui-lyrics": "*",
        },
    }, indent=2) + "\n", encoding="utf-8")
    for sub in ("assets/audio", "analysis", "productions", "renders"):
        (project / sub).mkdir(parents=True, exist_ok=True)
    scenes = project / "packages/ui-lyrics/client/scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    if example:
        ex = KIT / "examples" / example
        if not ex.is_dir():
            raise SystemExit(f"no example {example!r}; have: {[p.name for p in (KIT / 'examples').iterdir()]}")
        for f in (ex / "scenes").iterdir():
            shutil.copy2(f, scenes / f.name)
        shutil.copy2(ex / "words.final.json", project / "productions/words.final.json")
        for f in ("lyrics.txt", "lyrics_display.txt", "chunks.json"):
            if (ex / f).exists():
                shutil.copy2(ex / f, project / "analysis" / f)
    print(f"created {project}")
    if install:
        run(["npm", "install", "--no-audit", "--no-fund"], project)
        run(["hypit", "runtime", "use", "hypit.runtime.json"], project)
        run(["hypit", "programs", "prepare", "--endpoint", "html.local"], project)
    print("next: put the track at assets/audio/master.wav, write productions/words.final.json and "
          "packages/ui-lyrics/client/scenes/<edit>.js  (guide: skills/creative/ui-lyric-edit.md)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="lib.ui_lyrics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init", help="create a Hypit project for a UI-lyric edit")
    a.add_argument("project")
    a.add_argument("--example", help="copy an example's scene sets and words (e.g. mefedron)")
    a.add_argument("--no-install", action="store_true", help="skip npm install / runtime selection")
    args = ap.parse_args(argv)
    if args.cmd == "init":
        init(Path(args.project).resolve(), args.example, not args.no_install)


if __name__ == "__main__":
    main(sys.argv[1:])
