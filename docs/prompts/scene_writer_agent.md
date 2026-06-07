# scene_writer_agent

## Provider Profile

- Preferred China LLM profile: `kimi_creative`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Draft scene-level text suggestions from approved outline and character bible
artifacts. It complements deterministic Stage 5 output but does not silently
replace it.

## Inputs

- `story_map.yaml`
- `outline.yaml`
- `character_bible.yaml`
- `screenplay.yaml`
- optional `quality_report.yaml`

## Output

- Screenplay-compatible scene or element suggestions.
- Suggested patches requiring human approval.

## Forbidden Fields

- Do not change `source_trace`.
- Do not update beat objective, conflict, stakes, turn, or externalized action
  without explicit approval.
- Do not introduce unregistered characters.
- Do not change locked character facts.

## source_trace Requirements

Each proposed scene or element must preserve or cite the relevant source trace
and upstream outline scene ID.

## Human Approval

Required for all generated scene text before it is written to screenplay YAML.

## Failure Behavior

Return structured error when the requested scene lacks outline evidence, source
trace, or character grounding.

## Implemented JSON Contract

Return only a JSON object with `{"candidates": [...]}` to the provider caller.
The runtime wraps accepted model candidates into `scene_writer_agent_candidates`
sidecar YAML. Each model candidate must include:

- `type`
- `target`
- `proposed_text`
- `rationale`
- `source_trace`
- `source_trace_ids`
- `ai_tags`
- `constraints_observed`
- `risks`
- `confidence`

Allowed `type` values:

- `scene_action`
- `visual_beat`
- `element_insert`
- `element_rewrite`
- `transition`
- `reviewer_note`

Every accepted sidecar candidate is normalized with
`merge_policy: human_approval_required` and
`requires_author_approval: true`.

## Retention Policy

The run log may retain only metadata such as provider profile, model,
finish_reason, usage, and prompt hash. It must not retain prompt text, raw model
response, provider request/response body, API key, bearer token, Authorization
header value, `.env` content, or full source text.
