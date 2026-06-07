# Quality Dashboard

## Summary

- Readiness: pass
- Score: 98
- Decision: ready_for_author_review

## Gate Decision

No hard gate failures.

## Dimension Scores

| Dimension | Status | Score | Summary |
| --- | --- | ---: | --- |
| schema_validity | pass | 100 | Screenplay schema validation passed. |
| source_trace_coverage | pass | 100 | Source trace coverage is complete. |
| beat_completeness | pass | 100 | Beat fields are complete. |
| reference_integrity | pass | 100 | All references resolve. |
| character_consistency | pass | 100 | character_consistency reported no issues. |
| pacing | pass | 100 | pacing reported no issues. |
| dialogue_naturalness | warn | 80 | dialogue_naturalness reported 1 issue(s). |
| shootability | pass | 100 | shootability reported no issues. |
| fountain_roundtrip_safety | pass | 100 | Fountain roundtrip is safe. |
| semantic_staleness | pass | 100 | Semantic fields are not marked stale. |
| overall_readiness | pass | 98 | Overall decision: ready_for_author_review. |

## Blocking Items

- None

## Recommended Next Actions

- Review issue_001 from dialogue_naturalness.

## Source Artifacts

- screenplay: `examples/output/test1_sanguo_screenplay.stage26_roundtrip.yaml`
- validation_report: `examples/output/test1_sanguo_screenplay.stage26_roundtrip_validation_report.yaml`
- review_report: `examples/output/test1_sanguo_review_report.stage26.yaml`
- fountain_roundtrip_report: `examples/output/test1_sanguo_screenplay.stage26_roundtrip_report.yaml`
- quality_report_yaml: `examples/output/test1_sanguo_quality_report.stage26.yaml`
- quality_dashboard_markdown: `examples/output/test1_sanguo_quality_dashboard.stage26.md`

## Limitations

- Deterministic aggregation only; no model call or external review is used.
- Suggested patches are not applied automatically.
- Markdown is a companion view; YAML remains the source of truth.
