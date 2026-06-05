# QA Report

## Scope

Stage 6 QA covered deterministic multi-agent review reports for generated
screenplay YAML, including:

- `review_report` schema contract.
- deterministic reviewers for character consistency, pacing, dialogue
  naturalness, and shootability.
- `review-screenplay` CLI integration.
- generated `examples/output/generated_review_report.yaml`.
- review report structure and issue field requirements.
- verification that suggested patches are not automatically applied.
- regression coverage for Stage 2 through Stage 5 commands.

This pass did not connect to LLMs, did not run real Codex subagents, did not
apply suggested patches, and did not add UI/API behavior.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
python -m novel2script.cli build-screenplay --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_screenplay.yaml
python -m novel2script.cli review-screenplay --screenplay examples/output/generated_screenplay.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_review_report.yaml
python -m novel2script.cli validate examples/output/generated_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/generated_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
git status --short
```

Additional checks:

```bash
python - <<'PY'
from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

review_path = Path("examples/output/generated_review_report.yaml")
screenplay_path = Path("examples/output/generated_screenplay.yaml")
validation_path = Path("examples/output/generated_screenplay_validation_report.yaml")
fountain_path = Path("examples/output/generated_screenplay.fountain")
map_path = Path("examples/output/generated_screenplay.fountain.map.json")

for path in [review_path, screenplay_path, validation_path, fountain_path, map_path]:
    assert path.exists()
    assert path.stat().st_size > 0

review_doc = yaml.safe_load(review_path.read_text(encoding="utf-8"))
schema = json.loads(Path("schemas/review_report.schema.json").read_text(encoding="utf-8"))
Draft202012Validator(schema).validate(review_doc)
report = review_doc["review_report"]
assert report["reviewers"] == [
    "character_consistency",
    "pacing",
    "dialogue_naturalness",
    "shootability",
]
assert "summary" in report
required = {
    "id",
    "reviewer",
    "target",
    "severity",
    "confidence",
    "issue",
    "evidence",
    "suggestion",
    "requires_human_approval",
}
for issue in report.get("issues", []):
    assert required <= set(issue)
    assert issue.get("suggested_patch", {}).get("operation") in {"replace", "add", "note_only"}

validation = yaml.safe_load(validation_path.read_text(encoding="utf-8"))
assert validation["overall_passed"] is True
sidecar = json.loads(map_path.read_text(encoding="utf-8"))
assert sidecar["mappings"]
PY
```

Suggested patch non-application check:

```bash
python - <<'PY'
from pathlib import Path
import hashlib
path = Path("examples/output/generated_screenplay.yaml")
print(hashlib.sha256(path.read_bytes()).hexdigest())
PY

python -m novel2script.cli review-screenplay --screenplay examples/output/generated_screenplay.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_review_report.yaml

python - <<'PY'
from pathlib import Path
import hashlib
path = Path("examples/output/generated_screenplay.yaml")
print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

External-call check:

```powershell
Get-ChildItem -Recurse -File src,tests |
  Select-String -Pattern 'openai|anthropic|gemini|llm|chat\.completions|responses\.create|requests|httpx|urllib|aiohttp' -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 47 tests collected and 47 passed.
- `parse-novel` CLI: passed, regenerated `examples/output/generated_story_map.yaml`.
- `build-outline` CLI: passed, regenerated `examples/output/generated_outline.yaml`.
- `build-character-bible` CLI: passed, regenerated `examples/output/generated_character_bible.yaml`.
- `build-screenplay` CLI: passed, regenerated `examples/output/generated_screenplay.yaml`.
- `review-screenplay` CLI: passed, generated non-empty `examples/output/generated_review_report.yaml`.
- `review_report` schema validation: passed.
- Review report structure: passed. The report contains reviewers, summary, reviewer results, and an issues array.
- Issue structure check: passed. The current deterministic sample has 0 issues, which is allowed by the Stage 6 contract.
- Suggested patch non-application check: passed. `generated_screenplay.yaml` SHA-256 stayed `266c3c017b5b067594243c9d46a45a8e7675ff767ca22327ae5bcb9b828fdbe4` before and after review.
- Generated screenplay validation: passed, `overall_passed: true`.
- Generated screenplay Fountain export: passed, produced non-empty Fountain file and sidecar map with 12 mappings.
- External-call check: passed for `src` and `tests`; no LLM provider or HTTP client call patterns were found.
- `rg` was attempted for the external-call scan but failed with `Access is denied`; PowerShell `Select-String` fallback was used successfully.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_outline.yaml`
- `examples/output/generated_character_bible.yaml`
- `examples/output/generated_screenplay.yaml`
- `examples/output/generated_review_report.yaml`
- `examples/output/generated_screenplay_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`

## Tests Not Run

- Static type checking was not run because the project does not configure a type checker.
- Linting was not run because the project does not configure a lint command.
- UAT, UI/API tests, LLM tests, real custom-agent orchestration, and patch-application workflows were not run because they are outside Stage 6 scope.

## Risks

- The current deterministic sample has no dialogue elements, so dialogue reviewer CLI behavior is covered by unit tests and the no-dialogue skip path rather than by generated sample issues.
- Reviewers emit advisory `suggested_patch` objects only. A future patch application phase must implement a separate human approval gate before any screenplay mutation.
- Stage 6 contracts remain draft. If frozen later, changes must go through `docs/architecture/change-requests/`.
- Source text in sample artifacts may still display mojibake from the existing sample encoding path; this does not block deterministic structural QA.

## Gate Decision

Passed. Stage 6 deterministic multi-agent review meets the reviewer, CLI,
generated report, schema validation, no-auto-patch, no-LLM, and regression
requirements. The project is ready for Stage 7 Fountain limited round-trip.
