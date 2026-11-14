// Forced-alignment output + the lyrics as they should appear on screen -> productions/words.final.json
//
//   node tools/words_from_fa.mjs --fa analysis/words.json --display analysis/lyrics_display.txt \
//        --offset 11 --edits '{"chorus":[0,1,2,3],"verse":[4,5,6,7]}' \
//        --audio assets/audio/master.wav --label "ARTIST // EDIT"
//
// --fa       words.json written by `lib.vhs_lyrics.tools.audio align` ([{line, word, start, end, score}])
// --display  the same lines with the spelling, case and punctuation to show; word counts must match per line
// --offset   seconds to add to FA times to get track time (the start of the excerpt that was aligned)
// --edits    which lyric lines make each edit; the edit name becomes the scene-set name
// Edit window: starts PRE s before its first word, ends TAIL s after its last word. Check both against
// the neighbouring words by ear / on the spectrogram and adjust "start"/"frames" in the JSON by hand.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
const root = fileURLToPath(new URL("../", import.meta.url));
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i < 0 ? d : process.argv[i + 1]; };
const FPS = +arg("fps", 60), PRE = +arg("pre", 0.15), TAIL = +arg("tail", 0.05), offset = +arg("offset", 0);
const fa = JSON.parse(readFileSync(resolve(root, arg("fa", "analysis/words.json")), "utf8"));
const display = readFileSync(resolve(root, arg("display", "analysis/lyrics_display.txt")), "utf8").split(/\r?\n/).map(l => l.trim()).filter(Boolean).map(l => l.split(/\s+/));
const edits = JSON.parse(arg("edits"));
const out = { note: "Track time (s). Forced alignment on the vocal stem; verify on analysis/plots before rendering.", fps: FPS, lead: 1,
  label: arg("label", "EDIT"), audio: arg("audio", "assets/audio/master.wav"), edits: {}, words: [] };
for (const [name, lines] of Object.entries(edits)) {
  const ws = [];
  for (const li of lines) {
    const a = fa.filter(w => w.line === li), d = display[li];
    if (!d || a.length !== d.length) throw new Error(`Line ${li}: ${a.length} aligned words vs ${d ? d.length : 0} display words.`);
    a.forEach((w, i) => {
      if (w.score < 0.05) console.warn(`  check: line ${li} "${d[i]}" score ${w.score} (${(w.start + offset).toFixed(2)}s)`);
      ws.push({ edit: name, line: li, text: d[i], start: +(w.start + offset).toFixed(3), end: +(w.end + offset).toFixed(3) });
    });
  }
  const start = Math.max(0, +(ws[0].start - PRE).toFixed(2));
  out.edits[name] = { start, frames: Math.ceil((ws.at(-1).end + TAIL - start) * FPS) };
  out.words.push(...ws);
  console.log(`${name}: ${ws.length} words, ${start}s + ${out.edits[name].frames}f`);
}
mkdirSync(resolve(root, "productions"), { recursive: true });
writeFileSync(resolve(root, "productions/words.final.json"), JSON.stringify(out, null, 1).replace(/\{\n\s+"edit"/g, '{"edit"').replace(/,\n\s+"(line|text|start|end)"/g, ',"$1"').replace(/\n\s+\}(,?)\n/g, "}$1\n"));
