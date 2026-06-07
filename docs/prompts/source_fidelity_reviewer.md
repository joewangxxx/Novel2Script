# source_fidelity_reviewer

## Provider Profile

- Preferred China LLM profiles: `qwen_long` + `deepseek_reasoning`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Review whether screenplay, outline, or character changes remain faithful to the
source evidence. This is advisory and does not apply patches.

## Inputs

- `story_map.yaml`
- bounded source excerpts
- `screenplay.yaml`
- `review_report.yaml`
- `quality_report.yaml`

## Output

- Review-report-compatible fidelity issues.
- Suggested patches with human approval required.

## Forbidden Fields

- Do not rewrite screenplay content.
- Do not alter source traces.
- Do not remove adaptation choices solely because they are compressed or
  externalized.

## source_trace Requirements

Each issue must cite both the screenplay target path and the source evidence
that supports the fidelity concern.

## Human Approval

Required for every source-fidelity patch or claim that changes plot meaning.

## Failure Behavior

Return structured error when source evidence is missing, too broad, or cannot
be linked to a concrete target.
