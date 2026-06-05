# QA Report

## Scope

Stage 7 QA covered Fountain limited roundtrip import from edited Fountain back
to screenplay YAML, including:

- `fountain_roundtrip_report` schema contract.
- deterministic limited Fountain importer core.
- `import-fountain` CLI integration.
- generated roundtrip screenplay and import report samples.
- regression coverage for Stage 2 through Stage 6 commands.
- verification that protected screenplay fields are not rewritten by Fountain
  import.

This pass did not implement a full Fountain parser, did not create screenplay
YAML from arbitrary Fountain, did not call LLMs, and did not apply Stage 6
review suggestions.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
python -m novel2script.cli build-screenplay --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_screenplay.yaml
python -m novel2script.cli validate examples/output/generated_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/generated_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
python -m novel2script.cli import-fountain --screenplay examples/output/generated_screenplay.yaml --fountain <temp>/edited.fountain --map <temp>/edited.fountain.map.json --out examples/output/generated_screenplay_roundtrip.yaml --report examples/output/generated_screenplay_roundtrip_report.yaml
python -m novel2script.cli validate examples/output/generated_screenplay_roundtrip.yaml --schema schemas/screenplay.schema.json --out <temp>/generated_screenplay_roundtrip_validation_report.yaml
python -m novel2script.cli review-screenplay --screenplay examples/output/generated_screenplay_roundtrip.yaml --character-bible examples/output/generated_character_bible.yaml --out <temp>/generated_screenplay_roundtrip_review_report.yaml
git status --short
```

Additional structural check:

```bash
python - <<'PY'
from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

source = yaml.safe_load(Path("examples/output/generated_screenplay.yaml").read_text(encoding="utf-8"))
updated = yaml.safe_load(Path("examples/output/generated_screenplay_roundtrip.yaml").read_text(encoding="utf-8"))
report = yaml.safe_load(Path("examples/output/generated_screenplay_roundtrip_report.yaml").read_text(encoding="utf-8"))
schema = json.loads(Path("schemas/fountain_roundtrip_report.schema.json").read_text(encoding="utf-8"))
Draft202012Validator(schema).validate(report)

assert updated["metadata"]["semantic_fields_stale"] is True
assert updated["characters"] == source["characters"]
for scene_index, scene in enumerate(source["scenes"]):
    assert updated["scenes"][scene_index]["source_trace"] == scene["source_trace"]
    assert updated["scenes"][scene_index]["beats"] == scene["beats"]
for original_scene, updated_scene in zip(source["scenes"], updated["scenes"]):
    for original_beat, updated_beat in zip(original_scene["beats"], updated_scene["beats"]):
        for field in ["objective", "conflict", "stakes"]:
            assert updated_beat[field] == original_beat[field]
roundtrip = report["fountain_roundtrip_report"]
assert roundtrip["status"] in {"applied", "partial", "skipped", "blocked"}
assert "applied_changes" in roundtrip["summary"]
assert "skipped_changes" in roundtrip["summary"]
assert "blocking_issues" in roundtrip["summary"]
PY
```

External-call check:

```powershell
Get-ChildItem -Recurse -File src,tests |
  Select-String -Pattern 'openai|anthropic|gemini|llm|chat\.completions|responses\.create|requests|httpx|urllib|aiohttp|api[_-]?key' -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 54 tests collected and 54 passed.
- `parse-novel` CLI: passed.
- `build-outline` CLI: passed.
- `build-character-bible` CLI: passed.
- `build-screenplay` CLI: passed.
- Generated screenplay validation: passed.
- `export-fountain --map`: passed and preserved the existing `--map` option.
- `import-fountain`: passed using a temporary edited Fountain copy and temporary sidecar map.
- Imported screenplay validation: passed.
- `review-screenplay` on imported screenplay: passed.
- Roundtrip report schema validation: passed.
- Protected field check: passed. `source_trace`, `characters`, and all scene `beats` remained unchanged.
- Beat semantic fields check: passed for `objective`, `conflict`, and `stakes`.
- Metadata stale marker: passed, `metadata.semantic_fields_stale: true`.
- Import report status: passed, `status: applied` with `applied_changes: 2`.
- External-call check: passed. No LLM, HTTP client, or API-key patterns were found in `src` or `tests`.
- Git status scope check: passed. The worktree contains only Stage 7 contract, importer, CLI, tests, sample output, QA, and blackboard changes.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_outline.yaml`
- `examples/output/generated_character_bible.yaml`
- `examples/output/generated_screenplay.yaml`
- `examples/output/generated_screenplay_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`
- `examples/output/generated_screenplay_roundtrip.yaml`
- `examples/output/generated_screenplay_roundtrip_report.yaml`

## Tests Not Run

- Static type checking was not run because the project does not configure a type checker.
- Linting was not run because the project does not configure a lint command.
- Full Fountain AST parsing, new scene creation, character creation, source trace repair, LLM tests, UI/API tests, and UAT were not run because they are outside Stage 7 scope.

## Risks

- The importer is intentionally line-map based. Fountain line insertion,
  deletion, scene reorder, or unsafe sidecar paths block or skip import rather
  than attempting repair.
- Roundtrip text edits mark `metadata.semantic_fields_stale: true`; later stages
  need review or regeneration before treating beat semantics as current.
- The sample roundtrip report references a temporary edited Fountain path used
  during QA/sample generation. The source exported Fountain file is not
  modified.
- Stage 7 contracts remain draft. If frozen later, changes must go through
  `docs/architecture/change-requests/`.

## Gate Decision

Passed. Stage 7 Fountain limited roundtrip meets the importer, CLI, sample
output, report, protected-field, no-LLM, and regression requirements. The
project is ready for Stage 8 quality evaluation dashboard / visual workbench
planning.
