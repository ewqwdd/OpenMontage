"""Cut-out puppet: pose a character that is stored as parts + rig.json (see characters/<name>/puppet/<view>/).

    from lib.pixel_lyrics.puppet import Puppet
    p = Puppet("lib/pixel_lyrics/characters/hollow/puppet/front")
    frame = p.render({"arm_l_upper": -70, "arm_l_lower": -55, "head": 5})      # PIL RGBA, rig canvas size
    frame = p.render(p.mix("stand", "wave", 0.5), root=(0, -8))                 # between two named poses, lifted 8 px

    python -m lib.pixel_lyrics.puppet <rig dir> <out.gif>                        # demo loop through the rig's poses

A pose is {part: angle}: degrees, clockwise on screen, around the part's pivot; a child turns with its parent.
Sides are the character's own (arm_r is on the left of the picture). `root` moves the whole figure.
Rotation is nearest-neighbour, the picture stays hard-edged; the pixel filter of the edit hides the stair-steps.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _rot(angle: float, pivot) -> np.ndarray:
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    px, py = pivot
    return np.array([[c, -s, px - c * px + s * py], [s, c, py - s * px - c * py], [0, 0, 1]])


class Puppet:
    def __init__(self, rig_dir):
        self.dir = Path(rig_dir)
        self.rig = json.loads((self.dir / "rig.json").read_text(encoding="utf-8"))
        self.parts = self.rig["parts"]
        self.size = tuple(self.rig["canvas"])
        self.images = {n: Image.open(self.dir / p["file"]).convert("RGBA") for n, p in self.parts.items()}
        self.order = sorted(self.parts, key=lambda n: self.parts[n]["z"])

    def pose(self, pose) -> dict:
        """A named pose of the rig, or the dict itself."""
        return dict(self.rig["poses"][pose]) if isinstance(pose, str) else dict(pose or {})

    def mix(self, a, b, t: float) -> dict:
        a, b = self.pose(a), self.pose(b)
        return {k: a.get(k, 0) * (1 - t) + b.get(k, 0) * t for k in set(a) | set(b)}

    def matrices(self, pose=None, root=(0, 0)) -> dict:
        """Part name -> 3x3 matrix from rest-pose canvas pixels to posed canvas pixels."""
        pose = self.pose(pose)
        out: dict = {}

        def of(name):
            if name not in out:
                p = self.parts[name]
                parent = of(p["parent"]) if p["parent"] else np.array([[1, 0, root[0]], [0, 1, root[1]], [0, 0, 1.]])
                out[name] = parent @ _rot(pose.get(name, 0), p["pivot"])
            return out[name]

        for n in self.parts:
            of(n)
        return out

    def render(self, pose=None, root=(0, 0), background=None) -> Image.Image:
        mats = self.matrices(pose, root)
        frame = Image.new("RGBA", self.size, background or (0, 0, 0, 0))
        for name in self.order:
            ox, oy = self.parts[name]["origin"]
            m = mats[name] @ np.array([[1, 0, ox], [0, 1, oy], [0, 0, 1.]])      # part pixels -> canvas
            inv = np.linalg.inv(m)
            data = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])     # PIL samples at pixel centres itself
            layer = self.images[name].transform(self.size, Image.AFFINE, data, resample=Image.NEAREST)
            frame.alpha_composite(layer)
        return frame


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


def demo(rig_dir, out, fps: int = 12) -> None:
    """A-pose -> stand -> sway -> wave -> shrug -> stand, as a looping GIF at the rig's true pixel size."""
    p = Puppet(rig_dir)
    bg = (75, 63, 77, 255)
    frames = []

    def add(pose, root=(0, 0)):
        im = p.render(pose, root, bg).convert("RGB")
        k = p.rig.get("pixel", 1)
        frames.append(im.resize((im.width // k, im.height // k), Image.NEAREST))

    def move(a, b, n):
        for i in range(n):
            add(p.mix(a, b, _ease((i + 1) / n)))

    for _ in range(5):
        add("apose")
    move("apose", "stand", 8)
    stand = p.pose("stand")
    for i in range(24):                                          # sway: the torso leans, the head counters, the arms follow late
        w = math.sin(2 * math.pi * i / 24)
        w2 = math.sin(2 * math.pi * (i - 3) / 24)
        pose = dict(stand, torso=3 * w, head=-5 * w)
        pose["arm_r_upper"] = stand["arm_r_upper"] + 5 * w2
        pose["arm_l_upper"] = stand["arm_l_upper"] + 5 * w2
        add(pose, root=(0, 2 * round(abs(w))))
    move("stand", "wave", 6)
    wave = p.pose("wave")
    for i in range(18):
        add(dict(wave, arm_l_lower=wave["arm_l_lower"] + 22 * math.sin(2 * math.pi * i / 9)))
    move("wave", "shrug", 6)
    for _ in range(6):
        add("shrug")
    move("shrug", "stand", 6)
    for _ in range(4):
        add("stand")
    move("stand", "apose", 8)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0)


if __name__ == "__main__":
    demo(sys.argv[1], sys.argv[2])
