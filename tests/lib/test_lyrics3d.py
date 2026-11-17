"""lyrics3d kit: the example is complete and consistent, and the post pass runs without Blender."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest

from lib.lyrics3d.__main__ import init
from lib.lyrics3d.post import H, W, Post

KIT = Path(__file__).resolve().parents[2] / "lib" / "lyrics3d"
EX = KIT / "examples" / "mefedron"


def test_kit_files_exist():
    for rel in ("scene.py", "post.py", "lyrics.py", "textures.py", "__main__.py", "examples/mefedron/shots.py",
                "examples/mefedron/edit.json", "examples/mefedron/words.json"):
        assert (KIT / rel).is_file(), rel
    for name in ("rug", "wallrug", "wallpaper", "floor", "plaster", "mattress", "plaid", "pizzabox", "tv_0", "tv_3",
                 "window", "baggie", "blotter", "xanbar", "oxy"):
        assert (KIT / "assets" / "tex" / f"{name}.png").is_file(), name
    assert (KIT.parent / "glitch_drop/assets/fonts/CormorantGaramond.ttf").is_file()
    assert (KIT.parent / "pixel_lyrics/characters/hollow/model3d/hollow_smooth.blend").is_file()


def test_blender_scripts_parse():
    for rel in ("scene.py", "examples/mefedron/shots.py"):
        ast.parse((KIT / rel).read_text(encoding="utf-8"))


def test_example_edit_is_consistent():
    edit = json.loads((EX / "edit.json").read_text(encoding="utf-8"))
    words = json.loads((EX / "words.json").read_text(encoding="utf-8"))
    ws = [w for w in words["words"] if w["edit"] == edit["edit"]]
    froms = [s["from"] for s in edit["shots"]]
    assert froms == sorted(froms) and froms[0] == 0 and froms[-1] < edit["frames"]
    assert words["edits"][edit["edit"]]["frames"] == edit["frames"]
    covered = [i for a, b, _ in edit["screens"] for i in range(a, b + 1)]
    assert covered == list(range(len(ws))), "every word is on exactly one screen, in order"
    t0 = words["edits"][edit["edit"]]["start"]
    onsets = [round((w["start"] - t0) * edit["fps"]) for w in ws]
    # every shot after the first is cut on the first word of a line, or up to 3 frames before it
    line_starts = {onsets[a] for a, _, _ in edit["screens"]}
    for f in froms[1:]:
        assert any(0 <= o - f <= 3 for o in line_starts), f
    for f in edit["ticks"] + edit["hits"]:
        assert 0 <= f < edit["frames"]


@pytest.fixture()
def project(tmp_path):
    init(tmp_path / "p", "mefedron")
    return tmp_path / "p"


def test_init_copies_the_example(project):
    for rel in ("shots.py", "edit.json", "words.json", "assets/audio", "assets/tex", "renders"):
        assert (project / rel).exists(), rel
    with pytest.raises(SystemExit):
        init(project, "mefedron")


def test_post_frame(project):
    post = Post(project)
    img = np.full((H, W, 3), 0.3)
    meta = {"x": 180.0, "y": 300.0, "r": 30.0, "z": 1.0}
    out = post.frame(img, meta, 130)                       # shot B, a red-word frame
    assert out.shape == (H * 3, W * 3, 3) and out.dtype == np.uint8
    assert np.array_equal(out[::3, ::3].repeat(3, 0).repeat(3, 1), out), "one render pixel = 3x3 screen pixels"
    assert len(np.unique(out)) <= 32, "5 bits per channel"
    red = out[int(0.80 * H * 3) - 60:int(0.80 * H * 3) + 60].astype(int)
    assert ((red[..., 0] > 150) & (red[..., 1] < 90)).any(), "the accent word is red"
    assert np.array_equal(out, Post(project).frame(img, meta, 130)), "deterministic"


def test_glitch_schedule(project):
    post = Post(project)
    lv = [post.glitch_level(f)[0] for f in range(post.nframes)]
    assert all(0.0 <= v <= 1.0 for v in lv)
    shots = {s["name"]: s["from"] for s in post.shots}
    mean = lambda a, b: float(np.mean(lv[a:b]))            # noqa: E731
    assert mean(shots["D"], post.nframes) > mean(shots["B"], shots["C"]) > mean(0, shots["B"]), "it gets harder"
    assert min(lv[389:]) >= 0.75, "the last line never lets go"
    for f in post.hits:
        assert lv[f] >= 0.4
