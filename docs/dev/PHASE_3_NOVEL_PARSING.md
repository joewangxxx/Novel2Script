# Phase 3: Deterministic Novel Parsing

Phase 3 parses Markdown or TXT novel text into a structured `story_map`. Phase
3A defined the contract, Phase 3B added a deterministic parser, and Phase 3C
adds CLI access plus a generated sample output. The phase remains bounded to
rule-based parsing. It does not call an LLM, generate a screenplay, modify Phase
2 validator/exporter behavior, add Agent review, or add frontend/backend APIs.

## Goal

The parser should turn source text into a traceable intermediate map that later
phases can use for outlining, character bibles, and screenplay generation. The
map preserves chapter and paragraph anchors first, then layers heuristic
detections on top of those anchors.

## Implemented In Phase 3

- `src/novel2script/parsers/novel_parser.py` exposes
  `parse_novel_text(text, input_file="")`.
- `python -m novel2script.cli parse-novel INPUT --out OUTPUT` writes a
  `story_map` YAML file.
- Markdown and TXT-like chapter headings are split into ordered chapters.
- Paragraphs are split by blank lines.
- Stable chapter IDs use `ch_001`, `ch_002`, and so on.
- Stable paragraph IDs use `p_001`, `p_002`, and so on within each chapter.
- Deterministic heuristics extract basic character, location, prop, event,
  timeline, psychological passage, and uncertainty candidates.
- Key candidates include `source_trace` with `chapter_id` and `paragraph_ids`.

## Run The CLI

```bash
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
```

The output directory is created automatically when it does not exist. Missing or
unreadable input returns a non-zero exit code and does not create the output
file.

Regression commands for existing Phase 2 behavior:

```bash
python -m novel2script.cli validate examples/output/sample_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/sample_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
```

## Supported Chapter Formats

The deterministic parser recognizes these chapter heading shapes:

- `# 第一章 标题`
- `## 第一章 标题`
- `第1章 标题`
- `第一章 标题`
- `Chapter 1`
- `CHAPTER 1`

Markdown document titles that are not chapter headings are ignored for chapter
segmentation. TXT input without recognized headings falls back to one chapter.

## Output Contract

The output root is `story_map`. The schema is
`schemas/story_map.schema.json`, version `0.1.0`.

Required top-level fields:

- `schema_version`: contract version. Phase 3A fixes this to `"0.1.0"`.
- `source`: input metadata with `type`, `input_file`, `chapter_count`, and
  `trace_unit`.
- `chapters`: ordered chapter and paragraph inventory.
- `characters_detected`: explicit or high-surface-signal character candidates.
- `locations_detected`: place candidates.
- `props_detected`: story-relevant object candidates.
- `key_events`: explicit plot actions or state changes.
- `timeline`: source-order time hints and linked event order.
- `psychological_passages`: interiority passages that may later need
  externalization.
- `uncertainties`: ambiguities and parser limitations.

The generated YAML has this root shape:

Minimal shape:

```yaml
story_map:
  schema_version: "0.1.0"
  source:
    type: "novel"
    input_file: ""
    chapter_count: 3
    trace_unit: "chapter_paragraph"
  chapters:
    - id: "ch_001"
      index: 1
      title: ""
      source_heading: ""
      paragraphs:
        - id: "p_001"
          index: 1
          text_preview: ""
  characters_detected: []
  locations_detected: []
  props_detected: []
  key_events: []
  timeline: []
  psychological_passages: []
  uncertainties: []
```

## Source Trace

Phase 3 uses stable chapter and paragraph IDs while preserving the Phase 2
principle that every important derived item points back to source text.

```yaml
source_trace:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  quote_preview: "可选的短原文片段"
  note: "可选说明"
```

`chapter_id` must match `chapters[].id`. `paragraph_ids` must match paragraph
IDs inside that chapter. A trace can point to one or more paragraphs in the same
chapter. If evidence spans multiple chapters, the implementation should create
separate detected items or record an `uncertainties` entry instead of using an
ambiguous trace.

## Field Semantics

### `source`

Describes source type and trace assumptions. `type` is fixed to `novel`.
`trace_unit` is fixed to `chapter_paragraph`. `input_file` should be the user or
workspace path supplied to the parser. `chapter_count` must equal the number of
items in `chapters`.

### `chapters`

Stores document segmentation, not interpretation. Markdown headings such as
`## 第一章：雾里的钟声` should preserve the original text in `source_heading`
and store a normalized human-readable title in `title`. TXT input may use an
empty `source_heading` when no explicit heading exists.

Paragraph entries store `id`, 1-based `index`, and `text_preview`. The full
novel text should remain in the user input file, not be duplicated into
repository output unless the input is a public synthetic example.

### `characters_detected`

Character candidates should come from explicit names, repeated mentions,
dialogue attribution, role labels, or clear kinship/title references. The parser
may include `aliases`, `description_hint`, `first_seen`, `source_trace`, and
`confidence`. It must not invent backstory, hidden goals, or character arcs.

### `locations_detected`

Location candidates should come from explicit place nouns, setting headings, or
repeated spatial references. `location_type` is descriptive only and must not
force screenplay scene-heading normalization.

### `props_detected`

Prop candidates are objects that carry action, evidence, threat, memory, or plot
state. The parser should avoid noun dumping. A one-off background object belongs
in source text, not necessarily in `props_detected`.

### `key_events`

Key events summarize explicit actions or state changes in source order. Each
event can link `character_ids`, `location_ids`, and `prop_ids`. Events should be
brief and source-grounded. They must not contain adaptation choices such as scene
merges, act structure, shot design, or generated dialogue.

### `timeline`

Timeline items capture ordering and time expressions visible in the text. They
can link to `event_ids`. They are allowed to preserve vague expressions like
`第二天傍晚`, `七年前`, or `夜里`. They should not solve contradictions or infer
calendar dates unless explicitly present.

### `psychological_passages`

Psychological passages mark interiority, memory, emotion, fear, desire, or
motivation. `externalization_hint` can name why the passage matters for later
adaptation, but it is not generated screenplay action and should remain
optional.

### `uncertainties`

Uncertainties make parser limits visible. Use them for ambiguous pronouns,
speaker ambiguity, unclear chapter boundaries, weak event causality, uncertain
entity identity, or unsupported inference pressure. Downstream phases must not
silently resolve high-severity uncertainties.

## Heuristic Parsing Boundary

Allowed in Phase 3 implementation:

- Split Markdown by headings and TXT by chapter-like lines or fallback chunks.
- Split paragraphs by blank lines.
- Generate stable IDs from source order.
- Detect candidates with bounded rules, dictionaries, punctuation cues,
  repetition, and explicit labels.
- Emit confidence and uncertainty records.
- Validate output against `schemas/story_map.schema.json`.

Current heuristic examples:

- Psychological passage keywords include `想起`, `觉得`, `害怕`, `意识到`,
  `心里`, `怀疑`, `记得`, and `仿佛`.
- Location keywords include `邮局`, `灯塔`, `码头`, `海边`, `房间`, `街道`,
  `船`, and `钟楼`.
- Prop keywords include `信封`, `录音笔`, `钥匙`, `照片`, `灯`, `船`, and
  `信`.
- Event extraction uses surface action cues such as `听见`, `来到`, `递给`,
  `组织`, `拦住`, `敲响`, and `熄灭`.

Limitations:

- Character extraction is pattern-based and may miss names without nearby action
  cues.
- Location and prop extraction are keyword-based and may over-report words such
  as `船` when used as both place-like setting and object.
- Timeline extraction preserves text expressions; it does not solve a complete
  chronology.
- `uncertainties` records low-confidence situations instead of resolving them.
- The parser does not infer hidden motives, relationships, themes, worldbuilding,
  or adaptation structure.

Why no LLM integration:

- Phase 3 must be reproducible and testable with no external service.
- `story_map` is an evidence map, not a creative interpretation.
- Later LLM-assisted phases must consume source-traced facts instead of
  silently replacing the contract.

Still not allowed in Phase 3:

- LLM or external model integration.
- Screenplay scene, beat, or element generation.
- Changes to Phase 2 validators or Fountain exporter.
- Agent review implementation.
- Frontend or backend APIs.

## Implementation History And Remaining Work

- Done: contract and schema in `schemas/story_map.schema.json`.
- Done: parser package under `src/novel2script/parsers/`.
- Done: Markdown/TXT chapter splitting and blank-line paragraph indexing.
- Done: bounded heuristic detectors for characters, locations, props, time
  phrases, key events, psychological passages, and uncertainties.
- Done: `parse-novel` CLI command.
- Done: generated sample output at `examples/output/generated_story_map.yaml`.
- Remaining: no complete NLP, no relationship graph, no screenplay generation,
  no Agent workflow, no Web API, and no Fountain round-trip.
- Governance: after contract freeze, schema/API issues must be handled through
  `docs/architecture/change-requests/`.

## Run Tests

```bash
python -m pytest tests/test_novel_parser.py
python -m pytest tests/test_parse_novel_cli.py
python -m pytest
```

Current test coverage includes:

- sample novel parses into three chapters.
- chapter and paragraph IDs are stable.
- parser output conforms to `schemas/story_map.schema.json`.
- key events, psychological passages, and uncertainties include
  `source_trace`.
- `parse-novel` writes YAML and returns non-zero for missing input.
- Phase 2 validate/export commands continue to run through the full pytest
  suite.

## Gate Checklist

- `story_map` fields are defined and traceable.
- `source_trace` aligns with Phase 2 traceability goals.
- Heuristic boundaries are explicit.
- Parser and CLI remain deterministic and do not call external models.
- No LLM integration is introduced.
- No Phase 2 validator/exporter behavior is modified.
