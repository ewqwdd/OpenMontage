"""ui_lyrics kit: the template is complete and the example data is consistent with its scene code."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib.ui_lyrics.__main__ import init

KIT = Path(__file__).resolve().parents[2] / "lib" / "ui_lyrics"
EX = KIT / "examples" / "mefedron"


def test_template_files_exist():
    for rel in ("hypit.runtime.json", "dev/index.html", "tools/gen_source.mjs", "tools/words_from_fa.mjs",
                "tools/plot_align.py", "tools/check_sync.py", "packages/ui-lyrics/package.json",
                "packages/ui-lyrics/build.mjs", "packages/ui-lyrics/tsconfig.json",
                "packages/ui-lyrics/src/activation.ts", "packages/ui-lyrics/src/render.ts",
                "packages/ui-lyrics/client/engine.js", "packages/ui-lyrics/client/engine.css"):
        assert (KIT / "template" / rel).is_file(), rel


def test_runtime_is_local_only():
    rt = json.loads((KIT / "template/hypit.runtime.json").read_text(encoding="utf-8"))
    assert {e["use"] for e in rt["endpoints"].values()} == {"@hypit/media-local", "@hypit/provider-html-local"}


def test_engine_has_no_hardcoded_scene_set():
    eng = (KIT / "template/packages/ui-lyrics/client/engine.js").read_text(encoding="utf-8")
    assert "const SCENE_SETS = {};" in eng and "SCENE_SETS[data.variant]" in eng
    assert "buildChorus" not in eng and "Math.random" not in eng


def words():
    return json.loads((EX / "words.final.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("edit", ["chorus", "verse"])
def test_example_words_fit_their_edit(edit):
    w = words(); e = w["edits"][edit]; ws = [x for x in w["words"] if x["edit"] == edit]
    frames = [max(0, round((x["start"] - e["start"]) * w["fps"]) - w["lead"]) for x in ws]
    assert frames == sorted(frames) and len(set(frames)) == len(frames), "words must land on distinct, increasing frames"
    assert frames[-1] < e["frames"]
    assert all(x["end"] > x["start"] for x in ws)


@pytest.mark.parametrize("edit", ["chorus", "verse"])
def test_example_scenes_only_use_existing_words(edit):
    n = sum(1 for x in words()["words"] if x["edit"] == edit)
    js = (EX / "scenes" / f"{edit}.js").read_text(encoding="utf-8")
    assert f"SCENE_SETS.{edit} = function (A)" in js
    literal = [int(i) for i in re.findall(r"\bwf\((\d+)\)", js)]
    assert literal and max(literal) < n
    assert "Math.random" not in js, "scenes must be a pure function of the frame"


def test_display_lyrics_match_alignment_lyrics():
    a = [l.split() for l in (EX / "lyrics.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    d = [l.split() for l in (EX / "lyrics_display.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert [len(x) for x in a] == [len(x) for x in d]
    assert [w["text"] for w in words()["words"]] == [t for line in d for t in line]


def test_init_copies_template_and_example(tmp_path):
    proj = tmp_path / "My Edit"
    init(proj, "mefedron", install=False)
    pkg = json.loads((proj / "package.json").read_text(encoding="utf-8"))
    assert pkg["hypit"] == {"project": True} and pkg["name"] == "my-edit"
    assert (proj / "packages/ui-lyrics/client/scenes/chorus.js").is_file()
    assert (proj / "productions/words.final.json").is_file()
    assert (proj / "analysis/chunks.json").is_file()
    with pytest.raises(SystemExit):
        init(proj, None, install=False)
