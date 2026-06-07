# character_bible_agent

## Provider Profile

- Preferred China LLM profile: `kimi_creative`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Suggest source-grounded character bible improvements. It may propose want,
need, flaw, relationship, voice, and arc updates with confidence tags.

## Inputs

- `story_map.yaml`
- `outline.yaml`
- `character_bible.yaml`
- optional `review_report.yaml`

## Output

- Character-bible-compatible suggestions.
- Advisory patches requiring approval.

## Forbidden Fields

- Do not rename locked characters.
- Do not overwrite `locked: true` fields.
- Do not invent relationships without evidence.
- Do not modify screenplay dialogue directly.

## source_trace Requirements

Every character fact must cite source traces. Inferred want, need, flaw, voice,
or arc fields must include low-confidence metadata when evidence is weak.

## Human Approval

Required for relationship changes, locked character updates, major arc changes,
and all inferred fields.

## Failure Behavior

Return structured error when a character lacks source evidence or conflicts
with a locked profile.

## Implemented JSON Contract

Return only a JSON object with `{"candidates": [...]}` to the provider caller.
The runtime wraps accepted model candidates into
`character_bible_agent_candidates` sidecar YAML. Each model candidate must
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

- `want`
- `need`
- `flaw`
- `relationship`
- `voice`
- `arc`
- `uncertainty`
- `conflict_note`
- `reviewer_note`

Every accepted sidecar candidate is normalized with
`merge_policy: human_approval_required` and
`requires_author_approval: true`.

## Retention Policy

The run log may retain only metadata such as provider profile, model,
finish_reason, usage, and prompt hash. It must not retain prompt text, raw model
response, provider request/response body, API key, bearer token, Authorization
header value, `.env` content, or full source text.
