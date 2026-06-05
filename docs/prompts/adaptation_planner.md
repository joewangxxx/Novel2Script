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
