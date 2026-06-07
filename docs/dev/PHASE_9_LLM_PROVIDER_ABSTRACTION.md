# Phase 9: LLM Provider Abstraction

Stage 9 defines the provider boundary for later model-backed Novel2Script
agents. It introduces a shared request, response, routing, audit, cost, and
safety contract so future agents do not call different model APIs directly.

Stage 9A is architecture-only. It does not implement a real provider client,
does not call a network service, does not submit prompts, and does not implement
the full AI novel-to-screenplay workflow.

## Goals

- Define a uniform provider interface for future LLM-backed agents.
- Route agent tasks to provider profiles based on task strengths.
- Keep tests and default local execution on `mock_dry_run`.
- Require API keys to come from environment variables only.
- Log metadata, usage, cost, latency, and hashes without storing full prompts or
  full novel text.
- Preserve existing deterministic contracts from Stage 3 through Stage 8.

## Non-Goals

- No full AI screenplay generation chain.
- No real provider SDK integration.
- No committed API keys or secret configuration.
- No direct model calls from individual agents.
- No changes to `screenplay`, `review_report`, `fountain_roundtrip_report`, or
  `quality_report` schemas.

## Architecture Artifact

The detailed provider contract is:

- `docs/architecture/llm-provider.md`

That document is the source of truth for:

- `LLMRequest`
- `LLMResponse`
- `LLMRunRecord`
- provider profiles
- agent routing
- API key boundaries
- redacted logging rules
- safety gates

## Provider Profiles

Stage 9A defines these provider profile IDs:

| Profile | Purpose | Default Network |
| --- | --- | --- |
| `mock_dry_run` | deterministic tests and local dry runs | disabled |
| `qwen_long` | long-context source parsing and fidelity checks | disabled unless explicitly enabled |
| `kimi_creative` | adaptation planning, character bible, scene writing | disabled unless explicitly enabled |
| `deepseek_reasoning` | dramaturgy, reasoning, consistency review | disabled unless explicitly enabled |

Stage 11 narrows the active real-provider set to three Chinese models:
Qwen-Long, Kimi K2.6, and DeepSeek V4-Pro. Earlier optional dialogue and
structured-repair profiles were folded into `kimi_creative` and
`deepseek_reasoning`.

`mock_dry_run` is the default profile. A future implementation must not make
real network calls unless a run explicitly opts in and required environment
configuration is present.

## Agent Routing

The Stage 9A routing table is:

- `story_semantic_parser` -> `qwen_long`
- `adaptation_planner` -> `kimi_creative`
- `character_bible_agent` -> `kimi_creative`
- `scene_writer_agent` -> `kimi_creative`
- `dialogue_optimizer_agent` -> `kimi_creative`
- `beat_dramaturgy_agent` -> `deepseek_reasoning`
- `source_fidelity_reviewer` -> `qwen_long` + `deepseek_reasoning`
- `yaml_repair_agent` -> `deepseek_reasoning`

Every route falls back to `mock_dry_run` when dry-run mode is enabled or when
tests inject mock clients.

## LLMRequest Summary

Future provider code should accept an in-memory `LLMRequest` with:

- request and correlation IDs
- `agent_name`
- `task_type`
- optional requested provider profile
- `dry_run`
- model parameters
- input artifact references
- runtime-only prompt content
- prompt metadata and prompt hash
- output contract
- safety flags

Prompt content may exist in memory for the call but must not be stored in
`LLMRunRecord` logs.

## LLMResponse Summary

Future provider code should return an `LLMResponse` with:

- request and correlation IDs
- resolved provider profile and model ID
- status
- output content or structured result for the immediate caller
- output hash
- usage and estimated cost
- latency
- finish reason
- safety metadata
- structured error fields

Allowed statuses are `succeeded`, `failed`, `blocked`, and `dry_run`.

## LLMRunRecord Summary

Every provider attempt should write a redacted `LLMRunRecord` containing:

- run, request, and correlation IDs
- timestamp
- agent name and task type
- provider profile, provider type, and model ID
- routing decision and fallback state
- input artifact references
- prompt template ID/version and prompt hash
- output hash and schema validation status
- token usage, estimated cost, and latency
- safety flags
- structured error code and redacted message

It must not store:

- full novel text
- full prompts
- full model responses
- raw provider request/response JSON
- API keys, headers, bearer tokens, cookies, signed URLs, or other secrets

## API Key Boundary

API keys are allowed only through environment variables:

- `N2S_QWEN_API_KEY`
- `N2S_KIMI_API_KEY`
- `N2S_DEEPSEEK_API_KEY`

Optional base URL overrides may use:

- `N2S_QWEN_BASE_URL`
- `N2S_KIMI_BASE_URL`
- `N2S_DEEPSEEK_BASE_URL`

Rules:

- Do not commit API keys or secret `.env` files.
- Do not accept API keys from YAML artifacts, generated reports, prompts, or CLI
  positional args.
- Tests must pass with no real keys present.
- Missing keys for a real provider must produce a blocked/configuration error,
  not a fallback to a different real provider.

## Safety And Audit Boundary

Before a real provider call, future implementation must verify:

- network use is explicitly enabled for the run
- selected provider profile is registered
- `agent_name` is registered and allowed for that route
- required key environment variable is present
- prompt and response redaction are enabled for logs
- the request does not mark that it contains full novel text

If any safety gate fails, the provider returns `blocked` and writes a redacted
run record.

## Stage 9 File Plan

Stage 9A adds:

- `docs/dev/PHASE_9_LLM_PROVIDER_ABSTRACTION.md`
- `docs/architecture/llm-provider.md`
- updates to `docs/architecture/folder-plan.md`
- updates to `docs/blackboard/state.yaml`

Stage 9B may add a mock-first provider implementation:

- `src/novel2script/llm/__init__.py`
- `src/novel2script/llm/contracts.py`
- `src/novel2script/llm/provider_profiles.py`
- `src/novel2script/llm/router.py`
- `src/novel2script/llm/mock_provider.py`
- `src/novel2script/llm/run_records.py`
- `tests/test_llm_contracts.py`
- `tests/test_llm_router.py`
- `tests/test_mock_provider.py`

Real provider clients should wait until the mock provider, routing, redacted run
records, and no-network tests are stable.

## Gate For Stage 9A

Stage 9A passes if:

- `LLMRequest`, `LLMResponse`, and `LLMRunRecord` are documented.
- Provider profiles and agent routing are explicit.
- `mock_dry_run` is the default provider behavior.
- API keys are environment-only and never committed.
- Run logs store only metadata, usage, latency, hashes, and safety fields.
- No implementation code, real network call, API key, or prior schema change is
  introduced.
