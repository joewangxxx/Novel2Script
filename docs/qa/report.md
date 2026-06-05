# QA Report

## Scope

Stage 8 QA covered the deterministic Quality Eval Dashboard contract,
aggregator, `evaluate-quality` CLI, generated YAML quality report, generated
Markdown dashboard, and regression coverage for the Stage 3 through Stage 7
pipeline.

This pass did not implement a Web UI, did not connect a model provider, did not
rewrite screenplay YAML, and did not apply Stage 6 suggested patches.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
python -m novel2script.cli build-screenplay --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_screenplay.yaml
python -m novel2script.cli validate examples/output/generated_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/generated_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
python -m novel2script.cli review-screenplay --screenplay examples/output/generated_screenplay.yaml --character-bible examples/output/generated_character_bible.yaml --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --out examples/output/generated_review_report.yaml
python -m novel2script.cli import-fountain --screenplay examples/output/generated_screenplay.yaml --fountain <temp>/edited.fountain --map <temp>/edited.fountain.map.json --out examples/output/generated_screenplay_roundtrip.yaml --report examples/output/generated_screenplay_roundtrip_report.yaml
python -m novel2script.cli validate examples/output/generated_screenplay_roundtrip.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_roundtrip_validation_report.yaml
python -m novel2script.cli evaluate-quality --screenplay examples/output/generated_screenplay_roundtrip.yaml --validation-report examples/output/generated_screenplay_roundtrip_validation_report.yaml --review-report examples/output/generated_review_report.yaml --roundtrip-report examples/output/generated_screenplay_roundtrip_report.yaml --out examples/output/generated_quality_report.yaml --markdown examples/output/generated_quality_dashboard.md
```

Quality report schema and dashboard checks:

```bash
python - <<'PY'
import json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

schema = json.loads(Path("schemas/quality_report.schema.json").read_text(encoding="utf-8"))
quality = yaml.safe_load(Path("examples/output/generated_quality_report.yaml").read_text(encoding="utf-8"))
Draft202012Validator(schema).validate(quality)

report = quality["quality_report"]
for key in ["validation_report", "review_report", "fountain_roundtrip_report"]:
    assert report["source_artifacts"][key]

semantic = next(item for item in report["dimensions"] if item["id"] == "semantic_staleness")
assert semantic["status"] == "warn"
assert semantic["score"] == 70

dashboard = Path("examples/output/generated_quality_dashboard.md").read_text(encoding="utf-8")
for marker in [
    "# Quality Dashboard",
    "- Score:",
    "| Dimension | Status | Score | Summary |",
    "## Blocking Items",
    "## Recommended Next Actions",
]:
    assert marker in dashboard
assert dashboard.strip()
PY
```

External-call trace check:

```powershell
Get-ChildItem -Recurse -File src,tests -Include *.py |
  Select-String -Pattern 'openai|anthropic|gemini|llm|chat\.completions|responses\.create|requests|httpx|urllib|aiohttp|api[_-]?key' -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 60 tests collected and 60 passed.
- `parse-novel`: passed.
- `build-outline`: passed.
- `build-character-bible`: passed.
- `build-screenplay`: passed.
- Generated screenplay validation: passed.
- `export-fountain --map`: passed.
- `review-screenplay`: passed and generated review input for quality eval.
- `import-fountain`: passed using a temporary edited Fountain copy and matching
  temporary sidecar map.
- Roundtrip screenplay validation: passed.
- `evaluate-quality`: passed and generated both YAML and Markdown outputs.
- `generated_quality_report.yaml` schema validation: passed.
- Quality report input references: passed. It references validation, review,
  and roundtrip reports.
- Markdown dashboard check: passed. It is non-empty and contains total score,
  dimension table, blocking items, and next actions.
- `semantic_fields_stale: true` warning check: passed. The
  `semantic_staleness` dimension is `warn` with score `70`.
- External-call trace check: passed for Python files in `src` and `tests`; no
  model-provider, HTTP-client, or API-key call patterns were found.

One temporary QA setup attempt wrote the edited sidecar map with a UTF-8 BOM,
which Python JSON loading rejected. The temporary input was recreated with
BOM-less UTF-8, and the same `import-fountain` path passed. A later encoding
check also caught a PowerShell default-decoding issue in the temporary Fountain
copy; the temp file was recreated with explicit UTF-8 so the final sample has
exactly two intended applied changes.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_outline.yaml`
- `examples/output/generated_character_bible.yaml`
- `examples/output/generated_screenplay.yaml`
- `examples/output/generated_screenplay_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`
- `examples/output/generated_review_report.yaml`
- `examples/output/generated_screenplay_roundtrip.yaml`
- `examples/output/generated_screenplay_roundtrip_report.yaml`
- `examples/output/generated_screenplay_roundtrip_validation_report.yaml`
- `examples/output/generated_quality_report.yaml`
- `examples/output/generated_quality_dashboard.md`

## Tests Not Run

- Static type checking was not run because the project does not configure a type
  checker.
- Linting was not run because the project does not configure a lint command.
- Browser or Web UI tests were not run because Stage 8 does not include a Web UI.
- Model-provider, LLM, HTTP, UAT, and automatic patch-application tests were not
  run because they are outside Stage 8 scope.

## Risks

- The quality score is deterministic and threshold based. It is useful for
  gates and routing, but it is not a substitute for author judgment.
- A `pass` readiness can still include warnings, such as skipped dialogue
  review or stale semantic fields after Fountain roundtrip.
- The Markdown dashboard is a companion view; YAML remains the automation source
  of truth.
- Stage 8 contracts remain draft. If frozen later, changes must go through
  `docs/architecture/change-requests/`.

## Gate Decision

Passed. Stage 8 Quality Eval Dashboard meets the contract, aggregator, CLI,
sample output, schema validation, Markdown dashboard, no-model-call, and
regression requirements. The project is ready for Stage 9 LLM provider
abstraction.
