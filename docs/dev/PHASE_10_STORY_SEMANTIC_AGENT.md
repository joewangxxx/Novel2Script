# Phase 10: Story Semantic Agent

## Goal

Stage 10 introduces the first LLM-backed agent boundary for Novel2Script:
`story_semantic_parser`. The agent may propose semantic candidates that enrich a
deterministic `story_map`, but it must not directly modify the deterministic
parser output.

The first implementation must route through the Stage 9 LLM Provider abstraction
and default to `mock_dry_run`. Real network access is out of scope for the
contract phase.

## Non-Goals

- Do not implement a full AI novel-to-screenplay pipeline.
- Do not modify `story_map.yaml` in place.
- Do not generate outline, character bible, screenplay, Fountain, or review
  artifacts.
- Do not integrate multiple real model providers.
- Do not commit API keys or local private provider configuration.
- Do not let an agent bypass `LLMRouter`.

## Inputs

The agent consumes an existing deterministic story map:

```yaml
source_story_map: "examples/output/generated_story_map.yaml"
```

The implementation should read only the fields needed to form bounded semantic
requests:

- `story_map.chapters[].id`
- `story_map.chapters[].paragraphs[].id`
- short paragraph previews or approved prompt excerpts
- existing deterministic candidates and uncertainties

Prompts and logs must not copy the full novel text into persistent artifacts.

## Output Artifact

The machine-readable output is:

```text
examples/output/generated_semantic_candidates.yaml
```

It must validate against:

```text
schemas/semantic_candidates.schema.json
```

Root shape:

```yaml
semantic_candidates:
  schema_version: "0.1.0"
  source_story_map: "examples/output/generated_story_map.yaml"
  agent_id: "story_semantic_parser"
  provider_profile: "mock_dry_run"
  dry_run: true
  candidates: []
  errors: []
  human_approval_required: true
  run_log: "examples/output/generated_semantic_agent_run_log.yaml"
```

The run log output is:

```text
examples/output/generated_semantic_agent_run_log.yaml
```

It should contain the Stage 9 redacted run record only: agent ID, intended
profile, resolved profile, status, usage, latency, run ID, trace ID, and prompt
hash. It must not contain the full prompt or full source novel text.

## Candidate Contract

Every candidate must be advisory and source-traceable:

```yaml
id: "semcand_001"
type: "character_candidate"
confidence: "medium"
evidence:
  summary: "The paragraph suggests an additional named character."
  quote_preview: "short excerpt only"
  reasoning_note: "why the model proposed this candidate"
source_trace_ids:
  chapter_id: "ch_001"
  paragraph_ids: ["p_001"]
proposed_fields:
  name: "Candidate name"
merge_policy: "human_approval_required"
target_story_map_field: "characters_detected"
```

Allowed `type` values:

- `character_candidate`
- `location_candidate`
- `prop_candidate`
- `event_candidate`
- `psychological_passage_candidate`
- `timeline_candidate`

Allowed target fields:

- `characters_detected`
- `locations_detected`
- `props_detected`
- `key_events`
- `timeline`
- `psychological_passages`

`proposed_fields` is intentionally flexible by candidate type, but it must stay
inside the meaning of the target story map field. It must not introduce
screenplay scenes, beats, dialogue, production notes, or unsupported character
biography.

## Merge Policy

All candidates use:

```yaml
merge_policy: "human_approval_required"
human_approval_required: true
```

Stage 10 does not define automatic merge behavior. A later approval flow may
accept or reject candidates, but it must preserve deterministic story map data
and record the approval decision. Until then, generated semantic candidates are
sidecar artifacts only.

## Provider Routing

`src/novel2script/llm/router.py` already maps:

```python
"story_semantic_parser": "qwen_long"
```

The Stage 9 router currently resolves all calls to `mock_dry_run`. Stage 10
must keep that default:

- intended profile: `qwen_long`
- resolved profile: `mock_dry_run`
- `dry_run: true`

A future real `qwen_long` provider may run only when all of the following are
true:

- The user explicitly passes an `--allow-network` style flag.
- The required API key exists in an environment variable.
- Tests still default to mock and do not require network access.
- The implementation has checked the latest official provider API
  documentation and recorded links plus assumptions in
  `docs/architecture/llm-provider.md` or this phase document.

API keys must never be committed to the repository. Provider logs must preserve
only metadata, usage, latency, run ID, trace ID, and prompt hash.

## Error Contract

If the agent cannot form candidates or receives malformed model output, it must
write structured errors instead of guessing:

```yaml
errors:
  - code: "invalid_model_output"
    message: "The provider response did not parse as semantic candidates."
    retryable: true
```

Errors may include `source_trace_ids` if the failure is tied to a chapter or
paragraph. The artifact remains valid even when `candidates` is empty.

## Safety Boundary

The semantic agent may propose:

- missed characters, locations, props, events, timeline hints, and interiority
  passages;
- confidence and evidence notes;
- short quote previews.

The semantic agent must not:

- update deterministic `story_map` arrays directly;
- alter `source_trace`;
- infer hidden facts as accepted truth;
- create screenplay structures;
- call providers directly;
- save full novel text in run logs;
- run real network calls by default.

## Planned Implementation Files

These files are planned for later Stage 10 implementation work and must not be
created during Stage 10A:

- `src/novel2script/agents/__init__.py`
- `src/novel2script/agents/story_semantic_parser.py`
- `tests/test_story_semantic_agent.py`
- `tests/test_story_semantic_agent_cli.py`
- `examples/output/generated_semantic_candidates.yaml`
- `examples/output/generated_semantic_agent_run_log.yaml`

## Test Plan

Future Stage 10B tests should verify:

- the agent uses `LLMRouter` and does not instantiate providers directly;
- default execution resolves to `mock_dry_run`;
- generated candidates validate against
  `schemas/semantic_candidates.schema.json`;
- every candidate has `source_trace_ids` and
  `merge_policy: human_approval_required`;
- the run log omits full prompt and full source text;
- missing or malformed provider output creates structured `errors`;
- no tests require real API keys or HTTP calls.

## Stage 10A Gate

Stage 10A is complete when:

- `schemas/semantic_candidates.schema.json` defines the candidate artifact;
- this phase document defines routing, safety, output, and test boundaries;
- blackboard points to Stage 10B implementation readiness;
- no parser, generator, provider, or CLI code has been added.
