// Dev capture of the preview page (dev/index.html). Starts its own static server on the project root, so nothing else has to run.
//   node tools/shot.mjs <edit> <out.jpg> frames=0-430-10 [cols=8] [cell=250] [accent=warm]   contact sheet (cell px wide)
//   node tools/shot.mjs <edit> <out.png> f=120 [accent=warm]                                 one full 1080x1920 frame
//   node tools/shot.mjs <edit> cuts                                                          write the edit's cut frames to productions/cuts.json (tools/grade.mjs reads them)
import puppeteer from "puppeteer-core";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { extname, join, normalize, resolve } from "node:path";
import { homedir } from "node:os";

const root = fileURLToPath(new URL("../", import.meta.url));
const [edit, out, ...rest] = process.argv.slice(2);
if (!edit || !out) { console.error("usage: shot.mjs <edit> <out.png|out.jpg|cuts> [frames=a-b-step | f=N] [cols=] [cell=] [accent=]"); process.exit(1); }
const o = Object.fromEntries(rest.map(a => a.split("=")));

function chrome() {                     // the headless shell Hypit installed (hypit programs prepare), newest version
  if (process.env.PIXEL_CHROME) return process.env.PIXEL_CHROME;
  const base = join(homedir(), ".cache/puppeteer/chrome-headless-shell");
  const v = existsSync(base) ? readdirSync(base).sort().at(-1) : null;
  if (!v) throw new Error("No chrome-headless-shell in ~/.cache/puppeteer. Run `hypit programs prepare --endpoint html.local` or set PIXEL_CHROME.");
  const dir = join(base, v, readdirSync(join(base, v))[0]);
  return join(dir, process.platform === "win32" ? "chrome-headless-shell.exe" : "chrome-headless-shell");
}
const MIME = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".jpg": "image/jpeg", ".png": "image/png", ".woff2": "font/woff2", ".wav": "audio/wav" };
const server = createServer(async (req, res) => {
  const p = normalize(join(root, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!p.startsWith(normalize(root))) { res.writeHead(403); return res.end(); }
  try { const b = await readFile(p); res.writeHead(200, { "content-type": MIME[extname(p)] || "application/octet-stream" }); res.end(b); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}/dev/index.html?edit=${edit}${o.accent ? "&accent=" + o.accent : ""}`;
const b = await puppeteer.launch({ executablePath: chrome(), args: ["--no-sandbox"] });
const p = await b.newPage();
p.on("pageerror", e => console.log("PAGEERROR", e.message));
p.on("console", m => { if (m.type() === "error" && !/404/.test(m.text())) console.log("CONSOLE", m.text()); });
try {
  if (out === "cuts") {
    await p.goto(`${base}&f=0&scale=.2`);
    await p.waitForFunction(() => typeof window.go === "function", { timeout: 60000 });
    const cuts = await p.evaluate(() => window.cuts), file = resolve(root, "productions/cuts.json");
    const all = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {}; all[edit] = cuts;
    writeFileSync(file, JSON.stringify(all) + "\n"); console.log(edit, "cuts", cuts.join(","));
  } else if (o.frames) {
    const cols = +(o.cols || 6), cell = +(o.cell || 270);
    const n = o.frames.includes("-") ? (() => { const [a, z, s] = o.frames.split("-").map(Number); return Math.floor((z - a) / (s || 1)) + 1; })() : o.frames.split(",").length;
    await p.setViewport({ width: cols * (cell + 3), height: Math.ceil(n / cols) * (Math.round(cell * 16 / 9) + 3) });
    await p.goto(`${base}&sheet=${o.frames}&cols=${cols}&cell=${cell}`);
    await p.waitForFunction(() => document.title === "sheet ready", { timeout: 180000 });
    writeFileSync(out, await p.screenshot({ type: out.endsWith(".jpg") ? "jpeg" : "png", quality: out.endsWith(".jpg") ? 88 : undefined })); console.log("ok", out);
  } else {
    await p.setViewport({ width: 1080, height: 1920 });
    await p.goto(`${base}&f=${o.f || 0}&scale=1`);
    await p.waitForFunction(() => typeof window.go === "function", { timeout: 60000 });
    await p.evaluate(() => { document.getElementById("ui").remove(); });
    writeFileSync(out, await p.screenshot({ type: "png" })); console.log("ok", out);
  }
} finally { await b.close(); server.close(); }
