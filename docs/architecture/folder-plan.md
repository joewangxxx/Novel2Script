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
