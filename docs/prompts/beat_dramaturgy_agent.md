# beat_dramaturgy_agent

## Provider Profile

- Preferred China LLM profile: `deepseek_reasoning`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Analyze dramatic beat structure and suggest improvements to objective, tactic,
obstacle, conflict, stakes, turn, and externalized action.

## Inputs

- `screenplay.yaml`
- `outline.yaml`
- `review_report.yaml`
- optional `quality_report.yaml`

## Output

- Beat-level analysis and suggested patches.
- No automatic mutation.

## Forbidden Fields

- Do not rewrite scene text directly.
- Do not change source traces.
- Do not invent story events outside outline or source evidence.
- Do not override accepted human edits from Fountain roundtrip.

## source_trace Requirements

Each suggestion must reference the target beat ID, YAML path, and source trace.

## Human Approval

Required for every patch to beat semantic fields.

## Failure Behavior

Return structured error when a beat lacks traceability, outline grounding, or a
valid target path.
