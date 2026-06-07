# dialogue_optimizer_agent

## Provider Profile

- Preferred China LLM profile: `kimi_creative`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Suggest dialogue improvements for existing screenplay dialogue. It does not add
new plot facts or change character identity.

## Inputs

- `screenplay.yaml`
- `character_bible.yaml`
- `review_report.yaml`

## Output

- Dialogue text suggestions or note-only issues.
- Advisory patches requiring human approval.

## Forbidden Fields

- Do not change `dialogue.character_id`.
- Do not modify scene headings, beats, source traces, or character bible facts.
- Do not add new characters.
- Do not solve plot or continuity issues through dialogue without approval.

## source_trace Requirements

Dialogue suggestions must reference the target element YAML path and preserve
the existing element source trace.

## Human Approval

Required before replacing any dialogue text or parenthetical.

## Failure Behavior

Return structured error when dialogue targets are missing, character IDs do not
resolve, or the request asks for semantic plot changes.

## Implemented JSON Contract

Return only a JSON object with `{"candidates": [...]}` to the provider caller.
The runtime wraps accepted model candidates into
`dialogue_optimizer_agent_candidates` sidecar YAML. Each model candidate must
include:

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

- `dialogue_rewrite`
- `dialogue_insert`
- `parenthetical_suggestion`
- `subtext_note`
- `voice_consistency_note`
- `reviewer_note`

Every accepted sidecar candidate is normalized with
`merge_policy: human_approval_required` and
`requires_author_approval: true`.

## Retention Policy

The run log may retain only metadata such as provider profile, model,
finish_reason, usage, and prompt hash. It must not retain prompt text, raw model
response, provider request/response body, API key, bearer token, Authorization
header value, `.env` content, or full source text.
