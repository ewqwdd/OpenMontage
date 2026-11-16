import { assertAttributes, assertEmptyElement, createMarkupSurfaceFacet, textAttribute } from "@hypit/hypit/markup";
import { canonicalize, sameType } from "@hypit/hypit/protocol";
import { sealGraphFragment } from "@hypit/hypit/author";
import { createAdmissionPackageFacet } from "@hypit/hypit/admission";
import { createProducerPackageFacet } from "@hypit/hypit/producer";
import type { ProducerPackage } from "@hypit/hypit/producer";
import type { AdmissionPackage } from "@hypit/hypit/admission";
import type { FragmentOperation } from "@hypit/hypit/author";
import type { ModuleManifest, TypeRef } from "@hypit/hypit/protocol";
import type { StructuredSurfaceHandler, SurfaceResolvedReference } from "@hypit/hypit/markup";
import { compositionTypes } from "@hypit/composition";
import type { Timeline } from "@hypit/timeline";
import { timelineTypes } from "@hypit/timeline";
import { spatialTypes } from "@hypit/spatial";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalInstantFor, temporalTypes } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
import { resolveTemporalInstantReference, resolveTemporalWindowReference, resolveTemporalContext,
  temporalContextAttributeVocabulary, temporalInstantAttributeNames, temporalInstantAttributeVocabulary,
  temporalWindowAttributeNames, temporalWindowAttributeVocabulary } from "@hypit/temporal/markup";
import { renderEdit } from "./render.js";
import type { EditOptions, Word } from "./render.js";

const module = { name: "@kit/pixel-lyrics", version: "1" } as const;
const types = Object.fromEntries(["Options", "Word", "Words"].map(name => [name, { module, name }])) as Record<"Options" | "Word" | "Words", TypeRef>;
const producers = Object.fromEntries(["empty", "append", "render"].map(name => [name, { module, name }])) as Record<"empty" | "append" | "render", { module: typeof module; name: string }>;

export const manifest: ModuleManifest = { format: "hypit.module@1", ...module,
  dependencies: [compositionTypes.visualTrack, timelineTypes.timeline, spatialTypes.frame, temporalTypes.instant].map(type => ({ module: type.module })),
  types: Object.values(types).map(type => ({ name: type.name })), capabilities: [], producers: [
    { name: "empty", inputs: [], outputs: [{ name: "words", type: types.Words }], needs: [] },
    { name: "append", inputs: [{ name: "words", type: types.Words }, { name: "word", type: types.Word },
      { name: "at", type: temporalTypes.instant }, { name: "timeline", type: timelineTypes.timeline }], outputs: [{ name: "words", type: types.Words }], needs: [] },
    { name: "render", inputs: [{ name: "words", type: types.Words }, { name: "options", type: types.Options },
      { name: "timeline", type: timelineTypes.timeline }, { name: "within", type: spatialTypes.frame },
      { name: "window", type: temporalTypes.window }],
      outputs: [{ name: "visual", type: compositionTypes.visualTrack }], needs: [] },
  ],
};
const inline = <T>(record: { value: { kind: string; value?: unknown } } | undefined): T => {
  if (record?.value.kind !== "inline") throw new Error("pixel-lyrics inputs must be inline values.");
  return record.value.value as T;
};
const value = (data: unknown) => ({ kind: "inline" as const, value: canonicalize(data) });
const component: ProducerPackage & AdmissionPackage = { producers: [
  { producer: producers.empty, handler: () => ({ outputs: { words: value([]) }, needs: {} }) },
  { producer: producers.append, handler: ({ inputs }) => {
    const word = inline<Omit<Word, "at">>(inputs.word), at = inline<TemporalInstant>(inputs.at);
    const words = inline<Word[]>(inputs.words);
    assertTemporalInstantFor(at, { subjectId: word.id, timeline: inline<Timeline>(inputs.timeline) });
    if ((words.at(-1)?.at.frame ?? -1) > at.frame) throw new Error(`Word "${word.text}" is sung before the previous word; keep Words in sung order.`);
    return { outputs: { words: value([...words, { ...word, at }]) }, needs: {} };
  } },
  { producer: producers.render, handler: ({ inputs }) => ({ outputs: { visual: value(renderEdit(inline<Timeline>(inputs.timeline),
    inline<SpatialFrame>(inputs.within), inline<TemporalWindow>(inputs.window),
    inline<Word[]>(inputs.words), inline<EditOptions>(inputs.options))) }, needs: {} }) },
] };

export const decodeSurface: StructuredSurfaceHandler = ({ element, resolveReference }) => {
  assertAttributes(element, ["id", "timeline", "within", "variant", "accent", ...temporalWindowAttributeNames]);
  const id = textAttribute(element, "id"), context = resolveTemporalContext({ element, resolveReference });
  const window = resolveTemporalWindowReference({ element, resolveReference });
  const reference = (name: string, type: TypeRef): SurfaceResolvedReference => {
    const raw = element.attributes[name];
    if (typeof raw !== "object" || raw.kind !== "reference") throw new Error(`${name} must be a reference.`);
    const found = resolveReference(raw.path);
    if (found === undefined || !sameType(found.type, type)) throw new Error(`${name} has the wrong Type.`);
    return found;
  };
  const variant = textAttribute(element, "variant");
  if (!/^[a-z][a-z0-9_]*$/.test(variant)) throw new Error("Edit variant names a scene-set file: lowercase letters, digits, underscores.");
  const accent = element.attributes.accent === undefined ? "cold" : textAttribute(element, "accent");
  if (accent !== "warm" && accent !== "cold") throw new Error("Edit accent must be warm or cold.");
  const options: EditOptions = { id, variant, accent };
  const records = [{ id: `${id}.options`, type: types.Options, value: value(options), range: element.range }];
  const inputs = [{ name: "timeline", type: timelineTypes.timeline }, { name: "within", type: spatialTypes.frame },
    { name: "window", type: temporalTypes.window }, { name: "options", type: types.Options }];
  const bindings: Record<string, SurfaceResolvedReference["ref"]> = { timeline: context.timeline.ref, within: reference("within", spatialTypes.frame).ref,
    window: window.ref, options: { kind: "record", id: `${id}.options` } };
  const input = (name: string) => ({ kind: "fragment-input" as const, name });
  const operation = (name: string) => ({ kind: "fragment-operation" as const, operation: name });
  const operations: FragmentOperation[] = [{ id: "empty", producer: producers.empty, inputs: {}, result: { kind: "output", name: "words" } }];
  let previous = "empty", index = 0;
  for (const child of element.children) {
    if (child.kind === "text") { if (child.value.trim()) throw new Error("Edit accepts Word children."); continue; }
    if (child.name.split(":").at(-1) !== "Word") throw new Error("Edit accepts Word children.");
    assertAttributes(child, ["id", "text", ...temporalInstantAttributeNames]); assertEmptyElement(child);
    const at = resolveTemporalInstantReference({ element: child, resolveReference });
    const key = `word-${++index}`;
    records.push({ id: `${id}.${key}`, type: types.Word, value: value({ id: textAttribute(child, "id"), text: textAttribute(child, "text") }), range: child.range });
    inputs.push({ name: key, type: types.Word }, { name: `${key}-at`, type: temporalTypes.instant });
    bindings[key] = { kind: "record", id: `${id}.${key}` }; bindings[`${key}-at`] = at.ref;
    operations.push({ id: key, producer: producers.append, inputs: { words: operation(previous), word: input(key), at: input(`${key}-at`), timeline: input("timeline") }, result: { kind: "output", name: "words" } });
    previous = key;
  }
  if (!index) throw new Error("Edit requires its sung Words.");
  operations.push({ id: "render", producer: producers.render, inputs: { words: operation(previous), options: input("options"),
    timeline: input("timeline"), within: input("within"), window: input("window") }, result: { kind: "output", name: "visual" } });
  const fragment = sealGraphFragment({ inputs, operations, exports: [{ name: "visual", type: compositionTypes.visualTrack, root: operation("render") }] });
  return { records, fragments: [fragment], components:
    [{ id, fragment: fragment.id, inputs: bindings, outputs: { visual: `${id}.visual` }, range: element.range }], exports: [`${id}.visual`] };
};
const declaration = { name: "edit", tag: "Edit", mode: "structured" as const,
  outputs: [compositionTypes.visualTrack, ...Object.values(types)],
  vocabulary: { summary: "A dark pixel-game lyric edit: every sung line is one drawn shot of the same hero, crushed by the pixel filter; each Word lands on its own Instant.", attributes: [
    ...temporalContextAttributeVocabulary, ...temporalWindowAttributeVocabulary,
    ...["id", "within"].map(name => ({ name, kind: "expression" as const, required: true, summary: name })),
    { name: "variant", kind: "literal" as const, required: true, summary: "Which scene set to play: the name of client/scenes/<variant>.js." },
    { name: "accent", kind: "literal" as const, required: false, summary: "Accent colour of key words and the HUD: cold (ice blue, default) or warm (orange)." },
  ], children: [{ tag: "Word", cardinality: "many" as const, summary: "One sung word, in sung order, and the Instant it lands on.", attributes: [
    ...["id", "text"].map(name => ({ name, kind: "literal" as const, required: true, summary: name })), ...temporalInstantAttributeVocabulary,
  ] }], ports: [{ name: "visual", type: compositionTypes.visualTrack, summary: "The complete edit picture." }],
    example: '<px:Edit id="edit" timeline={t.timeline} within={canvas.bounds} during={t.window} variant="chorus" accent="cold"><px:Word id="w0" text="Я" at={t.w0}/></px:Edit>',
  },
};
export const hypitPackage = { format: "hypit.package@1" as const, modules: [{ manifest }],
  facets: [createProducerPackageFacet(component), createAdmissionPackageFacet(component),
    createMarkupSurfaceFacet({ module, declaration, handler: decodeSurface })] };
export default hypitPackage;
