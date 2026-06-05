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
