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
