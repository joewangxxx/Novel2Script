# QA Report

## Scope

Stage 4 QA covered deterministic outline and character bible generation,
including schemas, builders, CLI commands, generated sample outputs, Phase 4
documentation, and Stage 2/Stage 3 regression commands.

This pass did not implement new product behavior beyond Stage 4C, did not
connect to any LLM or external model service, did not generate screenplay YAML,
did not add UI/API behavior, and did not run Agent review.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
python -m novel2script.cli validate examples/output/sample_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/sample_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
git status --short
```

Additional structural checks:

```bash
python - <<'PY'
from pathlib import Path
import yaml

story = yaml.safe_load(Path("examples/output/generated_story_map.yaml").read_text(encoding="utf-8"))["story_map"]
outline = yaml.safe_load(Path("examples/output/generated_outline.yaml").read_text(encoding="utf-8"))["outline"]
bible = yaml.safe_load(Path("examples/output/generated_character_bible.yaml").read_text(encoding="utf-8"))["character_bible"]

assert outline["logline"]
assert outline["act_structure"]
assert outline["scene_plan"]
assert all(scene.get("source_trace") for scene in outline["scene_plan"])
assert [c["id"] for c in bible["characters"]] == [c["id"] for c in story["characters_detected"]]
assert all(character.get("source_trace") for character in bible["characters"])
assert all(character.get("locked") is False for character in bible["characters"])
PY
```

LLM-call check:

```bash
Get-ChildItem -Recurse -File src |
  Select-String -Pattern 'openai|anthropic|gemini|llm|chat.completions|responses.create|requests|httpx' -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 24 tests collected and 24 passed.
- `parse-novel` CLI: passed, regenerated `examples/output/generated_story_map.yaml`.
- `build-outline` CLI: passed, generated non-empty `examples/output/generated_outline.yaml`.
- `build-character-bible` CLI: passed, generated non-empty `examples/output/generated_character_bible.yaml`.
- `validate` CLI regression: passed, regenerated `examples/output/generated_validation_report.yaml`.
- `export-fountain` CLI regression: passed, regenerated `examples/output/generated_screenplay.fountain` and sidecar map.
- Outline structural check: passed. Output includes `logline`, `act_structure`, `scene_plan`, and every scene plan item has `source_trace`.
- Character bible structural check: passed. Characters match `story_map.characters_detected`, every character has `source_trace`, and `locked` defaults to `false`.
- LLM-call check: passed. No source code references to external LLM providers or HTTP client calls were found.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_outline.yaml`
- `examples/output/generated_character_bible.yaml`
- `examples/output/generated_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`

## Tests Not Run

- Static type checking was not run because the project does not configure a type checker.
- Linting was not run because the project does not configure a lint command.
- LLM, Agent, UI, Web API, full screenplay generation, and Fountain round-trip tests were not run because those capabilities are outside Stage 4 scope.

## Risks

- Outline and character bible outputs remain deterministic drafts, not human-approved creative decisions.
- `want`, `need`, `flaw`, `voice`, and `arc` are deliberately low-confidence placeholders when direct evidence is insufficient.
- `outline` and `character_bible` contracts are still marked as draft; schema changes after freeze must go through `docs/architecture/change-requests/`.
- Stage 5 screenplay generation must preserve `source_trace`, `ai_tags`, and `locked` semantics instead of silently expanding low-confidence planning fields.

## Gate Decision

Passed. Stage 4 deterministic outline and character bible generation meets the
current schema, builder, CLI, sample output, documentation, and regression
requirements. The project is ready for Stage 5 structured screenplay
generation, subject to normal contract review governance.
