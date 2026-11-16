"""assets/gen/*.png -> packages/pixel-lyrics/client/img/ (768 px wide JPEG is enough: the engine draws on 540x960).

    python tools/prep_img.py

Optional assets/gen/prep.json:
  {"skip":    ["hero_sheet"],                                   pictures that are references only
   "sprites": {"items": ["it_a", "it_b", "it_c", "it_d"]},      a 2x2 icon sheet on a flat dark ground -> four keyed PNG sprites
   "mosaic":  {"flatlay": [[106, 992, 206, 1082]]}}             boxes to pixelate (a real brand name the model drew)
Also writes img/manifest.json for the dev page.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

PROJ = Path(__file__).resolve().parents[1]
SRC = PROJ / "assets" / "gen"
DST = PROJ / "packages" / "pixel-lyrics" / "client" / "img"
KEY = (255, 0, 255)


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((SRC / "prep.json").read_text(encoding="utf-8")) if (SRC / "prep.json").exists() else {}
    skip, sprites, mosaic = set(cfg.get("skip", [])), cfg.get("sprites", {}), cfg.get("mosaic", {})
    for p in sorted(SRC.glob("*.png")):
        if p.stem in skip:
            continue
        im = Image.open(p).convert("RGB")
        if p.stem in sprites:
            w, h = im.size
            for k, name in enumerate(sprites[p.stem]):
                q = im.crop(((k % 2) * w // 2, (k // 2) * h // 2, (k % 2 + 1) * w // 2, (k // 2 + 1) * h // 2)).copy()
                for xy in [(2, 2), (q.width - 3, 2), (2, q.height - 3), (q.width - 3, q.height - 3), (q.width // 2, 2), (q.width // 2, q.height - 3)]:
                    if q.getpixel(xy) != KEY:
                        ImageDraw.floodfill(q, xy, KEY, thresh=46)
                rgba = q.convert("RGBA"); px = rgba.load()
                for y in range(q.height):
                    for x in range(q.width):
                        if px[x, y][:3] == KEY:
                            px[x, y] = (0, 0, 0, 0)
                rgba = rgba.crop(rgba.getbbox()); rgba = rgba.resize((rgba.width // 2, rgba.height // 2), Image.NEAREST)
                rgba.save(DST / f"{name}.png"); print(name, rgba.size)
            continue
        for box in mosaic.get(p.stem, []):
            box = tuple(box); patch = im.crop(box)
            im.paste(patch.resize((max(1, patch.width // 16), max(1, patch.height // 16)), Image.BOX).resize(patch.size, Image.NEAREST), box)
        if im.width > 768:
            im = im.resize((768, round(im.height * 768 / im.width)), Image.LANCZOS)
        im.save(DST / f"{p.stem}.jpg", quality=90, subsampling=0); print(p.stem, im.size)
    (DST / "manifest.json").write_text(json.dumps(sorted(f.name for f in DST.iterdir() if f.suffix in (".jpg", ".png"))), encoding="utf-8")


if __name__ == "__main__":
    main()
