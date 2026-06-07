# Phase 22: Kimi Cross-Repository Audit And Repair

## Goal

Audit the working Kimi integration in `E:\health_ai_platform_2.0`, compare it
with Novel2Script's Kimi K2.6 creative-agent path, repair the provider request
shape, and verify the minimal connection without retaining secrets, prompts, raw
model text, or provider request/response bodies.

## A. Successful Project Analysis

Reference project: `E:\health_ai_platform_2.0`.

### Configuration

- `backend/core/config.py:34` reads `OPENAI_API_KEY`.
- `backend/core/config.py:35` defaults `OPENAI_BASE_URL` to
  `https://api.moonshot.cn/v1`.
- `backend/core/config.py:36` defaults `OPENAI_MODEL` to `kimi-k2.5`.
- `backend/core/config.py:58-63` uses Pydantic settings with `.env`.
- `backend/core/config.py:95-98` masks the key in optional debug logging.
- Root `.env` exists and contains `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and
  `OPENAI_MODEL`; values were not printed or copied.

### Client And Request Shape

- `backend/services/chat_service.py:8` imports `AsyncOpenAI`.
- `backend/services/chat_service.py:51-56` creates
  `AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)`.
- `backend/services/chat_service.py:460-463` sends final chat with only
  `model` and `messages`.
- `backend/services/chef_service.py:123-130`,
  `backend/services/nutrition_service.py:164-171`, and
  `backend/services/ocr_service.py:433-440` all call
  `client.chat.completions.create(...)` without `temperature` and without
  `response_format`.
- The successful project explicitly comments that `temperature` and
  `response_format` were removed for Kimi K2.5 compatibility.

### Response Handling

- `backend/services/ocr_service.py:446-450` removes thinking tags and Markdown
  fences.
- `backend/services/ocr_service.py:452-467` attempts direct JSON parsing, then
  regex-extracts the first JSON object as fallback.
- `backend/services/chef_service.py:139-149` strips Markdown code fences before
  `json.loads`.

### Agent, Tools, Streaming, Context

- `backend/services/chat_service.py:84-99` exposes `stream_chat`, but this is
  application-level event streaming, not raw token streaming from Kimi.
- `backend/api/api_v1/endpoints/chat.py:385-416` wraps those events in SSE via
  `StreamingResponse(..., media_type="text/event-stream")`.
- `backend/services/chat_service.py:559-564` attempts native OpenAI tool
  calling with `tools=get_tool_definitions(...)` and `tool_choice="auto"`.
- `backend/services/chat_service.py:565-589` falls back to deterministic local
  tool planning if native tool calling is unavailable.
- `backend/services/agent_tools.py:86-110` builds OpenAI-compatible function
  tool definitions.
- `backend/services/agent_tools.py:165-243` executes registered tools or model
  tool calls.
- `backend/services/conversation_service.py:9-17` builds the message window.
- `backend/services/context_builder.py:38-88` trims history and context to
  approximate token budgets.

### Successful Call Sequence

1. FastAPI starts and imports settings from `backend/core/config.py`.
2. Services instantiate `AsyncOpenAI` with `OPENAI_API_KEY` and
   `OPENAI_BASE_URL`.
3. Chat endpoint receives a request.
4. `ChatService._chat_events` builds profile, RAG, tool, history, system, and
   user context.
5. Tool-planning call optionally sends `tools` and `tool_choice="auto"`.
6. Final answer call sends `model` and `messages`.
7. Response text is read from `response.choices[0].message.content`.
8. JSON tasks strip Markdown fences before parsing.
9. `/chat/stream` returns application-level SSE status/tool/final events.

## B. Novel2Script Findings

Current project: `C:\Users\JoeWang\Desktop\面向小说作者的 AI 剧本改编工作台\Novel2Script`.

### Previous Problems

- `src/novel2script/llm/router.py` previously defaulted Kimi to
  `https://api.moonshot.ai/v1`; the Chinese platform key returned HTTP 401.
- After `.env` was changed to `https://api.moonshot.cn/v1`, the request moved
  past authentication but returned HTTP 400 while `response_format` was still
  sent.
- After omitting `response_format`, HTTP 400 persisted.
- After also omitting `temperature`, the provider returned a model response;
  the minimal probe then failed only because strict `json.loads` did not accept
  the text as JSON. Raw text was not retained by policy.

### Current Kimi Chain

- `src/novel2script/llm/router.py:16` routes
  `kimi_dialogue_scene_drafter` to `kimi_creative`.
- `src/novel2script/llm/router.py:35-42` defines provider type, model,
  credential env var, base URL env var, default base URL, and Kimi compatibility
  flags.
- `src/novel2script/llm/router.py:80-103` creates
  `OpenAICompatibleProvider` from environment.
- `src/novel2script/llm/openai_compatible_provider.py:95-174` loads the key,
  builds the request, sends one or more attempts according to `max_attempts`,
  and returns a redacted `LLMResponse`.
- `src/novel2script/llm/openai_compatible_provider.py:202-228` builds the
  OpenAI-compatible payload.
- `src/novel2script/agents/creative_draft.py:326-343` builds the real Kimi
  `LLMRequest` and dispatches it with `max_attempts=1`.
- `src/novel2script/agents/creative_draft.py:359` now parses model JSON through
  `_parse_model_json`.
- `src/novel2script/agents/creative_draft.py:492-500` strips Markdown fences in
  memory before JSON parsing.

## C. Repairs Applied

- `src/novel2script/llm/router.py:40` changed Kimi default base URL to
  `https://api.moonshot.cn/v1`.
- `src/novel2script/llm/router.py:41-42` configures Kimi to omit
  `response_format` and `temperature`.
- `src/novel2script/llm/openai_compatible_provider.py:92-93` adds provider
  capability flags.
- `src/novel2script/llm/openai_compatible_provider.py:202-228` conditionally
  omits incompatible parameters while preserving JSON mode for providers that
  support it.
- `src/novel2script/agents/creative_draft.py:492-500` adds fenced-JSON cleanup.
- Tests added:
  - `tests/test_openai_compatible_provider.py:194-228`
  - `tests/test_llm_router.py:104-116`
  - `tests/test_creative_draft_agent.py:286-369`

## D. Official/API Compatibility Notes

Current Chinese platform references show `https://api.moonshot.cn/v1`, OpenAI
SDK compatibility, and `kimi-k2.6` availability. The local successful project
matches the Chinese endpoint and avoids `temperature`/`response_format` for
Kimi compatibility.

Official references checked:

- `https://platform.moonshot.cn/`
- `https://platform.moonshot.cn/docs/guide/kimi-k2-5-quickstart`
- `https://platform.moonshot.cn/blog/posts/kimi-thinking`

## E. Verification

### Offline Tests

- New red tests failed before implementation:
  - missing `supports_response_format`
  - missing `supports_temperature`
  - fenced JSON rejected by creative drafter
- Focused provider/router/readiness tests passed: `40 passed`.
- Full test suite passed: `163 passed`.

### Real Minimal Probe Evidence

Evidence file:
`examples/output/test1_sanguo_kimi_probe_cn_compat_payload_report.yaml`.

Result:

- Endpoint: `api.moonshot.cn`.
- Model: `kimi-k2.6`.
- Key present: true.
- `response_format` sent: false.
- `temperature` sent: false.
- Provider response received: true.
- HTTP status: none.
- Error category: `malformed_model_json`.
- Raw response retained: false.
- Prompt retained: false.
- Provider body retained: false.
- Creative drafter executed: false.

Interpretation: Kimi connectivity/authentication is now working for the minimal
provider path. The minimal JSON acceptance probe did not pass because the model
text was not accepted as strict JSON and raw text was not retained. The creative
agent now has fenced JSON cleanup coverage, but a full real creative draft has
not been run in this phase.

## F. Final Capability Matrix

- Successful Kimi API connection: yes, minimal provider response was received.
- Kimi K2.6 creative-agent construction: yes, offline chain and fake-router
  real-mode tests pass.
- Normal conversation: provider-level minimal chat response was received, but
  no raw conversation text was retained.
- Tool calling in Novel2Script: not implemented for the creative drafter.
- Streaming in Novel2Script: not implemented; current project is CLI/artifact
  oriented.
- Full real creative draft: not run in this phase.
- Enhanced screenplay: not generated.

## G. Next Stage Recommendation

Stage 23 may run a separately authorized real Kimi creative draft under the
existing no-retry/no-retention policy. It should not auto-apply candidates until
the retained sidecar validates against `schemas/creative_draft_candidates.schema.json`.
