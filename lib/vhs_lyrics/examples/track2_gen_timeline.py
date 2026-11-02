"""Builds timeline.json for track2 from word onsets (seconds, aligned on the vocal stem).

Audio starts at O seconds of the TikTok sound (dead intro trimmed); frame = round((t-O)*fps)+1.
Scenes follow skills/creative/vhs-kinetic-lyrics.md: rhyme couplets = scenes in wave 1,
one line = one scene in the caps climax (wave 2).
"""
import json
from pathlib import Path

O, FPS, FRAMES = 1.37, 30, 819

# Backgrounds: assets/bg/scene<N>.mp4. To swap one, replace the file (any size/aspect — it is
# cover-cropped) and set its start second here. Brightness is auto-graded to LOOK on every build.
BG = {  # scene: (start second in the clip, what was used originally)
    "G1": (2.0, "vibe/av03 river by day"), "G2": (1.0, "vibe/av10 sea waves"),
    "G3": (1.0, "vibe/av09 kittens"), "G4": (1.5, "vibe/av13 wind in trees"),
    "G5": (1.0, "vibe/av01 fog, street lamp"), "G6": (2.0, "vibe/av12 white cat alone"),
    "G7": (3.0, "vibe/av00 rainy street"), "G8": (1.0, "vibe/av11 snowstorm road"),
    "G9": (5.4, "vibe/av07 train leaving"),
}
# per-scene target: median / p95 luma (0-255), saturation, tint
LOOK = {
    "G1": (24, 95, 0.55, ""), "G2": (20, 85, 0.7, "colorbalance=bs=0.10:bm=0.05"),
    "G3": (26, 100, 0.6, ""), "G4": (19, 90, 0.6, "colorbalance=bs=0.08"),
    "G5": (32, 110, 0.7, ""), "G6": (22, 90, 0.6, "colorbalance=bs=0.06"),
    "G7": (17, 80, 0.6, "colorbalance=bs=0.10"), "G8": (27, 95, 0.5, "colorbalance=bs=0.12:rs=-0.04"),
    "G9": (22, 90, 0.6, ""),
}


def f(t):
    return round((t - O) * FPS) + 1


def bg(key):
    med, p95, sat, tint = LOOK[key]
    return {"src": f"assets/bg/scene{key[1:]}.mp4", "offset": BG[key][0],
            "look": {"median": med, "p95": p95, "sat": sat, "tint": tint}}


def grow(words, **kw):
    acc, states = [], []
    for w, t in words:
        acc.append(w)
        states.append([" ".join(acc), f(t)])
    return dict(grow=states, **kw)


def stretch(states, word, vowel, t0, n, step=6):
    """melisma: one more vowel every `step` frames after the word lands"""
    base = states[-1][0]
    for k in range(1, n + 1):
        states.append([base.replace(word, word.replace(vowel, vowel * (k + 1), 1)), f(t0) + k * step])
    return states


def T(text, t, **kw):
    return dict(text=text, at=f(t), **kw)


S = []

# S1 — pen lettering opener, wind punch (skewed, cold)
S1_hit = f(5.44)
S.append(dict(start=0, end=f(6.20), bg=bg("G1"), items=[
    T("ЛЕТОМ", 1.62, until=S1_hit, style="hand", box=[8, 47, 14, 32], track=0.15),
    T("СОЛНЦЕ", 2.32, until=S1_hit, style="hand", box=[52, 93, 14, 32], track=0.12),
    T("ЯРЧЕ", 2.58, until=S1_hit, style="hand", box=[12, 44, 36, 54], track=0.18),
    T("СВЕТИТ", 3.20, until=S1_hit, style="hand", box=[50, 90, 36, 54], track=0.15),
    grow([("КАК", 3.86), ("ЖЕ КРУТО", 4.20), ("КОГДА", 4.74)], until=S1_hit,
         style="condb", box=[26, 74, 62, 71]),
    T("ВЕТЕР", 5.44, style="rough", box=[6, 94, 24, 76], color="lblue", skew=-6),
]))

# S2 — sea breeze line (cold subtitle) -> wall -> red name punch
S.append(dict(start=f(6.20), end=f(10.81), bg=bg("G2"), items=[
    grow([("ОБДУВАЕТ", 6.20), ("МОРСКОЙ", 7.02), ("БРИЗ", 7.76)], style="cond", box=[18, 82, 10, 21], color="lblue"),
    T("НО", 8.40, style="cond", box=[5, 13, 29, 45]),
    T("ВСЕМ", 8.60, style="cond", box=[15, 37, 29, 45]),
    T("ПОХУЙ", 8.89, style="grunge", box=[40, 95, 26, 48], amp=5),
    T("ЕСЛИ", 9.31, style="cond", box=[30, 50, 50, 58]),
    T("ТЫ", 9.59, style="cond", box=[52, 62, 50, 58]),
    T("ИЛЬГИЗ", 9.79, style="grunge", box=[5, 95, 60, 97], color="red"),
]))

# S3 — second name as secondary red hit, pink "ball" punch
S.append(dict(start=f(10.81), end=f(15.25), bg=bg("G3"), items=[
    grow([("ИЛИ", 10.81), ("ТЕБЯ", 11.13), ("ВСЕ", 11.47), ("ЗОВУТ", 11.71)], style="cond", box=[26, 74, 14, 24]),
    T("ВАДИК", 12.27, style="grunge", box=[22, 78, 27, 52], color="red"),
    grow([("С ТОБОЙ", 12.90), ("НЕ БУДУТ", 13.57), ("ИГРАТЬ В", 14.03)], style="cond", box=[20, 80, 56, 64]),
    T("МЯЧИК", 14.67, style="grunge", box=[12, 88, 67, 98], color="pink"),
]))

# S4 — tiny subtitle with melisma stretch -> drum break: dim + big-shadow red punch
s4_grow = grow([("ВРЯД", 15.25), ("ЛИ", 15.51), ("С ТОБОЙ", 15.71), ("БУДУТ", 16.13), ("ДРУЖИТЬ", 16.56)],
               until=f(17.55), style="cond", box=[22, 78, 46, 52])
s4_grow["grow"] = stretch(s4_grow["grow"], "ДРУЖИТЬ", "И", 16.56, 4)
S4_hit = f(18.60)
S.append(dict(start=f(15.25), end=f(19.63), bg=bg("G4"),
              dim={"from": S4_hit - 1, "opacity": 0.35}, items=[
    s4_grow,
    T("ТАКИХ", 17.55, style="cond", box=[8, 40, 8, 26]),
    T("КАК", 17.86, style="cond", box=[44, 62, 8, 26]),
    T("ТЫ", 18.18, style="cond", box=[66, 82, 8, 26]),
    T("БУДУТ", 18.42, style="cond", box=[32, 68, 30, 42]),
    T("ГНОБИТЬ", 18.60, style="grunge", box=[3, 97, 46, 97], color="red", shadow="big"),
]))

# S5 — wave 2 reset: pen lettering, torn punch
S.append(dict(start=f(19.63), end=f(21.87), bg=bg("G5"), items=[
    T("ТВОЯ", 19.63, style="hand", box=[8, 44, 5, 25], track=0.15),
    T("МАТЬ", 19.96, style="hand", box=[52, 90, 5, 25], track=0.15),
    T("ШЛЮХА", 20.21, style="torn", box=[3, 97, 28, 74], color="tornred", shadow="mid"),
    T("ТЫ", 20.77, style="cond", box=[28, 38, 78, 93], shadow="mid"),
    T("ЕЕ", 20.96, style="cond", box=[41, 51, 78, 93], shadow="mid"),
    T("СЫН", 21.34, style="condb", box=[54, 69, 78, 93], shadow="mid"),
]))

# S6 — wall of the school line, cleared for a lonely blue "один"
S6_hit = f(23.61)
S.append(dict(start=f(21.87), end=f(24.20), bg=bg("G6"), items=[
    T("ТЕБЯ", 21.87, until=S6_hit, style="cond", box=[5, 38, 8, 26], shadow="mid"),
    T("БИЛИ", 22.17, until=S6_hit, style="grunge", box=[42, 95, 4, 32], color="red", shadow="mid"),
    T("В ШКОЛЕ", 22.49, until=S6_hit, style="cond", box=[5, 52, 34, 48], shadow="mid"),
    T("ТЫ", 23.13, until=S6_hit, style="cond", box=[5, 17, 52, 66], shadow="mid"),
    T("СИДЕЛ", 23.24, until=S6_hit, style="cond", box=[20, 52, 52, 66], shadow="mid"),
    T("ОДИН", 23.61, style="condb", box=[16, 84, 28, 72], color="blue", shadow="mid"),
]))

# S7 — lowercase setup, sung-out glitch punch bridging into the cut
S.append(dict(start=f(24.20), end=f(25.88), bg=bg("G7"), items=[
    grow([("твой", 24.20), ("папа", 24.50)], style="roboto", box=[30, 70, 13, 26], shadow="mid"),
    T("ДОЛБОЕБ", 24.76, style="robotom", box=[6, 94, 33, 69], fx="glitch"),
]))

# S8/S9 — the same line twice: identical design, new background (the train leaves)
def leave(t_sk, t_ot, t_vas, t_ud, start, end, key):
    return dict(start=start, end=end, bg=bg(key), items=[
        grow([("СКОРО", t_sk), ("ОТ", t_ot), ("ВАС", t_vas)], style="cond", box=[27, 73, 14, 28], shadow="mid"),
        T("УЙДЕТ", t_ud, style="grunge", box=[5, 95, 36, 92], color="red", shadow="mid"),
    ])


S.append(leave(25.88, 26.33, 26.49, 26.77, f(25.88), f(27.21), "G8"))
S.append(leave(27.21, 27.52, 27.70, 27.91, f(27.21), FRAMES, "G9"))

tl = {
    "title": "track2 — VHS lyrics",
    "fps": FPS, "width": 1440, "height": 1080, "frames": FRAMES,
    "audio": {"src": "assets/audio/original.m4a", "offset": O, "fade_out": 0.3},
    "effects": {"lens": True, "frame_holds": True, "vhs_wave": True, "veil": True, "dirt": True,
                "scanlines": 0.05, "vignette": 0.45},
    "scenes": S,
}
Path(__file__).with_name("timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
for sc in S:
    print(sc["start"], sc["end"], sc["end"] - sc["start"], sc["bg"]["src"])
