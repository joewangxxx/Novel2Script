# QA Report

## Scope

Stage 9 QA covered the LLM Provider abstraction contract, mock provider,
agent-to-provider router, redacted run log records, Agent Prompt Registry,
example provider/routing configs, and regression coverage for the Stage 8
quality evaluation chain.

This pass did not connect any real model provider, did not make network calls,
did not implement full AI novel-to-screenplay generation, and did not commit
secrets or local private provider configuration.

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
python -m pytest tests/test_llm_provider.py tests/test_llm_router.py
```

Additional Stage 9 checks:

```bash
python - <<'PY'
from pathlib import Path
import yaml

run_log = yaml.safe_load(Path("examples/output/generated_llm_run_log.yaml").read_text(encoding="utf-8"))["llm_run_log"]
routing = yaml.safe_load(Path("examples/output/generated_agent_routing_report.yaml").read_text(encoding="utf-8"))["agent_routing_report"]
assert len(run_log["records"]) == 8
assert len(routing["routes"]) == 8
for record in run_log["records"]:
    assert "prompt_hash" in record
    assert record["stored_prompt"] is False
    assert "prompt" not in record
    assert record["provider"] == "mock_dry_run"
for route in routing["routes"]:
    assert route["resolved_profile"] == "mock_dry_run"
    assert route["stored_prompt"] is False
PY
```

Secret and network-call scan:

```powershell
Get-ChildItem -Recurse -File src,tests,config |
  Select-String -Pattern 'sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{20,}|api[_-]?key\s*[:=]\s*[A-Za-z0-9._-]{12,}' -CaseSensitive:$false

Get-ChildItem -Recurse -File src,tests,config -Include *.py,*.yaml,*.yml |
  Select-String -Pattern 'requests\.|httpx|urllib\.request|aiohttp|openai\.|anthropic\.|gemini' -CaseSensitive:$false
```

The key scan filters documented `N2S_*_API_KEY` environment variable names as
allowed placeholders.

## Results

- `python -m pytest`: passed, 65 tests collected and 65 passed.
- Stage 8 quality evaluation chain: passed from novel parsing through quality
  dashboard generation.
- Mock provider unit tests: passed.
- Router tests: passed. Registered agents resolve to their intended profile and
  execute through `mock_dry_run` by default.
- Unknown agent routing test: passed, blocked with `ProviderRoutingError`.
- Run log redaction test: passed. Records contain `prompt_hash`, `agent_id`,
  `model`, `usage`, `status`, and do not contain full prompt text.
- `generated_llm_run_log.yaml`: generated with 8 redacted mock run records.
- `generated_agent_routing_report.yaml`: generated with 8 agent routes and
  resolved `mock_dry_run` execution.
- `config/llm_providers.example.yaml`: parsed successfully.
- `config/agent_routing.example.yaml`: parsed successfully.
- Secret scan: passed. No real API key patterns were found.
- HTTP/provider SDK scan: passed. No real HTTP client or provider SDK call
  patterns were found in `src`, `tests`, or `config`.

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
- `examples/output/generated_llm_run_log.yaml`
- `examples/output/generated_agent_routing_report.yaml`

## Tests Not Run

- Static type checking was not run because the project does not configure a type
  checker.
- Linting was not run because the project does not configure a lint command.
- Real provider integration tests were not run because Stage 9 intentionally
  defaults to mock/dry-run and forbids network-dependent tests.
- Full AI screenplay generation, UAT, and Web UI tests were not run because they
  are outside Stage 9 scope.

## Risks

- Provider contracts remain draft. After freeze, provider route, run log, or
  safety-boundary changes must go through architecture change requests.
- Mock responses prove routing and audit shape, not creative quality.
- Future real-provider work must keep tests no-network by default and must not
  persist prompts, full novel text, model responses, or credentials.

## Gate Decision

Passed. Stage 9 LLM Provider abstraction and Agent Prompt Registry meet the
mock provider, routing, run-log redaction, prompt registry, no-secret,
no-network, sample artifact, and regression requirements. The project is ready
for Stage 10 first LLM agent integration.
