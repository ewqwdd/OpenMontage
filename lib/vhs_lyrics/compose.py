"""HyperFrames composition: background, veil flicker, scene dims, words, scanlines, dirt, vignette.

Layer order (bottom -> top): bg video, black veil (stepped bg flicker), scene dims, words,
screen scanlines, dirt (overlay), vignette. CRT lens, frame holds and VHS wave come later
in post.py.
"""
import json
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .lens import make_remap
from .raster import raster_word
from .styles import KIT, SHADOWS
from .timeline import sec, words

# ПЛАВАТЬ-style glitch, frame by frame from its first frame: (frame offset, opacity, mode)
GLITCH_STEPS = [(0, .1, "blur"), (2, 1, ""), (4, .55, "blur"), (5, .12, ""), (6, 1, "clip"),
                (7, .5, ""), (8, .12, ""), (9, 1, ""), (12, .12, ""), (14, 1, ""), (15, 0, "")]
GLITCH_REPEAT = [(0, .12, ""), (1, 1, "clip"), (2, 1, "")]  # burst every 12 frames on long words
GLITCH_OFFSETS = (-13, 0, 11)  # px of the R / G / B copies

DIRT_N, DW, DH = 8, 720, 540


def dirt_sprite(path):
    """K grey-128-centred textures (blotches, specks, scratches, blocks) stacked vertically,
    used with mix-blend overlay; the mean offset per tile gives the brightness shimmer."""
    rng = np.random.default_rng(11)
    sprite = Image.new("L", (DW, DH * DIRT_N))
    for k in range(DIRT_N):
        n = Image.fromarray((rng.random((DH, DW)) * 255).astype(np.uint8))
        blot = np.asarray(n.filter(ImageFilter.GaussianBlur(rng.uniform(12, 20))), np.float32)
        blot = (blot - blot.mean()) / (blot.std() + 1e-6)
        t = 128 + blot * 128 * 0.08 + rng.uniform(-0.03, 0.03) * 128
        blocks = rng.normal(0, 1, (DH // 8 + 1, DW // 8 + 1)).repeat(8, 0).repeat(8, 1)[:DH, :DW]
        t += blocks * 128 * 0.02
        img = Image.fromarray(t.clip(0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for _ in range(rng.integers(5, 16)):
            x, y, r = rng.uniform(0, DW), rng.uniform(0, DH), rng.uniform(0.6, 1.6)
            d.ellipse([x - r, y - r, x + r, y + r], fill=int(128 * 0.55))
        for _ in range(rng.integers(0, 3)):
            x = rng.uniform(0, DW)
            v = int(128 * (1 + rng.choice([-0.1, 0.1])))
            d.line([(x, rng.uniform(0, DH * .4)), (x + rng.uniform(-3, 3), rng.uniform(DH * .6, DH))], fill=v)
        sprite.paste(img, (0, k * DH))
    sprite.save(path)


def build(tl, ws):
    """Write ws/index.html + ws/assets/{txt,dirt.png,gsap.min.js}; returns no-hold frame list."""
    W, H, FPS = tl["width"], tl["height"], tl["fps"]
    DUR = sec(tl["frames"], FPS)
    fx = {"veil": True, "dirt": True, "scanlines": 0.05, "vignette": 0.45, **tl.get("effects", {})}
    assets = ws / "assets"
    txt = assets / "txt"
    txt.mkdir(parents=True, exist_ok=True)
    for old in txt.glob("*.png"):
        old.unlink()
    shutil.copy(KIT / "assets" / "gsap.min.js", assets / "gsap.min.js")
    dirt_sprite(assets / "dirt.png")
    remap = make_remap(W, H, tl.get("lens_k1", 0.17), tl.get("lens_zoom", 1.17))
    f = lambda n: sec(n, FPS)  # noqa: E731

    els = words(tl)
    css, html, js, glitch_frames = [], [], [], set()
    for i, e in enumerate(els):
        names, left, top, w, h = raster_word(e, i, txt, W, H, remap)
        skew = f"skewX({e['skew']}deg)" if e.get("skew") else "none"
        css.append(f"#w{i}{{left:{left:.1f}px;top:{top:.1f}px;width:{w}px;height:{h}px;}}")
        if e.get("fx") == "glitch":
            imgs = "".join(f'<img src="assets/txt/{nm}" alt="" style="left:{dx}px">'
                           for nm, dx in zip(names, GLITCH_OFFSETS))
            css.append(f"#i{i}{{filter:blur(calc(1.5px + var(--gb,0px)));}}"
                       f"#i{i} img{{position:absolute;top:0;mix-blend-mode:screen;}}")
            steps = GLITCH_STEPS
            if e["f1"] - e["f0"] > GLITCH_STEPS[-1][0]:  # longer than the reference word: stay on, re-glitch
                steps = GLITCH_STEPS[:-1] + [(k + d, op, mode) for k in range(24, e["f1"] - e["f0"] - 2, 12)
                                             for d, op, mode in GLITCH_REPEAT]
            for k, op, mode in steps:
                clip = "inset(0 48% 0 0)" if mode == "clip" else "inset(0 0% 0 0)"
                blur = "2.5px" if mode == "blur" else "0px"
                js.append(f'tl.set("#i{i}",{{opacity:{op},clipPath:"{clip}","--gb":"{blur}"}},{f(e["f0"] + k)});')
            glitch_frames |= set(range(e["f0"], e["f1"] + 1))
        else:
            imgs = f'<img src="assets/txt/{names[0]}" alt="{e["text"]}">'
            css.append(f"#i{i}{{transform:{skew};filter:brightness(var(--tb,1)) {SHADOWS[e.get('shadow')]};}}")
        html.append(f'<div id="w{i}" class="clip word" data-start="{e["t0"]}" '
                    f'data-duration="{round(e["t1"] - e["t0"], 3)}" data-track-index="{20 + i}">'
                    f'<div id="i{i}" class="inner">{imgs}</div></div>')

    # scene dims: e.g. the backdrop drops 35% before a big hit
    dims = []
    for k, sc in enumerate(tl["scenes"]):
        if sc.get("dim"):
            d0, op = sc["dim"]["from"], sc["dim"].get("opacity", 0.35)
            dims.append(f'<div id="dim{k}" class="clip dim" style="opacity:{op}" data-start="{f(d0)}" '
                        f'data-duration="{round(f(sc["end"]) - f(d0), 3)}" data-track-index="3"></div>')

    # text almost steady (0.97–1.0); background flickers in steps through a black veil
    rng = np.random.default_rng(3)
    fl, fr = [], 0
    while fr < tl["frames"]:
        tb = rng.choice([0.97, 1.0], p=[.4, .6])
        veil = rng.choice([0.0, 0.08, 0.15, 0.0], p=[.35, .3, .2, .15])
        fl.append(f'tl.set("#root",{{"--tb":{tb}}},{f(fr)});')
        if fx["veil"]:
            fl.append(f'tl.set("#veil",{{opacity:{veil}}},{f(fr)});')
        fr += int(rng.choice([1, 2, 3], p=[.35, .4, .25]))
    # dirt: new pattern every frame, held on every 4th frame
    rng = np.random.default_rng(9)
    pat, dirt = 0, []
    for fr in range(tl["frames"]):
        if fr % 4 != 3:
            pat = int(rng.integers(0, DIRT_N))
        if fx["dirt"]:
            dirt.append(f'tl.set("#dirt",{{backgroundPositionY:"{-pat * H}px"}},{f(fr)});')

    page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{tl.get("title", "VHS lyrics")}</title>
<script src="assets/gsap.min.js"></script>
<style>
body{{margin:0;background:#000;}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#000;--tb:1;}}
#bg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;}}
#veil,.dim{{position:absolute;inset:0;background:#000;pointer-events:none;}}
#veil{{opacity:0;}}
.word{{position:absolute;}}
.inner{{position:relative;width:100%;height:100%;}}
.inner img{{display:block;width:100%;height:100%;}}
#scan{{position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(to bottom,rgba(0,0,0,{fx["scanlines"]}) 0 4px,transparent 4px 8px);}}
#dirt{{position:absolute;inset:0;pointer-events:none;mix-blend-mode:overlay;
  background:url(assets/dirt.png) 0 0/{W}px {H * DIRT_N}px no-repeat;{"" if fx["dirt"] else "display:none;"}}}
#vig{{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse at center,transparent 50%,rgba(0,0,0,{fx["vignette"]}) 100%);}}
{chr(10).join(css)}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-width="{W}" data-height="{H}" data-duration="{DUR}" data-fps="{FPS}" data-layout-allow-overflow>
<video id="bg" src="assets/bg.mp4" data-start="0" data-duration="{DUR}" data-track-index="0" muted playsinline></video>
<audio id="music" src="assets/audio.m4a" data-start="0" data-duration="{DUR}" data-track-index="1" data-volume="1"></audio>
<div id="veil" class="clip" data-start="0" data-duration="{DUR}" data-track-index="2"></div>
{chr(10).join(dims)}
{chr(10).join(html)}
<div id="scan" class="clip" data-start="0" data-duration="{DUR}" data-track-index="4"></div>
<div id="dirt" class="clip" data-start="0" data-duration="{DUR}" data-track-index="5"></div>
<div id="vig" class="clip" data-start="0" data-duration="{DUR}" data-track-index="6"></div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(fl)}
{chr(10).join(dirt)}
{chr(10).join(js)}
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
    (ws / "index.html").write_text(page, encoding="utf-8")
    noholds = sorted({e["f0"] for e in els} | glitch_frames | {sc["start"] for sc in tl["scenes"]})
    (assets / "noholds.json").write_text(json.dumps(noholds))
    print(f"compose: {len(els)} word clips, {len(dims)} dims, {len(noholds)} no-hold frames")
    return noholds
