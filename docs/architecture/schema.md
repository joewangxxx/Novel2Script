# Architecture Schema Notes

This document records Novel2Script data contracts that are shared across phases.
After a contract is frozen, FE, BE, QA, or tooling changes must not silently edit
the schema. Any contract change must be proposed under
`docs/architecture/change-requests/` and reviewed by the architecture owner.

## Phase 2 Screenplay YAML

Phase 2 uses `schemas/screenplay.schema.json` for the screenplay YAML contract.
Its `source_trace` points screenplay scenes, beats, and elements back to source
chapter and paragraph ranges. Phase 3 keeps the same traceability principle but
uses stable chapter and paragraph IDs so downstream phases can reference parser
output without relying on numeric ranges alone.

## Phase 3 Story Map

`story_map` is the Phase 3 intermediate representation produced from Markdown or
TXT novel input. It is not a screenplay, not an outline, and not an LLM analysis
record. It is a deterministic, inspectable map of chapters, paragraphs, detected
entities, events, chronology hints, psychological passages, and parser
uncertainties.

The schema file is `schemas/story_map.schema.json`. The initial contract version
is `0.1.0`.

```yaml
story_map:
  schema_version: "0.1.0"
  source:
    type: "novel"
    input_file: "examples/input/sample_novel_3_chapters.md"
    chapter_count: 3
    trace_unit: "chapter_paragraph"
  chapters:
    - id: "ch_001"
      index: 1
      title: "雾里的钟声"
      source_heading: "## 第一章：雾里的钟声"
      paragraphs:
        - id: "p_001"
          index: 1
          text_preview: "海边小镇连续三晚起雾。"
  characters_detected: []
  locations_detected: []
  props_detected: []
  key_events: []
  timeline: []
  psychological_passages: []
  uncertainties: []
```

### Shared Source Trace

All detected facts or hints that come from source text should use the same trace
shape:

```yaml
source_trace:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  quote_preview: "可选的短原文片段"
  note: "可选说明"
```

Rules:

- `chapter_id` must match a chapter in `story_map.chapters`.
- `paragraph_ids` must match paragraph IDs inside that chapter.
- Paragraph IDs are unique within a chapter; consumers must read them together
  with `chapter_id`.
- `quote_preview` is optional and must stay short. The full uploaded novel text
  should not be copied into public repository artifacts.
- `note` explains why the trace supports the detected item; it is not a place
  for new story facts.

## Story Map Fields

`source` describes the input file and parser trace granularity. `type` is fixed
to `novel`; `trace_unit` is fixed to `chapter_paragraph` in this contract.
Optional `parser_profile` and `content_hash` may be added by future parser
implementations without changing the core meaning.

`chapters` preserves document order. Each chapter has a stable `ch_###` ID,
1-based `index`, normalized `title`, original `source_heading`, and paragraph
list. Paragraph entries use `p_###` IDs within their chapter and keep only a
short `text_preview`, not the full paragraph body.

`characters_detected` records names that the parser can identify from explicit
text cues. It may include aliases, a short description hint, `first_seen`, a
broader `source_trace`, and confidence. It must not invent full biographies,
relationships, or motivations.

`locations_detected` records places or setting labels that appear in the text.
It may include a loose `location_type` such as `town`, `building`, or `room`.
It must not normalize locations into production-ready scene headings.

`props_detected` records objects with possible story relevance, such as letters,
recorders, weapons, keys, or documents. The parser should prefer recurring or
action-bearing objects and avoid listing every noun.

`key_events` records explicit plot actions or state changes in source order.
Each event can link detected characters, locations, and props by ID. Event
summaries must stay close to the source text and avoid adaptation decisions.

`timeline` records ordering and time expressions that are explicit or strongly
implied by surface text, such as "第二天傍晚" or "七年前". It may link to event
IDs. It is not a full chronology solver.

`psychological_passages` marks interiority, memory, fear, desire, motivation, or
emotion that may later require externalization in screenplay form. The optional
`externalization_hint` may describe a possible adaptation consideration, but
must be marked as a hint and must not become generated screenplay action.

`uncertainties` records ambiguity or parser limitations that should block silent
assumptions. Examples include unclear pronoun references, ambiguous speakers,
implicit causality, ambiguous time, or chapter heading detection issues.

## Heuristic Boundary

Phase 3 parser implementation must be bounded to heuristic parsing until a later
phase explicitly approves model integration:

- Markdown headings and TXT heading patterns can define chapters.
- Blank lines can define paragraphs.
- Name, place, prop, time, and event candidates can be extracted with rules,
  dictionaries, punctuation cues, repetition, and simple pattern matching.
- The parser may report low-confidence candidates and uncertainties.
- The parser must not infer hidden motives, relationships, themes, worldbuilding,
  or scene structure that is not supported by source text.
- The parser must not call LLM APIs in Phase 3A.
- The parser must not emit screenplay `scenes`, `beats`, or `elements`.

## Contract Governance

The Phase 3A contract is a draft until explicitly frozen. Once frozen:

- FE, BE, QA, and parser implementation work must treat
  `schemas/story_map.schema.json` and this document as source of truth.
- Schema or API conflicts must become architecture change requests under
  `docs/architecture/change-requests/`.
- FE, BE, or QA retry counts above the blackboard limit stop the workflow and
  require human intervention.

## Phase 4 Outline And Character Bible

Phase 4 consumes `story_map` and produces two draft planning artifacts:

- `schemas/outline.schema.json`
- `schemas/character_bible.schema.json`

These contracts are not frozen in Phase 4A. They define what later Stage 4B
implementation should emit, but they do not authorize generator code, LLM
integration, screenplay generation, Agent review, or parser changes.

### Shared Stage 4 Source Trace

Stage 4 keeps the Stage 3 chapter/paragraph trace shape and may additionally
reference Stage 3 event IDs:

```yaml
source_trace:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  event_ids: ["evt_001"]
  quote_preview: "short source excerpt"
  note: "why this supports the field"
```

Rules:

- `chapter_id` and `paragraph_ids` remain required.
- `event_ids` should be used when a field is derived from
  `story_map.key_events`.
- Multi-location evidence must be represented as an array of source traces.
- Full source paragraphs should not be copied into Stage 4 artifacts.

### Outline Fields

`outline` is a planning layer, not screenplay YAML. It includes:

- `logline`: a one-sentence adaptation premise with source evidence and
  `ai_tags`.
- `theme_candidates`: possible themes with rationale, trace, and confidence.
- `act_structure`: high-level act grouping and source-supported summaries.
- `scene_plan`: planned scene units for later generation. These are not final
  `scenes`, `beats`, or `elements`.
- `source_coverage`: coverage accounting from `story_map.key_events` to planned
  scene/event usage.
- `uncertainties`: weak evidence, scene merge risks, timeline ambiguity, or
  adaptation decisions requiring human review.

### Character Bible Fields

`character_bible` is the character planning layer keyed to
`story_map.characters_detected[].id`. Each character profile includes:

- `want`: external pursuit.
- `need`: internal or dramatic need.
- `flaw`: limitation, blind spot, fear, or friction point.
- `relationships`: links to other `char_###` IDs.
- `voice`: speech style summary and future dialogue rules.
- `arc`: start, turning points, and end state.
- `locked`: prevents later generators from silently overwriting accepted facts.
- `source_trace`: evidence for the profile.
- `ai_tags`: inference, confidence, and human-review metadata.

`want`, `need`, `flaw`, `voice`, `arc`, `theme_candidates`, and loglines are
often inferred. Low-confidence or inferred fields must use:

```yaml
ai_tags:
  inferred: true
  confidence: low
  needs_human_review: true
```

If a field cannot be supported by `story_map` evidence, implementations should
emit an uncertainty instead of filling it silently.

### Stage 4 Contract Governance

The Stage 4A contracts remain draft. After any future freeze:

- FE, BE, QA, and generator work must not silently edit
  `schemas/outline.schema.json` or `schemas/character_bible.schema.json`.
- Contract conflicts must be proposed under
  `docs/architecture/change-requests/`.
- Stage 4 generators must not bypass `source_trace` or `ai_tags` requirements
  for convenience.

## Phase 5 Structured Screenplay Generation

Phase 5 consumes `story_map`, `outline`, and `character_bible` to define a
deterministic mapping into the existing `schemas/screenplay.schema.json`
contract. Phase 5A does not implement a generator and does not change the
screenplay schema.

### Screenplay Schema Fit

The current screenplay schema is sufficient for the Stage 5 first draft:

- `characters` can carry character bible IDs, names, roles, `source_trace`,
  optional `ai_tags`, and optional `locked` values.
- `scenes` can carry outline scene candidates as screenplay scene records with
  headings, locations, times, beats, and elements.
- `beats` already require objective, tactic, obstacle, conflict, stakes, turn,
  externalized action, `source_trace`, and `ai_tags`.
- `elements` already support `action`, `dialogue`, `parenthetical`,
  `transition`, and `note`.

Stage 5 should not widen the schema unless implementation proves a real
contract gap. If the screenplay contract is frozen before that point, changes
must be proposed under `docs/architecture/change-requests/`.

### Stage 5 Source Trace Bridge

The screenplay schema currently requires numeric source traces:

```yaml
source_trace:
  chapter: 1
  paragraph_range: [1, 2]
  note: "derived from outline scene osp_001 and key_event evt_001"
```

Stage 3 and Stage 4 use stable source IDs. Stage 5 generators must convert ID
traces to numeric traces for schema compatibility and should preserve the
original stable IDs in an additional `source_trace_ids` field:

```yaml
source_trace_ids:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  event_ids: ["evt_001"]
  outline_scene_ids: ["osp_001"]
```

### Stage 5 Mapping Summary

- `outline.scene_plan[]` maps to `scenes[]`.
- `outline.scene_plan[].source_event_ids` and related `story_map.key_events[]`
  map to scene source traces, beat fields, and action or note elements.
- `character_bible.characters[]` maps to screenplay `characters[]`; locked
  profiles must not be silently changed.
- `story_map.locations_detected[]` and `story_map.timeline[]` may fill scene
  `location` and `time` when evidence is explicit.
- `story_map.psychological_passages[]` may inform
  `beats[].externalized_action`, but only as a reviewable adaptation hint.
- Low-confidence upstream fields must keep or escalate `ai_tags` in downstream
  beats and elements.

Stage 5 first drafts should prefer source-grounded `action` and `note`
elements. Full dialogue generation remains out of scope unless the dialogue is
explicitly present in source text or clearly marked as low-confidence
adaptation.

## Phase 6 Multi-Agent Review

Phase 6 consumes the generated screenplay and upstream Stage 3/4 planning
artifacts to produce a review report. The report is an advisory artifact only:
it records issues, evidence, suggestions, and patch proposals, but it must not
overwrite `screenplay.yaml` or any user draft.

The schema file is `schemas/review_report.schema.json`. The initial contract
version is `0.1.0`.

```yaml
review_report:
  schema_version: "0.1.0"
  source_screenplay: "examples/output/generated_screenplay.yaml"
  source_artifacts:
    story_map: "examples/output/generated_story_map.yaml"
    outline: "examples/output/generated_outline.yaml"
    character_bible: "examples/output/generated_character_bible.yaml"
  generated_at: "2026-06-05"
  review_profile: "deterministic_review_contract_v0"
  reviewers:
    - "character_consistency"
    - "pacing"
    - "dialogue_naturalness"
    - "shootability"
  summary:
    total_issues: 0
    by_severity:
      low: 0
      medium: 0
      high: 0
    blocking: false
  issues: []
```

### Review Issue Contract

Each issue targets exactly one screenplay, scene, beat, element, or character
record. The issue must include severity, confidence, evidence, suggestion, and a
suggested patch object:

```yaml
id: "issue_001"
reviewer: "shootability"
target_id: "beat_001"
target:
  type: "beat"
  id: "beat_001"
  yaml_path: "scenes[0].beats[0]"
severity: "medium"
confidence: "high"
issue: "The beat contains an internal state without a visible action."
evidence:
  description: "The beat turn is supported by source trace, but action is vague."
  source_trace:
    chapter: 1
    paragraph_range: [1, 1]
  source_trace_ids:
    chapter_id: "ch_001"
    paragraph_ids: ["p_001"]
    event_ids: ["evt_001"]
    outline_scene_ids: ["osp_001"]
suggestion: "Replace the internal-state wording with visible behavior."
suggested_patch:
  operation: "replace"
  yaml_path: "scenes[0].beats[0].externalized_action"
  value: "She closes the envelope and hides it under the lamp."
requires_human_approval: true
```

`target_id` duplicates `target.id` for filtering and must match it. Evidence may
carry the Stage 5 numeric `source_trace`, the Stage 3/4 stable
`source_trace_ids`, or both. If a reviewer cannot attach a source trace, it must
still provide a concrete `evidence.description`.

Allowed patch operations are `replace`, `add`, and `note_only`. Suggested
patches are never applied by reviewers. A later approval flow may accept or
reject them, but Stage 6 itself must treat every patchable change as requiring
human approval.

### Reviewer Set

The Stage 6A deterministic reviewer set is:

- `character_consistency`: checks character ID validity, character bible
  alignment, locked field consistency, and unsupported character introductions.
- `pacing`: checks scene order, beat presence, source event coverage, turn and
  stakes availability, and fixed-threshold density risks.
- `dialogue_naturalness`: checks dialogue element validity, empty or excessive
  dialogue, repeated lines, and low-confidence dialogue tags. It may produce no
  issues when a deterministic draft contains no dialogue.
- `shootability`: checks scene/beat traceability, visible externalized action,
  shootable action elements, and unresolved internal psychological passages.

These reviewers are bounded to deterministic YAML traversal, fixed thresholds,
keyword checks, and cross-reference checks. They must not call LLMs, perform
external HTTP requests, rewrite the screenplay, or make broad creative
judgments.

### Stage 6 Contract Governance

The Stage 6A contract remains draft. After a future freeze:

- FE, BE, QA, and reviewer implementations must not silently edit
  `schemas/review_report.schema.json`.
- Contract conflicts must be proposed under
  `docs/architecture/change-requests/`.
- Reviewers may emit only advisory patch suggestions; direct screenplay writes
  require a separate human-approved application flow.

## Phase 7 Fountain Limited Roundtrip

Phase 7 defines a limited Fountain import/sync contract. It lets users edit an
already exported Fountain file and sync only safe, mapped text fields back into
screenplay YAML. It is not a full Fountain parser and cannot create screenplay
YAML from arbitrary Fountain.

The report schema file is `schemas/fountain_roundtrip_report.schema.json`. The
initial contract version is `0.1.0`.

### Existing Fountain Map

The current Fountain export sidecar has this shape:

```json
{
  "source_yaml": "examples/output/generated_screenplay.yaml",
  "fountain_file": "examples/output/generated_screenplay.fountain",
  "mappings": [
    {
      "line_start": 5,
      "line_end": 5,
      "scene_id": "scene_001",
      "beat_id": null,
      "element_index": null,
      "yaml_path": "scenes[0].heading"
    }
  ]
}
```

`mappings[]` is the authority for limited import. The importer may consider only
mapped ranges whose `yaml_path` targets one of these safe fields:

- `scenes[i].heading`
- `scenes[i].elements[j].text`

The importer must not modify source traces, beats, characters,
`adaptation_policy`, or existing factual `ai_tags` values.

### Roundtrip Report

Every import attempt must produce a report:

```yaml
fountain_roundtrip_report:
  schema_version: "0.1.0"
  source_yaml: "examples/output/generated_screenplay.yaml"
  fountain_file: "examples/output/generated_screenplay.fountain"
  map_file: "examples/output/generated_screenplay.fountain.map.json"
  generated_at: "2026-06-05"
  status: "blocked"
  summary:
    mapped_regions: 12
    changed_regions: 0
    applied_changes: 0
    skipped_changes: 0
    blocking_issues: 1
  line_policy:
    expected_line_count: 22
    actual_line_count: 23
    line_drift_detected: true
    map_match: false
  changes: []
  issues:
    - id: "rt_issue_001"
      severity: "high"
      code: "line_drift"
      message: "Fountain line count changed from baseline export."
      action: "blocked"
```

When safe text changes are applied, the importer may add
`metadata.semantic_fields_stale: true` and a `metadata.roundtrip` record because
the screenplay schema permits additional metadata fields. That metadata marks
beat semantics as potentially stale; it does not authorize updating beat fields.

### Drift Policy

Line drift, scene or element insertion/deletion, map mismatch, ordering changes,
or unsafe paths must stop the global import or skip the affected range with a
report issue. Implementations must not guess a repair. Dialogue, parenthetical,
transition, and action normalization is limited to the mapped element text
rules documented in `docs/dev/PHASE_7_FOUNTAIN_LIMITED_ROUNDTRIP.md`.
