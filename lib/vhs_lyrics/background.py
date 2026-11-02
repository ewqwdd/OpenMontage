"""Background plate + audio for a timeline.

Each scene: its clip from bg.offset (seconds), cover-cropped to the frame, exactly
(end-start) frames, graded with an ffmpeg filter string (darken / desaturate / tint /
curves — tune so per-scene mean & median luma match the reference), or auto-graded from
bg.look (see grade.py). Concatenated hard cuts.
"""
import json
import subprocess
from pathlib import Path

from . import grade


def _src(tl, p):
    p = Path(p)
    return p if p.is_absolute() else (tl["base"] / p)


def _duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def build(tl, assets):
    W, H, FPS = tl["width"], tl["height"], tl["fps"]
    seg_dir = assets / "bg_segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    lst, report = [], []
    for k, sc in enumerate(tl["scenes"]):
        bg = sc["bg"]
        src, n = _src(tl, bg["src"]), sc["end"] - sc["start"]
        need, have = n / FPS, _duration(src)
        offset, loop = bg.get("offset", 0), []
        if offset + need > have:  # swapped-in clip too short for this offset: slide back, loop if still short
            offset = max(0.0, have - need - 0.05)
            loop = ["-stream_loop", "-1"] if have < need + 0.05 else []
            print(f"background: scene {k} offset {bg.get('offset', 0)} -> {offset:.2f}"
                  + (" (looped)" if loop else ""))
        if "look" in bg and not bg.get("grade"):
            bg["grade"], got = grade.fit(src, offset, n, W, H, FPS, bg["look"])
            report.append({"scene": k, "src": str(bg["src"]), "offset": offset, "grade": bg["grade"], **got})
        out = seg_dir / f"bg_{k}.mp4"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
              + (f",{bg['grade']}" if bg.get("grade") else "") + ",format=yuv420p")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *loop, "-ss", str(offset), "-i", str(src),
                        "-an", "-vf", vf, "-frames:v", str(n),
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast", str(out)], check=True)
        lst.append(f"file '{out.name}'")
    if report:
        (assets / "grades.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        for r in report:
            print(f"grade: scene {r['scene']} median {r['median']:.0f} p95 {r['p95']:.0f} mean {r['mean']:.0f}")
    (seg_dir / "concat.txt").write_text("\n".join(lst) + "\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
                    "-c", "copy", str((assets / "bg.mp4").resolve())], check=True, cwd=seg_dir)

    au = tl["audio"]
    dur = tl["frames"] / FPS
    fade = au.get("fade_out", 0.5)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(au.get("offset", 0)), "-i", str(_src(tl, au["src"])),
                    "-t", f"{dur:.3f}", "-vn", "-af", f"afade=t=out:st={dur - fade:.3f}:d={fade}",
                    "-c:a", "aac", "-b:a", "192k", str(assets / "audio.m4a")], check=True)
    print(f"background: {len(tl['scenes'])} scenes, {tl['frames']} frames")
