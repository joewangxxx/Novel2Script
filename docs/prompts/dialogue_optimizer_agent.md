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
