"""lib/card_strobe: grammar rules match the reference numbers, timeline validation, and a tiny render
from a synthetic clip (ffmpeg testsrc; no user media, no network)."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from lib.card_strobe import fx, render, timeline
from lib.card_strobe import grammar as g

KIT = Path(__file__).resolve().parents[2] / "lib" / "card_strobe"


# ---------------------------------------------------------------- grammar = measured reference
def test_hero_card_polarity_matches_reference():
    # ref3 MASTER/MIND f27-42: W27-28 B29-31 W32-33 B34-36 W37-38 B39-41 W42
    assert g.strobe_swaps(27, 42) == [27, 28, 32, 33, 37, 38, 42]
    # ZAE-/BAL f167-181: W167-169 B170-171 W172-173 B174-176 W177-179 B180-181
    assert g.strobe_swaps(167, 181, g.CARD2_RUNS) == [167, 168, 169, 172, 173, 177, 178, 179]


def test_burst_runs_match_reference():
    assert g.burst_runs(21) == [1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 2]       # ref3 f140-160
    assert sum(g.burst_runs(13)) == 13


def test_card_text_and_syllables():
    assert g.card_text("заебал") == "ZAEBAL"
    assert g.card_text("Mastermind,") == "MASTERMIND"
    assert g.card_text("сиги", latin=False) == "СИГИ"
    assert g.split_syllables("MASTERMIND") == ("MASTER", "MIND")
    assert g.split_syllables("ZAEBAL") == ("ZAE", "BAL")
    assert g.hero_fit("MASTER") == [1038, 823] and g.hero_fit("MIND") == [828, 932]


def test_time_maps():
    assert [fx.conform(j) for j in range(8)] == [0, 0, 1, 3, 3, 4, 6, 6]     # 20 fps inside 30
    assert [fx.pingpong(j, 2, 2) for j in range(10)] == [0, 0, 1, 1, 2, 2, 1, 1, 0, 0]


def test_find_gaps_on_synthetic_sub_band():
    t = np.arange(0, 6, 0.01)
    e = np.full_like(t, 54.0)
    e[(t >= 3.0) & (t < 3.75)] = 48.0                 # 4 eighths at 160 BPM, -6 dB
    gaps = g.find_gaps(t, e, 0.0, 0.5, 5.5, 0.1875)
    assert len(gaps) == 1 and abs(gaps[0][0] - 3.0) < 0.01 and abs(gaps[0][1] - 3.75) < 0.01


# ---------------------------------------------------------------- timeline
def _flat_tl(**over):
    tl = {"fps": 30, "frames": 6, "audio": {"path": "a.m4a", "duration": 0.2},
          "shots": [{"kind": "flat", "f": [0, 1], "value": 0},
                    {"kind": "card", "f": [2, 4], "swap": [3],
                     "states": [{"from": 2, "lines": [{"text": "ZAE-", "cap": 200, "at": [540, 540]}]}]},
                    {"kind": "flat", "f": [5, 5], "value": 254}],
          "subtitles": [{"f": [0, 1], "style": "band", "words": [[0, "меня"], [1, "Трамп"]]}],
          "events": {"inverts": [4], "bar_flash": [1]}}
    tl.update(over)
    return tl


def test_timeline_rejects_gaps_and_unknown_grades():
    bad = _flat_tl(shots=[{"kind": "flat", "f": [0, 2], "value": 0}, {"kind": "flat", "f": [4, 5], "value": 0}])
    with pytest.raises(ValueError, match="cover every frame"):
        timeline.resolve(bad)
    bad = _flat_tl(clips={"c": {"src": "x.mp4", "t0": 0, "dur": 1}},
                   shots=[{"kind": "clip", "f": [0, 5], "clip": "c", "t": 0, "grade": "nope"}])
    with pytest.raises(ValueError, match="unknown grade"):
        timeline.resolve(bad)


def test_example_timeline_is_valid_and_dumps_round_trip():
    raw = json.loads((KIT / "examples" / "mastermind_toilet.json").read_text(encoding="utf-8"))
    tl = timeline.resolve(raw, KIT / "examples")
    assert tl["frames"] == 364 and tl["shots"][-1]["f"][1] == 363
    assert json.loads(timeline.dumps(raw)) == raw


def test_cards_flats_bars_and_inverts():
    tl = timeline.resolve(_flat_tl())
    r = render.Renderer(tl, {}, {})
    f0, f1, f2, f3, f4, f5 = (r.frame(i) for i in range(6))
    assert f0.shape == (1920, 1080, 3)
    assert f0[100].max() == 0 and f0[420:1500].max() > 200          # black + white subtitle, black bars
    assert f1[100].min() == 254                                       # bar flash: bars white, square black
    assert f2[100].max() == 0 and f2[420:1500].max() == 254           # black card, white type, black bars
    assert f3[100].min() == 254 and f3[430, 20].min() == 254          # swapped polarity: white card AND bars
    assert f4[100].min() == 255                                       # invert: black bars -> white
    assert f5.min() == 254                                            # white flash, bars included


def test_bundled_fallback_fonts_render_cyrillic():
    from lib.card_strobe import fonts
    from lib.card_strobe import text as tx
    fb = {r: list(c[-1]) for r, c in fonts.ROLES.items()}          # last candidate = the bundled file
    for path, _, _ in fb.values():
        assert Path(path).exists() and "assets/fonts" in path
    fonts.set_overrides(fb)
    try:
        tofu = tx.text_mask("￿", "card", 80).sum()
        for role in fonts.ROLES:
            assert tx.text_mask("ЖЯД", role, 80).sum() > 0
        assert tx.text_mask("ЖЯД", "card", 80).sum() != tofu * 3
        assert tx.blocky_mask("БРЕНД", 124).shape[1] > 100
    finally:
        fonts.set_overrides(None)


# ---------------------------------------------------------------- footage path (needs ffmpeg)
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_clip_render_from_synthetic_source(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
                    "-t", "1.2", "-pix_fmt", "yuv420p", str(src)], check=True)
    tl = timeline.resolve({
        "fps": 30, "frames": 12, "audio": {"path": "a.m4a", "duration": 0.4},
        "clips": {"c": {"src": str(src), "t0": 0.1, "dur": 0.6, "ax": 0.5}},
        "shots": [{"kind": "clip", "f": [0, 7], "clip": "c", "t": 0.1, "grade": "red", "conform": 20,
                   "camera": {"push": {"to": 1.5, "frames": 8}, "about": [605, 605]},
                   "fx": {"entry": {"frames": 4}, "pulses": {"frames": [5]}}},
                  {"kind": "clip", "f": [8, 11], "clip": "c", "t": 0.3, "grade": "bw", "pingpong": [2, 2],
                   "fx": {"scratches": {"seed": 1}}}],
        "text": [{"kind": "word", "f": [2, 7], "text": "EU", "cap": 65, "at": [390, 680], "scale": [1.0, 0.75, 0.6]},
                 {"kind": "clones", "f": [3, 7], "text": "HA", "cap": 95, "positions": [[540, 270], [250, 760]]},
                 {"kind": "stack", "f": [8, 11], "text": "PAYPAL", "cap": 60, "at": [540, 540], "rows": [2, 4]}],
        "subtitles": [{"f": [8, 11], "style": "cursor", "words": [[8, "ты"], [10, "до сих пор"]], "slide_in": 3}],
        "motion": [{"f": [9, 11], "dx": {"9": 0, "10": 40, "11": 120}}],
        "events": {"inverts": [6], "mosaic": {"frames": [1], "block": 36}}}, tmp_path)
    frames = dict(render.frames(tl, 0, 12, tmp_path / "cache", log=lambda s: None))
    assert sorted(frames) == list(range(12))
    sq = frames[3][420:1500]
    assert sq[..., 1].mean() < sq[..., 0].mean()                     # red duotone: G crushed under R
    assert frames[10][420:1500].std() > 10                            # footage + text, not flat
    a = dict(render.frames(tl, 9, 11, tmp_path / "cache", log=lambda s: None))
    assert np.array_equal(a[10], frames[10])                          # pure function of the frame index


# ---------------------------------------------------------------- fused style + kit extensions
def test_fused_grammar_helpers():
    assert g.split_syllables("MEFEDRON") == ("MEFE", "DRON")
    assert g.split_syllables("PIDORASIT") == ("PIDO", "RASIT")
    assert g.show_ranges([[3, 5], [9, 9]]) == [3, 4, 5, 9]
    st = g.syllable_card([(10, ["DOLBO-"]), (14, ["DOLBO-", "YOBKA"])], "DOLBO-")
    a, b = st[0]["lines"][0], st[1]["lines"][0]
    assert a["fit"] == b["fit"] and a["fit"][0] == 1000          # one squeeze: DOLBO- keeps its width
    assert st[0]["lines"][0]["at"][1] == 540 and [ln["at"][1] for ln in st[1]["lines"]] == [300, 760]


def test_soft_strobe_and_invert_modes():
    from lib.card_strobe import grade
    img = np.full((4, 4, 3), 200, np.uint8)
    hard = grade.exposure_strobe(img, 5, (0, 9), [(5, 244)])
    soft = grade.exposure_strobe(img, 5, (0, 9), [(5, 244)], curve={"mode": "soft"})
    assert hard.max() == 255 and soft.max() <= 220                 # highlights roll off toward the ceiling
    warm = np.zeros((2, 2, 3), np.uint8)
    warm[:] = (200, 120, 60)
    rgb, hue = grade.invert(warm, "rgb"), grade.invert(warm, "hue")
    assert rgb[0, 0, 2] > rgb[0, 0, 0]                             # a plain invert turns orange blue
    assert hue[0, 0, 0] > hue[0, 0, 2]                             # the hue-safe invert stays warm
    duo = grade.invert(warm, "duotone", grade.PALETTES["ice"])
    assert duo[0, 0, 2] >= duo[0, 0, 0]                            # luma flipped through the ice ramp


def test_timeline_lint_and_invert_mode_validation(tmp_path):
    tl = _flat_tl(clips={"c": {"src": "x.mp4", "t0": 0, "dur": 1}},
                  shots=[{"kind": "clip", "f": [0, 5], "clip": "c", "t": 0, "grade": "red", "speed": 0.75}])
    assert any("repeats frames" in w for w in timeline.resolve(tl)["_warnings"])
    tl["clips"]["c"]["fps"] = 60
    assert not timeline.resolve(tl)["_warnings"]
    with pytest.raises(ValueError, match="invert_modes"):
        timeline.resolve(_flat_tl(events={"inverts": [4], "invert_modes": {"4": "sepia"}}))


def test_fused_block_resolves_steps_with_base_options():
    tl = timeline.resolve(_flat_tl(fused={
        "serif": {"lines": [{"f": [0, 1], "words": [[0, "я"]]}]},
        "vhs": {"until": 2, "soften": 2.2},
        "glitch": {"bars": "keep", "base": {"frames": [2, 3], "luma_cap": 200, "banned": ["iri"]},
                   "runs": [{"f": [4, 5], "pattern": "reference_drop", "from": 4}],
                   "steps": {"3": "inv hs=8", "1": {"step": "wash=1.15,8", "jpeg": 0, "stage": "pre"}}}}))
    st = tl["fused"]["_steps"]
    assert st[3]["step"] == "inv hs=8" and st[3]["luma_cap"] == 200 and st[3]["bars"] == "keep"
    assert st[1]["stage"] == "pre" and st[1]["luma_cap"] is None   # not a base frame: no base options
    assert "_step" in st[4] and tl["fused"]["vhs"][0]["f"] == [0, 1]


def test_fused_render_cards_glitch_and_purity():
    tl = timeline.resolve(_flat_tl(
        subtitles=[], events={"inverts": [], "bar_flash": []},
        fused={"serif": {"lines": [{"f": [0, 1], "words": [[0, "Эй,"], [1, "звонит"]], "y": 540}]},
               "captions": [{"f": [2, 4], "text": "заебал"}],
               "vhs": [{"f": [0, 0], "grain": 2.3}],
               "glitch": {"steps": {"3": "inv hs=8", "5": {"step": "fill=30,208,245", "bars": "keep"}}}}))
    from lib.card_strobe.fused import FusedRenderer
    assert render.renderer_for(tl) is FusedRenderer
    r = FusedRenderer(tl, {}, {})
    f = [r.frame(i) for i in range(6)]
    assert f[0][420:1500].max() > 120                                  # the glowing serif on black
    cap = f[2][420 + 1000:420 + 1035]                                  # caption under the card (y 1017)
    assert cap.max() > 200
    assert f[3][100].max() == 0                                        # inv step on a white (swapped) card:
                                                                       # the bars follow the step -> black
    assert f[5][100].max() == 254 and abs(int(f[5][960, 540, 2]) - 245) < 12   # fill step, bars kept
    r2 = FusedRenderer(tl, {}, {})
    assert np.array_equal(r2.frame(3), f[3]) and np.array_equal(r2.frame(0), f[0])   # pure in i


def test_fused_examples_are_valid():
    for name in ("fused_chorus_mefedron.json", "fused_verse_zvonit.json"):
        raw = json.loads((KIT / "examples" / name).read_text(encoding="utf-8"))
        tl = timeline.resolve(raw, KIT / "examples")
        assert tl["fused"]["_steps"] and tl["fused"]["serif"]["lines"]
        assert json.loads(timeline.dumps(raw)) == raw


def test_planner_reads_the_users_lyric_file(tmp_path):
    from lib.card_strobe.tools import plan
    p = tmp_path / "w.json"
    p.write_text(json.dumps({"name": "x", "words": [{"row": 1, "start": 2.0, "end": 2.4, "text": "люблю "},
                                                    {"row": 0, "start": 1.0, "end": 1.2, "text": "Я"}]}))
    ws = plan.load_words(p)
    assert [(w["line"], w["word"]) for w in ws] == [(0, "Я"), (1, "люблю")]
