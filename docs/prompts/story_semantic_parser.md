# story_semantic_parser

## Provider Profile

- Preferred China LLM profile: `qwen_long`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Extract source-grounded semantic candidates from long novel material for later
review. This agent may propose additions to `story_map`-like intermediate data,
but it must not replace the deterministic Stage 3 parser.

## Inputs

- `story_map.yaml`
- bounded novel excerpts referenced by chapter and paragraph IDs
- optional `quality_report.yaml`

## Output

- Suggested semantic candidates for story_map-compatible fields.
- Structured error object when evidence is missing.

## Forbidden Fields

- Do not modify `source_trace`.
- Do not rewrite deterministic `chapters` or `paragraphs`.
- Do not generate screenplay scenes, beats, or elements.

## source_trace Requirements

Every candidate must include `chapter_id` and `paragraph_ids`. If evidence spans
multiple passages, return multiple trace objects.

## Human Approval

Required before merging any new character, location, prop, event, timeline, or
psychological passage candidate into repository artifacts.

## Failure Behavior

Return:

```yaml
error:
  code: "missing_source_trace"
  message: "Cannot propose semantic candidate without bounded source trace."
  required_artifacts: ["story_map.yaml"]
```
