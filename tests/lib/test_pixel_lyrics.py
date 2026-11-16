"""pixel_lyrics kit: the template is complete and the example data is consistent with its scene code."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib.pixel_lyrics.__main__ import init

KIT = Path(__file__).resolve().parents[2] / "lib" / "pixel_lyrics"
EX = KIT / "examples" / "mefedron"
PKG = "packages/pixel-lyrics"


def test_template_files_exist():
    for rel in ("hypit.runtime.json", "dev/index.html", "tools/gen_source.mjs", "tools/words_from_fa.mjs",
                "tools/plot_align.py", "tools/check_sync.py", "tools/gen_img.py", "tools/prep_img.py",
                "tools/syllables.py", "tools/shot.mjs", "tools/grade.mjs", f"{PKG}/package.json", f"{PKG}/build.mjs",
                f"{PKG}/tsconfig.json", f"{PKG}/src/activation.ts", f"{PKG}/src/render.ts", f"{PKG}/client/engine.js",
                f"{PKG}/client/font/cyrillic.woff2", f"{PKG}/client/font/latin.woff2"):
        assert (KIT / "template" / rel).is_file(), rel
    for name in ("hero_sheet", "room", "closeup", "street"):
        assert (KIT / "style" / f"{name}.jpg").is_file(), name


def test_runtime_is_local_only():
    rt = json.loads((KIT / "template/hypit.runtime.json").read_text(encoding="utf-8"))
    assert {e["use"] for e in rt["endpoints"].values()} == {"@hypit/media-local", "@hypit/provider-html-local"}


def test_engine_has_no_hardcoded_scene_set():
    eng = (KIT / f"template/{PKG}/client/engine.js").read_text(encoding="utf-8")
    assert "(window.PIXEL_SCENES || {})[data.variant]" in eng and "function setupPixel(root, data)" in eng
    assert "Math.random" not in eng and "SHAKAL" not in eng
    assert "ACCENT[data.accent] || ACCENT.cold" in eng, "the approved accent is the default"


def test_paid_generation_needs_a_budget():
    src = (KIT / "template/tools/gen_img.py").read_text(encoding="utf-8")
    assert '"--budget", type=float, required=True' in src and "STOP" in src


def test_grade_keeps_every_blend_input_in_one_format():
    src = (KIT / "template/tools/grade.mjs").read_text(encoding="utf-8")
    assert src.count("format=gbrp") >= 6 and "all_opacity=${strength}" in src
    for look in ("ice", "halo", "dream"):
        assert f"\n  {look}: {{" in src


def words():
    return json.loads((EX / "words.final.json").read_text(encoding="utf-8"))


def frames(edit):
    w = words(); e = w["edits"][edit]
    return [max(0, round((x["start"] - e["start"]) * w["fps"] - w["lead"])) for x in w["words"] if x["edit"] == edit]


@pytest.mark.parametrize("edit", ["chorus", "verse"])
def test_example_words_fit_their_edit(edit):
    f = frames(edit)
    assert f == sorted(f) and len(set(f)) == len(f), "words must land on distinct, increasing frames"
    assert f[-1] < words()["edits"][edit]["frames"]


def test_example_chorus_lands_on_the_approved_frames():
    assert frames("chorus")[:12] == [4, 13, 34, 61, 73, 85, 118, 142, 156, 171, 195, 198]


@pytest.mark.parametrize("edit", ["chorus", "verse"])
def test_example_scenes_match_words_and_pictures(edit):
    n = len(frames(edit))
    js = (EX / "scenes" / f"{edit}.js").read_text(encoding="utf-8")
    assert f"(window.PIXEL_SCENES = window.PIXEL_SCENES || {{}}).{edit} = A =>" in js
    assert "cuts: S.cuts" in js and "Math.random" not in js, "scenes must be a pure function of the frame"
    literal = [int(i) for i in re.findall(r"\bW\((\d+)\)", js)]
    assert literal and max(literal) < n
    lines = re.findall(r"\{ from: (\d+), to: (\d+)", js)
    assert [int(a) for a, _ in lines][0] == 0 and int(lines[-1][1]) == n - 1, "phrases cover every word"
    have = {p.stem for p in (EX / "img").iterdir()}
    used = set(re.findall(r"'((?:[cv]\d_|it_)[a-z0-9_]+)'", js))
    assert used and used <= have, used - have


def test_example_syllables_spell_their_words():
    js = (EX / "scenes" / "chorus.js").read_text(encoding="utf-8")
    ws = [x["text"].strip(" ,").upper() for x in words()["words"] if x["edit"] == "chorus"]
    found = re.findall(r"syl: \{ (\d+): \[((?:\['[^']+', \d+\](?:, )?)+)\]", js)
    assert len(found) == 4
    for idx, body in found:
        parts = re.findall(r"\['([^']+)', (\d+)\]", body)
        assert "".join(p for p, _ in parts) == ws[int(idx)]
        offs = [int(o) for _, o in parts]
        assert offs[0] == 0 and offs == sorted(offs) and len(set(offs)) == len(offs)


def test_example_cuts_are_inside_the_edit():
    cuts = json.loads((EX / "cuts.json").read_text(encoding="utf-8"))
    for edit, cs in cuts.items():
        assert cs == sorted(cs) and 0 < cs[0] and cs[-1] < words()["edits"][edit]["frames"]


def test_init_copies_template_and_example(tmp_path):
    proj = tmp_path / "My Edit"
    init(proj, "mefedron", install=False)
    pkg = json.loads((proj / "package.json").read_text(encoding="utf-8"))
    assert pkg["hypit"] == {"project": True} and pkg["name"] == "my-edit"
    assert (proj / PKG / "client/scenes/chorus.js").is_file()
    assert (proj / "productions/words.final.json").is_file() and (proj / "productions/cuts.json").is_file()
    assert (proj / "assets/style/hero_sheet.jpg").is_file() and (proj / "assets/gen/prep.json").is_file()
    manifest = json.loads((proj / PKG / "client/img/manifest.json").read_text(encoding="utf-8"))
    assert "c1_room.jpg" in manifest and "it_meph.png" in manifest
    with pytest.raises(SystemExit):
        init(proj, None, install=False)
