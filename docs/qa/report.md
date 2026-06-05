# QA Report

## Scope

Stage 5 QA covered deterministic structured screenplay generation from Stage 3
and Stage 4 artifacts, including:

- `screenplay` builder output.
- `build-screenplay` CLI integration.
- generated `screenplay.yaml` sample output.
- Schema, source trace, beat completeness, and reference validation.
- Fountain export and sidecar map generation from the generated screenplay.
- Regression coverage for Stage 2, Stage 3, and Stage 4 commands.

This pass did not connect to any LLM or external model service, did not run
multi-Agent review, did not implement Fountain round-trip editing, and did not
add UI/API behavior.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
python -m novel2script.cli build-screenplay --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_screenplay.yaml
python -m novel2script.cli validate examples/output/generated_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/generated_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
git status --short
```

Additional structural checks:

```bash
python - <<'PY'
from pathlib import Path
import json
import yaml

screenplay_path = Path("examples/output/generated_screenplay.yaml")
report_path = Path("examples/output/generated_screenplay_validation_report.yaml")
fountain_path = Path("examples/output/generated_screenplay.fountain")
map_path = Path("examples/output/generated_screenplay.fountain.map.json")

for path in [screenplay_path, report_path, fountain_path, map_path]:
    assert path.exists()
    assert path.stat().st_size > 0

screenplay = yaml.safe_load(screenplay_path.read_text(encoding="utf-8"))
report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
sidecar = json.loads(map_path.read_text(encoding="utf-8"))

assert report["overall_passed"] is True
assert len(screenplay["scenes"]) >= 1
assert sidecar["mappings"]

characters = {character["id"] for character in screenplay["characters"]}
beat_required = {
    "objective",
    "tactic",
    "obstacle",
    "conflict",
    "stakes",
    "turn",
    "externalized_action",
}
for scene in screenplay["scenes"]:
    assert scene.get("source_trace")
    assert scene.get("beats")
    for beat in scene["beats"]:
        assert beat_required <= set(beat)
        assert all(str(beat[field]).strip() for field in beat_required)
        assert beat.get("source_trace")
        assert beat.get("ai_tags")
    for element in scene.get("elements", []):
        if element.get("type") == "dialogue":
            assert element.get("character_id") in characters
PY
```

External-call check:

```bash
Get-ChildItem -Recurse -File src tests |
  Select-String -Pattern 'openai|anthropic|gemini|llm|chat.completions|responses.create|requests|httpx' -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 31 tests collected and 31 passed.
- `parse-novel` CLI: passed, regenerated `examples/output/generated_story_map.yaml`.
- `build-outline` CLI: passed, regenerated `examples/output/generated_outline.yaml`.
- `build-character-bible` CLI: passed, regenerated `examples/output/generated_character_bible.yaml`.
- `build-screenplay` CLI: passed, generated non-empty `examples/output/generated_screenplay.yaml`.
- Generated screenplay validation: passed, `overall_passed: true`.
- Generated screenplay Fountain export: passed, generated non-empty Fountain file and sidecar map.
- Structural screenplay check: passed. Output contains 6 scenes, 3 characters, every scene has at least one beat, required beat fields are populated, scene and beat source traces exist, and inferred/low-confidence generated records carry `ai_tags`.
- Dialogue reference check: passed. No invalid `dialogue.character_id` references were found; the current deterministic sample emits action and note elements only.
- External-call check: passed. No source or test references to LLM providers or HTTP client calls were found.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_outline.yaml`
- `examples/output/generated_character_bible.yaml`
- `examples/output/generated_screenplay.yaml`
- `examples/output/generated_screenplay_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`

## Tests Not Run

- Static type checking was not run because the project does not configure a type checker.
- Linting was not run because the project does not configure a lint command.
- Multi-Agent review, UAT, UI/API tests, LLM tests, and Fountain round-trip editing tests were not run because they are outside Stage 5 scope.

## Risks

- Generated screenplay content is deterministic scaffolding, not polished screenplay prose.
- The builder intentionally emits conservative action and note elements; full dialogue generation remains out of scope.
- Stage 5 preserves draft contract status. If the screenplay schema is frozen later, contract changes must go through `docs/architecture/change-requests/`.
- Source text in the sample artifacts currently displays mojibake from the existing sample encoding path; this does not block structural QA but should be considered before human-facing demos.

## Gate Decision

Passed. Stage 5 deterministic structured screenplay generation meets the
builder, CLI, generated sample, schema validation, Fountain export, source trace,
`ai_tags`, no-LLM, and regression test requirements. The project is ready for
Stage 6 multi-Agent review.
