# Phase 11: Real LLM Provider Opt-In

## Goal

Stage 11 adds the first real provider execution path while keeping Novel2Script
safe by default. Local tests and normal commands still use `mock_dry_run`; a
real model call happens only when the user explicitly passes `--allow-network`
and the required provider API key is present in an environment variable.

The first real-call target is `story_semantic_parser` routed to `qwen_long`.
The output remains a sidecar `semantic_candidates.yaml`; the agent still must
not mutate `story_map.yaml`.

## Selected Chinese Model Set

| Provider Profile | API Model | Main Responsibility |
| --- | --- | --- |
| `qwen_long` | `qwen-long` | Long-context story semantic parsing and source fidelity extraction. |
| `kimi_creative` | `kimi-k2.6` | Adaptation planning, character work, scene writing, and dialogue suggestions. |
| `deepseek_reasoning` | `deepseek-v4-pro` | Dramaturgy reasoning, source fidelity review, and YAML repair suggestions. |

The previous optional `doubao_dialogue` and `glm_structured` profiles are not
part of the current active route set.

## Environment Variables

API keys must be configured outside the repository:

```powershell
$env:N2S_QWEN_API_KEY="<qwen key>"
$env:N2S_QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

$env:N2S_KIMI_API_KEY="<kimi key>"
$env:N2S_KIMI_BASE_URL="https://api.moonshot.ai/v1"

$env:N2S_DEEPSEEK_API_KEY="<deepseek key>"
$env:N2S_DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

Do not commit `.env` files, captured headers, bearer tokens, provider request
JSON, or raw provider responses.

## Real Call Gate

Default dry run:

```powershell
python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out examples/output/generated_semantic_candidates.yaml `
  --run-log examples/output/generated_semantic_agent_run_log.yaml
```

Explicit real Qwen-Long call:

```powershell
python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.real.yaml `
  --run-log temp/semantic_agent_run_log.real.yaml `
  --allow-network
```

Expected real-call behavior:

- `semantic_candidates.provider_profile: qwen_long`
- `semantic_candidates.dry_run: false`
- `semantic_candidates.human_approval_required: true`
- `run_log.llm_run_records[0].stored_prompt: false`
- no full prompt text, full source text, API key, or bearer token in generated
  artifacts
- `story_map.yaml` unchanged

## Implementation Boundary

Stage 11 implements:

- `OpenAICompatibleProvider` using `/chat/completions`
- environment-only credentials
- `LLMRouter.from_environment(allow_network=True)`
- `run-agent story-semantic-parser --allow-network`
- fake-transport tests for real provider behavior
- no-key CLI test proving real calls fail closed

Stage 11 does not implement:

- parsing arbitrary real model YAML into accepted story map changes
- automatic merge of semantic candidates
- full screenplay generation with real models
- real provider calls during automated tests
- storing raw prompts or responses in run logs

## Gate

Stage 11 passes when:

- all tests pass without real API keys;
- default CLI execution still resolves to `mock_dry_run`;
- `--allow-network` requires provider credentials and fails closed without them;
- fake provider tests verify request shape, usage mapping, and redaction;
- sample generated artifacts remain schema-valid in dry-run mode;
- docs and routing config reflect the active three-model plan.
