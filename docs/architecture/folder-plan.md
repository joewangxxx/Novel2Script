# Folder Plan

This file describes planned repository ownership for Phase 3 novel parsing. It
does not authorize implementation outside the listed phase scope.

## Existing Folders

- `schemas/`: JSON Schema contracts for YAML/JSON-compatible project data.
- `docs/architecture/`: shared contracts, schema notes, folder plans, and change
  request governance.
- `docs/dev/`: phase implementation notes and developer-facing runbooks.
- `examples/input/`: public, synthetic input texts only.
- `examples/output/`: generated or sample outputs safe for repository storage.
- `src/novel2script/`: application package. Phase 3 parser code will eventually
  live here, but Phase 3A does not add parser code.
- `tests/`: deterministic tests for schema, parser, validator, and exporter
  behavior.

## Phase 3A Files

- `schemas/story_map.schema.json`: draft JSON Schema for the `story_map`
  contract.
- `docs/architecture/schema.md`: cross-phase schema notes and contract
  governance.
- `docs/architecture/folder-plan.md`: planned file ownership for Phase 3.
- `docs/dev/PHASE_3_NOVEL_PARSING.md`: implementation plan and test plan for
  later parser work.

## Planned Phase 3 Implementation Files

These files are planned for a later implementation task and must not be created
as parser code during Phase 3A:

- `src/novel2script/parsers/__init__.py`: parser package marker.
- `src/novel2script/parsers/story_map.py`: story map data assembly from parsed
  chapters and detected candidates.
- `src/novel2script/parsers/novel_parser.py`: Markdown/TXT chapter and
  paragraph splitting plus heuristic extraction orchestration.
- `src/novel2script/parsers/heuristics.py`: bounded rule helpers for headings,
  time phrases, names, places, props, events, and psychological passages.
- `tests/test_story_map_schema.py`: schema validation tests for valid and
  invalid `story_map` fixtures.
- `tests/test_novel_parser.py`: deterministic parser tests for Markdown and TXT
  inputs.
- `examples/output/sample_story_map.yaml`: public sample output from the
  synthetic novel input.

## Ownership And Gates

- Architecture owns `schemas/story_map.schema.json`,
  `docs/architecture/schema.md`, and later contract changes.
- BE/parser implementation may add parser modules only after the contract is
  accepted or prototype mode is explicitly declared by the parent orchestrator.
- QA may add validation tests after implementation artifacts exist.
- FE and BE must not silently edit the frozen contract to fit implementation
  convenience. They must open a change request instead.

## Phase 4A Files

- `schemas/outline.schema.json`: draft JSON Schema for the Stage 4 outline
  contract.
- `schemas/character_bible.schema.json`: draft JSON Schema for the Stage 4
  character bible contract.
- `docs/dev/PHASE_4_OUTLINE_AND_CHARACTER_BIBLE.md`: Stage 4 contract notes,
  source trace rules, low-confidence policy, and implementation plan.
- `docs/architecture/schema.md`: cross-phase schema notes updated with Stage 4
  contracts.
- `docs/architecture/folder-plan.md`: this file, updated with Stage 4 file
  ownership and planned implementation files.

## Planned Phase 4 Implementation Files

These files are planned for a later implementation task and must not be created
as generator code during Phase 4A:

- `src/novel2script/planning/__init__.py`: planning package marker.
- `src/novel2script/planning/outline_builder.py`: deterministic outline shell
  creation from `story_map`.
- `src/novel2script/planning/character_bible_builder.py`: deterministic
  character bible shell creation from `story_map.characters_detected`.
- `src/novel2script/planning/source_coverage.py`: coverage helper comparing
  `story_map.key_events` against outline scene/event usage.
- `tests/test_outline_schema.py`: schema tests for valid and invalid outline
  samples.
- `tests/test_character_bible_schema.py`: schema tests for valid and invalid
  character bible samples.
- `tests/test_phase4_planning.py`: deterministic Stage 4B planning behavior
  tests.
- `examples/output/generated_outline.yaml`: public sample outline from the
  synthetic story map.
- `examples/output/generated_character_bible.yaml`: public sample character
  bible from the synthetic story map.

## Phase 4 Ownership And Gates

- Architecture owns `schemas/outline.schema.json`,
  `schemas/character_bible.schema.json`, and Stage 4 contract changes.
- BE/planning implementation may add generator modules only after this draft
  contract is accepted or prototype mode is explicitly declared by the parent
  orchestrator.
- QA may add Stage 4 validation tests after implementation artifacts exist.
- Later generators must preserve `source_trace`, `ai_tags`, and `locked`
  semantics. After freeze, schema/API changes require architecture change
  requests.

## Phase 5A Files

- `docs/dev/PHASE_5_STRUCTURED_SCREENPLAY_GENERATION.md`: Stage 5 mapping
  contract from `story_map`, `outline`, and `character_bible` to
  `screenplay.yaml`.
- `docs/architecture/schema.md`: cross-phase schema notes updated with Stage 5
  source trace bridge and mapping summary.
- `docs/architecture/folder-plan.md`: this file, updated with Stage 5 file
  ownership and planned implementation files.

Phase 5A intentionally does not create generator code and does not modify
`schemas/screenplay.schema.json`.

## Planned Phase 5 Implementation Files

These files are planned for later Stage 5 implementation work and must not be
created during Phase 5A:

- `src/novel2script/generators/__init__.py`: generator package marker.
- `src/novel2script/generators/screenplay_builder.py`: deterministic builder
  from Stage 3/4 artifacts into screenplay YAML.
- `tests/test_screenplay_builder.py`: unit tests for scene, beat, element,
  source trace, `ai_tags`, and locked-character behavior.
- `tests/test_screenplay_cli.py`: CLI tests for future `build-screenplay`
  behavior.
- `examples/output/generated_screenplay.yaml`: generated sample screenplay YAML
  from the public synthetic pipeline.

## Phase 5 Ownership And Gates

- Architecture owns Stage 5 mapping rules and any screenplay schema change
  request.
- BE/generator implementation may add screenplay builder modules only after the
  Phase 5A mapping contract is accepted or prototype mode is explicitly
  declared by the parent orchestrator.
- QA may add Stage 5 validation and regression tests after implementation
  artifacts exist.
- After contract freeze, FE, BE, QA, or tooling must not silently change
  screenplay, outline, character bible, or story map contracts.

## Phase 6A Files

- `schemas/review_report.schema.json`: draft JSON Schema for deterministic
  multi-reviewer reports.
- `docs/dev/PHASE_6_MULTI_AGENT_REVIEW.md`: Stage 6 review contract, reviewer
  scopes, issue structure, patch policy, and implementation plan.
- `docs/architecture/schema.md`: cross-phase schema notes updated with Stage 6
  review report contract.
- `docs/architecture/folder-plan.md`: this file, updated with Stage 6 file
  ownership and planned implementation files.

Phase 6A intentionally does not create reviewer code, does not call LLMs, and
does not modify `schemas/screenplay.schema.json`.

## Planned Phase 6 Implementation Files

These files are planned for later Stage 6 implementation work and must not be
created during Phase 6A:

- `src/novel2script/reviewers/__init__.py`: reviewer package marker.
- `src/novel2script/reviewers/review_report.py`: shared report assembly,
  summary counting, stable issue IDs, and schema-oriented helpers.
- `src/novel2script/reviewers/character_consistency_reviewer.py`: deterministic
  character reference and bible-alignment checks.
- `src/novel2script/reviewers/pacing_reviewer.py`: deterministic scene order,
  beat density, coverage, turn, and stakes checks.
- `src/novel2script/reviewers/dialogue_naturalness_reviewer.py`:
  deterministic dialogue validity, repetition, and low-confidence checks.
- `src/novel2script/reviewers/shootability_reviewer.py`: deterministic
  shootability, externalized action, traceability, and internal-state checks.
- `tests/test_review_report_schema.py`: schema tests for valid and invalid
  review report fixtures.
- `tests/test_reviewers.py`: reviewer unit tests for issue shape, source trace,
  deterministic ordering, and human approval policy.

Planned Stage 6 CLI and sample files:

- `tests/test_review_screenplay_cli.py`: future CLI test for
  `review-screenplay`.
- `examples/output/generated_review_report.yaml`: public sample review report
  from the deterministic screenplay.

## Phase 6 Ownership And Gates

- Architecture owns `schemas/review_report.schema.json` and any review report
  contract change request.
- BE/reviewer implementation may add reviewer modules only after the Phase 6A
  contract is accepted or prototype mode is explicitly declared by the parent
  orchestrator.
- QA may add Stage 6 validation and regression tests after implementation
  artifacts exist.
- Reviewers may only produce advisory patch suggestions. They must not apply
  patches, overwrite screenplay YAML, or bypass human approval.
- After contract freeze, FE, BE, QA, or tooling must not silently change review
  report, screenplay, outline, character bible, or story map contracts.

## Phase 7A Files

- `schemas/fountain_roundtrip_report.schema.json`: draft JSON Schema for
  Fountain limited import/sync reports.
- `docs/dev/PHASE_7_FOUNTAIN_LIMITED_ROUNDTRIP.md`: Stage 7 contract, safe
  field boundary, map behavior, normalization rules, drift policy, and
  implementation plan.
- `docs/architecture/schema.md`: cross-phase schema notes updated with Stage 7
  roundtrip contract.
- `docs/architecture/folder-plan.md`: this file, updated with Stage 7 file
  ownership and planned implementation files.

Phase 7A intentionally does not create importer code, does not implement a full
Fountain parser, does not call LLMs, and does not modify
`schemas/screenplay.schema.json`.

## Planned Phase 7 Implementation Files

These files are planned for later Stage 7 implementation work and must not be
created during Phase 7A:

- `src/novel2script/importers/__init__.py`: importer package marker.
- `src/novel2script/importers/fountain_roundtrip.py`: deterministic limited
  Fountain sync from mapped line ranges into safe screenplay YAML text fields.
- `tests/test_fountain_roundtrip.py`: unit tests for heading, action,
  dialogue, parenthetical, transition, unsafe path, and line drift behavior.
- `tests/test_fountain_roundtrip_cli.py`: CLI tests for future
  `import-fountain` behavior.
- `examples/output/generated_screenplay_roundtrip.yaml`: public sample synced
  screenplay created only after Stage 7B implementation.
- `examples/output/generated_fountain_roundtrip_report.yaml`: public sample
  import report created only after Stage 7B implementation.

## Phase 7 Ownership And Gates

- Architecture owns `schemas/fountain_roundtrip_report.schema.json` and any
  roundtrip contract change request.
- BE/importer implementation may add importer modules only after the Phase 7A
  contract is accepted or prototype mode is explicitly declared by the parent
  orchestrator.
- QA may add Stage 7 validation and regression tests after implementation
  artifacts exist.
- Importers may update only `scenes[i].heading`,
  `scenes[i].elements[j].text`, and allowed roundtrip metadata.
- Importers must not guess repairs for line drift, structure changes, unsafe
  paths, or map mismatch.
- After contract freeze, FE, BE, QA, or tooling must not silently change
  roundtrip report, review report, screenplay, outline, character bible, or
  story map contracts.
