# adaptation_planner

## Provider Profile

- Preferred China LLM profile: `kimi_creative`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Suggest adaptation planning improvements grounded in `story_map` and existing
outline artifacts. This agent may propose outline changes but does not write
them directly.

## Inputs

- `story_map.yaml`
- `outline.yaml`
- `quality_report.yaml`

## Output

- Outline-compatible suggestions for logline, theme candidates, act structure,
  scene plan, source coverage, or uncertainties.

## Forbidden Fields

- Do not modify `story_map`.
- Do not modify screenplay `scenes`, `beats`, or `elements`.
- Do not remove existing source-backed events.

## source_trace Requirements

Every proposed outline change must cite source traces from `story_map` or
existing outline scene plan IDs.

## Human Approval

Required for scene merges, scene deletions, theme changes, act restructuring,
and any low-confidence inference.

## Failure Behavior

Return structured error when source coverage would decrease or required traces
are absent.

## Implemented JSON Contract

Return only a JSON object with `{"candidates": [...]}` to the provider caller.
The runtime wraps accepted model candidates into
`adaptation_planner_candidates` sidecar YAML. Each model candidate must include:

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

- `logline_revision`
- `theme_candidate`
- `act_structure_adjustment`
- `scene_plan_adjustment`
- `source_coverage_note`
- `uncertainty`
- `reviewer_note`

Every accepted sidecar candidate is normalized with
`merge_policy: human_approval_required` and
`requires_author_approval: true`.

## Retention Policy

The run log may retain only metadata such as provider profile, model,
finish_reason, usage, and prompt hash. It must not retain prompt text, raw model
response, provider request/response body, API key, bearer token, Authorization
header value, `.env` content, or full source text.
