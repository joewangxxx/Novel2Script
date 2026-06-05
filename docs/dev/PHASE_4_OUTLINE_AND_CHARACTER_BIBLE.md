# Phase 4: Outline And Character Bible Contract

Phase 4 consumes the Phase 3 `story_map` and prepares two draft artifacts:
`outline` and `character_bible`. Phase 4A defined the contracts, Phase 4B added
deterministic builders, and Phase 4C adds CLI access plus generated sample
outputs. The phase does not call an LLM, generate `screenplay.yaml`, modify the
Phase 3 parser, run Agent review, or freeze the contract.

## Goal

Stage 4 turns the evidence map from Stage 3 into an adaptation planning layer.
The output should help later stages decide scene order, dramatic focus,
character motivation, relationships, voice, and arcs while keeping every
creative inference traceable and reviewable.

## Inputs

- `examples/output/generated_story_map.yaml` or another valid `story_map`.
- `schemas/story_map.schema.json` as the input contract.
- Phase 3 source trace shape:

```yaml
source_trace:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
  event_ids: ["evt_001"]
  quote_preview: "short source excerpt"
  note: "why this source supports the generated field"
```

`event_ids` is optional but recommended when the field is derived from
`story_map.key_events`. `chapter_id` and `paragraph_ids` remain required for
traceability.

## Output Artifacts

- `outline`: draft adaptation outline, validated by
  `schemas/outline.schema.json`.
- `character_bible`: draft character planning document, validated by
  `schemas/character_bible.schema.json`.
- `examples/output/generated_outline.yaml`: sample outline generated from the
  public synthetic story map.
- `examples/output/generated_character_bible.yaml`: sample character bible
  generated from the public synthetic story map.

Both contracts start at `schema_version: "0.1.0"` and remain draft until the
parent orchestrator explicitly freezes them.

## Run The CLI

Regenerate the Stage 3 story map:

```bash
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
```

Build the Stage 4 outline:

```bash
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
```

Build the Stage 4 character bible:

```bash
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
```

All commands are deterministic and local. Output directories are created by the
shared YAML writer. Missing input files return a non-zero exit code.

## Outline Contract

Root shape:

```yaml
outline:
  schema_version: "0.1.0"
  source_story_map:
    schema_version: "0.1.0"
    story_map_file: "examples/output/generated_story_map.yaml"
  logline:
    text: ""
    source_trace: []
    ai_tags:
      inferred: true
      confidence: low
      needs_human_review: true
  theme_candidates: []
  act_structure: []
  scene_plan: []
  source_coverage:
    story_event_count: 0
    covered_event_ids: []
    uncovered_event_ids: []
  uncertainties: []
```

Fields:

- `logline`: one-sentence adaptation premise. Because a logline compresses
  source material, it is normally inferred and should include `ai_tags`.
- `theme_candidates`: possible themes, each with rationale, source evidence,
  and confidence. Themes are candidates, not canon.
- `act_structure`: high-level act grouping such as `act_1`, `act_2`, `act_3`,
  `prologue`, `epilogue`, or `custom`.
- `scene_plan`: planned scene units for later screenplay generation. These are
  not screenplay scenes yet and must not contain generated dialogue or beats.
- `source_coverage`: maps Stage 3 key events to planned outline coverage so
  later validators can detect dropped source material.
- `uncertainties`: adaptation risks, weak evidence, timeline ambiguity, or scene
  merge risk that requires review.

## Character Bible Contract

Root shape:

```yaml
character_bible:
  schema_version: "0.1.0"
  source_story_map:
    schema_version: "0.1.0"
    story_map_file: "examples/output/generated_story_map.yaml"
  characters:
    - id: "char_001"
      name: ""
      want: {}
      need: {}
      flaw: {}
      relationships: []
      voice: {}
      arc: {}
      locked: false
      source_trace: []
      ai_tags:
        inferred: true
        confidence: low
        needs_human_review: true
  uncertainties: []
```

Character fields:

- `characters`: character profiles keyed to Phase 3 `characters_detected[].id`.
- `want`: what the character pursues externally.
- `need`: what the character may need internally or dramatically.
- `flaw`: limitation, fear, blind spot, or behavior that creates dramatic
  friction.
- `relationships`: links to other `char_###` IDs with relationship type and
  evidence.
- `voice`: speech style summary and dialogue rules for later scene writing.
- `arc`: start, turning points, and end state, linked to source events where
  possible.
- `locked`: when true, later generators must not overwrite the character profile
  silently. User-authored or manually approved facts should be locked.
- `source_trace`: source evidence for the profile as a whole.
- `ai_tags`: inference and confidence metadata for the profile.

## AI Tags

Every inferred or low-confidence field must include:

```yaml
ai_tags:
  inferred: true
  confidence: low
  needs_human_review: true
  notes:
    - "why this field needs review"
```

Use `confidence: high` only when the field is directly supported by explicit
story_map evidence. `want`, `need`, `flaw`, `theme_candidates`, `voice`, and
`arc` are usually inferred and should default to human review unless evidence is
strong.

## Source Trace Rules

- `source_trace` must point back to `story_map` chapter and paragraph IDs.
- If an output field is based on a `key_event`, include `event_ids`.
- If evidence spans multiple source locations, use an array of source traces.
- Do not copy full source paragraphs into outline or character bible artifacts.
- If a field cannot be supported by source evidence, create an uncertainty
  instead of silently filling the field.

## Implementation History And Remaining Work

- Done: contract and schema in `schemas/outline.schema.json` and
  `schemas/character_bible.schema.json`.
- Done: deterministic builder package under `src/novel2script/planners/`.
- Done: outline builder creates logline, theme candidates, act grouping, scene
  candidates, source coverage, and inherited uncertainties from `story_map`.
- Done: character bible builder creates character shells, low-confidence
  placeholders for want/need/flaw/voice, arc links to visible events, and
  uncertainties for weak inference fields.
- Done: CLI commands `build-outline` and `build-character-bible`.
- Done: generated sample outputs under `examples/output/`.
- Remaining: no LLM generation, no complete character psychology inference, no
  screenplay YAML, no Agent review, no UI/API, and no contract freeze.
- Governance: keep any schema conflict in `docs/architecture/change-requests/`
  after contract freeze.

## Non-Goals

- No LLM integration.
- No screenplay YAML generation.
- No full character psychology inference.
- No Agent review workflow.
- No changes to Stage 3 parser or Stage 2 validator/exporter behavior.

## Run Tests

```bash
python -m pytest tests/test_outline_builder.py tests/test_character_bible_builder.py
python -m pytest tests/test_planner_cli.py
python -m pytest
```

Current test coverage includes:

- outline builder output validates against `schemas/outline.schema.json`.
- character bible builder output validates against
  `schemas/character_bible.schema.json`.
- source trace and AI tag requirements are preserved.
- outline source coverage covers Stage 3 key events.
- character bible low-confidence fields stay empty instead of inventing facts.
- planner CLI writes schema-valid YAML and returns non-zero for missing input.
- Stage 2 and Stage 3 commands remain covered by the full pytest suite.

## Gate Checklist

- `outline` fields are defined and source-traceable.
- `character_bible` fields are defined and source-traceable.
- Low-confidence and inferred fields require `ai_tags`.
- Stage 4 builders and CLI remain deterministic and do not call external models.
- Stage 4 file plan and CLI usage are documented.
- Contracts remain draft unless explicitly frozen by the parent orchestrator.
