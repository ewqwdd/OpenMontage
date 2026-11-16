import { sealVisualTrack } from "@hypit/composition";
import { htmlVisual } from "@hypit/html-program";
import type { Timeline } from "@hypit/timeline";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalWindowFor } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
import { FONTS, IMAGES, SETUP } from "./generated.js";

export type Word = { id: string; text: string; at: TemporalInstant };
export type EditOptions = { id: string; variant: string; accent: "warm" | "cold" };

/**
 * One pixel-game edit: the illustrated scenes, their camera, word events, lyrics and the crush filter are one
 * frame-addressed canvas scene. Every sung word arrives as a resolved Instant; the design is fixed in client/.
 */
export function renderEdit(timeline: Timeline, within: SpatialFrame, window: TemporalWindow,
  words: readonly Word[], options: EditOptions) {
  assertTemporalWindowFor(window, { subjectId: options.id, timeline });
  const start = window.span.startFrame, total = window.span.endFrameExclusive - start;
  if (words.some(word => word.at.frame < start || word.at.frame >= window.span.endFrameExclusive)) {
    throw new Error("Every Word must be sung inside the Edit's window.");
  }
  const fps = timeline.frameRate.numerator / timeline.frameRate.denominator;
  const program = htmlVisual({
    // the pictures travel inside the program; the page's readiness check settles them before any frame is captured
    html: `<div class="imgs">${Object.entries(IMAGES).map(([name, uri]) => `<img data-img="${name}" src="${uri}">`).join("")}</div>`,
    css: ".imgs{position:absolute;left:0;top:0;width:1px;height:1px;overflow:hidden;opacity:0}",
    data: { fps, total, variant: options.variant, accent: options.accent, fonts: FONTS, words: words.map(word => ({ t: word.text, f: word.at.frame - start })) },
    setup: SETUP,
  });
  return sealVisualTrack({ id: options.id, timelineId: timeline.id, visualIr: "hypit.visual-ir@1",
    presents: [{ id: options.id, order: 0, z: 0, span: window.span,
      elements: [{ id: "edit", kind: "program", order: 0, program,
        style: [{ name: "position", value: "absolute" }, { name: "left", value: `${within.xPx}px` },
          { name: "top", value: `${within.yPx}px` },
          { name: "width", value: `${within.widthPx}px` }, { name: "height", value: `${within.heightPx}px` }] }] }] });
}
