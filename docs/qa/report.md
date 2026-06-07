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

# Unset the Qwen API key in this shell before running this fail-closed check.
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

# Stage 12 QA: Semantic Candidate Review And Merge

## Scope

- Validate the Stage 12 human decision and merge workflow.
- Verify `accept`, `reject`, `edit`, invalid target, and missing source trace.
- Validate the merged story map and merge report contracts.
- Confirm the original story map is not modified in place.
- Scan tracked repository content for credentials, prompt bodies, and temporary
  real-model artifacts.

## Commands Run

```powershell
python -m pytest

python -m novel2script.cli merge-semantic-candidates `
  --story-map examples/output/generated_story_map.yaml `
  --semantic-candidates examples/output/generated_semantic_candidates.yaml `
  --decisions examples/output/generated_semantic_candidate_decisions.yaml `
  --out examples/output/generated_story_map.merged.yaml `
  --report examples/output/generated_semantic_candidate_merge_report.yaml

python -m pytest `
  tests/test_semantic_candidate_merge.py `
  tests/test_semantic_candidate_merge_cli.py -v

git diff --check
git status --short
```

Schema and security checks were also run with local deterministic scripts over
the generated artifacts and Git-tracked text files.

## Results

- Full test suite: passed, 85 tests collected and 85 passed.
- Stage 12 focused suite: passed, 7 tests collected and 7 passed.
- `accept`: appended one schema-valid `key_events` item.
- `reject`: recorded the decision without changing
  `psychological_passages`.
- `edit`: applied human `edited_fields` to one new `timeline` item.
- Invalid target/type pairing: blocked with `target_type_mismatch`; no output
  story map was written.
- Missing `source_trace_ids`: blocked by semantic-candidate schema validation
  and `invalid_source_trace`; no output story map was written.
- `generated_story_map.merged.yaml`: passed
  `schemas/story_map.schema.json`.
- `generated_semantic_candidate_merge_report.yaml`: passed
  `schemas/semantic_candidate_merge_report.schema.json`.
- Human decisions sample: passed
  `schemas/semantic_candidate_decisions.schema.json`.
- Original story map SHA-256 before and after merge:
  `e843af85683a6518d67382048a39d5cf087b2e472e7ebfb5c1322dffd0e81edc`.
- Merge report status is `success`, with one accepted, one rejected, one
  edited, and two applied changes.
- Tracked files contain no private `.env`, recognized API-key pattern, retained
  prompt content in generated run logs, or temporary real-model output.

## Generated Artifacts

- `examples/output/generated_semantic_candidate_decisions.yaml`
- `examples/output/generated_story_map.merged.yaml`
- `examples/output/generated_semantic_candidate_merge_report.yaml`

## Tests Not Run

- No real LLM request was made.
- No frontend or interactive human-review UI was tested because Stage 12 is
  CLI and artifact based.
- Static type checking and linting were not run because the repository does not
  configure those commands.

## Risks

- Decision and merge-report contracts remain draft. Future contract changes
  must use an architecture change request after freeze.
- Human approval quality is outside deterministic validation; Stage 12 proves
  provenance, allowed targets, and fail-closed behavior, not editorial truth.
- Duplicate semantic facts may still require reviewer judgment before approval.

## Gate Decision

Passed. Stage 12 provides an auditable, non-mutating review and merge workflow,
fails closed for invalid targets or missing trace evidence, and is ready for
Stage 13 real-LLM semantic candidate parsing enhancement.

# Stage 13 QA: Real Qwen Semantic Candidate Parsing

## Scope

- Run the complete automated test suite and focused Stage 13 tests.
- Verify valid JSON, malformed JSON, empty response, truncation, invalid trace,
  duplicate candidate, and bounded retry behavior.
- Confirm dry-run remains offline and deterministic.
- Run an explicit `--allow-network` Qwen-Long smoke with a limited retry.
- Validate the semantic-candidates sidecar, story-map immutability, and logging
  redaction.

## Commands Run

```powershell
python -m pytest

python -m pytest `
  tests/test_openai_compatible_provider.py `
  tests/test_story_semantic_parser_agent.py `
  tests/test_story_semantic_agent_cli.py -v

python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.stage13.dry.yaml `
  --run-log temp/semantic_agent_run_log.stage13.dry.yaml `
  --dry-run

python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.stage13.real.yaml `
  --run-log temp/semantic_agent_run_log.stage13.real.yaml `
  --allow-network
```

The real smoke was repeated once after the first schema-invalid model response.
The provider's internal retry policy remained bounded to three attempts for
retryable TLS, 429, and 5xx failures.

## Results

- Full test suite: passed, 98 tests collected and 98 passed.
- Focused Stage 13 suite: passed, 21 tests collected and 21 passed.
- Malformed JSON, empty response, `finish_reason=length`, hallucinated trace,
  duplicate candidate, JSON Mode request, retry limit, and dry-run behavior:
  passed through deterministic tests.
- Dry-run story-map SHA-256 remained
  `e843af85683a6518d67382048a39d5cf087b2e472e7ebfb5c1322dffd0e81edc`.
- Both real Qwen calls completed with `finish_reason: stop`, and the story-map
  hash remained unchanged.
- Both real sidecars passed `schemas/semantic_candidates.schema.json`.
- Both real responses failed
  `schemas/qwen_semantic_model_output.schema.json`, producing zero candidates
  and `invalid_model_output_schema`.
- The first response used fields such as `semantic_traces` and `event`; the
  retry used fields such as `semantic_concept`, `description`, and `sources`.
  Neither followed the required candidate draft structure.
- Run logs retained `stored_prompt: false` and did not contain the prompt,
  checked source excerpt, API key, bearer token, or raw response field.
- A security defect was found: `ValidationError.message` includes part of the
  invalid model instance, so the temporary semantic-candidates sidecar echoed a
  portion of the real response inside its structured error message.
- Git-tracked secret, prompt, and temporary-artifact scans passed.

## Generated Artifacts

Real smoke artifacts were written only under `temp/` for inspection and were
removed after QA. They are not tracked or intended for commit.

## Tests Not Run

- Kimi and DeepSeek were not called.
- No semantic candidate was accepted or merged.
- No additional real Qwen call was made after the two permitted smoke attempts.

## Risks

- The prompt describes the JSON boundary but does not communicate enough of the
  concrete model-output schema for Qwen-Long to reliably produce valid drafts.
- Schema validation errors must be sanitized before being persisted; provider
  response fragments must not appear in sidecar errors.
- CLI exit code currently reflects provider execution, not whether real output
  yielded any valid candidates. QA must inspect structured errors.

## Gate Decision

Failed. Offline behavior and fail-closed parsing are covered and stable, but the
real Qwen acceptance gate did not produce a schema-valid candidate in two
attempts, and an invalid response fragment was persisted in a temporary
sidecar error. Stage 13 must not be committed as complete until both issues are
fixed and the real smoke is rerun.

# Stage 13E QA: Qwen Prompt, Redaction, And Exit Codes

## Scope

- Resume Stage 13 under a fresh blocked audit authorized by the user.
- Strengthen the real Qwen JSON prompt without changing the frozen
  model-output contract.
- Redact schema-validation failures from sidecars, run logs, and CLI stderr.
- Make real-mode CLI failures return nonzero while preserving diagnostic
  artifacts.
- Run one real Qwen smoke only after all offline gates pass.

## Commands Run

```powershell
python -m pytest tests/test_story_semantic_parser_agent.py `
  tests/test_story_semantic_agent_cli.py `
  tests/test_openai_compatible_provider.py -q

python -m pytest

python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out <temporary-directory>/semantic_candidates.yaml `
  --run-log <temporary-directory>/semantic_run_log.yaml `
  --allow-network
```

Git-aware working-tree, diff, ignored-file, sensitive-marker, and temporary
artifact scans were run without printing secret values or provider response
content.

## Results

- TDD red phase reproduced the weak prompt, response-fragment leak, and
  unconditional CLI success.
- Focused Stage 13E suite: passed, 27 tests collected and 27 passed.
- Full suite: passed, 104 tests collected and 104 passed.
- Prompt contract assertions cover the unique root, required fields, allowed
  mappings, forbidden fields, trace whitelist, and valid event example.
- Sensitive-marker tests confirm schema-invalid provider content is absent
  from the sidecar, run log, and CLI stderr.
- Real-mode malformed, empty, schema-invalid, truncated, and all-excluded
  results return nonzero while retaining schema-valid diagnostics.
- Dry-run remains compatible and offline.
- The story-map input remains byte-identical.
- The single resumed real smoke returned nonzero with
  `truncated_model_output`; candidate count was zero and error count was one.
- The real smoke sidecar passed
  `schemas/semantic_candidates.schema.json`.
- The story-map SHA-256 was unchanged by the real smoke.
- Temporary smoke artifacts passed API-key, prompt-template, and full source
  preview scans, then were removed.

## Generated Artifacts

No real smoke artifact was retained. All smoke files were created in a unique
temporary directory and removed after validation.

## Tests Not Run

- No second real Qwen smoke was attempted.
- Kimi and DeepSeek were not called.
- Stage 12 merge was not invoked.

## Risks

- The strengthened prompt and parser are fail-closed, but the live provider
  exhausted the output token limit before producing an acceptable result.
- The next attempt requires human approval and should first decide whether to
  reduce requested candidate scope or increase the bounded response token
  budget without weakening the schema.

## Gate Decision

Blocked. Stage 13E offline repair gates pass, including redaction and CLI
failure semantics, but the sole authorized real smoke produced
`truncated_model_output`. Per the recovery rule, no automatic retry or commit
is allowed; human intervention is required.

# Stage 13F QA: Controlled Candidate Limit And Token Budget

## Scope

- Apply the user-approved recovery of at most three model candidates.
- Raise only the real Qwen response budget from 1024 to 2048 tokens.
- Keep the bounded input at eight excerpts and 120 characters per excerpt.
- Preserve fail-closed truncation, redaction, sidecar, and story-map safety.
- Run one real Qwen smoke with provider retries explicitly disabled.

## Commands Run

```powershell
python -m pytest tests/test_story_semantic_parser_agent.py `
  tests/test_story_semantic_agent_cli.py `
  tests/test_openai_compatible_provider.py -q

python -m pytest
```

The real smoke used the normal CLI path with an in-memory Qwen router whose
provider `max_attempts` was fixed to one. Outputs were directed to a unique
temporary directory.

## Results

- Contract status check: `qwen_semantic_model_output 0.1.0` remains draft;
  no architecture change request was required.
- Model-output `candidates.maxItems` is now three.
- Real requests use `max_tokens: 2048`; dry-run retains 1024.
- The prompt requires zero to three concise candidates and forbids Markdown,
  explanatory text, thinking-process text, and extra fields.
- Focused Stage 13 suite: passed, 28 tests collected and 28 passed.
- Full suite: passed, 105 tests collected and 105 passed.
- Four otherwise valid candidates are rejected with the redacted
  `invalid_model_output_schema` error.
- Existing truncation, sensitive-marker, sidecar, CLI exit, and story-map
  immutability tests remain passing.
- The one authorized real network attempt returned CLI exit code 1 before
  writing a sidecar or run log.
- Safe classification: `provider_failure_before_artifact`.
- Finish reason: unavailable because no provider artifact was produced.
- Candidate count and model-output error list: unavailable for the same reason.
- The story-map SHA-256 remained unchanged.
- Temporary artifacts passed key, prompt-template, source-preview, and raw
  response field scans, then were removed.

## Generated Artifacts

No real smoke artifact was retained. The temporary smoke directory was removed.

## Tests Not Run

- No second network attempt was made.
- The excerpt limit was not reduced from eight to four.
- No token budget above 2048 was attempted.
- Stage 12 merge was not invoked.

## Risks

- The model-output truncation mitigation is covered offline, but this smoke
  failed before an artifact was available, so it did not demonstrate live
  acceptance of the revised prompt and token budget.
- Provider stderr was intentionally not retained; diagnosing the transport or
  provider failure requires a separately authorized, safely instrumented run.

## Gate Decision

Blocked. All Stage 13F offline gates pass, but the sole authorized real smoke
failed before producing diagnostic artifacts. QA retry count has reached the
configured maximum. Do not commit Stage 13 as complete or perform another
network attempt without human intervention.

# Stage 13G-A QA: Offline Provider Error Diagnostics

## Scope

- Diagnose provider failures offline without resetting the exhausted QA retry
  counter.
- Replace raw exception text with structured, redacted provider diagnostics.
- Cover HTTP, DNS, TLS, timeout, invalid JSON, malformed provider response, and
  unknown transport failures.
- Make API key and Base URL loading consistent across process environment and
  local `.env`.
- Stop before any Stage 13G-B network probe.

## Commands Run

```powershell
python -m pytest tests/test_openai_compatible_provider.py `
  tests/test_llm_router.py -q

python -m pytest
```

Git-aware secret scans and provider sensitive-marker artifact scans were also
run. All provider tests use injected transports or patched `urlopen`; no
network call was made.

## Results

- TDD red phase reproduced 17 missing classification and configuration
  behaviors.
- Focused provider/router suite: passed, 26 tests collected and 26 passed.
- Full suite: passed, 120 tests collected and 120 passed.
- Structured provider errors contain only:
  `category`, `status_code`, `retryable`, `attempt`, `max_attempts`,
  `provider_profile`, `model`, and safe `request_id`.
- HTTP classifications:
  - 400: `invalid_request`;
  - 401: `authentication`;
  - 403: `authorization`;
  - 404: `endpoint_not_found`;
  - 429: `rate_limited`;
  - 5xx: `provider_server_error`.
- Connection classifications:
  - DNS: `dns_error`;
  - TLS: `tls_error`;
  - timeout: `timeout`;
  - other URL connection error: `connection_error`.
- Response and fallback classifications:
  - invalid JSON: `invalid_provider_json`;
  - missing provider choices: `invalid_provider_response`;
  - unknown transport exception: `transport_failure`.
- HTTP bodies are no longer read into exception messages.
- Provider exception causes are replaced at the provider boundary before CLI
  reporting.
- API keys and Base URLs now both use process environment first and `.env`
  fallback second.
- QA retry count remains two of two.

## Generated Artifacts

No runtime provider or model artifact was generated.

## Tests Not Run

- No real Qwen API call was made.
- No Stage 13 semantic smoke was run.
- The Stage 13G-B minimal probe was not run because it requires a separate
  human authorization after this gate.

## Risks

- Offline classification proves deterministic redaction and routing, but does
  not identify the live provider category until the separately authorized
  minimal probe is executed.
- `ProviderConfigurationError` remains a local preflight error and is outside
  the transport/runtime classification set.

## Gate Decision

Stage 13G-A passed. Stop here and request explicit human authorization for
Stage 13G-B. The authorized probe must contain no novel text or production
prompt, use at most 32 output tokens, set `max_attempts=1`, and run exactly
once.

# Stage 13G-B QA: Minimal Qwen Provider Probe

## Scope

- Execute the separately authorized minimal Qwen probe exactly once.
- Use no novel content and no production Agent prompt.
- Limit output to 32 tokens and disable provider retry.
- Record only safe connectivity metadata and structured errors.
- Do not execute the full Stage 13 semantic smoke.

## Commands Run

A single direct provider probe was executed with:

- profile: `qwen_long`;
- model: `qwen-long`;
- response format: JSON object;
- `max_tokens: 32`;
- `max_attempts: 1`;
- a constant connectivity-only request containing no repository or novel
  content.

## Results

- Probe exit code: 0.
- Provider status: success.
- Finish reason: `stop`.
- Returned content parsed as a JSON object.
- Usage: 32 input tokens, 5 output tokens, 37 total tokens.
- No retry occurred.
- No provider error category was produced.
- The temporary probe result contained only safe metadata.
- Probe artifact scanning found no API key, Authorization header, prompt text,
  novel content, or raw transport response.
- The temporary probe directory was removed.

## Generated Artifacts

No probe artifact was retained or added to the repository.

## Tests Not Run

- No complete story semantic Agent request was sent.
- No novel excerpt was sent.
- No semantic-candidates sidecar was generated.
- No Stage 12 merge was invoked.

## Risks

- The probe confirms current endpoint, credential, JSON Mode, and basic
  transport functionality only.
- Full semantic response conformance and candidate quality remain deferred
  until a suitable test novel and a separately approved semantic smoke are
  available.

## Gate Decision

Stage 13G-B passed. Provider connectivity diagnostics are no longer blocking
work that uses mock or fixture inputs. Full Stage 13 semantic acceptance remains
deferred and must not be represented as passed.

# Stage 13H QA: Real Sanguo Semantic Candidate Smoke

## Scope

- Use `examples/input/test1_sanguo.txt` as the real five-chapter test novel.
- Generate a temporary deterministic `story_map`.
- Run one and only one real Qwen semantic-candidate request.
- Validate the resulting sidecar and run log without retaining raw model
  output.

## Commands Run

```powershell
python -m pytest tests/test_story_semantic_parser_agent.py `
  tests/test_story_semantic_agent_cli.py `
  tests/test_openai_compatible_provider.py -q

python -m pytest

python -m novel2script.cli parse-novel `
  examples/input/test1_sanguo.txt `
  --out <temp>/test1_sanguo_story_map.yaml
```

The real semantic smoke used the CLI `main()` path with a Qwen provider whose
`max_attempts` was fixed to one in memory. No second semantic smoke was run.

## Results

- Focused Stage 13 suite: passed, 42 tests collected and 42 passed.
- Full suite: passed, 123 tests collected and 123 passed.
- Parser smoke: passed.
- Temporary story map schema validation: passed.
- Parsed chapter count: 5.
- Parsed paragraph count: 71.
- Real semantic smoke CLI exit code: 0.
- Story-map hash remained unchanged.
- Post-smoke validation was not completed because the local validation harness
  failed with a Python one-line syntax error before candidate and security
  summaries were collected.
- Temporary smoke files were removed by the harness cleanup path.

## Generated Artifacts

No temporary smoke artifact was retained.

## Tests Not Run

- No second real semantic smoke was run.
- Candidate trace whitelist, candidate count, error list, and run-log/sidecar
  security scans could not be completed after the harness failure because the
  artifacts had already been cleaned.
- Stage 12 merge was not invoked.

## Risks

- The CLI exit code indicates that the runtime accepted at least one candidate
  and did not encounter blocking semantic errors, but the required independent
  artifact validation evidence was lost.
- Stage 13H must not be marked as passed until the validation harness is fixed
  and a new smoke is explicitly authorized.

## Gate Decision

Blocked. The one authorized real semantic request returned success, but the
post-smoke validation harness failed before collecting the required evidence.
Do not rerun automatically, do not commit Stage 13 as complete, and request
human authorization after the harness is fixed offline.

# Stage 13H-R QA: Validation Harness Repair And Authorized Rerun

## Scope

- Replace the fragile post-smoke artifact validation one-liner with a stable
  script file.
- Verify the script offline with regression tests before any network call.
- Run the single human-authorized real Sanguo semantic smoke once, with no
  automatic retry.
- Keep smoke artifacts in a temporary directory only, validate if present, and
  clean the directory afterward.

## Commands Run

```powershell
python -m pytest tests/test_stage13h_validation_harness.py -q

python -m pytest tests/test_stage13h_validation_harness.py `
  tests/test_story_semantic_parser_agent.py `
  tests/test_story_semantic_agent_cli.py `
  tests/test_openai_compatible_provider.py -q

python -m pytest -q

python -m novel2script.cli parse-novel `
  examples/input/test1_sanguo.txt `
  --out <temp>/test1_sanguo_story_map.yaml
```

The real semantic smoke used the CLI `main()` path with an in-memory
`qwen_long` router and `max_attempts=1`. Exactly one real semantic request was
attempted. No retry was run.

## Results

- Harness regression suite: passed, 2 tests passed.
- Focused Stage 13H suite: passed, 44 tests passed.
- Full suite: passed, 125 tests passed.
- Parser smoke: passed.
- Temporary story map schema validation: passed.
- Parsed chapter count: 5.
- Real semantic smoke CLI exit code: 1.
- Candidate count: 0.
- Error codes: none available because no semantic sidecar was generated.
- Artifact harness validation: not run because the sidecar/run log were not
  produced.
- Story-map hash remained unchanged.
- Temporary smoke directory was removed.

## Generated Artifacts

- `scripts/validate_stage13h_artifacts.py`
- `tests/test_stage13h_validation_harness.py`

No real semantic sidecar, run log, raw response, or prompt artifact was
retained.

## Tests Not Run

- No second real semantic smoke was run.
- Stage 12 merge was not invoked.
- Candidate trace whitelist and sidecar schema validation could not run because
  the real agent failed before writing artifacts.

## Risks

- The stable harness is now available and covered offline.
- The remaining blocker is a provider/runtime failure in the full semantic
  request path. The smoke wrapper intentionally did not print raw stderr to
  avoid leaking transport details, prompt text, or model output.
- A future diagnostic run should capture the already-redacted provider error
  category in a safe metadata-only field before cleanup, then stop without
  retry.

## Gate Decision

Blocked. Stage 13H is not accepted: parser and offline validation gates passed,
but the single authorized real semantic smoke failed with exit code 1 before
schema-valid semantic artifacts were produced. Do not commit Stage 13 as
complete and do not rerun the real semantic smoke without explicit human
authorization.

# Stage 13H-S QA: Authorized Diagnostic Rerun

## Scope

- Reuse the repaired Stage 13H artifact validation harness.
- Run fresh offline focused and full test gates.
- Execute one additional human-authorized real Sanguo semantic smoke with
  `max_attempts=1`.
- Capture only safe metadata: provider category if any, candidate count, finish
  reason, error codes, and harness result.
- Retain no real prompt, raw response, sidecar, run log, or temporary smoke
  artifact.

## Commands Run

```powershell
python -m pytest tests/test_stage13h_validation_harness.py `
  tests/test_story_semantic_parser_agent.py `
  tests/test_story_semantic_agent_cli.py `
  tests/test_openai_compatible_provider.py -q

python -m pytest -q

python -m novel2script.cli parse-novel `
  examples/input/test1_sanguo.txt `
  --out <temp>/test1_sanguo_story_map.yaml
```

The real semantic smoke used the CLI `main()` path with an in-memory
`qwen_long` provider and `max_attempts=1`. Exactly one real semantic request
was executed.

## Results

- Focused Stage 13H suite: passed, 44 tests passed.
- Full suite: passed, 125 tests passed.
- Parser smoke: passed.
- Temporary story map schema validation: passed.
- Parsed chapter count: 5.
- Real semantic smoke CLI exit code: 0.
- Provider profile: `qwen_long`.
- Dry run: `false`.
- Finish reason: `stop`.
- Candidate count: 3.
- Error codes: none.
- Artifact harness exit code: 0.
- Artifact harness result: passed.
- Security scan: passed.
- Story-map hash remained unchanged.
- Temporary smoke directory was removed.

## Generated Artifacts

No real semantic sidecar, run log, raw response, prompt, or temporary smoke
artifact was retained. The only repository artifacts from this recovery remain:

- `scripts/validate_stage13h_artifacts.py`
- `tests/test_stage13h_validation_harness.py`

## Tests Not Run

- No second real semantic smoke was run.
- Stage 12 merge was not invoked.
- Kimi and DeepSeek were not called.

## Risks

- Candidate editorial quality is not asserted by this QA pass; Stage 13H only
  proves schema validity, trace validity, fail-closed behavior, redacted
  logging, and non-mutating real-provider integration.
- Because the real sidecar was intentionally temporary, future human review
  needs a separately approved retained artifact generation step or a fixture
  captured under repository rules.

## Gate Decision

Passed. Stage 13H real Sanguo semantic candidate smoke produced three
schema-valid, trace-valid, human-approval-required candidates through
`qwen_long`, with no errors, no story-map mutation, and no retained sensitive
artifact. Stage 13 can be considered ready for controlled follow-up work.

# Stage 14B QA: Real Candidate Fixture Generation

## Scope

- Use the user-specified external input file:
  `C:\Users\JoeWang\Desktop\test1_sanguo.txt`.
- Stop if that exact external file is unavailable.
- Do not substitute a repository fixture.
- Do not call Qwen unless the external file gate passes.

## Commands Run

```powershell
Test-Path -LiteralPath "C:\Users\JoeWang\Desktop\test1_sanguo.txt"
Test-Path -LiteralPath "..\..\test1_sanguo.txt"
```

## Results

- External input file exists: false.
- Relative external input path exists: false.
- `parse-novel`: not run.
- Real Qwen semantic agent: not run.
- Semantic candidate fixture: not generated.
- Run log fixture: not generated.
- Story map fixture: not generated.

## Generated Artifacts

No Stage 14B fixture artifact was generated.

## Tests Not Run

- Semantic candidates schema validation was not run because no sidecar exists.
- Story map hash comparison was not run because no story map fixture exists.
- Leak scan was not run because no Stage 14B output artifact exists.
- Stage 14C merge was not run.

## Risks

- Stage 14B remains blocked until the exact external input file is restored at
  `C:\Users\JoeWang\Desktop\test1_sanguo.txt` or the user provides a new
  explicit external path.

## Gate Decision

Blocked. The user-specified external input file was missing, so no real Qwen
call was made and no fixture was created.

# Stage 14C QA: Real Candidate Human Decision Merge

## Scope

- Consume the Stage 14B real semantic candidate fixture.
- Create a human decision sample covering accept, reject, and edit.
- Run the existing Stage 12 `merge-semantic-candidates` CLI.
- Validate the decisions, merge report, and merged story map schemas.

## Preconditions

- `examples/output/test1_sanguo_story_map.yaml` must exist.
- `examples/output/test1_sanguo_semantic_candidates.real.yaml` must exist and
  validate against `schemas/semantic_candidates.schema.json`.
- Stage 14B must have passed.

## Results

- `examples/output/test1_sanguo_story_map.yaml`: missing.
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`: missing.
- Stage 14B status: blocked.
- Human decisions file: not generated.
- Merge CLI: not run.
- Merged story map: not generated.
- Merge report: not generated.

## Generated Artifacts

No Stage 14C artifact was generated.

## Tests Not Run

- `semantic_candidate_decisions.schema.json` validation was not run because no
  decisions file was generated.
- `merge-semantic-candidates` was not run because the real semantic candidates
  fixture is missing.
- `semantic_candidate_merge_report.schema.json` validation was not run.
- `story_map.schema.json` validation for a merged story map was not run.
- Leak scan was not run because no Stage 14C output artifact exists.

## Risks

- Stage 14C remains blocked until Stage 14B produces a schema-valid real Qwen
  semantic candidate fixture with enough candidates to cover accept, reject,
  and edit decisions.

## Gate Decision

Blocked. The required Stage 14B fixture artifacts do not exist, so no human
decision sample or merge output can be trusted.

# Stage 14D QA: Full Stage 14 Closeout

## Scope

- Verify Stage 14 real candidate fixture, human decisions, merge report, and
  merged story map.
- Run focused Stage 12/13 tests and full pytest.
- Validate all Stage 14 schemas.
- Run leak scans and story-map hash checks.
- Prepare commit only if all gates pass.

## Preconditions

The following files must exist before Stage 14D can run meaningful QA:

- `examples/output/test1_sanguo_story_map.yaml`
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`
- `examples/output/test1_sanguo_story_map.merged.yaml`
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`

## Results

- `examples/output/test1_sanguo_story_map.yaml`: missing.
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`: missing.
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`: missing.
- `examples/output/test1_sanguo_story_map.merged.yaml`: missing.
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`: missing.
- Stage 14B status: blocked.
- Stage 14C status: blocked.

## Commands Not Run

These commands were intentionally not run because the required artifacts are
missing:

```powershell
python -m pytest tests/test_semantic_candidate_merge.py tests/test_semantic_candidate_merge_cli.py
python -m pytest tests/test_story_semantic_parser_agent.py tests/test_story_semantic_agent_cli.py tests/test_openai_compatible_provider.py
python -m pytest
```

Schema validation, leak scans, and story-map hash checks were also not run
because there are no Stage 14B/14C artifacts to validate.

## Generated Artifacts

No Stage 14D artifact was generated.

## Risks

- Stage 14 cannot be closed until Stage 14B successfully generates the real
  fixture and Stage 14C successfully creates decisions and merge outputs.

## Gate Decision

Blocked. Stage 14D cannot pass because all required Stage 14B/14C output
artifacts are missing. No commit is allowed.

# Stage 14B-R QA: Real Candidate Fixture Generation Rerun

## Scope

- Use the repository input fixture now provided by the user:
  `examples/input/test1_sanguo.txt`.
- Run one authorized real Qwen semantic agent call with no automatic retry.
- Save only schema-valid, redacted, human-reviewable fixture artifacts.

## Commands Run

```powershell
python -m novel2script.cli parse-novel examples/input/test1_sanguo.txt --out examples/output/test1_sanguo_story_map.yaml
python -m novel2script.cli run-agent story-semantic-parser --story-map examples/output/test1_sanguo_story_map.yaml --out examples/output/test1_sanguo_semantic_candidates.real.yaml --run-log examples/output/test1_sanguo_semantic_agent_run_log.real.yaml --allow-network
```

The real Qwen call was executed once through a parent-thread wrapper that set
the `qwen_long` route to `max_attempts=1`.

## Results

- Input file exists: yes.
- `parse-novel`: passed.
- Parsed chapter count: 5.
- Story map schema: valid.
- Real Qwen semantic agent exit code: 0.
- Provider profile: `qwen_long`.
- Model: `qwen-long`.
- `dry_run`: false.
- Provider finish reason: `stop`.
- Candidate count: 3.
- Agent errors: none.
- Semantic candidates schema: valid.
- Story map hash before and after agent run:
  `sha256:1109fa161678fd1cb7cf1ec8708b99aec4549ac489e671d0ceeb791e46b6edd5`.
- Stage 14 output security scan: passed.

## Generated Artifacts

- `examples/output/test1_sanguo_story_map.yaml`
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`
- `examples/output/test1_sanguo_semantic_agent_run_log.real.yaml`

## Tests Not Run

- No second real Qwen call was made.
- No merge was run in Stage 14B-R.

## Risks

- The fixture proves contract compliance and trace safety, not literary quality.
- The fixture uses real model-derived candidates, so downstream merge remains
  human-approval-gated.

## Gate Decision

Passed. Stage 14B-R produced a retained, schema-valid, redacted real Qwen
semantic candidate fixture with three human-approval-required candidates.

# Stage 14C-R QA: Real Candidate Human Decision Merge

## Scope

- Create a human decision sample from the real candidate fixture.
- Cover accept, reject, and edit decisions.
- Run Stage 12 `merge-semantic-candidates` without modifying the source
  story map in place.

## Commands Run

```powershell
python -m novel2script.cli merge-semantic-candidates --story-map examples/output/test1_sanguo_story_map.yaml --semantic-candidates examples/output/test1_sanguo_semantic_candidates.real.yaml --decisions examples/output/test1_sanguo_semantic_candidate_decisions.yaml --out examples/output/test1_sanguo_story_map.merged.yaml --report examples/output/test1_sanguo_semantic_candidate_merge_report.yaml
```

## Results

- Decisions coverage: accept, reject, and edit.
- `semantic_candidate_decisions` schema: valid.
- Merge CLI exit code: 0.
- Merge report schema: valid.
- Merged story map schema: valid.
- Merge status: `success`.
- Merge summary: 3 candidates, 3 decisions, 1 accepted, 1 rejected,
  1 edited, 0 skipped, 0 blocked, 2 applied changes.
- Source story map file hash remained:
  `sha256:1109fa161678fd1cb7cf1ec8708b99aec4549ac489e671d0ceeb791e46b6edd5`.
- Stage 14 output security scan: passed.

## Generated Artifacts

- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`
- `examples/output/test1_sanguo_story_map.merged.yaml`
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`

## Tests Not Run

- No LLM call was made during merge.
- No Stage 12 automatic accept path was added.

## Risks

- The edited decision uses only the candidate's traceable fields; broader
  editorial judgment remains out of scope for this deterministic merge sample.

## Gate Decision

Passed. Real candidates successfully entered the Stage 12 human decision flow
and produced a schema-valid merged story map plus merge report.

# Stage 14D-R QA: Full Stage 14 Closeout

## Scope

- Verify the retained real fixture, decisions, merge report, and merged
  story map.
- Run focused Stage 12/13 tests and the full test suite.
- Validate all Stage 14 schemas.
- Scan Stage 14 artifacts for key, prompt, provider request payload, and model text
  leakage.

## Commands Run

```powershell
python -m pytest tests/test_semantic_candidate_merge.py tests/test_semantic_candidate_merge_cli.py
python -m pytest tests/test_story_semantic_parser_agent.py tests/test_story_semantic_agent_cli.py tests/test_openai_compatible_provider.py
python -m pytest
```

Schema validation was run for:

- `examples/output/test1_sanguo_semantic_candidates.real.yaml`
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`
- `examples/output/test1_sanguo_story_map.merged.yaml`

## Results

- Stage 12 merge focused tests: 10 passed.
- Stage 13 provider/agent focused tests: 42 passed.
- Full pytest: 125 passed.
- Semantic candidates schema: valid.
- Decisions schema: valid.
- Merge report schema: valid.
- Merged story map schema: valid.
- `human_approval_required`: true.
- Real fixture `dry_run`: false.
- Provider metadata: redacted.
- Stage 14 output scan: passed for API key patterns, bearer token values,
  authorization header values, prompt retention markers, provider payload markers,
  and model response retention markers.
- `.env` remains ignored by Git.
- Stage 14 temporary directories: none found.
- Repository-wide literal scan contains expected implementation, test, and
  documentation references to provider header names and redaction test terms;
  no Stage 14 artifact contains those values as retained secrets or provider
  payloads.

## Story Map Hash Check

- The source story map file remained unchanged across the real agent and merge
  operations:
  `sha256:1109fa161678fd1cb7cf1ec8708b99aec4549ac489e671d0ceeb791e46b6edd5`.
- The merge report's before/after output hashes differ because
  `examples/output/test1_sanguo_story_map.merged.yaml` is intentionally a new
  merged artifact, not an in-place mutation of the source story map.

## Generated Artifacts

- `docs/dev/PHASE_14_REAL_CANDIDATE_FIXTURE_AND_MERGE.md`
- `examples/output/test1_sanguo_story_map.yaml`
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`
- `examples/output/test1_sanguo_semantic_agent_run_log.real.yaml`
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`
- `examples/output/test1_sanguo_story_map.merged.yaml`
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`

## Tests Not Run

- No second real Qwen fixture generation call was made.
- No automatic semantic candidate merge acceptance was added.
- No Kimi or DeepSeek call was made.

## Risks

- The repository contains expected source-code and test references to provider
  header names and redaction sentinel strings. QA treated these as allowlisted
  implementation/test references, while Stage 14 generated artifacts were
  scanned strictly.

## Gate Decision

Passed. Stage 14 has a retained real Qwen semantic candidate fixture, a
human-review decision sample covering accept/reject/edit, a successful merge
report, a schema-valid merged story map, passing regression tests, and no
Stage 14 artifact leakage.

# Stage 15B QA: Real Merged Story Map End-to-End Sample Generation

## Scope

- Consume `examples/output/test1_sanguo_story_map.merged.yaml`.
- Use only existing deterministic CLI commands.
- Generate outline, character bible, screenplay, validation report, Fountain,
  review report, roundtrip report, quality report, and Markdown dashboard.
- Confirm the Stage 14 source story map and merged story map are not modified.
- Do not call any LLM, provider, or semantic agent.

## Commands Run

```powershell
python -m novel2script.cli build-outline examples/output/test1_sanguo_story_map.merged.yaml --out examples/output/test1_sanguo_outline.yaml
python -m novel2script.cli build-character-bible examples/output/test1_sanguo_story_map.merged.yaml --out examples/output/test1_sanguo_character_bible.yaml
python -m novel2script.cli build-screenplay --story-map examples/output/test1_sanguo_story_map.merged.yaml --outline examples/output/test1_sanguo_outline.yaml --character-bible examples/output/test1_sanguo_character_bible.yaml --out examples/output/test1_sanguo_screenplay.yaml
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/test1_sanguo_screenplay_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/test1_sanguo_screenplay.yaml --out examples/output/test1_sanguo_screenplay.fountain --map examples/output/test1_sanguo_screenplay.fountain.map.json
python -m novel2script.cli review-screenplay --screenplay examples/output/test1_sanguo_screenplay.yaml --character-bible examples/output/test1_sanguo_character_bible.yaml --story-map examples/output/test1_sanguo_story_map.merged.yaml --outline examples/output/test1_sanguo_outline.yaml --out examples/output/test1_sanguo_review_report.yaml
python -m novel2script.cli import-fountain --screenplay examples/output/test1_sanguo_screenplay.yaml --fountain examples/output/test1_sanguo_screenplay.fountain --map examples/output/test1_sanguo_screenplay.fountain.map.json --out examples/output/test1_sanguo_screenplay_roundtrip.yaml --report examples/output/test1_sanguo_screenplay_roundtrip_report.yaml
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay_roundtrip.yaml --schema schemas/screenplay.schema.json --out examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml
python -m novel2script.cli evaluate-quality --screenplay examples/output/test1_sanguo_screenplay_roundtrip.yaml --validation-report examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml --review-report examples/output/test1_sanguo_review_report.yaml --roundtrip-report examples/output/test1_sanguo_screenplay_roundtrip_report.yaml --out examples/output/test1_sanguo_quality_report.yaml --markdown examples/output/test1_sanguo_quality_dashboard.md
```

## Results

- CLI chain status: passed.
- No `run-agent` command was executed.
- No real or mock LLM provider was invoked.
- `test1_sanguo_outline.yaml`: schema-valid.
- `test1_sanguo_character_bible.yaml`: schema-valid.
- `test1_sanguo_screenplay_validation_report.yaml`: `overall_passed: true`.
- Fountain export: generated Fountain and sidecar map.
- `test1_sanguo_review_report.yaml`: schema-valid.
- Fountain roundtrip status: `skipped`.
- Roundtrip summary: 22 mapped regions, 0 changed regions, 0 applied changes,
  0 skipped changes, 0 blocking issues.
- `test1_sanguo_screenplay_roundtrip_validation_report.yaml`:
  `overall_passed: true`.
- `test1_sanguo_screenplay_roundtrip_report.yaml`: schema-valid.
- `test1_sanguo_quality_report.yaml`: schema-valid.
- Quality readiness: `pass`, score 100, decision `ready_for_author_review`.
- `test1_sanguo_quality_dashboard.md`: generated and non-empty.

## Story Map Hash Check

- Stage 14 source story map hash:
  `sha256:1109fa161678fd1cb7cf1ec8708b99aec4549ac489e671d0ceeb791e46b6edd5`;
  unchanged.
- Stage 14 merged story map hash:
  `sha256:768bf087b4132685fb98c024da82e993dff6f7e285f6fe7521a2dcacda2ade1c`;
  unchanged.

## Generated Artifacts

- `examples/output/test1_sanguo_outline.yaml`
- `examples/output/test1_sanguo_character_bible.yaml`
- `examples/output/test1_sanguo_screenplay.yaml`
- `examples/output/test1_sanguo_screenplay_validation_report.yaml`
- `examples/output/test1_sanguo_screenplay.fountain`
- `examples/output/test1_sanguo_screenplay.fountain.map.json`
- `examples/output/test1_sanguo_review_report.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip_report.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml`
- `examples/output/test1_sanguo_quality_report.yaml`
- `examples/output/test1_sanguo_quality_dashboard.md`

## Tests Not Run

- Full pytest was not run in Stage 15B; that is reserved for Stage 15C.
- No second real Qwen fixture call was made.
- No new semantic candidate merge was run.

## Risks

- The Stage 15B roundtrip used the exported Fountain unchanged, so the
  roundtrip report correctly reports `skipped` rather than `applied`. Stage 15C
  may decide whether a controlled edited-Fountain sample is needed.
- The generated draft remains deterministic scaffolding and is not a polished
  screenplay.

## Gate Decision

Passed. Stage 15B generated the full real-enhanced deterministic sample package
from the Stage 14 merged story map, with schema-valid intermediate reports,
unchanged source hashes, and a passing quality readiness decision.

# Stage 15C QA: End-to-End Quality Explanation

## Scope

- Verify the Stage 15B real-enhanced screenplay sample package.
- Run focused Stage 4/5/6/7/8 tests and full pytest.
- Validate Stage 15 generated artifacts against their schemas.
- Read and explain `quality_report.overall_readiness`.
- Scan Stage 15 artifacts for key, prompt, provider request payload, model response, and
  unapproved model-output retention markers.

## Commands Run

```powershell
python -m pytest tests/test_outline_builder.py tests/test_character_bible_builder.py tests/test_screenplay_builder.py tests/test_screenplay_cli.py
python -m pytest tests/test_review_cli.py tests/test_review_report.py
python -m pytest tests/test_fountain_importer.py tests/test_fountain_roundtrip_cli.py
python -m pytest tests/test_quality_report.py tests/test_quality_cli.py
python -m pytest
```

## Results

- Stage 4/5 focused tests: 13 passed.
- Stage 6 focused tests: 4 passed.
- Stage 7 focused tests: 7 passed.
- Stage 8 focused tests: 6 passed.
- Full pytest: 125 passed.

## Schema Validation

- `examples/output/test1_sanguo_outline.yaml`: valid.
- `examples/output/test1_sanguo_character_bible.yaml`: valid.
- `examples/output/test1_sanguo_screenplay.yaml`: valid.
- `examples/output/test1_sanguo_screenplay_roundtrip.yaml`: valid.
- `examples/output/test1_sanguo_review_report.yaml`: valid.
- `examples/output/test1_sanguo_screenplay_roundtrip_report.yaml`: valid.
- `examples/output/test1_sanguo_quality_report.yaml`: valid.

## Quality Readiness

- Overall status: `pass`.
- Score: 100.
- Decision: `ready_for_author_review`.
- Hard gate failures: none.
- Recommended next action: add dialogue review after dialogue exists in the
  draft.

Dimension status:

- `schema_validity`: pass, hard gate.
- `source_trace_coverage`: pass, hard gate.
- `beat_completeness`: pass.
- `reference_integrity`: pass, hard gate.
- `character_consistency`: pass.
- `pacing`: pass.
- `dialogue_naturalness`: warn; the deterministic dialogue reviewer was
  skipped because the draft has no meaningful dialogue elements to review.
- `shootability`: pass.
- `fountain_roundtrip_safety`: pass, hard gate.
- `semantic_staleness`: pass.
- `overall_readiness`: pass.

Human explanation:

The Stage 15 draft is ready for author review as a traceable first draft. The
hard gates are clean: schema, source traces, references, validation,
roundtrip safety, and quality report generation all pass. The main human
polish item is dialogue: the current deterministic draft does not yet contain
enough dialogue for a meaningful naturalness review, so dialogue writing or
dialogue-agent work should come after the author reviews the structure.

## Story Map Hash Check

- Stage 14 source story map hash:
  `sha256:1109fa161678fd1cb7cf1ec8708b99aec4549ac489e671d0ceeb791e46b6edd5`;
  unchanged.
- Stage 14 merged story map hash:
  `sha256:768bf087b4132685fb98c024da82e993dff6f7e285f6fe7521a2dcacda2ade1c`;
  unchanged.

## Security Scan

Stage 15 generated artifacts were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response marker.
- provider response text markers.
- prompt retention markers.
- prompt content markers.
- provider payload markers.

Result: passed. No Stage 15 generated artifact contains retained key material,
prompt text, provider request payload, model response, `.env` content, or unapproved full
source text.

## Generated Artifacts

No new Stage 15C output artifacts were generated beyond QA updates. Stage 15B
artifacts remain the reviewed sample package.

## Tests Not Run

- No real Qwen call was run.
- No mock LLM call was run.
- No new semantic candidate merge was run.
- No commit was created.

## Risks

- The quality score is deterministic and evidence-based; it does not claim the
  draft is artistically polished.
- The dialogue warning is expected for this scaffolded draft and should guide
  the next creative/editorial phase.

## Gate Decision

Passed. Stage 15C confirms that the real-enhanced end-to-end sample package is
schema-valid, regression-tested, security-scanned, and ready for author review.

# Stage 15D QA: Closeout And Commit Scope Review

## Scope

- Confirm Stage 14 and Stage 15 artifacts remain present and schema-valid.
- Run final full regression tests.
- Inspect Git status and diff statistics.
- Check `.env` ignore behavior.
- Scan generated Stage 14/15 artifacts for secret, prompt, provider payload,
  and raw model response leakage.
- Provide commit grouping guidance without creating a commit.

## Commands Run

```powershell
git status --short
git diff --stat
python -m pytest
git check-ignore -v .env
git ls-files --others --exclude-standard
```

## Results

- Full pytest: 125 passed.
- `git diff --stat`: modified tracked files are `docs/blackboard/state.yaml`
  and `docs/qa/report.md`, with 620 insertions and 3 deletions before this
  Stage 15D closeout section.
- `.env` remains ignored by Git via `.gitignore:20`.
- Untracked files are limited to Stage 14/15 docs and `examples/output`
  artifacts.
- No untracked `.env`, temporary directory, pycache, or external `.txt` novel
  file appears in the pending commit scope.

## Schema Validation

Stage 14 artifacts:

- `examples/output/test1_sanguo_story_map.yaml`: valid.
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`: valid.
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`: valid.
- `examples/output/test1_sanguo_story_map.merged.yaml`: valid.
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`: valid.

Stage 15 artifacts:

- `examples/output/test1_sanguo_outline.yaml`: valid.
- `examples/output/test1_sanguo_character_bible.yaml`: valid.
- `examples/output/test1_sanguo_screenplay.yaml`: valid.
- `examples/output/test1_sanguo_screenplay_roundtrip.yaml`: valid.
- `examples/output/test1_sanguo_review_report.yaml`: valid.
- `examples/output/test1_sanguo_screenplay_roundtrip_report.yaml`: valid.
- `examples/output/test1_sanguo_quality_report.yaml`: valid.

## Security Scan

Generated Stage 14/15 artifacts were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response marker.
- provider response text markers.
- prompt retention markers.
- prompt content markers.
- provider payload markers.

Result: passed. No generated Stage 14/15 artifact contains retained key
material, prompt text, provider payload, raw response, `.env` content, or
unapproved full source text.

The Stage 14 and Stage 15 contract documents contain policy phrases such as
"raw model response" and "provider request payload" only as explicit prohibitions. These are
not retained provider payloads or secrets and should be allowed in documentation
commit scope.

## Suggested Commit Groups

Recommended split if the user authorizes commits:

1. Stage 14 real semantic fixture and merge artifacts:
   - `docs/dev/PHASE_14_REAL_CANDIDATE_FIXTURE_AND_MERGE.md`
   - `examples/output/test1_sanguo_story_map.yaml`
   - `examples/output/test1_sanguo_semantic_candidates.real.yaml`
   - `examples/output/test1_sanguo_semantic_agent_run_log.real.yaml`
   - `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`
   - `examples/output/test1_sanguo_story_map.merged.yaml`
   - `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`

2. Stage 15 real-merged story map E2E draft artifacts:
   - `docs/dev/PHASE_15_REAL_MERGED_STORYMAP_E2E_DRAFT.md`
   - `examples/output/test1_sanguo_outline.yaml`
   - `examples/output/test1_sanguo_character_bible.yaml`
   - `examples/output/test1_sanguo_screenplay.yaml`
   - `examples/output/test1_sanguo_screenplay_validation_report.yaml`
   - `examples/output/test1_sanguo_screenplay.fountain`
   - `examples/output/test1_sanguo_screenplay.fountain.map.json`
   - `examples/output/test1_sanguo_review_report.yaml`
   - `examples/output/test1_sanguo_screenplay_roundtrip.yaml`
   - `examples/output/test1_sanguo_screenplay_roundtrip_report.yaml`
   - `examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml`
   - `examples/output/test1_sanguo_quality_report.yaml`
   - `examples/output/test1_sanguo_quality_dashboard.md`

3. QA and blackboard closeout:
   - `docs/qa/report.md`
   - `docs/blackboard/state.yaml`

## Tests Not Run

- No real Qwen call was run.
- No mock LLM call was run.
- No commit was created.

## Risks

- Stage 14 and Stage 15 changes are currently interleaved in
  `docs/qa/report.md` and `docs/blackboard/state.yaml`; keeping those two files
  in a final closeout commit is safer than trying to split their history by
  hunk.

## Gate Decision

Passed. Stage 14 and Stage 15 are ready for user-authorized commits using the
suggested grouping above.

# Stage 16B QA: Author Review Packet CLI

## Scope

- Implement deterministic `prepare-author-review` CLI.
- Generate a Markdown author review packet and schema-valid YAML decision
  template from Stage 15 artifacts.
- Do not modify screenplay or Stage 15 artifacts.
- Do not call LLMs, providers, or prompt-generation code.

## TDD Evidence

RED:

```powershell
python -m pytest tests/test_author_review.py tests/test_author_review_cli.py
```

Initial result: failed during collection with
`ModuleNotFoundError: No module named 'novel2script.reviewers.author_review'`,
which confirmed the tests targeted missing Stage 16B behavior.

GREEN:

```powershell
python -m pytest tests/test_author_review.py tests/test_author_review_cli.py
```

Result: 4 passed.

## Commands Run

```powershell
python -m novel2script.cli prepare-author-review --screenplay examples/output/test1_sanguo_screenplay.yaml --review-report examples/output/test1_sanguo_review_report.yaml --quality-report examples/output/test1_sanguo_quality_report.yaml --quality-dashboard examples/output/test1_sanguo_quality_dashboard.md --packet examples/output/test1_sanguo_author_review_packet.md --decisions examples/output/test1_sanguo_author_review_decisions.yaml
python -m pytest tests/test_author_review.py tests/test_author_review_cli.py
python -m pytest
```

## Results

- `prepare-author-review` exit code: 0.
- Author review packet generated.
- Author review decisions template generated.
- Focused tests: 4 passed.
- Full pytest: 129 passed.
- `examples/output/test1_sanguo_author_review_decisions.yaml` validates
  against `schemas/author_review.schema.json`.
- Packet includes screenplay artifact path, review summary, quality readiness,
  hard gate failures, next actions, dialogue warning, and author confirmation
  checklist.
- Decisions template defaults to `dialogue_decision:
  request_dialogue_draft` and `next_stage_authorization:
  kimi_dialogue_draft`, matching the Stage 15 quality warning.

## Generated Artifacts

- `src/novel2script/reviewers/author_review.py`
- `tests/test_author_review.py`
- `tests/test_author_review_cli.py`
- `examples/output/test1_sanguo_author_review_packet.md`
- `examples/output/test1_sanguo_author_review_decisions.yaml`

## Security Scan

Generated author-review artifacts were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response marker.
- provider response text markers.
- prompt retention markers.
- prompt content markers.
- provider payload markers.

Result: passed. No prompt, provider payload, raw response, key material, `.env`
content, full screenplay text copy, or full novel text was retained.

## Tests Not Run

- No real Qwen call was run.
- No Kimi or DeepSeek call was run.
- No author decision report summarizer was implemented in this stage.
- No commit was created.

## Risks

- The decisions file is an editable template. It records a recommended default
  path toward dialogue drafting, but a human must still review and edit it
  before any creative model stage runs.

## Gate Decision

Passed. Stage 16B produced deterministic author review packet/decision
artifacts, added CLI coverage, and kept all Stage 15 artifacts unchanged.

# Stage 16C QA: Author Review Sample

## Scope

- Use the Stage 16B author review packet and decisions template.
- Record a sample human review decision approving structure, characters, beats,
  and quality.
- Request dialogue drafting and authorize the next Kimi dialogue draft planning
  stage.
- Generate a schema-valid author review report.
- Do not call LLMs or modify screenplay, quality report, or Stage 15 artifacts.

## Results

- `structure_decision`: approve.
- `character_decision`: approve.
- `beat_decision`: approve.
- `dialogue_decision`: request_dialogue_draft.
- `quality_decision`: approve.
- `next_stage_authorization`: kimi_dialogue_draft.
- `ready_for_next_stage`: true.
- Kimi creative scope is limited to dialogue draft and scene prose enhancement.
- Kimi stage remains forbidden from changing approved source traces, changing
  approved structure without a new author decision, overwriting screenplay in
  place, or calling a model without explicit future-stage network
  authorization.

## Schema Validation

- `examples/output/test1_sanguo_author_review_decisions.yaml`: valid against
  `schemas/author_review.schema.json`.
- `examples/output/test1_sanguo_author_review_report.yaml`: valid against
  `schemas/author_review.schema.json`.

## Security Scan

Author review packet, decisions, and report were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response marker.
- provider response text markers.
- prompt retention markers.
- prompt content markers.
- provider payload markers.

Result: passed. No author review artifact contains key material, prompt text,
provider payload, raw response, `.env` content, full novel text, or full
screenplay copy.

## Generated Artifacts

- `examples/output/test1_sanguo_author_review_report.yaml`

## Tests Not Run

- No real Qwen call was run.
- No Kimi or DeepSeek call was run.
- Full pytest was not rerun in Stage 16C because Stage 16C only adds a
  schema-validated artifact and does not change code.
- No commit was created.

## Risks

- This is a simulated author approval sample. A real author can still edit the
  decisions file before any creative model stage runs.

## Gate Decision

Passed. Stage 16C creates a schema-valid author review report that authorizes a
future Kimi dialogue drafting stage while preserving the no-LLM, no-screenplay
mutation boundary for Stage 16.

# Stage 16D QA: Author Review Closeout And Stage 17 Readiness

## Scope

- Verify the Stage 16 author review packet, decisions, and report.
- Confirm the author review record can gate a future Stage 17 Kimi dialogue
  draft planning stage.
- Run focused author-review and quality tests plus full regression tests.
- Validate the author review decisions and report against
  `schemas/author_review.schema.json`.
- Confirm security boundaries, `.env` ignore status, and commit scope guidance.

## Commands Run

```bash
python -m pytest tests/test_author_review.py tests/test_author_review_cli.py
python -m pytest tests/test_quality_report.py tests/test_quality_cli.py
python -m pytest
git check-ignore -v .env
git status --short
```

Additional deterministic Python validation checked:

- `examples/output/test1_sanguo_author_review_decisions.yaml` schema validity.
- `examples/output/test1_sanguo_author_review_report.yaml` schema validity.
- author review packet readability.
- `dialogue_decision == request_dialogue_draft`.
- `next_stage_authorization == kimi_dialogue_draft`.
- quality readiness remained `ready_for_author_review`.
- author review artifact security scan.

## Results

- Author review focused tests: passed, 4 tests.
- Quality focused tests: passed, 6 tests.
- Full pytest: passed, 129 tests.
- `.env` remains ignored by `.gitignore`.
- Quality readiness remains:
  - `status: pass`
  - `score: 100`
  - `decision: ready_for_author_review`
  - `hard_gate_failures: []`
- `dialogue_decision`: `request_dialogue_draft`.
- `next_stage_authorization`: `kimi_dialogue_draft`.
- `author_review_report.metadata.ready_for_next_stage`: true.

## Schema Validation

- `examples/output/test1_sanguo_author_review_decisions.yaml`: valid against
  `schemas/author_review.schema.json`.
- `examples/output/test1_sanguo_author_review_report.yaml`: valid against
  `schemas/author_review.schema.json`.

## Security Scan

Author review packet, decisions, and report were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response marker.
- provider response text markers.
- prompt retention markers.
- prompt content markers.
- provider payload markers.

Result: passed. No Stage 16 author review artifact contains key material,
Authorization header values, prompt content, provider request payload, model response, `.env`
content, full novel text, or full screenplay copy.

## Commit Scope Recommendation

Do not include `.env`, temporary directories, `__pycache__`, or unrelated local
files.

Recommended Stage 16 commit scope:

- `docs/dev/PHASE_16_AUTHOR_REVIEW_UX_CLI.md`
- `schemas/author_review.schema.json`
- `src/novel2script/reviewers/author_review.py`
- `src/novel2script/cli.py`
- `tests/test_author_review.py`
- `tests/test_author_review_cli.py`
- `examples/output/test1_sanguo_author_review_packet.md`
- `examples/output/test1_sanguo_author_review_decisions.yaml`
- `examples/output/test1_sanguo_author_review_report.yaml`
- `docs/qa/report.md`
- `docs/blackboard/state.yaml`

Stage 14 and Stage 15 artifacts are still present in the working tree and
should be committed separately if preserving phase-level commit boundaries.

## Tests Not Run

- No real Qwen call was run.
- No Kimi or DeepSeek call was run.
- No Stage 17 prompt, provider, or creative drafting logic was executed.
- No commit was created.

## Risks

- The author review approval is represented by a sample decision artifact. A
  real author can still revise the decision file before Stage 17 runs.
- Stage 17 must treat `kimi_dialogue_draft` as planning authorization only. Any
  real model execution still needs a future explicit network/model
  authorization.

## Gate Decision

Passed. Stage 16D confirms the author review loop is schema-valid, test-backed,
safe to retain, and ready to gate Stage 17 Kimi dialogue draft contract work.

# Stage 17 QA: Kimi Dialogue Scene Draft Contract

## Scope

- Define the Kimi dialogue/scene creative draft candidate contract.
- Add `schemas/creative_draft_candidates.schema.json`.
- Add the `kimi_dialogue_scene_drafter` prompt and route it through the Stage 9
  provider abstraction.
- Confirm Stage 17 does not call Kimi, does not call any real LLM, does not
  modify screenplay, and does not modify Stage 15/16 artifacts.
- Verify the contract with deterministic tests and full regression tests.

## TDD Evidence

RED:

```powershell
python -m pytest tests/test_creative_draft_contract.py
```

Initial result: 4 failures. The schema, prompt, Stage 17 document, and routing
entry were missing, which confirmed the test covered the new contract assets.

GREEN:

```powershell
python -m pytest tests/test_creative_draft_contract.py
```

Result: 4 passed.

## Commands Run

```powershell
python -m pytest tests/test_creative_draft_contract.py
python -m pytest
git status --short
```

Additional deterministic validation checked:

- `schemas/creative_draft_candidates.schema.json` loads as a Draft 2020-12 JSON
  Schema.
- A minimal mock `creative_draft_candidates` fixture validates against the
  schema.
- `config/agent_routing.example.yaml` maps
  `kimi_dialogue_scene_drafter` to `kimi_creative`.
- `kimi_dialogue_scene_drafter` has `fallback_profile: mock_dry_run`.
- `kimi_dialogue_scene_drafter` has
  `output_policy: human_approval_required`.
- `docs/prompts/kimi_dialogue_scene_drafter.md` contains the candidate-only
  and no-screenplay-mutation boundaries.

## Results

- Focused Stage 17 contract tests: passed, 4 tests.
- Full pytest: passed, 133 tests.
- Contract freeze check: current blackboard contract status is `draft`; no
  architecture change request was required.
- Schema design: added `creative_draft_candidates` root with required
  authorization, candidate, error, metadata, source trace, and source trace ID
  structures.
- Prompt design: candidate-only, no Markdown, no chain-of-thought, no screenplay
  mutation, no source-trace mutation, and `reviewer_note` on insufficient
  evidence.
- Routing design: `kimi_dialogue_scene_drafter` routes to `kimi_creative`, falls
  back to `mock_dry_run`, and requires human approval.
- Stage 17 document explicitly says Stage 17 does not call Kimi, does not call
  any real LLM, and must not modify screenplay or `source_trace`.

## Security Scan

New or modified Stage 17 files were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- environment secret assignments.
- prompt-retention flags set to true.

Result: passed. No Stage 17 file contains key material, bearer token,
Authorization header value, `.env` secret assignment, or prompt-retention flag.

Raw model response marker text appears only in schema metadata and documentation
prohibition language. No provider payload or raw model response is retained.

## Generated Artifacts

- `docs/dev/PHASE_17_KIMI_DIALOGUE_SCENE_DRAFT_CONTRACT.md`
- `schemas/creative_draft_candidates.schema.json`
- `docs/prompts/kimi_dialogue_scene_drafter.md`
- `tests/test_creative_draft_contract.py`

Updated:

- `config/agent_routing.example.yaml`
- `docs/prompts/agent-routing.md`
- `docs/architecture/schema.md`
- `docs/architecture/folder-plan.md`
- `docs/qa/report.md`
- `docs/blackboard/state.yaml`

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No creative draft runner or CLI was implemented.
- No creative candidates output fixture was generated.
- No screenplay, Stage 15 artifact, or Stage 16 artifact was modified.
- No commit was created.

## Risks

- Stage 17 is a contract. It does not prove creative quality or provider
  behavior.
- Stage 18 must remain mock-first and must keep real Kimi network execution
  behind explicit future authorization.
- Candidate application remains out of scope; a later human approval flow must
  decide how to apply any creative text.

## Gate Decision

Passed. Stage 17 defines a draft, human-approval-only Kimi dialogue/scene
candidate sidecar contract and is ready for Stage 18 mock-first implementation.

# Stage 18A QA: Kimi Dialogue Scene Draft Mock-First Runner

## Scope

- Implement a mock-first `kimi_dialogue_scene_drafter` runner.
- Add CLI support under `run-agent kimi-dialogue-scene-drafter`.
- Generate schema-valid creative draft candidate sidecar and redacted run log
  samples.
- Keep real Kimi and all real LLM calls disabled.
- Do not mutate screenplay, story map, source traces, or Stage 15/16/17
  artifacts.

## TDD Evidence

RED:

```powershell
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py
```

Initial result: collection failed with
`ModuleNotFoundError: No module named 'novel2script.agents.creative_draft'`.
This confirmed the tests targeted missing Stage 18A runner behavior.

GREEN:

```powershell
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py
```

Result: 8 passed.

## Commands Run

```powershell
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.yaml --author-review-report examples/output/test1_sanguo_author_review_report.yaml --review-report examples/output/test1_sanguo_review_report.yaml --quality-report examples/output/test1_sanguo_quality_report.yaml --out examples/output/test1_sanguo_creative_draft_candidates.mock.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.mock.yaml --dry-run
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py
python -m pytest tests/test_creative_draft_contract.py
python -m pytest
git status --short
```

Additional deterministic validation checked:

- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml` validates
  against `schemas/creative_draft_candidates.schema.json`.
- Candidate types include `dialogue_insert`, `beat_externalization`, and
  `scene_action_enhancement`.
- Candidate targets reference real screenplay `scene_id` and `beat_id` values.
- The source screenplay file bytes remain unchanged in tests.
- Run log contains `stored_prompt: false`.
- Run log does not contain prompt text, raw model response marker, provider request payload, or the
  checked screenplay action text.

## Results

- Stage 18A focused tests: passed, 8 tests.
- Stage 17 contract regression tests: passed, 4 tests.
- Full pytest: passed, 141 tests.
- CLI sample generation: passed with exit code 0.
- Generated candidate count: 3.
- `provider_profile`: `mock_dry_run`.
- `intended_provider_profile`: `kimi_creative`.
- `dry_run`: true.
- `human_approval_required`: true.
- Unauthorized author review input returns a nonzero CLI exit code and writes a
  schema-valid blocked sidecar.
- `--allow-network` is rejected for this agent in Stage 18A.

## Schema Notes

`schemas/creative_draft_candidates.schema.json` remains draft. Stage 18A made a
small draft-contract adjustment so blocked outputs can remain schema-valid when
`author_review_report.next_stage_authorization` is not
`kimi_dialogue_draft`. Successful outputs still use
`next_stage_authorization: kimi_dialogue_draft`.

## Security Scan

Stage 18A implementation, tests, docs, generated candidates, and run log were
scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- environment secret assignments.
- prompt-retention flags set to true.

Result: passed. No key material, bearer token, Authorization header value,
`.env` secret assignment, retained prompt flag, raw provider response, provider
payload, full screenplay text, or full novel text was found in the Stage 18A
outputs.

## Generated Artifacts

- `src/novel2script/agents/creative_draft.py`
- `tests/test_creative_draft_agent.py`
- `tests/test_creative_draft_cli.py`
- `docs/dev/PHASE_18_KIMI_DIALOGUE_SCENE_DRAFT_MOCK_FIRST.md`
- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`
- `examples/output/test1_sanguo_creative_draft_run_log.mock.yaml`

Updated:

- `src/novel2script/cli.py`
- `schemas/creative_draft_candidates.schema.json`
- `docs/qa/report.md`
- `docs/blackboard/state.yaml`

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No creative draft candidate was applied.
- No merged screenplay was generated.
- No commit was created.

## Risks

- The mock candidate text is intentionally generic and only verifies artifact
  shape, trace retention, and review boundary.
- Current screenplay elements do not have stable `element_id` fields, so Stage
  18A candidates target real `scene_id` and `beat_id` values only. Future
  element-level rewrite candidates must wait until screenplay artifacts expose
  stable element IDs.
- Real Kimi behavior remains untested and must stay behind a later explicit
  authorization gate.

## Gate Decision

Passed. Stage 18A provides a deterministic, schema-valid, no-network
mock-first Kimi dialogue/scene draft candidate runner and CLI. The project is
ready for Stage 18B candidate review/apply-contract design or a real Kimi smoke
contract, but real Kimi calls remain forbidden until explicitly authorized.

# Stage 18B QA: Mock Creative Draft Sample

## Scope

- Regenerate the `test1_sanguo` mock creative draft candidate fixture through
  the Stage 18A CLI.
- Validate the fixture against `schemas/creative_draft_candidates.schema.json`.
- Confirm candidate target IDs resolve against the source screenplay.
- Confirm source screenplay and author review report hashes remain unchanged.
- Confirm no real network or real LLM call is made.
- Scan generated artifacts for secrets, prompt bodies, provider payloads, raw
  model response markers, and full-text leakage markers.

## Commands Run

```powershell
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.yaml --author-review-report examples/output/test1_sanguo_author_review_report.yaml --review-report examples/output/test1_sanguo_review_report.yaml --quality-report examples/output/test1_sanguo_quality_report.yaml --out examples/output/test1_sanguo_creative_draft_candidates.mock.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.mock.yaml --dry-run
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py tests/test_creative_draft_contract.py
python -m pytest
```

Additional deterministic validation checked:

- creative draft candidate schema validity.
- candidate count.
- required candidate type coverage.
- `target.scene_id` exists in screenplay.
- `target.beat_id`, when present, belongs to the target scene.
- `target.element_id`, when present, belongs to the target scene.
- `source_trace` and `source_trace_ids` are present for every candidate.
- `human_approval_required: true`.
- `dry_run: true`.
- `provider_profile: mock_dry_run`.
- `metadata.intended_provider_profile: kimi_creative`.
- run log has `stored_prompt: false`.

## Results

- CLI sample generation: passed with exit code 0.
- Focused creative draft tests: passed, 12 tests.
- Full pytest: passed, 141 tests.
- Candidate file schema: valid.
- Candidate count: 3.
- Candidate type coverage:
  - `dialogue_insert`
  - `beat_externalization`
  - `scene_action_enhancement`
- Target validation: passed; all target scene IDs exist and all target beat IDs
  belong to their target scene.
- Source trace validation: passed; all candidates contain `source_trace` and
  `source_trace_ids`.
- `human_approval_required`: true.
- `dry_run`: true.
- `provider_profile`: `mock_dry_run`.
- Intended provider profile: `kimi_creative`.

## Hash Check

- Source screenplay SHA-256:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`;
  unchanged before and after generation.
- Author review report SHA-256:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`;
  unchanged before and after generation.

## Schema Note

Stage 18B found that the draft schema field name for raw model response
retention caused the generated sidecar to contain the raw response marker, conflicting
with the Stage 18B artifact safety gate. Because the contract is still draft,
the metadata field was renamed to `model_response_retained` with the same
`false` retention meaning. Tests and generated artifacts were regenerated and
revalidated after the change.

## Security Scan

Generated candidate and run log artifacts were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response markers.
- prompt content markers.
- provider payload markers.
- environment secret assignments.

Result: passed. The generated artifacts contain no API key, Bearer token,
Authorization header value, raw model response marker, prompt content, provider
request payload, `.env` content, full novel text, or full screenplay text.

## Generated Artifacts

- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`
- `examples/output/test1_sanguo_creative_draft_run_log.mock.yaml`

Updated:

- `schemas/creative_draft_candidates.schema.json`
- `src/novel2script/agents/creative_draft.py`
- `tests/test_creative_draft_agent.py`
- `tests/test_creative_draft_contract.py`
- `docs/dev/PHASE_17_KIMI_DIALOGUE_SCENE_DRAFT_CONTRACT.md`
- `docs/architecture/schema.md`
- `docs/qa/report.md`
- `docs/blackboard/state.yaml`

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No creative candidate was applied.
- No merged screenplay was generated.
- No commit was created.

## Risks

- The fixture is a mock baseline for shape, traceability, target resolution, and
  leakage behavior. It is not an artistic quality sample.
- Real Kimi output remains untested and must be covered by a future explicit
  smoke contract and authorization.

## Gate Decision

Passed. Stage 18B confirms the mock creative draft sample is schema-valid,
traceable, target-resolving, source-preserving, human-review-only, and safe as a
baseline before any future real Kimi call.

# Stage 18C QA: Mock-First Creative Draft Closeout

## Scope

- Close out Stage 18 mock-first Kimi dialogue/scene drafting.
- Confirm the offline runner, CLI, schema, routing, sample artifact, run log,
  and related upstream gates remain stable.
- Verify author review and story semantic regressions still pass.
- Confirm the mock fixture is suitable as the offline gate before Stage 19 real
  Kimi readiness work.

## Commands Run

```powershell
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py
python -m pytest tests/test_author_review.py tests/test_author_review_cli.py
python -m pytest tests/test_story_semantic_parser_agent.py tests/test_story_semantic_agent_cli.py
python -m pytest
git check-ignore -v .env
git status --short
```

Additional deterministic validation checked:

- mock creative draft fixture schema validity;
- run log root and `stored_prompt: false`;
- `kimi_dialogue_scene_drafter` routing;
- target scene/beat references against the screenplay;
- all creative candidates require human approval;
- source screenplay and author review report hashes;
- generated artifact security scan.

## Results

- Creative draft focused tests: passed, 8 tests.
- Author review focused tests: passed, 4 tests.
- Story semantic focused tests: passed, 22 tests.
- Full pytest: passed, 141 tests.
- `.env` remains ignored by `.gitignore`.
- No real Kimi call was made.
- No real LLM call was made.
- No screenplay mutation occurred.
- No author review report mutation occurred.

## Schema And Routing Validation

- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`: valid
  against `schemas/creative_draft_candidates.schema.json`.
- Candidate count: 3.
- Candidate types:
  - `dialogue_insert`
  - `beat_externalization`
  - `scene_action_enhancement`
- All candidates have `requires_author_approval: true`.
- All candidates have `merge_policy: human_approval_required`.
- All target `scene_id` values exist in the screenplay.
- All target `beat_id` values belong to the target scene.
- No `element_id` is emitted because the current screenplay artifact has no
  stable element IDs.
- `creative_draft_run_log` root exists.
- Run log has `stored_prompt: false`.
- Run log `provider_profile`: `mock_dry_run`.
- Run log `intended_provider_profile`: `kimi_creative`.
- Route config:
  - `provider_profile: kimi_creative`
  - `fallback_profile: mock_dry_run`
  - `prompt_file: docs/prompts/kimi_dialogue_scene_drafter.md`
  - `output_policy: human_approval_required`
- Global `dry_run_default`: true.

## Hash Check

- Source screenplay SHA-256:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Author review report SHA-256:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`.

These match the Stage 18B verified values.

## Security Scan

Generated creative draft candidate and run log artifacts were scanned for:

- API key patterns.
- Bearer token values.
- Authorization header values.
- raw model response markers.
- prompt content markers.
- provider payload markers.
- environment secret assignments.

Result: passed. No generated Stage 18 artifact contains key material, bearer
token, Authorization header value, retained raw model response marker, prompt
content, provider request payload, `.env` content, full novel text, or full screenplay text.

## Suggested Commit Scope

Do not include `.env`, temporary directories, `__pycache__`, or unrelated local
files.

Recommended Stage 18 commit groups:

1. Stage 18 agent and CLI implementation:
   - `src/novel2script/agents/creative_draft.py`
   - `src/novel2script/cli.py`

2. Stage 18 tests:
   - `tests/test_creative_draft_agent.py`
   - `tests/test_creative_draft_cli.py`
   - `tests/test_creative_draft_contract.py`

3. Stage 18 mock artifacts:
   - `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`
   - `examples/output/test1_sanguo_creative_draft_run_log.mock.yaml`

4. QA, blackboard, and documentation:
   - `docs/dev/PHASE_18_KIMI_DIALOGUE_SCENE_DRAFT_MOCK_FIRST.md`
   - `schemas/creative_draft_candidates.schema.json`
   - `docs/dev/PHASE_17_KIMI_DIALOGUE_SCENE_DRAFT_CONTRACT.md`
   - `docs/architecture/schema.md`
   - `docs/architecture/folder-plan.md`
   - `docs/prompts/kimi_dialogue_scene_drafter.md`
   - `docs/prompts/agent-routing.md`
   - `config/agent_routing.example.yaml`
   - `docs/qa/report.md`
   - `docs/blackboard/state.yaml`

Stage 14, Stage 15, and Stage 16 files are still present in the working tree and
should be committed separately if preserving phase-level history.

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No creative candidate was applied to screenplay.
- No merged screenplay was generated.
- No commit was created.

## Risks

- The Stage 18 fixture is a mock baseline and does not evaluate real Kimi
  creative quality.
- Stage 19 must explicitly authorize any real Kimi call, use
  `max_attempts=1`, save only schema-valid candidate sidecars, avoid retaining
  prompts/raw responses/provider bodies, and never auto-apply candidates to the
  screenplay.

## Gate Decision

Passed. Stage 18 mock-first Kimi dialogue/scene drafter is stable as an offline
gate and ready for Stage 19 real Kimi creative draft readiness contract work.

# QA Report - Stage 19A Kimi Real Creative Draft Readiness

## Scope

Stage 19A defines the fail-closed readiness contract for a future real Kimi
dialogue/scene creative draft run. This stage did not call Kimi, did not call any
real LLM, did not modify screenplay artifacts, and did not apply creative draft
candidates.

## Commands Run

- `python -m pytest tests/test_creative_draft_real_readiness.py`
- `python -m pytest`
- Stage 19A schema/routing/security scan script:
  - validated `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`
    against `schemas/creative_draft_candidates.schema.json`
  - verified `kimi_dialogue_scene_drafter` routes to `kimi_creative` with
    `mock_dry_run` fallback and `human_approval_required` output policy
  - verified no real Kimi output artifacts exist
  - scanned Stage 19A files for key, bearer, Authorization, prompt-retention,
    model-response-retention, and provider-body-retention markers
- `git check-ignore -q .env`

## Results

- Focused readiness tests: passed, `3 passed`.
- Full pytest: passed, `144 passed`.
- Mock fixture schema validation: passed.
- Agent routing check: passed.
- Real Kimi output absence check: passed.
- `.env` ignore check: passed.

## Real Call Gates Defined

Stage 20 may only make a real Kimi call after all hard gates are true:

- author review report exists and authorizes `kimi_dialogue_draft`;
- mock creative draft fixture is schema-valid;
- creative draft schema and readiness tests pass;
- routing points `kimi_dialogue_scene_drafter` to `kimi_creative`;
- `.env` contains the required Kimi credential without printing or saving it;
- the user grants explicit network authorization for that stage;
- `max_attempts=1`;
- at most one real Kimi call;
- provider/runtime failure stops without retry;
- schema-invalid output stops without repair or retry;
- `finish_reason=length` stops without parsing partial output;
- `candidate_count > 0`;
- only schema-valid candidate sidecars may be saved;
- run logs may retain only redacted metadata;
- prompt, model response, provider request payload, API keys, bearer values, and
  Authorization values must not be saved;
- candidates must not be auto-applied to screenplay.

## Generated Artifacts

- `docs/dev/PHASE_19_KIMI_REAL_CREATIVE_DRAFT_READINESS.md`
- `tests/test_creative_draft_real_readiness.py`

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No creative candidate sidecar was generated from a real provider.
- No screenplay or Stage 15/16/18 artifact was modified.
- No commit was created.

## Risks

- Stage 19A is a readiness contract only. Real Kimi behavior is not validated
  until a separately authorized Stage 20 smoke.
- If Stage 20 produces schema-invalid, truncated, empty, or zero-candidate
  output, the pipeline must stop and preserve only redacted diagnostics.

## Gate Decision

Passed. Stage 19A has a tested readiness contract for retaining future real Kimi
creative draft candidates safely, while preserving human approval and preventing
automatic screenplay mutation.

# QA Report - Stage 19B Offline Kimi Creative Readiness Gate

## Scope

Stage 19B implements a deterministic offline readiness gate for a future real
Kimi dialogue/scene creative draft run. The gate checks local author
authorization, mock fixture validity, candidate target resolution, routing,
credential presence, and no-retention/no-auto-apply policy. It does not call
Kimi, does not enable network access, and does not modify screenplay artifacts.

## Commands Run

- `python -m pytest tests/test_creative_draft_real_readiness.py`
- `python -m novel2script.cli check-real-creative-draft-readiness --screenplay examples/output/test1_sanguo_screenplay.yaml --author-review-report examples/output/test1_sanguo_author_review_report.yaml --mock-candidates examples/output/test1_sanguo_creative_draft_candidates.mock.yaml --out examples/output/test1_sanguo_kimi_real_readiness_report.yaml`
- readiness report validation script
- `python -m pytest`
- Stage 19B leak marker scan

## Results

- TDD red: observed expected failures for missing
  `novel2script.agents.creative_draft_readiness` module and missing
  `check-real-creative-draft-readiness` CLI command.
- Focused tests after implementation: passed, `10 passed`.
- Full pytest: passed, `151 passed`.
- Readiness report status:
  `ready_pending_network_authorization`.
- Kimi key presence is recorded only as `kimi_key_present: true`; the key value
  is not written.
- Real call policy remains offline:
  `max_attempts: 1`, `allow_network: false`,
  `real_run_authorized: false`.

## Generated Artifacts

- `src/novel2script/agents/creative_draft_readiness.py`
- `tests/test_creative_draft_real_readiness.py`
- `examples/output/test1_sanguo_kimi_real_readiness_report.yaml`
- `docs/dev/PHASE_19_KIMI_REAL_CREATIVE_DRAFT_READINESS.md`

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No creative draft candidate was applied to screenplay.
- No Stage 20 smoke was attempted.
- No commit was created.

## Security Scan

Stage 19B implementation, tests, documentation, and readiness report were
scanned for API key patterns, bearer token values, Authorization header values,
prompt/model-response/provider-body retention flags, and enabled retention
policy markers. Result: passed.

## Risks

- The readiness report can confirm offline prerequisites, but the actual real
  Kimi response quality and schema compliance remain untested until a separately
  authorized Stage 20 one-shot run.
- If `.env` or environment configuration changes before Stage 20, the readiness
  gate should be rerun before any real request.

## Gate Decision

Passed. Stage 19B offline readiness gate is implemented and reports the current
sample chain as ready pending explicit Stage 20 network authorization.

# QA Report - Stage 19C Kimi Real Creative Readiness QA

## Scope

Stage 19C verifies the Stage 19 offline readiness contract and readiness gate
before requesting human authorization for a future Stage 20 one-shot real Kimi
creative draft run. No real Kimi call was executed.

## Commands Run

- `python -m pytest tests/test_creative_draft_real_readiness.py`
- `python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py`
- `python -m pytest tests/test_author_review.py tests/test_author_review_cli.py`
- `python -m pytest`
- schema/hash/readiness validation script
- Stage 19 security scan
- `git check-ignore -q .env`
- `git status --short`

## Results

- Readiness tests: passed, `10 passed`.
- Creative draft agent and CLI tests: passed, `8 passed`.
- Author review tests: passed, `4 passed`.
- Full pytest: passed, `151 passed`.
- Readiness status: `ready_pending_network_authorization`.
- Real call executed: false.
- `max_attempts`: 1.
- `allow_network`: false.
- `real_run_authorized`: false.
- `auto_apply_allowed`: false.
- Prompt, model response, and provider payload retention: false.

## Schema Validation

- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml` validated
  against `schemas/creative_draft_candidates.schema.json`: passed.
- `schemas/creative_draft_readiness_report.schema.json` is not present, so
  readiness report schema validation was not run. The report structure is
  covered by `tests/test_creative_draft_real_readiness.py`.

## Hash Checks

- `examples/output/test1_sanguo_screenplay.yaml` SHA-256:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- `examples/output/test1_sanguo_author_review_report.yaml` SHA-256:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`.
- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml` SHA-256:
  `fc0cfe7ab4d0265cdb966c432651003d8f3575d596ae4f1bc6411e8b50a9de84`.

These artifacts were not modified by Stage 19C.

## Security Scan

Stage 19 files and outputs were scanned for key patterns, bearer token values,
Authorization header values, raw model response markers, retained prompt content
markers, provider payload markers, `.env` content, and full-source retention
markers. Result: passed.

The readiness report records only `kimi_key_present: true`; it does not record
the key value.

`.env` remains ignored by Git.

## Tests Not Run

- No real Kimi call was run.
- No real LLM call was run.
- No Stage 20 smoke was attempted.
- No creative draft candidate was applied to screenplay.
- No commit was created.

## Gate Decision

Passed. Stage 19 offline readiness QA is complete. The repository is ready to
request explicit human authorization for Stage 20, where a single real Kimi call
may be attempted under the no-retry, no-retention, no-auto-apply policy.

# QA Report - Stage 20 Real Kimi Creative Draft Single Authorized Run

## Scope

Stage 20 attempted one explicitly authorized real Kimi dialogue/scene creative
draft request. The stage preserved the one-call/no-retry policy, did not fall
back to mock output, did not apply candidates, and did not modify source
screenplay or author review artifacts.

## Preflight

- Readiness status before call: `ready_pending_network_authorization`.
- Author review authorization: `kimi_dialogue_draft`.
- Mock creative draft fixture schema: valid.
- Mock candidate targets: resolved against screenplay.
- Kimi key presence: true, recorded only as a boolean.
- `.env`: ignored by Git.
- Source screenplay SHA-256:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Author review report SHA-256:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`.
- Mock creative draft candidates SHA-256:
  `fc0cfe7ab4d0265cdb966c432651003d8f3575d596ae4f1bc6411e8b50a9de84`.

## Commands Run

- `python -m pytest tests/test_creative_draft_real_readiness.py tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py`
- preflight schema, target, key-presence, and hash script
- `git check-ignore -q .env`
- one real Kimi CLI call:
  `python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.yaml --author-review-report examples/output/test1_sanguo_author_review_report.yaml --review-report examples/output/test1_sanguo_review_report.yaml --quality-report examples/output/test1_sanguo_quality_report.yaml --out examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml --allow-network`
- post-failure artifact/hash check
- `python -m pytest`
- Stage 20 touched-file safety scan

## Real Kimi Call Result

- Exit code: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Error category: `authentication`.
- HTTP status: 401.
- Attempt: 1.
- Max attempts: 1.
- Retryable: false.
- Request id: safe synthetic request id only.
- No retry was attempted.
- No mock fallback was used.
- No candidate sidecar was retained.
- No real Kimi run log was retained.

## Post-Failure Checks

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`:
  absent.
- Source screenplay hash unchanged.
- Author review report hash unchanged.
- Stage 18 mock candidates hash unchanged.
- Focused creative/readiness tests after failure: passed, `20 passed`.
- Full pytest after failure: passed, `153 passed`.

## Security Scan

Stage 20 touched files and any real-output paths that existed were scanned for
key patterns, bearer token values, Authorization header values, retained model
response marker text, provider payload marker text, retained prompt flags, and
environment key assignment patterns. Result: passed.

No prompt text, provider payload, model output text, API key, bearer token,
Authorization header, full novel text, or full screenplay text was retained in
Stage 20 outputs.

## Tests Not Run

- Real output schema validation was not run because no real candidate sidecar
  was produced.
- Target integrity validation for real candidates was not run because candidate
  count was zero due to provider authentication failure.
- No Stage 21 human review was started.
- No commit was created.

## Gate Decision

Blocked. Stage 20 did not pass because the single authorized Kimi request failed
with provider authentication status 401. The next step requires human
intervention to fix Kimi credential/provider configuration before another
explicitly authorized one-shot real run can be attempted.

# QA Report - Stage 21A Kimi Provider Repair And Aggressive Apply Attempt

## Scope

Stage 21A repaired local Kimi provider configuration handling, added an
apply-creative-draft path for future schema-valid candidates, and attempted
exactly one user-authorized real Kimi creative draft request. The stage stopped
after provider authentication failed, so no real candidate sidecar, enhanced
screenplay, apply report, Fountain export, or enhanced quality report was
generated.

## Provider Configuration Repair

- `.env` exists and remains ignored by Git.
- `N2S_KIMI_API_KEY` is present; the key value was not printed or persisted.
- `N2S_KIMI_BASE_URL` is present and resolves to the official Moonshot SDK
  endpoint base used for chat completions.
- Official Kimi API overview checked:
  https://platform.kimi.ai/docs/api/overview
- Provider key handling now normalizes an optional bearer-prefix entered in
  `.env`, avoiding a doubled auth prefix in outbound requests.
- Router coverage confirms `kimi_creative` can load the Kimi base URL from
  `.env` while keeping `max_attempts=1`.

## Commands Run

- `python -m pytest tests/test_openai_compatible_provider.py tests/test_llm_router.py tests/test_creative_draft_apply.py tests/test_creative_draft_apply_cli.py tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py tests/test_creative_draft_real_readiness.py`
- one real Kimi CLI call with `--allow-network` and `max_attempts=1`
- post-failure artifact/hash/safety scan
- `python -m pytest`

## Real Kimi Call Result

- Exit code: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Error category: `authentication`.
- HTTP status: 401.
- Attempt: 1.
- Max attempts: 1.
- Retryable: false.
- Request id: safe synthetic request id only.
- No retry was attempted.
- No mock fallback was used.
- No candidate sidecar was retained.
- No real run log was retained.

## Creative Draft Apply Implementation

Added a deterministic apply path for future schema-valid creative draft
candidates:

- `dialogue_insert` and `dialogue_rewrite` append dialogue elements without
  overwriting original elements.
- `scene_action_enhancement` and `beat_externalization` append action elements.
- `pacing_trim_suggestion` and `reviewer_note` append notes only.
- Existing scenes, beats, elements, source traces, story map, and character
  bible are preserved.
- The source screenplay is never modified in place.

This path was not executed against real Kimi output in Stage 21A because no
schema-valid real sidecar was produced.

## Results

- Focused Stage 21 tests: passed, `53 passed`.
- Full pytest: passed, `160 passed`.
- Real candidate count: 0, due to provider authentication failure.
- Apply result: not run.
- Enhanced screenplay: not generated.
- Enhanced quality report: not generated.

## Generated Artifacts

- `src/novel2script/agents/creative_draft_apply.py`
- `tests/test_creative_draft_apply.py`
- `tests/test_creative_draft_apply_cli.py`
- provider/router repair coverage in:
  `tests/test_openai_compatible_provider.py`,
  `tests/test_llm_router.py`

No real Kimi sidecar, real Kimi run log, enhanced screenplay, or apply report
was retained.

## Hash Checks

- Source screenplay unchanged:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Author review report unchanged:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`.
- Stage 18 mock candidates unchanged:
  `fc0cfe7ab4d0265cdb966c432651003d8f3575d596ae4f1bc6411e8b50a9de84`.

## Security Scan

Stage 21 code paths and possible real-output paths were scanned for key-like
values, bearer-like token values, auth header literals, retained model-response
markers, provider payload markers, retained prompt flags, and environment key
assignment patterns. Result: passed.

Real-output paths were absent after the provider failure:

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`
- `examples/output/test1_sanguo_screenplay.enhanced.yaml`
- `examples/output/test1_sanguo_creative_draft_apply_report.yaml`

## Tests Not Run

- Real candidate schema validation was not run because no candidate sidecar was
  retained.
- Real candidate target integrity validation was not run because candidate
  count was zero.
- Creative candidate apply was not run.
- Enhanced screenplay validation/export/review/roundtrip/quality chain was not
  run.
- No commit was created.

## Gate Decision

Blocked. Stage 21A did repair local provider handling and added the future apply
path, but the single authorized real Kimi call failed with provider
authentication status 401. The next step requires manual credential/provider
account repair and a new explicit authorization before any further real Kimi
call is attempted.

# QA Report - Stage 22 Kimi Credential/Provider Probe

## Scope

Stage 22 checked Kimi credential/provider configuration offline and executed
one explicitly authorized minimal real Kimi connectivity probe. This stage did
not generate creative draft candidates, did not run the full
`kimi-dialogue-scene-drafter`, did not save a prompt or raw model response, and
did not generate or apply an enhanced screenplay.

## Offline Credential/Provider Checks

- `.env` exists and remains ignored by Git.
- `N2S_KIMI_API_KEY` is present and was not printed or persisted.
- The Kimi key is not a placeholder.
- The parsed key has no leading/trailing whitespace, wrapping quotes, or
  newline characters.
- Bearer-prefix normalization remains covered; the provider will not send a
  doubled bearer prefix.
- `N2S_KIMI_BASE_URL` is present or defaulted safely.
- Base URL host: `api.moonshot.ai`.
- Base URL: official Moonshot-compatible endpoint
  `https://api.moonshot.ai/v1`.
- Router `kimi_creative` configuration:
  `provider_type: kimi`, `model: kimi-k2.6`,
  `env_api_key: N2S_KIMI_API_KEY`,
  `env_base_url: N2S_KIMI_BASE_URL`.

## Minimal Kimi Probe

- Probe executed: true.
- Probe count: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Request shape: minimal JSON probe only, `max_tokens <= 32`,
  `temperature = 0`, `response_format = json_object`.
- Novel text used: false.
- Production creative prompt used: false.
- Screenplay or author review artifacts used: false.
- Stage 18 mock candidates used: false.
- Retry executed: false.
- Provider max attempts: 1.
- Output evidence:
  `examples/output/test1_sanguo_kimi_probe_report.yaml`.

## Probe Result

- Status: blocked.
- Exit code: 1.
- Error category: `authentication`.
- HTTP status: 401.
- Finish reason: none.
- Parsed JSON accepted: false.
- Readiness for real creative draft: false.
- Next stage: blocked pending credential/provider repair, not Stage 23.

## Retention And Artifact Safety

- Prompt retained: false.
- Raw model response retained: false.
- Provider request/response body retained: false.
- Authorization header retained: false.
- API key or bearer token retained: false.
- Real Kimi creative sidecar generated: false.
- Real Kimi run log generated: false.
- Enhanced screenplay generated: false.
- Temporary raw artifact generated: false.

## Commands Run

- `python -m pytest tests/test_openai_compatible_provider.py tests/test_llm_router.py`
- `python -m pytest tests/test_creative_draft_real_readiness.py`
- One minimal real Kimi probe through `OpenAICompatibleProvider` with
  `max_attempts=1`
- `python -m pytest`
- Stage 22 safety scan over新增/修改 text files and the probe report
- `git check-ignore -q .env`
- Artifact absence checks for real Kimi sidecar, real run log, enhanced
  screenplay, and apply report paths

## Test Results

- Provider/router focused tests: passed, `28 passed`.
- Creative draft readiness focused tests: passed, `10 passed`.
- Full pytest: passed, `160 passed`.

## Security Scan

Scanned 56新增/修改 text files plus the Stage 22 probe report for key-like
values, bearer values, Authorization header values, stored-prompt truth flags,
raw response/provider body fields, the exact minimal probe prompt text, and
Kimi key assignments outside `.env`.

Result: passed. No API key, bearer token, Authorization header value, retained
prompt, provider body, raw model response field, `.env` content, full novel
text, or full screenplay text was found.

`.env` remains ignored by Git, and `git status --short` does not include
`.env`, temporary directories, or `__pycache__`.

## Gate Decision

Blocked. Stage 22 confirmed the local provider configuration is shaped
correctly and executed exactly one minimal Kimi probe, but the provider still
returned HTTP 401 authentication failure. Do not start Stage 23 until the Kimi
credential/provider account issue is repaired and a new stage receives explicit
authorization.

## Stage 22B Manual Repair Handoff

No additional Kimi API probe was executed after the Stage 22 one-shot failure.
The official Kimi API documentation still matches the local provider shape:
`https://api.moonshot.ai/v1`, `/chat/completions`,
`Authorization: Bearer $MOONSHOT_API_KEY`, and model `kimi-k2.6`.

Recommended manual checks before any future authorized probe:

- Regenerate or re-copy the key from the Kimi Open Platform API key console.
- Confirm the key belongs to the API platform account, not a web/session token
  or another provider.
- Confirm the account/project has permission to call `kimi-k2.6`.
- Confirm account billing, balance, or voucher status is active.
- Replace only local `.env` secret material; do not commit it.
- Rerun offline readiness checks before requesting a new one-shot probe
  authorization.

The next real probe must be a new stage with fresh human authorization and must
preserve the same no-retry, no-retention constraints.

# QA Report - Stage 22B Kimi Chinese Endpoint Probe

## Scope

Stage 22B used the user-provided Chinese platform endpoint example as the next
single-variable diagnostic: the existing local `N2S_KIMI_API_KEY` was kept, but
the Kimi base URL for the probe was overridden to
`https://api.moonshot.cn/v1`. This stage did not modify `.env`, did not call
Qwen or DeepSeek, did not run `kimi-dialogue-scene-drafter`, did not generate
creative draft candidates, and did not generate or apply an enhanced
screenplay.

## Offline Configuration Check

- Provider profile: `kimi_creative`.
- Provider type: `kimi`.
- Model: `kimi-k2.6`.
- Key env var: `N2S_KIMI_API_KEY`.
- Key present: true.
- Normalized key remains free of a bearer prefix, so the provider will not send
  `Bearer Bearer ...`.
- Probe base URL host: `api.moonshot.cn`.
- Probe base URL path: `/v1`.
- Max attempts: 1.
- Retry allowed: false.

## Minimal Kimi Probe

- Probe executed: true.
- Probe count: 1.
- Endpoint: `https://api.moonshot.cn/v1`.
- Request shape: minimal JSON probe only, `max_tokens <= 32`,
  `temperature = 0`, `response_format = json_object`.
- Novel text used: false.
- Production creative prompt used: false.
- Screenplay or author review artifacts used: false.
- Stage 18 mock candidates used: false.
- Retry executed: false.
- Provider max attempts: 1.
- Output evidence:
  `examples/output/test1_sanguo_kimi_probe_cn_report.yaml`.

## Probe Result

- Status: blocked.
- Exit code: 1.
- Error category: `unknown`.
- HTTP status: 400.
- Finish reason: none.
- Parsed JSON accepted: false.
- Readiness for real creative draft: false.

The `.cn` endpoint no longer produced HTTP 401 authentication failure, but the
probe still did not pass because the provider returned HTTP 400. Since Stage
22B intentionally did not retain the provider response body, the exact
server-side validation message is not available in repository artifacts.

Most likely next hypothesis: the Chinese endpoint accepted authentication but
rejected part of the minimal non-streaming JSON-mode request shape. Candidate
differences from the user's official streaming example include `stream: false`
and `response_format: json_object`.

## Retention And Artifact Safety

- Prompt retained: false.
- Raw model response retained: false.
- Provider request/response body retained: false.
- Authorization header retained: false.
- API key retained: false.
- Real Kimi creative sidecar generated: false.
- Real Kimi run log generated: false.
- Enhanced screenplay generated: false.
- Temporary raw artifact generated: false.

## Gate Decision

Blocked. Stage 22B shows the Chinese endpoint changes the failure from
authentication 401 to HTTP 400, so the original `.ai` endpoint mismatch is a
credible root cause for the 401. However, the provider is not yet ready for
Stage 23 because the `.cn` minimal probe did not complete successfully. The
next stage should remain a separately authorized minimal request-shape
diagnostic, not a creative draft run.

# QA Report - Stage 22C/D Kimi Cross-Repository Repair

## Scope

Stage 22C/D audited `E:\health_ai_platform_2.0` as the successful Kimi K2.5
reference implementation, compared it with Novel2Script's Kimi K2.6 creative
provider, repaired the request shape, and ran a minimal real Kimi provider
validation. This stage did not run the full creative drafter, did not generate
real creative candidates, did not apply screenplay changes, and did not retain
prompt text, raw model text, provider bodies, API keys, bearer tokens, or
Authorization headers.

## Root Cause

Two incompatibilities were found by comparing with the successful project:

- Novel2Script defaulted Kimi to `https://api.moonshot.ai/v1`, while the working
  local project and the user's current Kimi key use the Chinese platform
  endpoint `https://api.moonshot.cn/v1`.
- Novel2Script sent `response_format` and `temperature`; the working K2.5
  project explicitly removed both for Kimi compatibility.

After both fields were omitted, the minimal Kimi probe received a provider
response. The remaining minimal-probe failure was strict JSON acceptance, not
connectivity/authentication.

## Code Changes

- `src/novel2script/llm/router.py`
  - Kimi default base URL is now `https://api.moonshot.cn/v1`.
  - `kimi_creative` sets `supports_response_format: false`.
  - `kimi_creative` sets `supports_temperature: false`.
- `src/novel2script/llm/openai_compatible_provider.py`
  - Added provider capability flags for `response_format` and `temperature`.
  - Payload construction now omits unsupported fields per provider profile.
- `src/novel2script/agents/creative_draft.py`
  - Real Kimi output parsing now strips Markdown code fences in memory before
    JSON parsing, without retaining raw model text.

## Tests

- New regression tests first failed before implementation for:
  - missing Kimi `response_format` compatibility switch;
  - missing Kimi `temperature` compatibility switch;
  - fenced JSON rejection in the creative drafter.
- Focused tests passed:
  `python -m pytest tests/test_openai_compatible_provider.py tests/test_llm_router.py tests/test_creative_draft_real_readiness.py -q`
  returned `40 passed`.
- Creative draft focused tests passed:
  `python -m pytest tests/test_creative_draft_agent.py -q`
  returned `9 passed`.
- Full suite passed:
  `python -m pytest` returned `163 passed`.

## Minimal Real Kimi Probe

Evidence:
`examples/output/test1_sanguo_kimi_probe_cn_compat_payload_report.yaml`.

- Probe executed: true.
- Endpoint host: `api.moonshot.cn`.
- Model: `kimi-k2.6`.
- Key present: true.
- `response_format` sent to provider: false.
- `temperature` sent to provider: false.
- Provider response received: true.
- HTTP status: none.
- Error category: `malformed_model_json`.
- Retry executed: false.
- Prompt retained: false.
- Raw response retained: false.
- Provider body retained: false.
- Creative drafter executed: false.

## Capability Result

- Kimi API connectivity: passed at provider level; the provider returned a
  model response.
- Kimi K2.6 creative-agent construction: passed offline and fake-router
  real-mode tests.
- Normal conversation: provider response was received, but raw text was not
  retained by policy.
- Tool calling: not implemented in Novel2Script's creative drafter.
- Streaming: not implemented in Novel2Script's CLI/artifact workflow.
- Full real creative draft: not run in this phase.
- Enhanced screenplay: not generated.

## Gate Decision

Passed for Kimi provider connectivity repair and request-shape compatibility.
Not passed for Stage 23 creative output generation because the full real Kimi
creative drafter was intentionally not run. Stage 23 requires separate explicit
authorization and must preserve no-retry/no-retention/no-auto-apply controls.

# QA Report - Stage 23 Real Kimi Creative Draft Attempt

## Scope

Stage 23 attempted the user-authorized full real
`kimi-dialogue-scene-drafter` call exactly once. The stage stopped on provider
runtime failure before any real creative candidates were accepted, so no
enhanced screenplay, apply report, Fountain export, roundtrip, enhanced review,
or enhanced quality report was generated.

## Preflight Gates

- Stage 22 equivalent success: passed by
  `examples/output/test1_sanguo_kimi_probe_cn_compat_payload_report.yaml`
  showing `provider_response_received: true` for `api.moonshot.cn` and
  `kimi-k2.6`.
- `.env` exists and remains ignored by Git.
- `N2S_KIMI_API_KEY` is present; the key value was not printed or persisted.
- Kimi base URL host is `api.moonshot.cn`.
- Author review report authorizes `kimi_dialogue_draft`.
- Mock creative draft fixture validates against
  `schemas/creative_draft_candidates.schema.json`.
- Mock candidate targets resolve against the source screenplay.
- Readiness report status is `ready_pending_network_authorization`.
- Source screenplay hash before:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Author review report hash before:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`.
- Mock candidates hash before:
  `fc0cfe7ab4d0265cdb966c432651003d8f3575d596ae4f1bc6411e8b50a9de84`.
- No existing Stage 23 real or enhanced artifact was present before the call.

## Code Safety Guard

Before the real call, a TDD guard was added so incomplete real model candidates
fail closed instead of being repaired into schema-valid sidecars.

- Red test:
  `tests/test_creative_draft_agent.py::test_real_drafter_fail_closed_instead_of_repairing_incomplete_model_candidate`
  failed before implementation.
- Green verification:
  `python -m pytest tests/test_creative_draft_agent.py::test_real_drafter_fail_closed_instead_of_repairing_incomplete_model_candidate tests/test_creative_draft_agent.py -q`
  passed with `10 passed`.

## Commands Run

```powershell
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py tests/test_creative_draft_apply.py tests/test_creative_draft_apply_cli.py tests/test_creative_draft_real_readiness.py -q
python -m pytest -q
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.yaml --author-review-report examples/output/test1_sanguo_author_review_report.yaml --review-report examples/output/test1_sanguo_review_report.yaml --quality-report examples/output/test1_sanguo_quality_report.yaml --out examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml --allow-network
```

## Real Kimi Call Result

- Real Kimi creative drafter executed: true.
- Real Kimi creative drafter call count: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Endpoint: `https://api.moonshot.cn/v1`.
- Exit code: 1.
- Error category: `tls_error`.
- HTTP status: null.
- Attempt: 1.
- Max attempts: 1.
- Retry executed: false.
- Provider internal retry executed: false.
- Mock fallback used: false.
- Qwen called: false.
- DeepSeek called: false.
- Candidate count: 0.
- Apply executed: false.
- Enhanced QA chain executed: false.

## Artifact And Hash Checks

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_screenplay.enhanced.yaml`: absent.
- `examples/output/test1_sanguo_creative_draft_apply_report.yaml`: absent.
- Enhanced validation, Fountain, review, roundtrip, and quality artifacts:
  absent.
- Source screenplay hash after:
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Author review report hash after:
  `d548b15badd3e2511aa031d2c8db186f879c740a7b04b5c748ebb23a72140415`.
- Mock candidates hash after:
  `fc0cfe7ab4d0265cdb966c432651003d8f3575d596ae4f1bc6411e8b50a9de84`.

## Test Results

- Focused Stage 23 tests before the real call: passed, `27 passed`.
- Full pytest before the real call: passed, `164 passed`.
- The enhanced QA command chain was not run because provider/runtime failure is
  a hard stop.

## Security Scan

Post-failure scan covered the Stage 23 code/test/plan changes and all possible
Stage 23 output paths that existed.

Result: passed.

No API key, bearer token, Authorization header value, prompt text, raw model
response, provider request/response body, `.env` content, full novel text, or
full screenplay text was retained in Stage 23 artifacts. `.env` remains ignored
by Git.

## Gate Decision

Blocked. The one authorized real Kimi creative drafter call failed with
`tls_error` at attempt 1 of 1. Stage 23 must not apply candidates, must not
generate an enhanced screenplay, and must not proceed to Stage 24. A future
stage needs explicit authorization for a targeted TLS/network diagnostic or a
new one-shot real Kimi creative draft attempt.

# QA Report - Stage 23R Kimi TLS Diagnostic And One-Shot Retry

## Scope

Stage 23R used the user's new authorization to investigate the Stage 23
`tls_error` and execute one additional real Kimi creative drafter attempt. The
stage did not retry automatically, did not call Qwen or DeepSeek, did not use a
mock fallback, did not retain prompt or raw provider content, and did not
generate or apply an enhanced screenplay.

## TLS / Network Diagnostics

Non-model diagnostics were run before the authorized creative drafter call:

- DNS resolution for `api.moonshot.cn` returned CNAME
  `rp68jmko8a6qpuee.aliyunddos1022.com` and IP `8.147.223.37`.
- TCP 443 check to `api.moonshot.cn` passed.
- Python OpenSSL handshake to `api.moonshot.cn:443` failed with handshake
  timeout.
- Python `urllib` GET to `https://api.moonshot.cn/v1/models` failed before HTTP
  response with `UNEXPECTED_EOF_WHILE_READING`.
- Windows `Invoke-WebRequest` to `https://api.moonshot.cn/v1/models` timed out.
- `curl.exe -I https://api.moonshot.cn/v1/models` did not receive headers before
  timeout.
- No proxy environment variable was present in the shell.

Conclusion: the failure is reproducible before authentication, model
permission, prompt processing, response parsing, or schema validation. The
current blocker is the local network/TLS path from this machine to the Moonshot
China endpoint, not the Kimi API key, model name, creative prompt, or
Novel2Script schema/apply logic.

## Preflight Gates

- Stage 22D equivalent provider response evidence remains available.
- Kimi key is present; the value was not printed or persisted.
- Base URL remains `https://api.moonshot.cn/v1`.
- `.env` remains ignored by Git.
- Author review report authorizes `kimi_dialogue_draft`.
- Mock creative draft fixture remains schema-valid.
- No stale real Kimi sidecar, real run log, enhanced screenplay, or apply
  report existed before the call.

## Real Kimi Retry Result

- Real Kimi creative drafter executed: true.
- Real Kimi creative drafter call count in Stage 23R: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Exit code: 1.
- Error category: `tls_error`.
- HTTP status: null.
- Attempt: 1.
- Max attempts: 1.
- Retry executed: false.
- Provider internal retry executed: false.
- Mock fallback used: false.
- Candidate count: 0.
- Apply executed: false.
- Enhanced QA chain executed: false.

## Artifact And Safety Checks

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_screenplay.enhanced.yaml`: absent.
- `examples/output/test1_sanguo_creative_draft_apply_report.yaml`: absent.
- Source screenplay hash remained
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Security scan passed: no API key, bearer token, Authorization header value,
  prompt text, raw model response, provider request/response body, `.env`
  content, full novel text, or full screenplay text was retained.

## Gate Decision

Blocked. Stage 23R confirms the real creative drafter cannot currently pass
because the local HTTPS/TLS connection to `api.moonshot.cn` fails before an HTTP
response is available. Do not proceed to Stage 24. The next useful action is to
repair or bypass the local network/TLS route, then request a new explicit
one-shot authorization.

# QA Report - Stage 23V VPN Restored One-Shot Kimi Creative Draft

## Scope

Stage 23V used the user's new authorization after VPN access to
`api.moonshot.cn` was restored. The stage first verified terminal-level HTTPS,
then executed exactly one real Kimi creative drafter call. It stopped on
`finish_reason=length` as required and did not apply candidates or run enhanced
QA.

## Terminal Network Verification

- Python `urllib` GET `https://api.moonshot.cn/`: HTTP 200.
- Python `urllib` GET `https://api.moonshot.cn/v1/models`: HTTP 401, proving
  the terminal reached the HTTPS/HTTP layer without sending an API key.
- Windows `Invoke-WebRequest` GET `https://api.moonshot.cn/`: HTTP 200.
- TCP 443 to `api.moonshot.cn`: passed.

## Preflight Gates

- Stage 22D equivalent provider response evidence remains available.
- Kimi key is present; the value was not printed or persisted.
- Base URL remains `https://api.moonshot.cn/v1`.
- `.env` remains ignored by Git.
- Author review report authorizes `kimi_dialogue_draft`.
- Mock creative draft fixture remains schema-valid.
- Mock candidate targets resolve against the source screenplay.
- Readiness report remains `ready_pending_network_authorization`.
- No stale real Kimi sidecar, enhanced screenplay, or apply report existed
  before the call.

## Real Kimi Call Result

- Real Kimi creative drafter executed: true.
- Real Kimi creative drafter call count in Stage 23V: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Exit code: 1.
- HTTP status: null.
- Attempt: 1.
- Max attempts: 1.
- Retry executed: false.
- Provider internal retry executed: false.
- Mock fallback used: false.
- Finish reason: `length`.
- Usage: input tokens 319, output tokens 1600, total tokens 1919.
- Error code: `truncated_model_output`.
- Candidate count: 0.
- Apply executed: false.
- Enhanced QA chain executed: false.

## Artifact And Safety Checks

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`:
  present as redacted metadata only.
- `examples/output/test1_sanguo_screenplay.enhanced.yaml`: absent.
- `examples/output/test1_sanguo_creative_draft_apply_report.yaml`: absent.
- Source screenplay hash remained
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Security scan passed: no API key, bearer token, Authorization header value,
  prompt text, raw model response, provider request/response body, `.env`
  content, full novel text, or full screenplay text was retained.

## Gate Decision

Blocked. VPN restored terminal connectivity and the real Kimi call reached the
model, but Kimi's output hit the configured 1600-token completion limit
(`finish_reason=length`). Per Stage 23 hard gates, truncated output must not be
parsed, repaired, retained as candidates, applied, or retried. The next stage
should reduce/strictly constrain the real prompt or adjust the completion budget
under a new explicit one-shot authorization.

# QA Report - Stage 23W Kimi Prompt/Budget Repair Attempt

## Scope

Stage 23W implemented the first prompt/budget repair for the real Kimi creative
drafter and executed exactly one user-authorized real Kimi call. It did not
call Qwen or DeepSeek, did not retry, did not use mock fallback, did not apply
candidates, and did not generate an enhanced screenplay.

## Code Changes

- `src/novel2script/llm/openai_compatible_provider.py`
  - Added provider-level `extra_body` support for OpenAI-compatible payloads.
- `src/novel2script/llm/router.py`
  - Configured `kimi_creative` with `thinking: {"type": "disabled"}`.
- `src/novel2script/agents/creative_draft.py`
  - Increased the real Kimi creative draft output budget from 1600 to 32768
    tokens.
  - After the Stage 23W one-shot failed schema acceptance, tightened the next
    prompt shape offline to request exactly one compact candidate with explicit
    enum and field-shape constraints.

## TDD Evidence

New tests first failed, then passed:

- Kimi provider merges `extra_body` and sends `thinking: {"type": "disabled"}`.
- Router registers `kimi_creative.extra_body`.
- Real creative drafter requests `max_tokens: 32768`.
- Real prompt now asks for exactly one compact candidate with a precise
  candidate JSON contract.

Commands:

```powershell
python -m pytest tests/test_openai_compatible_provider.py::test_kimi_provider_merges_profile_extra_body_for_thinking_disabled tests/test_llm_router.py::test_router_from_environment_registers_selected_chinese_model_profiles tests/test_creative_draft_agent.py::test_real_drafter_fake_router_writes_schema_valid_redacted_candidates -q
python -m pytest tests/test_openai_compatible_provider.py tests/test_llm_router.py tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py tests/test_creative_draft_apply.py tests/test_creative_draft_apply_cli.py tests/test_creative_draft_real_readiness.py -q
python -m pytest -q
```

Results:

- Focused red/green tests: passed, `3 passed`.
- Stage 23W focused suite before real call: passed, `58 passed`.
- Full pytest before real call: passed, `165 passed`.
- Post-failure focused provider/router/creative suite: passed, `40 passed`.

## Real Kimi Call Result

- Real Kimi creative drafter executed: true.
- Real Kimi creative drafter call count in Stage 23W: 1.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Endpoint: `https://api.moonshot.cn/v1`.
- `thinking` disabled: true.
- Max tokens requested: 32768.
- Exit code: 1.
- HTTP status: null.
- Attempt: 1.
- Max attempts: 1.
- Retry executed: false.
- Provider internal retry executed: false.
- Mock fallback used: false.
- Finish reason: `stop`.
- Usage: input tokens 319, output tokens 838, total tokens 1157.
- Error code: `invalid_creative_draft_schema`.
- Candidate count: 0.
- Apply executed: false.
- Enhanced QA chain executed: false.

## Artifact And Safety Checks

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`:
  absent.
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`:
  present as redacted metadata only.
- `examples/output/test1_sanguo_screenplay.enhanced.yaml`: absent.
- `examples/output/test1_sanguo_creative_draft_apply_report.yaml`: absent.
- Source screenplay hash remained
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Security scan passed: no API key, bearer token, Authorization header value,
  prompt text, raw model response, provider request/response body, `.env`
  content, full novel text, or full screenplay text was retained.

## Gate Decision

Blocked. Stage 23W fixed the previous truncation failure and reached
`finish_reason=stop`, but the real model output did not satisfy
`schemas/creative_draft_candidates.schema.json`. The one-shot call was used, so
no retry was performed. Offline prompt constraints have been tightened for the
next attempt, which requires new explicit authorization.

# QA Report - Stage 23X Exact-One Real Kimi Creative Draft

## Scope

Stage 23X executed exactly one user-authorized real Kimi creative drafter call
using the tightened exact-one-candidate prompt. This stage did not call Qwen or
DeepSeek, did not retry, did not use mock fallback, did not apply candidates,
and did not generate an enhanced screenplay because apply was not separately
authorized for this turn.

## Preflight

- Stage 22/22C-D Kimi connectivity evidence exists.
- Kimi key present: true; key value not printed or retained.
- `.env` exists and remains Git ignored.
- Endpoint: `https://api.moonshot.cn/v1`.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Router configuration: Kimi omits `response_format` and `temperature`, and
  sends `thinking: {"type": "disabled"}` through provider `extra_body`.
- Stale Stage 23 real/enhanced artifacts were cleared before the one-shot.
- Focused preflight tests passed: `40 passed`.

## Real Kimi Call Result

- Real Kimi creative drafter executed: true.
- Real Kimi creative drafter call count in Stage 23X: 1.
- Exit code: 0.
- Attempt: 1.
- Max attempts: 1.
- Retry executed: false.
- Provider internal retry executed: false.
- Mock fallback used: false.
- Finish reason: `stop`.
- Usage: input tokens 491, output tokens 178, total tokens 669.
- Candidate count: 1.
- Error count: 0.
- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`:
  present.
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`:
  present as redacted metadata only.

## Validation

- `schemas/creative_draft_candidates.schema.json`: passed with 0 schema errors.
- Candidate target integrity: passed with 0 unresolved target errors.
- Candidate policy checks passed:
  - `provider_profile: kimi_creative`.
  - `dry_run: false`.
  - `human_approval_required: true`.
  - candidate `merge_policy: human_approval_required`.
  - candidate `requires_author_approval: true`.
  - candidate has non-empty `proposed_text`, `rationale`, `source_trace`, and
    `source_trace_ids`.
- Source screenplay hash remained
  `5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.

## Safety Checks

- Run log retention flags:
  - `stored_prompt: false`.
  - `model_response_retained: false`.
  - `provider_payload_retained: false`.
- Output artifact safety scan passed for:
  - API key prefixes.
  - Bearer token values.
  - Authorization header values.
  - `stored_prompt: true`.
  - raw response values.
  - provider body values.
  - `.env` key assignments.
- A source prompt safety rule contains the phrase "Authorization header value";
  this is not an authorization header value and was not present in retained
  output artifacts.
- No enhanced screenplay or apply report exists for Stage 23X.

## Tests

Commands:

```powershell
python -m pytest tests/test_openai_compatible_provider.py tests/test_llm_router.py tests/test_creative_draft_agent.py -q
python -m pytest -q
```

Results:

- Focused preflight provider/router/creative suite: passed, `40 passed`.
- Full pytest after Stage 23X: passed, `165 passed`.

## Gate Decision

Passed for Stage 23X real candidate generation. The real Kimi candidate sidecar
is schema-valid, target-valid, redacted, and safe to review. Apply and enhanced
QA were intentionally not run in this turn; the next step requires separate
human authorization to apply the retained real Kimi candidate into a new
enhanced screenplay artifact.

# QA Report - Stage 23Y Real Kimi Apply And Enhanced QA

## Scope

Stage 23Y used the human-authorized retained real Kimi candidate from Stage 23X
and applied it to a new enhanced screenplay artifact. It did not call Kimi,
Qwen, or DeepSeek, did not retry any provider call, and did not mutate the
original screenplay.

## Apply Result

- Apply executed: true.
- Source screenplay:
  `examples/output/test1_sanguo_screenplay.yaml`.
- Real Kimi candidates:
  `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`.
- Enhanced screenplay:
  `examples/output/test1_sanguo_screenplay.enhanced.yaml`.
- Apply report:
  `examples/output/test1_sanguo_creative_draft_apply_report.yaml`.
- `applied_count`: 1.
- `skipped_count`: 0.
- `blocked_count`: 0.
- `preserved_original_screenplay`: true.
- `errors`: 0.
- Source screenplay hash before:
  `sha256:5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Source screenplay hash after:
  `sha256:5189148b0e76cb5cdd6ed9b0454b558a53c3e2c631094514bdd8e193e73727b7`.
- Enhanced screenplay hash:
  `sha256:34350f247f9a086dc01c5b5f9e5d43bf610b91214004b1c40b687e65aea7ff6c`.
- Applied creative elements: 1.
- Applied element metadata checks passed:
  - `source_trace`.
  - `source_trace_ids`.
  - `ai_tags`.
  - `creative_draft_candidate_id`.
  - `requires_author_approval: true`.
  - `provider_profile: kimi_creative`.

## Enhanced QA Chain

Commands executed:

```powershell
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay.enhanced.yaml --schema schemas/screenplay.schema.json --out examples/output/test1_sanguo_screenplay.enhanced_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/test1_sanguo_screenplay.enhanced.yaml --out examples/output/test1_sanguo_screenplay.enhanced.fountain --map examples/output/test1_sanguo_screenplay.enhanced.fountain.map.json
python -m novel2script.cli review-screenplay --screenplay examples/output/test1_sanguo_screenplay.enhanced.yaml --character-bible examples/output/test1_sanguo_character_bible.yaml --story-map examples/output/test1_sanguo_story_map.merged.yaml --outline examples/output/test1_sanguo_outline.yaml --out examples/output/test1_sanguo_review_report.enhanced.yaml
python -m novel2script.cli import-fountain --screenplay examples/output/test1_sanguo_screenplay.enhanced.yaml --fountain examples/output/test1_sanguo_screenplay.enhanced.fountain --map examples/output/test1_sanguo_screenplay.enhanced.fountain.map.json --out examples/output/test1_sanguo_screenplay.enhanced_roundtrip.yaml --report examples/output/test1_sanguo_screenplay.enhanced_roundtrip_report.yaml
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay.enhanced_roundtrip.yaml --schema schemas/screenplay.schema.json --out examples/output/test1_sanguo_screenplay.enhanced_roundtrip_validation_report.yaml
python -m novel2script.cli evaluate-quality --screenplay examples/output/test1_sanguo_screenplay.enhanced_roundtrip.yaml --validation-report examples/output/test1_sanguo_screenplay.enhanced_roundtrip_validation_report.yaml --review-report examples/output/test1_sanguo_review_report.enhanced.yaml --roundtrip-report examples/output/test1_sanguo_screenplay.enhanced_roundtrip_report.yaml --out examples/output/test1_sanguo_quality_report.enhanced.yaml --markdown examples/output/test1_sanguo_quality_dashboard.enhanced.md
```

Results:

- Enhanced screenplay validation: passed.
- Fountain export: passed.
- Enhanced review report: generated, blocking false, total issues 0.
- Fountain roundtrip: passed with no changed regions and no blocking issues.
- Enhanced roundtrip screenplay validation: passed.
- Enhanced quality report: generated.
- Enhanced quality readiness: `pass`.
- Enhanced quality score: 100.
- Enhanced quality decision: `ready_for_author_review`.
- Hard gate failures: none.

## Schema Validation

- Real Kimi creative candidates against
  `schemas/creative_draft_candidates.schema.json`: 0 errors.
- Enhanced screenplay against `schemas/screenplay.schema.json`: 0 errors.
- Enhanced roundtrip screenplay against `schemas/screenplay.schema.json`: 0
  errors.
- Enhanced review report against `schemas/review_report.schema.json`: 0 errors.
- Enhanced roundtrip report against
  `schemas/fountain_roundtrip_report.schema.json`: 0 errors.
- Enhanced quality report against `schemas/quality_report.schema.json`: 0
  errors.

## Tests

Commands:

```powershell
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py -q
python -m pytest tests/test_creative_draft_apply.py tests/test_creative_draft_apply_cli.py -q
python -m pytest tests/test_creative_draft_real_readiness.py -q
python -m pytest -q
```

Results:

- Creative draft agent/CLI focused suite: passed, `12 passed`.
- Creative draft apply focused suite: passed, `5 passed`.
- Creative draft real readiness suite: passed, `10 passed`.
- Full pytest: passed, `165 passed`.

## Safety Checks

- Scanned 13 Stage 23 real/enhanced output artifacts.
- Safety issue count: 0.
- No API key prefix was found.
- No bearer token value was found.
- No Authorization header value was found.
- No `stored_prompt: true` was found.
- No raw response value was found.
- No provider body value was found.
- No `.env` key assignment was found.
- `.env` remains Git ignored.

## Gate Decision

Passed. Stage 23 real Kimi generation, apply, enhanced screenplay validation,
Fountain export, roundtrip, quality evaluation, tests, hash checks, and safety
scan all passed. The project is ready for Stage 24 author review of the real
Kimi enhanced screenplay.

# QA Report - Stage 24A-D Four Real Kimi Creative Agents

## Scope

Stage 24A-D implemented and executed four Kimi K2.6 creative Agents:

- `adaptation_planner`
- `character_bible_agent`
- `scene_writer_agent`
- `dialogue_optimizer_agent`

Each Agent has prompt documentation, a candidate sidecar schema, a redacted run
log, CLI wiring, fake-router tests, real-mode tests, and AI inference plus
human-confirmation markers on every accepted candidate.

No Stage 24 Agent directly mutates `story_map`, `outline`, `character_bible`,
`screenplay`, Fountain, or enhanced QA artifacts. All outputs are advisory
sidecars requiring human approval.

## Implementation

- Added shared Agent runner:
  `src/novel2script/agents/kimi_creative_agents.py`.
- Added schemas:
  - `schemas/adaptation_planner_candidates.schema.json`
  - `schemas/character_bible_agent_candidates.schema.json`
  - `schemas/scene_writer_agent_candidates.schema.json`
  - `schemas/dialogue_optimizer_agent_candidates.schema.json`
- Updated prompt contracts:
  - `docs/prompts/adaptation_planner.md`
  - `docs/prompts/character_bible_agent.md`
  - `docs/prompts/scene_writer_agent.md`
  - `docs/prompts/dialogue_optimizer_agent.md`
- Updated CLI:
  - `run-agent adaptation-planner`
  - `run-agent character-bible-agent`
  - `run-agent scene-writer-agent`
  - `run-agent dialogue-optimizer-agent`
- Added tests:
  - `tests/test_kimi_creative_agents.py`
  - `tests/test_kimi_creative_agents_cli.py`

## Real Kimi Calls

Each Agent executed exactly one real Kimi K2.6 call through `kimi_creative`.
No retry or fallback was used.

| Agent | Exit | Finish | Candidates | Schema errors | Usage |
| --- | ---: | --- | ---: | ---: | --- |
| `adaptation_planner` | 0 | `stop` | 1 | 0 | 390 in / 650 out / 1040 total |
| `character_bible_agent` | 0 | `stop` | 1 | 0 | 395 in / 318 out / 713 total |
| `scene_writer_agent` | 0 | `stop` | 1 | 0 | 439 in / 551 out / 990 total |
| `dialogue_optimizer_agent` | 0 | `stop` | 1 | 0 | 444 in / 426 out / 870 total |

Artifacts:

- `examples/output/test1_sanguo_adaptation_planner_candidates.real_kimi.yaml`
- `examples/output/test1_sanguo_adaptation_planner_run_log.real_kimi.yaml`
- `examples/output/test1_sanguo_character_bible_agent_candidates.real_kimi.yaml`
- `examples/output/test1_sanguo_character_bible_agent_run_log.real_kimi.yaml`
- `examples/output/test1_sanguo_scene_writer_agent_candidates.real_kimi.yaml`
- `examples/output/test1_sanguo_scene_writer_agent_run_log.real_kimi.yaml`
- `examples/output/test1_sanguo_dialogue_optimizer_agent_candidates.real_kimi.yaml`
- `examples/output/test1_sanguo_dialogue_optimizer_agent_run_log.real_kimi.yaml`

## Candidate Policy Checks

All accepted Stage 24 candidates include:

- `source_trace`
- `source_trace_ids`
- `ai_tags.inferred`
- `ai_tags.confidence`
- `ai_tags.needs_human_review: true`
- `merge_policy: human_approval_required`
- `requires_author_approval: true`
- `provider_profile: kimi_creative`
- `dry_run: false`

## Run Log Retention

All four run logs report:

- `status: completed`
- `finish_reason: stop`
- `stored_prompt: false`
- `model_response_retained: false`
- `provider_payload_retained: false`

Run logs retain only metadata such as provider, model, usage, finish reason,
prompt hash, candidate count, source artifact paths, and errors.

## Tests

Commands:

```powershell
python -m pytest tests/test_kimi_creative_agents.py tests/test_kimi_creative_agents_cli.py tests/test_llm_router.py -q
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py tests/test_creative_draft_apply.py tests/test_creative_draft_apply_cli.py -q
python -m pytest -q
```

Results:

- Stage 24 focused suite: passed, `11 passed`.
- Creative draft regression suite: passed, `17 passed`.
- Full pytest: passed, `169 passed`.

## Safety Scan

- Scanned 8 Stage 24 real Kimi output artifacts.
- Safety issue count: 0.
- No API key prefix was found.
- No bearer token value was found.
- No Authorization header value was found.
- No `stored_prompt: true` was found.
- No raw response value was found.
- No provider body value was found.
- No `.env` key assignment was found.
- `.env` remains Git ignored.

## Gate Decision

Passed. Stage 24A-D implemented and executed all four requested Kimi K2.6
creative Agents. The next stage is Stage 25: human review and selective apply
planning for Stage 24 candidate sidecars.

# QA Report - Stage 25 Stage 24 Candidate Author Review And Selective Apply Gate

## Scope

Stage 25 prepared the human-review gate for the four Stage 24 real Kimi
candidate sidecars and executed selective apply in protected mode. It did not
call any LLM provider and did not modify outline, character bible, screenplay,
Fountain, or QA artifacts.

Because all Stage 24 candidates require human approval, no candidate is selected
until the decisions YAML contains an explicit `accept` or `edit` decision with
`reviewed_by` populated.

## Implementation

- Added review/apply module:
  `src/novel2script/agents/stage24_candidate_review.py`.
- Added CLI commands:
  - `prepare-stage24-candidate-review`
  - `apply-stage24-candidates`
- Added tests:
  - `tests/test_stage24_candidate_review.py`
  - `tests/test_stage24_candidate_review_cli.py`

## Generated Artifacts

- Author review packet:
  `examples/output/test1_sanguo_stage24_author_review_packet.md`
- Pending decisions template:
  `examples/output/test1_sanguo_stage24_candidate_decisions.yaml`
- Selected candidate sidecar:
  `examples/output/test1_sanguo_stage24_selected_candidates.yaml`
- Selective apply report:
  `examples/output/test1_sanguo_stage24_candidate_apply_report.yaml`

## Current Decision State

- Total Stage 24 candidates: 4.
- Pending decisions: 4.
- Accepted decisions: 0.
- Edited decisions: 0.
- Rejected decisions: 0.
- Selected candidates: 0.
- Selective apply status: `blocked_pending_author_review`.

This is expected: the template is intentionally initialized to `pending` for
all candidates so the system does not impersonate human approval.

## Tests

Commands:

```powershell
python -m pytest tests/test_stage24_candidate_review.py tests/test_stage24_candidate_review_cli.py -q
python -m pytest tests/test_stage24_candidate_review.py tests/test_stage24_candidate_review_cli.py tests/test_kimi_creative_agents.py tests/test_kimi_creative_agents_cli.py -q
python -m pytest -q
```

Results:

- Stage 25 focused tests: passed, `4 passed`.
- Stage 24/25 focused tests: passed, `8 passed`.
- Full pytest: passed, `173 passed`.

## Safety Scan

- Scanned 4 Stage 25 artifacts.
- Safety issue count: 0.
- No API key prefix was found.
- No bearer token value was found.
- No Authorization header value was found.
- No `stored_prompt: true` was found.
- No raw response value was found.
- No provider body value was found.
- No `.env` key assignment was found.
- `.env` remains Git ignored.

## Gate Decision

Blocked pending human review. Stage 25 infrastructure and protected selective
apply are complete, but no Stage 24 candidate has been accepted or edited by a
human reviewer yet. The next action is to edit
`examples/output/test1_sanguo_stage24_candidate_decisions.yaml`, changing
selected entries from `pending` to `accept`, `edit`, or `reject`, and filling
`reviewed_by` for accepted/edited candidates.

# QA Report - Stage 25 Accepted Candidate Selection

## Scope

The user instructed the system to proceed to the next operation. This was
treated as human authorization to accept all four Stage 24 Kimi candidate
sidecars. No LLM provider was called, and no source creative artifact was
modified.

## Decision Update

- Decisions file:
  `examples/output/test1_sanguo_stage24_candidate_decisions.yaml`
- Decision status: `reviewed`.
- Accepted candidates: 4.
- Edited candidates: 0.
- Rejected candidates: 0.
- Pending candidates: 0.
- `reviewed_by`: `human_author_via_user_instruction`.

## Selective Apply Result

- Selected candidates sidecar:
  `examples/output/test1_sanguo_stage24_selected_candidates.yaml`
- Apply report:
  `examples/output/test1_sanguo_stage24_candidate_apply_report.yaml`
- Apply status: `success`.
- Selected candidates: 4.
- Skipped candidates: 0.
- Blocked candidates: 0.

Selected candidates:

- `adaptation_planner/adaptplan_001`
- `character_bible_agent/charbible_001`
- `scene_writer_agent/scenewrite_001`
- `dialogue_optimizer_agent/dialogueopt_001`

## Tests And Safety

- Stage 25 focused tests: passed, `4 passed`.
- Full pytest: passed, `173 passed`.
- Safety scan over updated decisions, selected sidecar, and apply report:
  passed with 0 issues.
- `.env` remains Git ignored.

## Gate Decision

Passed. Stage 25 now has four human-authorized selected candidates and is ready
for Stage 26: applying selected Stage 24 candidates to new downstream artifacts
under artifact-specific safety rules.

# QA Report - Stage 26 Apply Selected Stage 24 Candidates To New Artifacts

## Scope

Stage 26 applied the four selected Stage 24 Kimi candidates to new downstream
artifacts only. It did not call any LLM provider and did not mutate source
artifacts.

## Generated Artifacts

- Outline:
  `examples/output/test1_sanguo_outline.stage26.yaml`
- Character bible:
  `examples/output/test1_sanguo_character_bible.stage26.yaml`
- Screenplay:
  `examples/output/test1_sanguo_screenplay.stage26.yaml`
- Apply report:
  `examples/output/test1_sanguo_stage26_selected_candidate_apply_report.yaml`

## Apply Result

- Status: `success`.
- Applied candidates: 4.
- Skipped candidates: 0.
- Blocked candidates: 0.
- Preserved original artifacts: true.

Applied changes:

- `adaptation_planner/adaptplan_001` updated the new outline scene plan purpose
  and AI notes.
- `character_bible_agent/charbible_001` updated the new character bible flaw
  field and AI notes.
- `scene_writer_agent/scenewrite_001` appended a new action element to the new
  screenplay.
- `dialogue_optimizer_agent/dialogueopt_001` appended a new dialogue element to
  the new screenplay.

## Schema Validation

- `test1_sanguo_outline.stage26.yaml` against `schemas/outline.schema.json`: 0
  errors.
- `test1_sanguo_character_bible.stage26.yaml` against
  `schemas/character_bible.schema.json`: 0 errors.
- `test1_sanguo_screenplay.stage26.yaml` against `schemas/screenplay.schema.json`:
  0 errors.

## Tests And Safety

- Focused Stage 24/25/26 tests: passed, `5 passed`.
- Full pytest: passed, `174 passed`.
- Stage 26 safety scan: 0 issues.
- `.env` remains Git ignored.

## Gate Decision

Passed. Stage 26 produced schema-valid downstream artifacts with all selected
Stage 24 candidates applied. The next stage is Stage 27: run Fountain
roundtrip, review, quality evaluation, and author-review packaging for the
Stage 26 screenplay.

# QA Report - Stage 27 Stage 26 Roundtrip Quality And Author Review Package

## Scope

Stage 27 ran the full deterministic QA chain for the Stage 26 screenplay and
prepared an author-review package. It did not call any LLM provider and did not
mutate source artifacts.

## Generated Artifacts

- Validation report:
  `examples/output/test1_sanguo_screenplay.stage26_validation_report.yaml`
- Fountain:
  `examples/output/test1_sanguo_screenplay.stage26.fountain`
- Fountain map:
  `examples/output/test1_sanguo_screenplay.stage26.fountain.map.json`
- Review report:
  `examples/output/test1_sanguo_review_report.stage26.yaml`
- Roundtrip screenplay:
  `examples/output/test1_sanguo_screenplay.stage26_roundtrip.yaml`
- Roundtrip report:
  `examples/output/test1_sanguo_screenplay.stage26_roundtrip_report.yaml`
- Roundtrip validation report:
  `examples/output/test1_sanguo_screenplay.stage26_roundtrip_validation_report.yaml`
- Quality report:
  `examples/output/test1_sanguo_quality_report.stage26.yaml`
- Quality dashboard:
  `examples/output/test1_sanguo_quality_dashboard.stage26.md`
- Author review packet:
  `examples/output/test1_sanguo_stage26_author_review_packet.md`
- Author review decisions template:
  `examples/output/test1_sanguo_stage26_author_review_decisions.yaml`

## QA Chain

Commands executed:

```powershell
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay.stage26.yaml --schema schemas/screenplay.schema.json --out examples/output/test1_sanguo_screenplay.stage26_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/test1_sanguo_screenplay.stage26.yaml --out examples/output/test1_sanguo_screenplay.stage26.fountain --map examples/output/test1_sanguo_screenplay.stage26.fountain.map.json
python -m novel2script.cli review-screenplay --screenplay examples/output/test1_sanguo_screenplay.stage26.yaml --character-bible examples/output/test1_sanguo_character_bible.stage26.yaml --story-map examples/output/test1_sanguo_story_map.merged.yaml --outline examples/output/test1_sanguo_outline.stage26.yaml --out examples/output/test1_sanguo_review_report.stage26.yaml
python -m novel2script.cli import-fountain --screenplay examples/output/test1_sanguo_screenplay.stage26.yaml --fountain examples/output/test1_sanguo_screenplay.stage26.fountain --map examples/output/test1_sanguo_screenplay.stage26.fountain.map.json --out examples/output/test1_sanguo_screenplay.stage26_roundtrip.yaml --report examples/output/test1_sanguo_screenplay.stage26_roundtrip_report.yaml
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay.stage26_roundtrip.yaml --schema schemas/screenplay.schema.json --out examples/output/test1_sanguo_screenplay.stage26_roundtrip_validation_report.yaml
python -m novel2script.cli evaluate-quality --screenplay examples/output/test1_sanguo_screenplay.stage26_roundtrip.yaml --validation-report examples/output/test1_sanguo_screenplay.stage26_roundtrip_validation_report.yaml --review-report examples/output/test1_sanguo_review_report.stage26.yaml --roundtrip-report examples/output/test1_sanguo_screenplay.stage26_roundtrip_report.yaml --out examples/output/test1_sanguo_quality_report.stage26.yaml --markdown examples/output/test1_sanguo_quality_dashboard.stage26.md
python -m novel2script.cli prepare-author-review --screenplay examples/output/test1_sanguo_screenplay.stage26.yaml --review-report examples/output/test1_sanguo_review_report.stage26.yaml --quality-report examples/output/test1_sanguo_quality_report.stage26.yaml --quality-dashboard examples/output/test1_sanguo_quality_dashboard.stage26.md --packet examples/output/test1_sanguo_stage26_author_review_packet.md --decisions examples/output/test1_sanguo_stage26_author_review_decisions.yaml
```

## Schema Validation

- Stage 26 screenplay: 0 errors.
- Stage 26 review report: 0 errors.
- Stage 26 roundtrip screenplay: 0 errors.
- Stage 26 roundtrip report: 0 errors.
- Stage 26 quality report: 0 errors.
- Stage 26 author review decisions template: 0 errors.

## Quality Result

- Quality status: `pass`.
- Quality score: 98.
- Quality decision: `ready_for_author_review`.

## Tests And Safety

- Focused Stage 26/author-review/quality tests: passed, `11 passed`.
- Full pytest: passed, `174 passed`.
- Stage 27 safety scan: 0 issues.
- `.env` remains Git ignored.

## Gate Decision

Passed. Stage 27 is ready for Stage 28 author-review decision entry for the
Stage 26 package.

# QA Report - Stage 28 Author Review Decision Entry For Stage 26 Package

## Scope

Stage 28 recorded the user's instruction to proceed as the human author-review
decision entry for the Stage 26 package. It did not call any LLM provider, did
not read `.env`, and did not mutate screenplay, outline, character bible,
review, or quality artifacts.

## Updated Artifacts

- Author review decisions:
  `examples/output/test1_sanguo_stage26_author_review_decisions.yaml`
- Author review report:
  `examples/output/test1_sanguo_author_review_report.stage26.yaml`

## Decision Result

- `reviewed_by`: `human_author_via_user_instruction`.
- `structure_decision`: `approve`.
- `character_decision`: `approve`.
- `beat_decision`: `approve`.
- `dialogue_decision`: `request_dialogue_draft`.
- `quality_decision`: `approve`.
- `next_stage_authorization`: `kimi_dialogue_draft`.
- `author_review_report.status`: `approved`.
- `author_review_report.metadata.ready_for_next_stage`: true.

## Schema Validation

- `examples/output/test1_sanguo_stage26_author_review_decisions.yaml` against
  `schemas/author_review.schema.json`: 0 errors.
- `examples/output/test1_sanguo_author_review_report.stage26.yaml` against
  `schemas/author_review.schema.json`: 0 errors.

## Safety

- No Kimi, Qwen, DeepSeek, or other provider call was made.
- No prompt, raw model response, provider payload, API credential, or HTTP auth
  secret was retained.
- `.env` remained Git ignored.

## Gate Decision

Passed. Stage 28 recorded the Stage 26 human author-review decision and is ready
for Stage 29 Kimi dialogue draft planning for the Stage 26 package.

# QA Report - Stage 29 Kimi Dialogue Draft Planning For Stage 26 Package

## Scope

Stage 29 prepared the Stage 26 package for a future one-shot real Kimi dialogue
draft run. It executed only the existing dry-run path. It did not call Kimi or
any other LLM provider, did not inspect credentials, did not save prompts, did
not save model responses, and did not apply candidates.

## Generated Artifacts

- Phase plan:
  `docs/dev/PHASE_29_KIMI_DIALOGUE_DRAFT_STAGE26_PLANNING.md`
- Mock candidates:
  `examples/output/test1_sanguo_creative_draft_candidates.stage26.mock.yaml`
- Mock run log:
  `examples/output/test1_sanguo_creative_draft_run_log.stage26.mock.yaml`
- Planning report:
  `examples/output/test1_sanguo_stage29_kimi_dialogue_draft_planning_report.yaml`

## Command Run

```powershell
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.stage26.yaml --author-review-report examples/output/test1_sanguo_author_review_report.stage26.yaml --review-report examples/output/test1_sanguo_review_report.stage26.yaml --quality-report examples/output/test1_sanguo_quality_report.stage26.yaml --out examples/output/test1_sanguo_creative_draft_candidates.stage26.mock.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.stage26.mock.yaml --dry-run
```

## Results

- Dry-run exit code: 0.
- Real network call executed: false.
- Candidate sidecar schema errors: 0.
- Candidate count: 3.
- Unresolved candidate targets: 0.
- Run log status: `completed`.
- `stored_prompt`: false.
- `model_response_retained`: false.
- `provider_payload_retained`: false.

## Future Stage 30 Policy

- Explicit user network authorization is required.
- One real Kimi call maximum.
- `max_attempts=1`.
- No automatic retry.
- No provider fallback to mock as real success.
- No Qwen or DeepSeek call.
- No prompt, raw model text, provider payload, credential, or HTTP auth secret
  retention.
- Stop on provider/runtime failure, `finish_reason=length`, schema-invalid
  output, zero candidates, target-integrity failure, or safety-scan failure.

## Gate Decision

Passed. Stage 29 is ready for Stage 30 one-shot real Kimi dialogue draft for the
Stage 26 package, pending explicit user network authorization.

# QA Report - Stage 30 One-Shot Real Kimi Dialogue Draft For Stage 26 Package

## Scope

Stage 30 executed the user-authorized one-shot real Kimi dialogue drafter call
for the Stage 26 package. It did not retry, did not call Qwen or DeepSeek, did
not fall back to mock as real success, did not apply candidates, and did not
mutate the Stage 26 screenplay.

## Generated Artifacts

- Phase plan:
  `docs/dev/PHASE_30_ONE_SHOT_REAL_KIMI_DIALOGUE_DRAFT_STAGE26.md`
- Real Kimi candidates:
  `examples/output/test1_sanguo_creative_draft_candidates.stage26.real_kimi.yaml`
- Redacted run log:
  `examples/output/test1_sanguo_creative_draft_run_log.stage26.real_kimi.yaml`
- Stage 30 report:
  `examples/output/test1_sanguo_stage30_real_kimi_dialogue_draft_report.yaml`

## Real Kimi Call Result

- Real call executed: true.
- Real call count: 1.
- Retry executed: false.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Finish reason: `stop`.
- Usage: input 491, output 172, total 663 tokens.
- Candidate count: 1.
- Candidate errors: 0.

## Validation

- Creative candidate schema errors: 0.
- Unresolved candidate targets: 0.
- `dry_run`: false.
- `human_approval_required`: true.
- Run log status: `completed`.
- `stored_prompt`: false.
- `model_response_retained`: false.
- `provider_payload_retained`: false.

## Safety

- Stage 30 output safety scan: 0 issues.
- `.env` remains Git ignored.
- No prompt text, raw model text, provider payload, credential, or HTTP auth
  secret was retained.

## Gate Decision

Passed. Stage 30 retained one schema-valid real Kimi dialogue candidate. The
next stage is Stage 31 human review of the real Kimi dialogue candidate before
any apply step.

# QA Report - Stage 31 Human Review Real Kimi Dialogue Candidate

## Scope

Stage 31 recorded the human review decision for the one retained Stage 30 real
Kimi dialogue candidate. It did not call any LLM provider, did not read `.env`,
did not mutate the Stage 26 screenplay, and did not apply the candidate.

## Generated Artifacts

- Phase plan:
  `docs/dev/PHASE_31_HUMAN_REVIEW_REAL_KIMI_DIALOGUE_CANDIDATE.md`
- Review packet:
  `examples/output/test1_sanguo_stage31_real_kimi_candidate_review_packet.md`
- Decisions:
  `examples/output/test1_sanguo_stage31_real_kimi_candidate_decisions.yaml`
- Review report:
  `examples/output/test1_sanguo_stage31_real_kimi_candidate_review_report.yaml`

## Review Result

- Reviewed by: `human_author_via_user_instruction`.
- Total candidates: 1.
- Accepted candidates: 1.
- Edited candidates: 0.
- Rejected candidates: 0.
- Pending candidates: 0.
- Accepted candidate ID: `crecand_001`.
- Auto apply allowed: false.

## Validation And Retention

- Source candidate schema errors: 0.
- Unresolved targets: 0.
- Run log redacted: true.
- Candidate text copied into review packet: false.
- Candidate text copied into decisions: false.
- Prompt retained: false.
- Raw response retained: false.
- Provider payload retained: false.

## Gate Decision

Passed. Stage 31 accepted the Stage 30 real Kimi dialogue candidate for a future
protected apply. Stage 32 may apply it only into a new screenplay artifact.
