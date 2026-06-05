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

# Stage 11 QA: Real LLM Provider Opt-In

## Commands

```powershell
python -m pytest

python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.stage11.yaml `
  --run-log temp/semantic_agent_run_log.stage11.yaml

python -m novel2script.cli validate temp/semantic_candidates.stage11.yaml `
  --schema schemas/semantic_candidates.schema.json `
  --out temp/semantic_candidates_stage11_validation.yaml

$env:N2S_QWEN_API_KEY=$null
python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.should_not_exist.yaml `
  --run-log temp/semantic_agent_run_log.should_not_exist.yaml `
  --allow-network

Get-ChildItem -Path src,tests,config,docs,examples -Recurse -File |
  Where-Object { @(".py",".yaml",".yml",".md",".json",".txt") -contains $_.Extension } |
  Select-String -Pattern "sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]+|N2S_DOUBAO|N2S_GLM|doubao_dialogue|glm_structured" -CaseSensitive:$false
```

## Results

- `python -m pytest`: passed, 77 tests collected and 77 passed.
- Default `run-agent story-semantic-parser`: passed in dry-run mode.
- `validate temp/semantic_candidates.stage11.yaml`: passed against
  `schemas/semantic_candidates.schema.json`.
- `run-agent story-semantic-parser --allow-network` with
  `N2S_QWEN_API_KEY` unset: failed closed with a clear provider configuration
  error and produced no output files.
- Secret/profile scan: no real `sk-...` API key was found in repository files.
  Matches were limited to fake test data and documentation safety language.
- Old optional `doubao_dialogue` and `glm_structured` profiles were removed
  from active code/config/prompt routes; only an explanatory Stage 11 note
  remains.

## Tests Not Run

- Real Qwen-Long, Kimi K2.6, or DeepSeek V4-Pro API calls were not executed in
  automated QA. Real calls remain opt-in through environment variables plus
  `--allow-network`.
- Linting and static type checking were not run because the project does not
  configure those commands.

## Gate Decision

Passed. Stage 11 adds a real OpenAI-compatible provider path that is disabled
by default, environment-variable-only, redacted in logs, covered by fake
transport tests, and guarded by explicit `--allow-network`.

## Stage 11 Closeout: Local `.env` And Real Qwen Smoke

### Commands

```powershell
python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.real.retry.yaml `
  --run-log temp/semantic_agent_run_log.real.retry.yaml `
  --allow-network

python -m novel2script.cli validate temp/semantic_candidates.real.retry.yaml `
  --schema schemas/semantic_candidates.schema.json `
  --out temp/semantic_candidates_real_retry_validation.yaml

python -m pytest
```

### Results

- Local `.env` was created and confirmed ignored by Git.
- `.env.example` was added as the only shareable provider-key template.
- First Qwen smoke attempt failed with a transient TLS EOF error before schema
  validation.
- Retry succeeded with:
  - `provider_profile: qwen_long`
  - `dry_run: false`
  - `candidate_count: 3`
  - `errors: 0`
  - `run_record_provider: qwen_long`
  - `run_record_model: qwen-long`
  - `run_record_status: completed`
  - `stored_prompt: false`
  - `finish_reason: length`
  - `total_tokens: 1455`
- Real smoke output validated against
  `schemas/semantic_candidates.schema.json`.
- Temporary run artifacts were scanned for API keys, bearer tokens, and prompt
  text markers; no matches were found.

### Gate Decision

Passed with retry note. Real Qwen-Long connectivity is verified, but the first
attempt showed transient TLS/network instability, so later real-provider stages
should add retry/backoff around provider calls.
