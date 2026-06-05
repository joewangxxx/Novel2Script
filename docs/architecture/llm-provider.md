# LLM Provider Architecture

Stage 9 defines a shared provider abstraction for later real model-backed
agents. It does not implement a full AI novel-to-screenplay workflow and does
not authorize individual agents to call model APIs directly.

The provider layer is the only approved boundary for model calls. Agents submit
an `LLMRequest`, receive an `LLMResponse`, and the provider layer writes a
redacted `LLMRunRecord` for audit, cost, latency, routing, and safety checks.

## Design Goals

- Route each agent task to a provider profile without hard-coding one universal
  model.
- Keep the default execution mode as `mock_dry_run` so tests and local
  deterministic workflows do not depend on network access.
- Keep API keys out of repository files and generated artifacts.
- Record enough metadata for audit and cost visibility without saving full
  novel text, full prompts, or full model responses in logs.
- Preserve existing screenplay, review, roundtrip, and quality contracts.

## Non-Goals

- No full AI generation chain.
- No provider SDK implementation in Stage 9A.
- No committed API keys, endpoints with secrets, or captured real prompts.
- No replacement for deterministic Stage 3 through Stage 8 behavior.
- No direct model calls from parser, planner, generator, reviewer, importer, or
  quality modules.

## Provider Profiles

Provider profile IDs are stable routing names. They are not API keys and not
hard-coded model monopolies.

```yaml
provider_profiles:
  mock_dry_run:
    provider_type: mock
    default: true
    network_enabled: false
    purpose: "Tests, local dry runs, contract verification."
  qwen_long:
    provider_type: qwen
    env_api_key: N2S_QWEN_API_KEY
    env_base_url: N2S_QWEN_BASE_URL
    strengths: ["long_context", "source_fidelity", "semantic_extraction"]
  kimi_creative:
    provider_type: kimi
    env_api_key: N2S_KIMI_API_KEY
    env_base_url: N2S_KIMI_BASE_URL
    strengths: ["creative_planning", "adaptation", "character_work"]
  doubao_dialogue:
    provider_type: doubao
    env_api_key: N2S_DOUBAO_API_KEY
    env_base_url: N2S_DOUBAO_BASE_URL
    strengths: ["dialogue", "naturalness", "localized_expression"]
  deepseek_reasoning:
    provider_type: deepseek
    env_api_key: N2S_DEEPSEEK_API_KEY
    env_base_url: N2S_DEEPSEEK_BASE_URL
    strengths: ["reasoning", "dramaturgy", "consistency_review"]
  glm_structured:
    provider_type: glm
    env_api_key: N2S_GLM_API_KEY
    env_base_url: N2S_GLM_BASE_URL
    strengths: ["structured_output", "yaml_repair", "schema_following"]
```

Rules:

- `mock_dry_run` is the default profile unless configuration explicitly opts in
  to a real provider.
- Real provider profiles require API keys from environment variables only.
- Missing real-provider keys must fail closed with a clear configuration error.
- Test suites must use `mock_dry_run` or injected fake clients only.
- Provider profile names can change only through architecture review after
  contract freeze.

## Agent Routing

The router maps agent intent to one or more provider profiles:

| Agent | Primary Route | Secondary Route | Notes |
| --- | --- | --- | --- |
| `story_semantic_parser` | `qwen_long` | `mock_dry_run` | Long-context source reading; must preserve source refs. |
| `adaptation_planner` | `kimi_creative` | `mock_dry_run` | Outline and adaptation choices. |
| `character_bible_agent` | `kimi_creative` | `mock_dry_run` | Character wants, needs, voice, arc. |
| `scene_writer_agent` | `kimi_creative` | `mock_dry_run` | Scene draft expansion from approved outline. |
| `dialogue_optimizer_agent` | `doubao_dialogue` | `mock_dry_run` | Dialogue rewrite suggestions only. |
| `beat_dramaturgy_agent` | `deepseek_reasoning` | `mock_dry_run` | Beat objective, conflict, stakes, and turn analysis. |
| `source_fidelity_reviewer` | `qwen_long` + `deepseek_reasoning` | `mock_dry_run` | Two-pass source check: long-context extraction plus reasoning. |
| `yaml_repair_agent` | `glm_structured` | `mock_dry_run` | Structured YAML repair under schema validation. |

Routing rules:

- The caller requests an `agent_name`, not a raw provider.
- The router resolves the provider profile from this table.
- A caller may request `dry_run: true`; this forces `mock_dry_run`.
- A real provider call is allowed only when configuration enables network use
  for that run.
- Multi-provider routes must record a separate `LLMRunRecord` for each provider
  call and a parent correlation ID for the whole agent task.

## LLMRequest Contract

`LLMRequest` is an in-memory request object. It may contain prompt text at
runtime, but prompt text must not be persisted in run logs.

```yaml
LLMRequest:
  request_id: "llm_req_001"
  correlation_id: "agent_run_001"
  agent_name: "scene_writer_agent"
  task_type: "scene_generation"
  provider_profile: null
  dry_run: true
  model_parameters:
    temperature: 0.4
    max_output_tokens: 1200
    top_p: 0.9
  input_artifacts:
    story_map: "examples/output/generated_story_map.yaml"
    outline: "examples/output/generated_outline.yaml"
    character_bible: "examples/output/generated_character_bible.yaml"
    screenplay: "examples/output/generated_screenplay.yaml"
  prompt:
    system: "<runtime only>"
    user: "<runtime only>"
  prompt_metadata:
    prompt_template_id: "scene_writer_v0"
    prompt_template_version: "0.1.0"
    prompt_hash: "sha256:..."
    source_excerpt_policy: "bounded_trace_excerpt"
    contains_full_novel_text: false
  output_contract:
    format: "yaml"
    schema_ref: "schemas/screenplay.schema.json"
  safety:
    allow_network: false
    redact_prompt_in_logs: true
    redact_response_in_logs: true
    require_source_trace: true
```

Required fields:

- `request_id`
- `correlation_id`
- `agent_name`
- `task_type`
- `dry_run`
- `model_parameters`
- `input_artifacts`
- `prompt_metadata`
- `output_contract`
- `safety`

Prompt rules:

- Full novel text should not be embedded when artifact refs and bounded source
  traces are enough.
- If excerpts are needed, the request must keep them bounded and traceable.
- `prompt_hash` is computed over the runtime prompt content and template
  metadata, but the prompt itself is not written to run records.

## LLMResponse Contract

`LLMResponse` is returned to the caller. It may contain generated text or
structured data because it is the immediate result of the call, but persistence
outside explicit output artifacts must follow the same redaction rules.

```yaml
LLMResponse:
  request_id: "llm_req_001"
  correlation_id: "agent_run_001"
  provider_profile: "mock_dry_run"
  model_id: "mock-model"
  status: "succeeded"
  output:
    content: ""
    structured: null
    content_hash: "sha256:..."
  usage:
    input_tokens: 0
    output_tokens: 0
    total_tokens: 0
    estimated_cost_cny: 0.0
  latency_ms: 0
  finish_reason: "dry_run"
  safety:
    redacted_for_log: true
    contains_full_novel_text: false
    schema_validation: "not_run"
  error:
    code: null
    message: null
```

Allowed statuses:

- `succeeded`
- `failed`
- `blocked`
- `dry_run`

Error handling:

- Provider timeouts, rate limits, bad credentials, invalid schema output, and
  safety violations must return structured errors.
- Failed responses must still produce an `LLMRunRecord`.
- Callers must not retry indefinitely; future implementation should respect the
  blackboard retry limits.

## LLMRunRecord Contract

`LLMRunRecord` is the persisted audit log unit. It stores metadata, hashes,
usage, latency, routing, and safety decisions. It must not store full prompt
content, full novel text, or full generated response text.

```yaml
LLMRunRecord:
  schema_version: "0.1.0"
  run_id: "llm_run_001"
  request_id: "llm_req_001"
  correlation_id: "agent_run_001"
  generated_at: "2026-06-05T20:30:00+08:00"
  agent_name: "scene_writer_agent"
  task_type: "scene_generation"
  provider_profile: "mock_dry_run"
  provider_type: "mock"
  model_id: "mock-model"
  status: "dry_run"
  dry_run: true
  routing:
    requested_profile: null
    resolved_profile: "mock_dry_run"
    fallback_used: false
    route_reason: "default dry-run profile"
  input_artifacts:
    story_map: "examples/output/generated_story_map.yaml"
    outline: "examples/output/generated_outline.yaml"
  prompt:
    prompt_template_id: "scene_writer_v0"
    prompt_template_version: "0.1.0"
    prompt_hash: "sha256:..."
    prompt_chars: 4200
    stored_prompt: false
  output:
    content_hash: "sha256:..."
    output_chars: 0
    stored_output: false
    schema_ref: "schemas/screenplay.schema.json"
    schema_validation_status: "not_run"
  usage:
    input_tokens: 0
    output_tokens: 0
    total_tokens: 0
    estimated_cost_cny: 0.0
  latency_ms: 0
  safety:
    allow_network: false
    prompt_redacted: true
    response_redacted: true
    contains_full_novel_text: false
    api_key_source: "environment"
    api_key_persisted: false
  error:
    code: null
    message: null
```

Run record rules:

- Store hashes, lengths, artifact paths, usage, latency, status, and routing.
- Do not store full prompts, full novel text, or full model output.
- Do not store API keys, headers, signed URLs, or provider credentials.
- If a response is later saved as a product artifact, that artifact must follow
  the target artifact contract and provenance rules.
- Cost must be recorded as a best-effort estimate and may be `0.0` for mock.

## API Key And Environment Boundary

API keys may come only from environment variables:

- `N2S_QWEN_API_KEY`
- `N2S_KIMI_API_KEY`
- `N2S_DOUBAO_API_KEY`
- `N2S_DEEPSEEK_API_KEY`
- `N2S_GLM_API_KEY`

Optional base URL overrides may come from:

- `N2S_QWEN_BASE_URL`
- `N2S_KIMI_BASE_URL`
- `N2S_DOUBAO_BASE_URL`
- `N2S_DEEPSEEK_BASE_URL`
- `N2S_GLM_BASE_URL`

Rules:

- Never commit API keys, `.env` files containing secrets, request headers, or
  provider credential dumps.
- Do not accept API keys from YAML artifacts, CLI positional args, generated
  reports, or prompt files.
- If a future CLI needs provider configuration, it should accept profile names
  and dry-run flags, not secret values.
- Tests must not require real keys. Missing keys should be expected in CI.

## Logging And Privacy Boundary

Approved run log content:

- IDs and timestamps.
- Agent name, task type, provider profile, provider type, model ID.
- Artifact paths or artifact IDs.
- Prompt template ID and version.
- Prompt hash, response hash, prompt length, output length.
- Token usage, estimated cost, latency.
- Status, finish reason, error code, and redacted error message.
- Safety flags and whether network was allowed.

Forbidden run log content:

- Full novel text.
- Full prompts.
- Full generated responses.
- API keys, headers, bearer tokens, cookies, signed URLs, or account IDs.
- Raw provider request/response JSON.

## Safety Gates

Before any real provider call, the provider layer must verify:

- The selected provider profile is not `mock_dry_run`.
- Network use is explicitly enabled for the run.
- Required environment variables are present.
- The request allows prompt and response redaction in logs.
- The request does not mark `contains_full_novel_text: true`.
- The caller uses a registered `agent_name`.
- The route is allowed for that agent.

Any failed gate returns a structured `blocked` response and writes a redacted
run record.

## Planned Implementation Boundary

Stage 9B may add a provider package such as:

- `src/novel2script/llm/__init__.py`
- `src/novel2script/llm/contracts.py`
- `src/novel2script/llm/provider_profiles.py`
- `src/novel2script/llm/router.py`
- `src/novel2script/llm/mock_provider.py`
- `src/novel2script/llm/run_records.py`
- `tests/test_llm_contracts.py`
- `tests/test_llm_router.py`
- `tests/test_mock_provider.py`

Stage 9B should still default to mock/dry-run. Real provider clients should be
added only after tests prove the abstraction and logging boundary without
network access.

## Governance

This Stage 9A contract is draft. After a future freeze:

- Agents must not bypass the provider abstraction.
- Provider routing changes must be reviewed as architecture changes.
- Existing screenplay, review, roundtrip, and quality schemas must not be
  modified to fit provider implementation shortcuts.
- Contract conflicts must be proposed under
  `docs/architecture/change-requests/`.
