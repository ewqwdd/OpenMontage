"""Post for the 3D lyric edit: glitch on the head, bloom, cold grade, vignette, the lyric line, 15-bit dither,
x3 nearest, mux with the audio. Driven by the project's edit.json.

    python -m lib.lyrics3d post   projects/<id> [--out renders/<edit>_3d.mp4] [--notext] [--crf 18]
    python -m lib.lyrics3d stills projects/<id> 60 150 290 400

Input: 360x640 PNG frames + meta_*.json written by scene.py (the head's place on screen per frame).
One render pixel becomes 3x3 screen pixels: 1080x1920.

edit.json, the part read here:
  shots   [{"name", "from", "glitch": [p, k], "text_y", ...}]   in frame order. p: how often a ~3-frame burst starts,
          k: its strength (0..1). Optional per shot:
            "calm":  {"from": frame, "k": 0.6}              from that frame the level is multiplied (a still stare)
            "build": [b0, b1]                               level never below b0 + b1 * progress through the shot
            "hold":  {"from": frame, "min": .75, "rand": .25}   from that frame the level never drops below min
            "hard":  true                                   bigger torn area, longer smears, a ghost head, row tears
  ticks   frames of the hook syllables: a short tear on each
  hits    frames of the head throws: a strong tear on each
  screens, words, edit, audio, fps, frames                  see lyrics.py and the guide
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from .lyrics import Lyrics

W, H, S = 360, 640, 3
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) / 16.0 - 0.5
YY, XX = np.mgrid[0:H, 0:W]
RAD = np.hypot((XX - W / 2) / (W / 2), (YY - H / 2) / (H / 2)) / np.sqrt(2)


def hsh(i, salt=0):
    x = np.sin(i * 127.1 + salt * 311.7) * 43758.5453
    return float(x - np.floor(x))


class Post:
    def __init__(self, project, text=True):
        self.project = Path(project).resolve()
        self.edit = json.loads((self.project / "edit.json").read_text(encoding="utf-8"))
        self.fps, self.nframes = self.edit.get("fps", 30), self.edit["frames"]
        self.shots = sorted(self.edit["shots"], key=lambda s: s["from"])
        self.ticks, self.hits = self.edit.get("ticks", []), self.edit.get("hits", [])
        self.lyrics = Lyrics(self.project, self.edit) if text and self.edit.get("screens") else None

    # ------------------------------------------------------------ the glitch schedule
    def shot_at(self, f):
        i = max((k for k, s in enumerate(self.shots) if s["from"] <= f), default=0)
        end = self.shots[i + 1]["from"] if i + 1 < len(self.shots) else self.nframes
        return self.shots[i], end

    def glitch_level(self, f):
        """-> (0..1, shot). 0 = clean. How hard the head is torn on this frame."""
        sh, end = self.shot_at(f)
        p, k = sh["glitch"]
        lvl = 0.0
        if hsh(f // 3, 21) < p:                                   # bursts of ~3 frames
            lvl = k * (0.45 + 0.55 * hsh(f // 3, 22))
        for s in self.ticks:                                      # a tick on every hook syllable
            if 0 <= f - s < 2:
                lvl = max(lvl, k * 0.8)
        for s in self.hits:                                       # and on every head throw
            if 0 <= f - s < 3:
                lvl = max(lvl, k * 1.0)
        if "build" in sh:                                         # builds to the end of the shot
            lvl = max(lvl, sh["build"][0] + sh["build"][1] * (f - sh["from"]) / float(end - sh["from"]))
        if "hold" in sh and f >= sh["hold"]["from"]:
            lvl = max(lvl, sh["hold"]["min"] + sh["hold"].get("rand", 0.0) * hsh(f, 23))
        if "calm" in sh and f >= sh["calm"]["from"]:              # a stare: mostly still, rare ticks
            lvl *= sh["calm"]["k"]
        return min(1.0, lvl), sh

    def glitch(self, img, m, f):
        """Tear the picture round the head. m: the frame's meta (x, y, r in render pixels, z > 0 = in front of the camera)."""
        lvl, sh = self.glitch_level(f)
        hard = bool(sh.get("hard"))
        if lvl <= 0 or m is None or m["z"] <= 0:
            return img
        cx, cy, r = m["x"], m["y"], max(6.0, m["r"])
        if not (-r < cx < W + r and -r < cy < H + r):
            return img
        rng = np.random.default_rng(1000 + (f // 2 if lvl < 0.8 else f))
        R = r * (1.35 + (0.9 if hard else 0.3) * lvl)
        x0, x1 = int(max(0, cx - R)), int(min(W, cx + R))
        y0, y1 = int(max(0, cy - R * 1.1)), int(min(H, cy + R * 1.1))
        if x1 - x0 < 6 or y1 - y0 < 6:
            return img
        out = img.copy()
        # 1. horizontal slices of the head thrown sideways
        for _ in range(2 + int(7 * lvl)):
            hgt = int(rng.integers(2, max(3, int(min(r, 40) * 0.4))))
            ys = int(rng.integers(y0, max(y0 + 1, y1 - hgt)))
            dx = int(rng.integers(-int(r * 1.1 * lvl) - 2, int(r * 1.1 * lvl) + 3))
            if dx == 0:
                continue
            a0, a1 = max(0, x0 + dx), min(W, x1 + dx)
            if a1 - a0 > 2:
                out[ys:ys + hgt, a0:a1] = img[ys:ys + hgt, a0 - dx:a1 - dx]
        # 2. colour channels pulled apart
        k = 1 + int(4 * lvl)
        reg = out[y0:y1, x0:x1].copy()
        reg[:, k:, 0] = out[y0:y1, x0:x1 - k, 0]
        reg[:, :-k, 2] = out[y0:y1, x0 + k:x1, 2]
        out[y0:y1, x0:x1] = reg
        # 3. blocks copied to the wrong place, some recoloured
        for _ in range(int(1 + 7 * lvl * lvl)):
            bw, bh = int(rng.integers(4, max(5, int(min(r, 40) * 0.6)))), int(rng.integers(2, max(3, int(min(r, 40) * 0.3))))
            sx, sy = int(rng.integers(x0, max(x0 + 1, x1 - bw))), int(rng.integers(y0, max(y0 + 1, y1 - bh)))
            tx, ty = int(rng.integers(x0, max(x0 + 1, x1 - bw))), int(rng.integers(y0, max(y0 + 1, y1 - bh)))
            blk = img[sy:sy + bh, sx:sx + bw].copy()
            mode = rng.random()
            if mode < 0.22:
                blk = 1.0 - blk
            elif mode < 0.5:
                blk = blk * np.array([(0.3, 1.2, 1.6), (1.5, 0.4, 1.3), (0.5, 0.8, 2.0)][int(rng.integers(0, 3))])
            elif mode < 0.6:
                blk = np.round(blk * 3) / 3
            th, tw = min(bh, H - ty), min(bw, W - tx)
            out[ty:ty + th, tx:tx + tw] = blk[:th, :tw]
        # 4. pixel smears: a column of the head dragged along the row
        if lvl > 0.5:
            for _ in range(int(2 + 8 * (lvl - 0.5))):
                ys = int(rng.integers(y0, y1))
                xs = int(rng.integers(x0, x1))
                ln = int(rng.integers(8, int(20 + 120 * (lvl - 0.5) * (2.0 if hard else 1.0))))
                hh = int(rng.integers(1, 4))
                if rng.random() < 0.5:
                    out[ys:ys + hh, xs:min(W, xs + ln)] = img[ys:ys + hh, xs:xs + 1]
                else:
                    out[ys:ys + hh, max(0, xs - ln):xs] = img[ys:ys + hh, xs:xs + 1]
        # 5. a "hard" shot: a ghost of the head beside it and whole-frame row tears
        if hard and lvl > 0.55:
            dx = int((r * (0.6 + 0.8 * rng.random())) * (1 if rng.random() < 0.5 else -1))
            a0, a1 = max(0, x0 + dx), min(W, x1 + dx)
            if a1 - a0 > 2:
                gh = img[y0:y1, a0 - dx:a1 - dx] * np.array((0.4, 0.9, 1.4))
                out[y0:y1, a0:a1] = np.maximum(out[y0:y1, a0:a1], gh * 0.7)
            for _ in range(int(4 * (lvl - 0.5))):
                ys, hh = int(rng.integers(0, H - 6)), int(rng.integers(2, 9))
                out[ys:ys + hh] = np.roll(out[ys:ys + hh], int(rng.integers(-40, 41)), axis=1)
        return np.clip(out, 0, 1.5)

    # ------------------------------------------------------------ the look
    def grade(self, img, f):
        # bloom from the bright things (TV, phone, pickups, the lit face)
        hi = np.clip(img - 0.70, 0, None)
        hi = np.stack([gaussian_filter(hi[..., c], 5) for c in range(3)], -1)
        img = img * 1.12 + hi * 1.1
        # channels drift apart towards the edges, like a cheap lens
        k = np.clip((RAD - 0.35) * 2.2, 0, 1)[..., None]
        sh = img.copy()
        sh[:, 1:, 0] = img[:, :-1, 0]
        sh[:, :-1, 2] = img[:, 1:, 2]
        img = img * (1 - k) + sh * k
        # cold grade: less colour, blue in the dark, pale ice in the light
        lum = (img @ np.array((0.3, 0.59, 0.11)))[..., None]
        img = lum + (img - lum) * 0.86
        img = img * np.array((0.93, 1.0, 1.09))
        img = img + (1 - np.clip(lum * 2.2, 0, 1)) * np.array((0.0, 0.012, 0.045))
        img = np.clip(img, 0, 1)
        img = img * img * (3 - 2 * img) * 0.55 + img * 0.45                    # contrast
        img = img * (1 - 0.62 * np.clip(RAD * 1.25, 0, 1)[..., None] ** 2.2)   # heavy vignette
        if self.lyrics:                                                        # the lyric line, over the graded picture
            lvl, shot = self.glitch_level(f)
            img = self.lyrics.draw(img, f, lvl, shot["name"], shot.get("text_y", 0.8))
        # grain + ordered dither to 5 bits per channel (PS1 frame buffer)
        rng = np.random.default_rng(f // 2)
        img = img + rng.normal(0, 0.008, (H, W, 1))
        q = 31.0
        img = np.floor(img * q + 0.5 + BAYER[YY % 4, XX % 4][..., None] * 0.9) / q
        return np.clip(img, 0, 1)

    def frame(self, img, m, f):
        """img: HxWx3 float 0..1 render frame -> 1920x1080x3 uint8."""
        img = self.grade(self.glitch(img, m, f), f)
        a = (img * 255 + 0.5).astype(np.uint8)
        return a.repeat(S, 0).repeat(S, 1)

    def process(self, path, m, f):
        return self.frame(np.asarray(Image.open(path).convert("RGB"), float) / 255.0, m, f)

    # ------------------------------------------------------------ files
    @staticmethod
    def load_meta(seq, tag=""):
        """All meta_*.json of a frame folder; where two cover the same frame, the newer file wins."""
        meta = {}
        for p in sorted(Path(seq).glob(f"meta_{tag}*.json"), key=lambda p: p.stat().st_mtime):
            meta.update({int(k): v for k, v in json.loads(p.read_text()).items()})
        return meta

    def stills(self, frames, seq=None, out=None, tag=""):
        seq = Path(seq) if seq else self.project / "renders" / "test"
        out = Path(out) if out else self.project / "renders" / "stills"
        out.mkdir(parents=True, exist_ok=True)
        meta = self.load_meta(seq, tag)
        if self.lyrics:
            self.lyrics.prev = None
        for f in frames:
            Image.fromarray(self.process(seq / f"{tag}{f:04d}.png", meta.get(f), f)).save(out / f"{tag}{f:04d}.png")
        return out

    def video(self, dst, seq=None, crf="18", audio=True):
        seq = Path(seq) if seq else self.project / "renders" / "seq"
        meta = self.load_meta(seq)
        frames = sorted(int(p.stem) for p in seq.glob("[0-9][0-9][0-9][0-9].png"))
        if not frames:
            raise SystemExit(f"no frames in {seq}")
        dst = Path(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * S}x{H * S}", "-r", str(self.fps), "-i", "-"]
        wav = self.project / self.edit.get("audio", "assets/audio/audio.wav")
        if audio and wav.exists():
            cmd += ["-ss", str(frames[0] / self.fps), "-i", str(wav)]
        elif audio:
            print("no audio at", wav, "- the video will be silent")
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
                "-shortest", "-movflags", "+faststart", str(dst)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in frames:
            p.stdin.write(self.process(seq / f"{f:04d}.png", meta.get(f), f).tobytes())
        p.stdin.close()
        if p.wait():
            raise SystemExit("ffmpeg failed")
        return dst, len(frames)
