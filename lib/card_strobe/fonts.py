"""Font roles of the card-strobe style.

Each role prefers the macOS system face the approved edit was built with. When that file is
missing (Linux, CI, another Mac without it), the bundled open-licence fallback is used instead:

| role     | job                                   | system face (not redistributable)        | bundled fallback (licence)            |
|----------|---------------------------------------|------------------------------------------|---------------------------------------|
| `card`   | giant hero cards (MASTER / ZAE-BAL)   | Impact                                   | Oswald Bold (OFL)                     |
| `pop`    | mid-size pop words, clones, stacks    | Helvetica Neue Condensed Black (ttc #9)  | Oswald Bold (OFL)                     |
| `sub`    | tiny subtitles                        | Helvetica (ttc #0)                       | Arimo Regular (OFL, Helvetica metrics)|
| `blocky` | intro pixel-stencil glyphs            | Menlo Bold (ttc #1)                      | DejaVu Sans Mono Bold (Bitstream Vera)|
| `script` | money / accent words (Доллар, падал)  | -                                        | Bad Script (OFL, always bundled)      |

All five render Cyrillic. The licences are in `assets/fonts/`. A timeline can point a role at any
other file: `"fonts": {"card": "/path/Anton.ttf"}` or `{"pop": ["/path/x.ttc", 3, "Bold"]}`.
The old names of the one-off edit (`impact`, `hcb`, `helv`, `menlo_b`) are accepted as aliases.
"""
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
SF = "/System/Library/Fonts/"

ROLES = {
    "card": [(SF + "Supplemental/Impact.ttf", 0, None), (str(FONT_DIR / "Oswald.ttf"), 0, "Bold")],
    "pop": [(SF + "HelveticaNeue.ttc", 9, None), (str(FONT_DIR / "Oswald.ttf"), 0, "Bold")],
    "sub": [(SF + "Helvetica.ttc", 0, None), (str(FONT_DIR / "Arimo.ttf"), 0, None)],
    "blocky": [(SF + "Menlo.ttc", 1, None), (str(FONT_DIR / "DejaVuSansMono-Bold.ttf"), 0, None)],
    "script": [(str(FONT_DIR / "BadScript-Regular.ttf"), 0, None)],
}
ALIASES = {"impact": "card", "hcb": "pop", "helv": "sub", "menlo_b": "blocky"}
_OVERRIDES = {}


def set_overrides(fonts):
    """{"role": path | [path, index, variation]} from the timeline; clears the caches."""
    _OVERRIDES.clear()
    for role, spec in (fonts or {}).items():
        if isinstance(spec, str):
            spec = [spec, 0, None]
        spec = list(spec) + [0, None][len(spec) - 1:]
        _OVERRIDES[ALIASES.get(role, role)] = (str(Path(spec[0]).expanduser()), int(spec[1]), spec[2])
    resolve.cache_clear()
    font.cache_clear()


@lru_cache(maxsize=None)
def resolve(role):
    """-> (path, index, variation) of the first existing candidate for `role`."""
    role = ALIASES.get(role, role)
    if role in _OVERRIDES:
        return _OVERRIDES[role]
    if role not in ROLES:
        if Path(role).expanduser().exists():          # a plain font path used as a role
            return str(Path(role).expanduser()), 0, None
        raise KeyError(f"unknown font role {role!r} (roles: {', '.join(ROLES)})")
    for cand in ROLES[role]:
        if Path(cand[0]).exists():
            return cand
    raise FileNotFoundError(f"no font file for role {role!r}: {[c[0] for c in ROLES[role]]}")


@lru_cache(maxsize=128)
def font(role, size):
    path, idx, var = resolve(role)
    f = ImageFont.truetype(path, int(round(size)), index=idx)
    if var:
        f.set_variation_by_name(var)
    return f


def report():
    """{role: path actually used}: printed by the renderer so a fallback never goes unnoticed."""
    return {r: resolve(r)[0] for r in ROLES}
