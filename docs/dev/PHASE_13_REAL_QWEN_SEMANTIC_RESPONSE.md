# Phase 13: Real Qwen Semantic Response

## Goal

Stage 13 converts an explicitly enabled Qwen-Long JSON response into the
existing `semantic_candidates` sidecar. The model supplies candidate drafts
only. Local code supplies candidate IDs, artifact paths, merge policy, provider
metadata, and redacted run records.

Dry-run behavior remains deterministic and unchanged.

## Official Provider Assumptions

- Qwen JSON Mode is enabled with
  `response_format: {"type": "json_object"}`.
- A system or user message must contain the word `JSON`.
- Qwen-Long is listed as supporting structured JSON output.
- OpenAI-compatible requests use `/chat/completions`.

References:

- https://help.aliyun.com/zh/model-studio/qwen-structured-output
- https://help.aliyun.com/zh/model-studio/long-context-qwen-long
- https://help.aliyun.com/zh/model-studio/error-code

## Two-Layer Contract

Provider text must first validate against:

```text
schemas/qwen_semantic_model_output.schema.json
```

The model output root contains only:

```json
{"candidates": []}
```

Each draft contains:

- `type`
- `confidence`
- `evidence`
- `source_trace_ids`
- `target_story_map_field`
- type-specific `proposed_fields`

The draft contract remains at version `0.1.0` and is still marked draft.
`candidates` accepts zero to three items. Responses containing more than three
items fail schema validation as a whole.

The model must not return:

- candidate IDs;
- source or output file paths;
- run IDs or run logs;
- `merge_policy`;
- approval decisions;
- provider metadata.

Local conversion adds stable `semcand_###` IDs in accepted response order and
sets `merge_policy: human_approval_required`.

## Trace Trust Boundary

The request contains at most the bounded excerpts selected by the existing
agent. The local program builds an exact whitelist of
`(chapter_id, paragraph_id)` pairs from those excerpts.

A candidate enters the sidecar only when:

- its chapter exists in the sent whitelist;
- every paragraph ID was sent for that same chapter;
- its model-output shape validates;
- it is not a canonical duplicate of an earlier accepted draft.

The model's trace values are therefore untrusted references until local
validation succeeds. The model cannot create new source trace IDs or widen the
request scope.

## Response Handling

| Condition | Result |
| --- | --- |
| Valid JSON and valid schema | Convert accepted drafts locally |
| Empty or whitespace response | No candidates; `empty_model_output` |
| Malformed JSON | No candidates; `malformed_model_json` |
| Unknown field or invalid shape | No candidates; `invalid_model_output_schema` |
| `finish_reason: length` | No candidates; `truncated_model_output` |
| Trace outside excerpt whitelist | Skip candidate; `hallucinated_source_trace` |
| Canonical duplicate | Keep first; skip later duplicate; `duplicate_candidate` |

Errors are written to the existing sidecar error array. Raw provider text is
not written to the sidecar or run log.

## JSON Prompt Boundary

Real-mode prompts must:

- require the unique root shape `{"candidates": [...]}`;
- require zero to three concise candidates;
- enumerate every required candidate field;
- enumerate all allowed candidate-type to target-field mappings;
- enumerate the type-specific `proposed_fields`;
- include a schema-valid `event_candidate` example;
- forbid Markdown fences, prose, candidate IDs, paths, merge policy, run
  metadata, thinking-process text, `semantic_traces`, `semantic_concept`,
  `description`, and `sources`;
- state that only supplied chapter and paragraph IDs may be referenced.

Dry-run requests do not depend on provider response text and keep the existing
deterministic candidate builder.

## Stage 13E Fail-Closed Recovery

Stage 13E strengthens the prompt without changing the model-output schema.
Schema-validation failures use the stable message:

```text
Provider JSON did not match qwen semantic model-output schema.
```

`ValidationError.message`, the failing instance, nested validation context, and
raw provider response are never persisted to the sidecar, run log, CLI stderr,
or QA artifacts.

Real-mode CLI exit behavior is also part of the contract:

- return zero only when at least one candidate is accepted and there is no
  global model-output error;
- return nonzero for empty, malformed, schema-invalid, or truncated output;
- return nonzero when all candidates are excluded by trace or duplicate
  checks;
- still write the schema-valid sidecar and redacted run log for diagnosis.

The resumed real smoke is limited to one invocation after all offline tests and
security scans pass. A failed smoke is not retried automatically and requires
human review.

## Stage 13F Controlled Output Budget

The user-approved Stage 13F recovery keeps the bounded input unchanged:

- at most eight excerpts;
- at most 120 characters per excerpt.

Real requests use `max_tokens: 2048`; dry-run requests retain their existing
1024-token request metadata. The model is instructed to return at most three
concise candidates. `finish_reason: length` remains a blocking error, and
truncated JSON is never repaired or partially parsed.

## Retry Policy

Network execution uses at most three total attempts.

- Retry TLS/connectivity failures and timeouts.
- Retry HTTP 429 and HTTP 500, 502, 503, and 504.
- Do not retry authentication, authorization, invalid request, malformed JSON,
  schema errors, invalid traces, duplicates, or `finish_reason: length`.
- HTTP 429 is retried within the same three-attempt limit because provider
  error bodies are not a stable machine-readable way to distinguish transient
  throttling from quota-related failures.
- Backoff delays are bounded exponential delays: 0.5 seconds, then 1.0 second.
- Tests inject fake transports and a no-op sleeper; automated tests never
  access the network.

## Safety And Logging

- Real execution still requires `--allow-network` and an environment API key.
- No API key is accepted as a CLI argument.
- The run log stores hashes, usage, latency, finish reason, routing metadata,
  and retry-safe status only.
- The full prompt, bounded excerpt text, and raw model response are not stored
  in the run log.
- The deterministic `story_map` is read-only.
- Stage 12 merge is never invoked automatically.

## Test Plan

- JSON Mode request includes `response_format` and a JSON prompt.
- Valid real response produces schema-valid semantic candidates.
- Candidate IDs are assigned locally and stably.
- Dry-run output remains deterministic.
- Empty, malformed, schema-invalid, and truncated responses fail closed.
- Hallucinated trace IDs are excluded.
- Duplicate drafts are excluded after the first occurrence.
- Fake TLS, 429, and 5xx failures retry within the fixed limit.
- Non-retryable HTTP failures make one attempt.
- CLI fake-router execution writes no prompt or raw response.
