"""Draw the hero and the scenes with Google Gemini image (PAID: about $0.039 per picture).

    python tools/gen_img.py <spec.json> --budget 1.5

spec = [{"name", "prompt", "aspect" ("9:16" | "1:1"), "refs": [project-relative pictures]}]
Writes assets/gen/<name>.png, skips names that already exist, appends every call to assets/gen/_log.jsonl.
--budget is the user's spending cap in USD for the whole project: the run stops before the logged total would pass it.
Never run this before the user has said yes to the amount. The key is GOOGLE_API_KEY in the repo .env and its
Google project must have billing enabled (the free tier quota for image models is 0 -> HTTP 429).
"""
import argparse, json, os, sys, time
from pathlib import Path

PRICE = 0.039
MODEL = "gemini-2.5-flash-image"
ROOT = Path(__file__).resolve().parents[3]          # repo root: projects/<id>/tools/gen_img.py
PROJ = Path(__file__).resolve().parents[1]


def spent(log: Path) -> float:
    if not log.exists():
        return 0.0
    rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    return sum((r.get("cost") or 0) for r in rows if r.get("ok"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--budget", type=float, required=True, help="spending cap in USD agreed with the user")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).resolve().read_text(encoding="utf-8"))
    out = PROJ / "assets" / "gen"; out.mkdir(parents=True, exist_ok=True); log = out / "_log.jsonl"
    sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
    try:
        from dotenv import load_dotenv; load_dotenv(ROOT / ".env")
    except Exception:
        pass
    from tools.tool_registry import registry
    registry.discover()
    tool = registry._tools["google_imagen"]
    for s in spec:
        dst = out / f"{s['name']}.png"
        if dst.exists():
            print("skip", s["name"]); continue
        if spent(log) + PRICE > args.budget + 1e-9:
            print(f"STOP: ${spent(log):.3f} spent, the next picture would pass the ${args.budget} budget"); break
        inp = {"prompt": s["prompt"], "aspect_ratio": s.get("aspect", "9:16"), "model": MODEL, "output_path": str(dst)}
        refs = [str(PROJ / r) for r in s.get("refs", [])]
        if refs:
            inp["generation_mode"] = "edit"; inp["image_paths"] = refs
        t = time.time(); r = tool.execute(inp)
        rec = {"name": s["name"], "ok": r.success, "cost": getattr(r, "cost_usd", None), "sec": round(time.time() - t, 1), "err": r.error}
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(rec)
    print(f"total spent: ${spent(log):.3f} of ${args.budget}")


if __name__ == "__main__":
    main()
