import { sealVisualTrack } from "@hypit/composition";
import type { VisualElement } from "@hypit/composition";
import { htmlVisual } from "@hypit/html-program";
import type { FontStackRef } from "@hypit/media";
import type { Timeline } from "@hypit/timeline";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalWindowFor } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
import { CSS, SETUP } from "./generated.js";

export type Word = { id: string; text: string; at: TemporalInstant };
export type EditOptions = { id: string; variant: string; label: string; timecode: number };
export type EditFonts = { ui: FontStackRef; bold: FontStackRef; black: FontStackRef; mono: FontStackRef };

/**
 * One UI-lyric edit: scenes, captions, HUD and transitions are one frame-addressed scene.
 * Every sung word arrives as a resolved Instant; the design itself is fixed in the client code.
 */
export function renderEdit(timeline: Timeline, within: SpatialFrame, window: TemporalWindow,
  fonts: EditFonts, words: readonly Word[], options: EditOptions) {
  assertTemporalWindowFor(window, { subjectId: options.id, timeline });
  const start = window.span.startFrame, total = window.span.endFrameExclusive - start;
  if (words.some(word => word.at.frame < start || word.at.frame >= window.span.endFrameExclusive)) {
    throw new Error("Every Word must be sung inside the Edit's window.");
  }
  const fps = timeline.frameRate.numerator / timeline.frameRate.denominator;
  let order = 0;
  // Hidden probes carry the exact faces into the page; the scene reads their resolved families.
  const probe = (id: string, stack: FontStackRef): VisualElement => ({
    id, kind: "text", parent: "edit", order: ++order, text: "Яя Aa 0123 ₽ ×", fonts: stack.faces,
    style: [{ name: "font-size", value: "20px" }, { name: "line-height", value: 1.2 }, { name: "color", value: "#000000" }],
  });
  const children = [probe("p-ui", fonts.ui), probe("p-bold", fonts.bold), probe("p-black", fonts.black), probe("p-mono", fonts.mono)];
  const program = htmlVisual({
    html: `<div class="probes"><i data-probe="ui">{{p-ui}}</i><i data-probe="bold">{{p-bold}}</i><i data-probe="black">{{p-black}}</i><i data-probe="mono">{{p-mono}}</i></div>`,
    css: CSS,
    data: { fps, total, variant: options.variant, tc0: options.timecode, label: options.label,
      words: words.map(word => ({ t: word.text, f: word.at.frame - start })) },
    setup: SETUP,
  });
  return sealVisualTrack({ id: options.id, timelineId: timeline.id, visualIr: "hypit.visual-ir@1",
    presents: [{ id: options.id, order: 0, z: 0, span: window.span,
      elements: [{ id: "edit", kind: "program", order: 0, program,
        style: [{ name: "position", value: "absolute" }, { name: "left", value: `${within.xPx}px` },
          { name: "top", value: `${within.yPx}px` },
          { name: "width", value: `${within.widthPx}px` }, { name: "height", value: `${within.heightPx}px` }] }, ...children] }] });
}
