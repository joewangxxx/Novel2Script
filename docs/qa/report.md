# QA Report

## Scope

Stage 10 QA covered the first LLM Agent integration:
`story_semantic_parser`.

The pass verified that the agent runs through the Stage 9 `LLMRouter`, resolves
to `mock_dry_run`, writes schema-valid semantic candidates, writes a redacted
run log, does not mutate deterministic `story_map`, and keeps the Stage 8
quality evaluation regression chain working.

This pass did not connect a real external LLM, did not pass API keys, did not
merge semantic candidates into `story_map`, and did not generate screenplay
content from the agent output.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli run-agent story-semantic-parser --story-map examples/output/generated_story_map.yaml --out examples/output/generated_semantic_candidates.yaml --run-log examples/output/generated_semantic_agent_run_log.yaml --dry-run
python -m novel2script.cli build-outline examples/output/generated_story_map.yaml --out examples/output/generated_outline.yaml
python -m novel2script.cli build-character-bible examples/output/generated_story_map.yaml --out examples/output/generated_character_bible.yaml
python -m novel2script.cli build-screenplay --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --character-bible examples/output/generated_character_bible.yaml --out examples/output/generated_screenplay.yaml
python -m novel2script.cli validate examples/output/generated_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/generated_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
python -m novel2script.cli review-screenplay --screenplay examples/output/generated_screenplay.yaml --character-bible examples/output/generated_character_bible.yaml --story-map examples/output/generated_story_map.yaml --outline examples/output/generated_outline.yaml --out examples/output/generated_review_report.yaml
python -m novel2script.cli import-fountain --screenplay examples/output/generated_screenplay.yaml --fountain examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json --out examples/output/generated_screenplay_roundtrip.yaml --report examples/output/generated_screenplay_roundtrip_report.yaml
python -m novel2script.cli validate examples/output/generated_screenplay_roundtrip.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_screenplay_roundtrip_validation_report.yaml
python -m novel2script.cli evaluate-quality --screenplay examples/output/generated_screenplay_roundtrip.yaml --validation-report examples/output/generated_screenplay_roundtrip_validation_report.yaml --review-report examples/output/generated_review_report.yaml --roundtrip-report examples/output/generated_screenplay_roundtrip_report.yaml --out examples/output/generated_quality_report.yaml --markdown examples/output/generated_quality_dashboard.md
```

Additional checks:

```powershell
Get-FileHash examples/output/generated_story_map.yaml -Algorithm SHA256
```

```bash
python - <<'PY'
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

schema = yaml.safe_load(Path("schemas/semantic_candidates.schema.json").read_text(encoding="utf-8"))
semantic = yaml.safe_load(Path("examples/output/generated_semantic_candidates.yaml").read_text(encoding="utf-8"))
Draft202012Validator(schema).validate(semantic)

story_map = yaml.safe_load(Path("examples/output/generated_story_map.yaml").read_text(encoding="utf-8"))
excerpt = story_map["story_map"]["chapters"][0]["paragraphs"][0]["text_preview"]
run_log_text = Path("examples/output/generated_semantic_agent_run_log.yaml").read_text(encoding="utf-8")
assert "prompt_hash" in run_log_text
assert "stored_prompt: false" in run_log_text
assert "Agent: story_semantic_parser" not in run_log_text
assert "Task: propose source-grounded semantic candidates only." not in run_log_text
assert excerpt not in run_log_text
PY
```

Secret and network-call scans:

```powershell
# Real secret scan, excluding documented env var placeholders such as N2S_QWEN_API_KEY.
Get-ChildItem -Path src,tests,config,docs/prompts -Recurse -File |
  Where-Object { @(".py",".yaml",".yml",".md",".json") -contains $_.Extension } |
  Select-String -Pattern "<real secret regex>" -CaseSensitive:$false

Get-ChildItem -Path src,tests -Recurse -File |
  Where-Object { $_.Extension -eq ".py" } |
  Select-String -Pattern "requests\.|httpx\.|urllib\.request|aiohttp|openai\.|anthropic\.|dashscope|zhipuai|http://|https://" -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 71 tests collected and 71 passed.
- `parse-novel`: passed and generated `examples/output/generated_story_map.yaml`.
- `run-agent story-semantic-parser`: passed with exit code 0.
- `generated_semantic_candidates.yaml`: exists, non-empty, and validates against
  `schemas/semantic_candidates.schema.json`.
- `generated_semantic_agent_run_log.yaml`: exists, non-empty, contains
  `prompt_hash`, and does not contain the prompt text or the checked story map
  excerpt.
- `generated_story_map.yaml` hash before and after `run-agent`: unchanged
  (`E843AF85683A6518D67382048A39D5CF087B2E472E7EBFB5C1322DFFD0E81EDC`).
- Semantic candidates use `provider_profile: mock_dry_run`, `dry_run: true`,
  `human_approval_required: true`, and
  `merge_policy: human_approval_required`.
- Stage 8 quality evaluation regression chain: passed from outline generation
  through `evaluate-quality`.
- Secret scan: passed. Only documented environment variable placeholders were
  observed before filtering; no real API key patterns remained.
- HTTP/provider SDK scan: passed. No real HTTP client or provider SDK call
  patterns were found in `src` or `tests`.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_semantic_candidates.yaml`
- `examples/output/generated_semantic_agent_run_log.yaml`
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

- Real `qwen_long` or other provider calls were not run because Stage 10 remains
  mock/dry-run only.
- Static type checking was not run because the project does not configure a type
  checker.
- Linting was not run because the project does not configure a lint command.
- Candidate merge or human approval workflows were not run because they are
  outside Stage 10 scope.

## Risks

- `semantic_candidates` remains a draft contract. After freeze, schema changes
  must go through architecture change requests.
- Mock dry-run verifies routing, audit, and artifact shape; it does not verify
  real model quality.
- The next stage must choose between real-provider opt-in and human-reviewed
  semantic candidate merge flow. Either path must keep mock/no-network tests as
  the default.

## Gate Decision

Passed. Stage 10 first LLM Agent integration is stable in mock/dry-run mode,
safe by default, auditable, and non-mutating. The project is ready for
`stage_11_semantic_candidate_merge_review`.
