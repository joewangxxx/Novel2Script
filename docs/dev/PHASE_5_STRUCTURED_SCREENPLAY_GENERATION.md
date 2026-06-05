# Phase 5: Structured Screenplay Generation Contract

Phase 5 consumes the Stage 3 `story_map`, Stage 4 `outline`, and Stage 4
`character_bible` and defines how a later deterministic generator should create
a first-pass `screenplay.yaml` that validates against
`schemas/screenplay.schema.json`.

Phase 5A was architecture only. Phase 5B added the deterministic builder, and
Phase 5C connects it to CLI generation plus Stage 2 validation/export
regression. The phase still does not call an LLM, write a final shootable
script, run Agent review, perform Fountain round-trip editing, or add UI/API
behavior.

## Goal

Stage 5 turns the planning layer into a structured screenplay draft made of
Scene, Beat, and Element records. The output should be valid enough for the
existing validator and Fountain exporter, while remaining honest about weak
inference and preserving traceability back to the parsed novel.

## Input Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_outline.yaml`
- `examples/output/generated_character_bible.yaml`
- `schemas/story_map.schema.json`
- `schemas/outline.schema.json`
- `schemas/character_bible.schema.json`
- `schemas/screenplay.schema.json`

The generator must treat all three input artifacts as source evidence. If the
inputs disagree, the order of authority is:

1. `story_map` for source structure, detected facts, and source traces.
2. `character_bible` for character IDs, names, locked fields, and review flags.
3. `outline` for scene order, scene purpose, act grouping, and coverage intent.

## Schema Fit Review

`schemas/screenplay.schema.json` is sufficient for the Stage 5 first draft and
does not need to change in Phase 5A.

Existing fields already cover the required output:

- root `metadata`, `source`, `adaptation_policy`, `characters`, and `scenes`.
- `characters[]` with IDs, names, roles, and `source_trace`.
- `scenes[]` with heading, location, time, `source_trace`, `beats`, and
  `elements`.
- `beats[]` with objective, tactic, obstacle, conflict, stakes, turn,
  `externalized_action`, `source_trace`, and `ai_tags`.
- `elements[]` with type, text, optional `character_id`, `source_trace`, and
  `ai_tags`.

The schema currently uses numeric screenplay `source_trace` fields:

```yaml
source_trace:
  chapter: 1
  paragraph_range: [1, 2]
  note: "why this scene, beat, or element maps to the source"
```

Stage 3 and Stage 4 use stable ID traces:

```yaml
source_trace:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  event_ids: ["evt_001"]
  quote_preview: "short source excerpt"
  note: "why this supports the field"
```

For Stage 5, generated screenplay records must include the schema-required
numeric trace and should also preserve the stable upstream trace in an
additional field named `source_trace_ids`. This is allowed by the draft
screenplay schema because relevant objects permit additional properties.

```yaml
source_trace:
  chapter: 1
  paragraph_range: [1, 1]
  note: "derived from outline scene osp_001 and key_event evt_001"
source_trace_ids:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  event_ids: ["evt_001"]
  outline_scene_ids: ["osp_001"]
```

If `schemas/screenplay.schema.json` is frozen before implementation, any change
to these trace fields must go through
`docs/architecture/change-requests/`.

## Output Shape

The later Stage 5 generator should output:

```yaml
schema_version: "0.1.0"
metadata:
  title: ""
  language: "zh-CN"
  created_by: "Novel2Script stage-five deterministic generator"
  created_at: "2026-06-05"
source:
  type: "novel"
  chapter_count: 3
  trace_unit: "chapter_paragraph"
adaptation_policy:
  target_format: "short_screenplay"
  allow_inference: true
  preserve_source_order: true
characters: []
scenes: []
```

The generator must produce at least one scene when `outline.scene_plan` contains
at least one planned scene.

## Field Mapping

### Root Metadata

- `schema_version`: fixed to the current screenplay schema version used by the
  repository, currently `"0.1.0"`.
- `metadata.title`: derive from story input filename, outline logline context,
  or a neutral fallback such as `"Untitled Adaptation"`. If inferred, add a
  root-level optional `ai_tags` only if the implementation later adds root
  metadata tags; otherwise record title uncertainty in a note element.
- `metadata.language`: default to `"zh-CN"` unless a later explicit language
  detector is approved.
- `metadata.created_by`: deterministic generator label.
- `metadata.created_at`: local date string from generation time.

### Source

- `source.type`: copy from `story_map.source.type`, expected `"novel"`.
- `source.chapter_count`: copy from `story_map.source.chapter_count`.
- `source.trace_unit`: copy from `story_map.source.trace_unit`.
- Optional fields may include upstream artifact paths such as
  `story_map_file`, `outline_file`, and `character_bible_file`.

### Adaptation Policy

- `target_format`: default `"short_screenplay"` for the current sample pipeline.
- `allow_inference`: `true`, because beats and elements require adaptation
  decisions even when deterministic.
- `preserve_source_order`: `true`, because `outline.scene_plan.order` follows
  key event order.
- Optional fields may include `generator_profile` and
  `source_trace_strategy: "numeric_plus_ids"`.

### Characters

Build `characters[]` from `character_bible.characters[]`, not directly from
`story_map.characters_detected[]`, so `locked`, review flags, and character
planning evidence remain available to generation.

Mapping:

- `id`: copy `character_bible.characters[].id`.
- `name`: copy `character_bible.characters[].name`.
- `role`: use a conservative role string only when explicit evidence exists.
  If no role is explicit, use an empty string or omit the field.
- `source_trace`: convert the first or broadest character bible trace to numeric
  screenplay trace.
- `source_trace_ids`: preserve the original character bible trace.
- Optional `ai_tags`: copy profile-level `ai_tags`.
- Optional `locked`: copy `locked` so later tools know whether edits are allowed.

Locked character fields must not be overwritten by Stage 5 generation. If a
locked field conflicts with outline needs, create an uncertainty or note element
instead of changing the character profile.

### Scenes

Build `scenes[]` primarily from `outline.scene_plan[]`.

Mapping:

- `id`: deterministic `scene_###` by `outline.scene_plan.order`.
- `heading`: deterministic placeholder, not final prose. Recommended format:
  `INT./EXT. LOCATION - TIME` when location/time evidence exists, otherwise
  `INT./EXT. UNKNOWN - TIME UNKNOWN`.
- `location`: map `scene_plan.location_ids[0]` through
  `story_map.locations_detected[]`; fallback `""`.
- `time`: map the matching `story_map.timeline[]` item when its `event_ids`
  overlap `scene_plan.source_event_ids`; fallback `""`.
- `source_trace`: convert the scene plan trace to numeric screenplay trace.
- `source_trace_ids`: preserve chapter IDs, paragraph IDs, event IDs, and
  `outline_scene_ids`.
- `beats`: generate one or more deterministic beats for the scene boundary.
- `elements`: generate source-grounded action or note elements.

Scene merging is allowed only when multiple `outline.scene_plan[]` items share
the same chapter, location, and adjacent order. If merged, the scene must keep
all source event IDs and all upstream scene IDs in `source_trace_ids`.

### Beats

Each scene must have at least one beat. A deterministic Stage 5 generator should
start with one beat per scene candidate unless the outline explicitly requests
multiple beats.

Beat boundaries:

- `objective`: derive from the primary character's visible action or scene
  purpose. If unclear, use a reviewable placeholder such as
  `"Clarify the scene objective from source evidence."`
- `tactic`: derive from visible action in the source event, not hidden motive.
- `obstacle`: derive from explicit opposition, ambiguity, danger, missing
  information, or uncertainty.
- `conflict`: use a conservative statement of tension between objective and
  obstacle.
- `stakes`: derive from explicit danger or story consequence; otherwise mark
  as low confidence.
- `turn`: derive from the event summary or state change.
- `externalized_action`: prefer
  `story_map.psychological_passages[].externalization_hint` when linked to the
  same paragraph; otherwise summarize visible action.
- `source_trace`: numeric trace converted from the linked scene/event trace.
- `source_trace_ids`: preserve upstream trace IDs.
- `ai_tags`: required. Use `inferred: true` for any field not directly copied
  from source evidence.

Beat text must not invent relationship facts, backstory, hidden motivation, or
theme resolution that is absent from the inputs.

### Elements

Elements are the only records exported to Fountain by the current exporter.
Stage 5 first draft should keep them conservative.

Allowed element generation in Stage 5B:

- `action`: source-grounded visible action derived from `key_events`,
  paragraph previews, or `externalized_action`.
- `note`: review note for uncertainties, weak inference, locked character
  conflicts, missing location, missing time, or dialogue gaps.

Dialogue policy:

- Do not generate full dialogue from prose by default.
- A `dialogue` element is allowed only when the source already contains explicit
  quoted speech or the implementation marks it with low-confidence `ai_tags`
  and a review note.
- Do not generate `parenthetical` except to preserve explicit source intent.
- Use `transition` only for deterministic act or sequence boundaries if later
  implementation needs it; otherwise omit.

Every element must include:

- `type`
- `text`
- `source_trace`
- `source_trace_ids`
- `ai_tags`

## Source Trace Conversion

The generator must be able to convert Stage 3/4 traces to the current
screenplay numeric trace.

Conversion rules:

1. Resolve `chapter_id` to `story_map.chapters[].index`.
2. Resolve each `paragraph_id` within that chapter to the matching paragraph
   `index`.
3. `paragraph_range` is `[min(indexes), max(indexes)]`.
4. If evidence spans multiple chapters, split the generated output into
   multiple scenes or choose the primary scene trace and preserve all evidence
   in `source_trace_ids`.
5. Preserve `event_ids`, `outline_scene_ids`, and optional `quote_preview` in
   `source_trace_ids` or adjacent notes, not in the schema-required numeric
   trace.

## AI Tags Inheritance

`ai_tags` must be inherited or escalated, never silently dropped.

- Direct source facts copied from `story_map.key_events` can use
  `inferred: false`, `confidence: high`, and `needs_human_review: false`.
- Any field derived from `outline.logline`, `theme_candidates`,
  `act_structure`, `scene_plan.purpose`, or character bible `want`, `need`,
  `flaw`, `voice`, or `arc` should use `inferred: true`.
- If any upstream evidence has `confidence: low`, the generated beat or element
  must be `confidence: low` unless stronger direct source evidence exists.
- If any upstream field has `needs_human_review: true`, downstream generated
  records should also require review.
- If a character profile is `locked: true`, generator output may reference it
  but must not alter it.

## Generation Boundaries

Stage 5 is a structured draft generator, not a complete screenwriter.

Allowed:

- Deterministic scene creation from outline scene candidates.
- Conservative headings from detected locations and timeline hints.
- One or more beats per scene with required fields populated.
- Source-grounded action elements.
- Note elements for missing evidence, weak inference, or review needs.
- Trace and coverage metadata to help QA verify preservation of source material.

Not allowed:

- LLM calls.
- Full dialogue invention.
- Complete character psychology inference.
- Untraceable scene additions.
- Silent deletion of `outline.source_coverage.covered_event_ids`.
- Silent edits to schema contracts after freeze.
- Fountain round-trip editing.
- UI/API work.

## Stage 5 File Plan

Stage 5B implementation files:

- `src/novel2script/generators/__init__.py`
- `src/novel2script/generators/screenplay_builder.py`
- `tests/test_screenplay_builder.py`

Stage 5C CLI and sample files:

- `tests/test_screenplay_cli.py`
- `examples/output/generated_screenplay.yaml`
- `examples/output/generated_screenplay_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`
- `src/novel2script/cli.py` command `build-screenplay`.

The generated screenplay sample is deterministic scaffolding. It is intended for
schema validation, source-trace checks, and Fountain export smoke testing, not
as a polished screenplay.

## Run The CLI

Regenerate the upstream Stage 3 and Stage 4 artifacts:

```bash
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
```

Build the Stage 5 screenplay YAML:

```bash
python -m novel2script.cli build-screenplay --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_screenplay.yaml
```

Validate and export the generated screenplay through the Stage 2 chain:

```bash
python -m novel2script.cli validate examples/output/generated_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/generated_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
```

`build-screenplay` returns non-zero when any input YAML path is missing. The
shared YAML writer creates output directories automatically.

## Test Plan For Later Implementation

Stage 5B tests verify:

- generated screenplay validates against `schemas/screenplay.schema.json`.
- one outline scene candidate can generate one screenplay scene.
- scene IDs are stable (`scene_001`, `scene_002`, ...).
- every scene has at least one beat and one element.
- every beat has required beat fields, `source_trace`, `source_trace_ids`, and
  `ai_tags`.
- every element has `source_trace`, `source_trace_ids`, and `ai_tags`.
- low-confidence upstream `ai_tags` are preserved or escalated.
- character IDs come from `character_bible.characters[]`.
- locked character profiles are not mutated.
- Stage 2 `validate` and `export-fountain` behavior is not changed.

Stage 5C CLI tests verify:

- `build-screenplay` writes a non-empty YAML file.
- missing input files return non-zero.
- output directories are created automatically.
- existing `parse-novel`, `build-outline`, `build-character-bible`,
  `validate`, and `export-fountain` commands still work.
- generated screenplay YAML can pass the Stage 2 validator and be exported to
  Fountain with a sidecar map.

## Gate Checklist

- Mapping from `story_map`, `outline`, and `character_bible` to screenplay is
  defined.
- Scene, beat, and element boundaries are explicit.
- `source_trace` numeric conversion and `source_trace_ids` preservation are
  defined.
- `ai_tags` inheritance and low-confidence handling are defined.
- Deterministic builder and CLI remain local and reproducible.
- No LLM integration is introduced.
- `schemas/screenplay.schema.json` remains unchanged unless a later architecture
  change request requires it.
