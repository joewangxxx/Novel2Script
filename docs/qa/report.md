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
- Tracked files contain no private `.env`, recognized API-key pattern, prompt
  body in generated run logs, or temporary real-model output.

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
