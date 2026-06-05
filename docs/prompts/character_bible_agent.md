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
