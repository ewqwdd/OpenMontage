// Post grade for a finished edit (ffmpeg only, the audio stream is copied untouched).
//   node tools/grade.mjs <in.mp4> <out.mp4> <look> <edit> [strength]         full video
//   node tools/grade.mjs <in.mp4> <out.jpg> <look> <edit> [strength] still   one row of sample frames (look development)
// Looks: ice   steel-teal night, neutral whites, hard contrast; cuts melt through a gaussian blur
//        halo  violet neon, wide anamorphic streaks, chromatic fringes, grain; cuts whip sideways
//        dream blue night, reds to magenta, mist, light trails; cuts punch in with a flash
// strength 0..1 (default 1) mixes the look over the source; cut effects always stay full.
// The approved finish is `ice 0.5` on the cold accent.
// Cut frames come from productions/cuts.json (written by `node tools/shot.mjs <edit> cuts`) or --cuts=118,168,225.
import { spawnSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const pos = process.argv.slice(2).filter(a => !a.startsWith("--"));
const flag = k => (process.argv.find(a => a.startsWith(`--${k}=`)) || "").split("=")[1];
const [src, out, look, edit, ...more] = pos;
const still = more.includes("still");
const strength = more.map(Number).find(x => x > 0 && x <= 1) ?? 1;
const cutsFile = resolve(root, "productions/cuts.json");
const CUTS = flag("cuts") ? flag("cuts").split(",").map(Number) : existsSync(cutsFile) ? JSON.parse(readFileSync(cutsFile, "utf8"))[edit.replace(/-(warm|cold)$/, "")] : null;
const near = w => CUTS.map(c => `between(n,${c - w},${c + w})`).join("+");          // timeline: within w frames of a cut
const pulse = w => CUTS.map(c => `max(0,1-abs(n-${c})/${w})`).join("+");              // 0..1 triangle on every cut

const LOOKS = {
  ice: {
    grade: "hue=h=-7,colorbalance=rs=-0.22:gs=0.02:bs=0.15:rm=-0.11:gm=0.01:bm=0.08:rh=-0.07:gh=0.01:bh=0.05," +
      "curves=all='0/0 0.22/0.15 0.5/0.5 0.78/0.87 1/1',vibrance=intensity=0.5:rbal=1.2,eq=saturation=1.05",
    glow: "curves=all='0/0 0.62/0 1/1',gblur=sigma=22", glowMode: "screen", glowOp: 0.45,
    cut: () => `gblur=sigma=4:enable='${near(5)}',gblur=sigma=9:enable='${near(3)}',gblur=sigma=16:enable='${near(1)}'`,
    finish: "vignette=a=PI/5,noise=alls=6:allf=t",
  },
  halo: {
    grade: "rgbashift=rh=-3:bh=3,hue=h=-10,colorbalance=rs=0.08:gs=-0.1:bs=0.24:rm=0.02:gm=-0.07:bm=0.13:rh=-0.02:gh=-0.03:bh=0.06," +
      "curves=all='0/0.03 0.25/0.2 0.5/0.5 0.8/0.87 1/0.99',eq=saturation=1.28:contrast=1.05",
    glow: "curves=all='0/0 0.6/0 1/1',gblur=sigma=80:sigmaV=2.5,colorchannelmixer=rr=0.75:gg=0.45:bb=1.4", glowMode: "screen", glowOp: 0.85,
    cut: () => `gblur=sigma=14:sigmaV=0.6:enable='${near(4)}',gblur=sigma=34:sigmaV=0.6:enable='${near(2)}',rgbashift=rh=-16:bh=16:enable='${near(2)}'`,
    finish: "vignette=a=PI/4,noise=alls=13:allf=t",
  },
  dream: {
    grade: "hue=h=-20,colorbalance=rs=0.04:gs=-0.05:bs=0.18:rm=-0.02:gm=-0.02:bm=0.08:rh=-0.08:gh=0.02:bh=0.07," +
      "curves=all='0/0 0.25/0.2 0.5/0.52 0.75/0.84 1/1',vibrance=intensity=0.6,eq=saturation=1.12:gamma=0.96",
    glow: "gblur=sigma=16", glowMode: "lighten", glowOp: 0.6, trails: 0.84,
    cut: () => `scale=w='2*trunc(540*(1+0.07*(${pulse(7)})))':h='2*trunc(960*(1+0.07*(${pulse(7)})))':eval=frame:flags=bilinear,crop=1080:1920,setsar=1,` +
      `gblur=sigma=6:enable='${near(3)}',gblur=sigma=14:enable='${near(1)}',eq=brightness='0.16*(${pulse(5)})':eval=frame`,
    finish: "vignette=a=PI/4.6,noise=alls=7:allf=t",
  },
};
const L = LOOKS[look];
if (!src || !out || !L || !edit) { console.error("usage: grade.mjs <in.mp4> <out> <ice|halo|dream> <edit> [strength 0..1] [still] [--cuts=a,b,c]"); process.exit(1); }
if (!still && !CUTS) { console.error(`No cut frames for "${edit}". Run: node tools/shot.mjs ${edit} cuts   (or pass --cuts=...)`); process.exit(1); }

let samples = "";
if (still) {                             // seven frames spread over the edit
  const n = +spawnSync("ffprobe", ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", src], { encoding: "utf8" }).stdout.trim();
  samples = [0.09, 0.22, 0.34, 0.47, 0.6, 0.74, 0.9].map(k => `eq(n,${Math.round(n * k)})`).join("+");
}
// every blend input is forced to gbrp: a branch that silently changes pixel format tints the whole frame
let g = `[0:v]${still ? `select='${samples}',` : ""}format=gbrp,split[o][x];[x]${L.grade},format=gbrp,split[a][b];[b]${L.glow},format=gbrp[gl];[a][gl]blend=all_mode=${L.glowMode}:all_opacity=${L.glowOp}[m]`;
let last = "m";
if (L.trails && !still) { g += `;[m]format=gbrp,split[t1][t2];[t2]lagfun=decay=${L.trails},format=gbrp[lag];[t1][lag]blend=all_mode=lighten:all_opacity=0.45[tr]`; last = "tr"; }
g += `;[${last}]${L.finish},format=gbrp[gr];[gr][o]blend=all_mode=normal:all_opacity=${strength}[mix];[mix]${still ? "" : L.cut() + ","}format=yuv420p${still ? ",scale=360:640:flags=lanczos,tile=7x1" : ""}[v]`;
const args = ["-v", "error", "-y", "-i", src, "-filter_complex", g, "-map", "[v]"];
if (still) args.push("-frames:v", "1", "-q:v", "3", out);
else args.push("-map", "0:a", "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", flag("crf") || "17", "-maxrate", flag("maxrate") || "18M", "-bufsize", "36M", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out);
const r = spawnSync("ffmpeg", args, { stdio: "inherit" });
console.log(r.status === 0 ? `ok ${out} (${look} ${strength})` : "FAILED " + out); process.exit(r.status || 0);
