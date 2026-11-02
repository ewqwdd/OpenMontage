"""Text styles, palette and shadows of the VHS kinetic-lyrics look.

Every preset was measured on the reference edit (projects/tupaya-tvar-remake). Colours are
*base* values: the render (baked scanlines, overlays) lands them ~8% darker, i.e. on the
values measured on the reference.
"""
from pathlib import Path

KIT = Path(__file__).parent
FONT_DIRS = [KIT / "assets" / "fonts", Path("C:/Windows/Fonts")]

PALETTE = {
    "white": (255, 255, 255),
    "red": (222, 28, 34),        # main aggressive red
    "darkred": (190, 25, 30),    # brush "ТЫ УМРЕШЬ!"
    "hotred": (243, 32, 41),     # thin clean red
    "tornred": (230, 25, 28),    # giant torn letter
    "pink": (205, 20, 70),       # trailing word in a red line ("СЗАДИ")
    "blue": (5, 158, 254),       # light caption blue
    "lblue": (0, 150, 254),      # light blue big words
    "dblue": (0, 54, 155),       # deep blue giant letter
    "green": (6, 100, 17),       # camo / army word
}

# style -> font file, variable-font instance, letter spacing (em), edge mode, edge amplitude (px)
#   edge modes: none | spiky (hair fringe) | torn (paper tear + holes) | wobble (brush)
STYLES = {
    "hand":    dict(font="BadScript-Regular.ttf", var=None, track=0.0, edge="none", amp=0),
    "grunge":  dict(font="impact.ttf", var=None, track=0.0, edge="spiky", amp=9),
    "torn":    dict(font="impact.ttf", var=None, track=0.0, edge="torn", amp=7),
    "clean":   dict(font="impact.ttf", var=None, track=0.0, edge="none", amp=0),
    "rough":   dict(font="Oswald.ttf", var=b"Bold", track=0.0, edge="wobble", amp=3),
    "cond":    dict(font="Oswald.ttf", var=b"SemiBold", track=0.0, edge="none", amp=0),
    "condb":   dict(font="Oswald.ttf", var=b"Bold", track=0.0, edge="none", amp=0),
    "thin":    dict(font="Oswald.ttf", var=b"Light", track=0.02, edge="none", amp=0),
    "brush":   dict(font="Oswald.ttf", var=b"Regular", track=0.02, edge="wobble", amp=2.5),
    "roboto":  dict(font="RobotoCondensed.ttf", var=b"Bold", track=0.0, edge="none", amp=0),
    "robotom": dict(font="RobotoCondensed.ttf", var=b"Medium", track=0.0, edge="none", amp=0),
}

SHADOWS = {
    None: "",
    "none": "",
    # heavy soft shadow pushed down — reads as "the screen darkens under the word"
    "mid": "drop-shadow(0 8px 10px rgba(0,0,0,.85)) drop-shadow(0 22px 60px rgba(0,0,0,.95))",
    "big": "drop-shadow(0 12px 16px rgba(0,0,0,.9)) drop-shadow(0 45px 120px rgba(0,0,0,1))",
}


def font_path(name):
    for d in FONT_DIRS:
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(f"font {name} not found in {FONT_DIRS}")


def color(c):
    return tuple(PALETTE[c]) if isinstance(c, str) else tuple(c)
