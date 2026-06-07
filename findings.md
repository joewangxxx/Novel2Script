# Kimi Cross-Repository Audit Findings

## Confirmed Before Audit

- Novel2Script's `.ai` endpoint probe returned HTTP 401.
- Novel2Script's `.cn` endpoint probe returned HTTP 400.
- Existing Kimi key is present locally and remains redacted.
- Novel2Script currently uses a custom `urllib` OpenAI-compatible provider.
- Novel2Script currently sends non-streaming requests and conditionally sends
  `response_format: {"type": "json_object"}`.

## Successful Reference Project

- Repository exists and contains its own `AGENTS.md`.
- Its required read order includes `.codex/config.toml`, role configuration,
  and `docs/blackboard/state.yaml`.
- The root contains a local `.env`; its contents must not be printed.
- Detailed call-chain audit remains in progress.

## Novel2Script

- `.env` now exists in the Novel2Script repository and `N2S_KIMI_BASE_URL`
  resolves to host `api.moonshot.cn`, path `/v1`.
- `src/novel2script/llm/router.py` routes
  `kimi_dialogue_scene_drafter` to `kimi_creative`.
- Before repair, `kimi_creative` defaulted to `https://api.moonshot.ai/v1`
  and the provider sent `response_format: {"type": "json_object"}` when the
  agent requested JSON.
- The creative drafter requests `response_format="json_object"` in
  `src/novel2script/agents/creative_draft.py`, but downstream parsing already
  uses `json.loads(response.text)`, so provider-level JSON mode is not required
  to keep the sidecar validation behavior.

## Official API References

- Chinese Kimi docs and examples use `https://api.moonshot.cn/v1` with the
  OpenAI SDK and `Authorization: Bearer $MOONSHOT_API_KEY`.
- The K2.5 quickstart states OpenAI SDK compatibility and shows
  `openai>=1.0`.
- Kimi platform lists `kimi-k2.6` as a current model.
- Official examples do not require `response_format` for JSON-like tasks; the
  working local K2.5 project explicitly removed `temperature` and
  `response_format` for Kimi compatibility.

## Root-Cause Hypotheses

1. Endpoint region/platform mismatch caused the `.ai` 401.
2. The `.cn` HTTP 400 may be caused by a request parameter unsupported by
   Kimi K2.6 or the Chinese endpoint, especially JSON mode.
3. SDK/request-shape differences may explain why K2.5 works in the reference
   project while the custom HTTP provider fails here.

## Repairs Applied

- Added provider-level `supports_response_format` to Novel2Script.
- Configured `kimi_creative` with `default_base_url:
  https://api.moonshot.cn/v1`.
- Configured `kimi_creative` with `supports_response_format: false`.
- Added tests proving Kimi omits provider JSON mode while Qwen still supports
  it.

## Latest Probe Evidence

- Stage 22C minimal `.cn` probe with provider JSON mode disabled still returned
  HTTP 400 `invalid_request`.
- This means `response_format` was not the only incompatible parameter.
- Next local hypothesis from the successful project: Kimi compatibility may
  also require omitting explicit `temperature`.
