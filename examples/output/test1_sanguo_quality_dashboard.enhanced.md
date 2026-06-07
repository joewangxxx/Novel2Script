# Quality Dashboard

## Summary

- Readiness: pass
- Score: 100
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
| dialogue_naturalness | warn | 100 | dialogue_naturalness reviewer was skipped. |
| shootability | pass | 100 | shootability reported no issues. |
| fountain_roundtrip_safety | pass | 100 | Fountain roundtrip is safe. |
| semantic_staleness | pass | 100 | Semantic fields are not marked stale. |
| overall_readiness | pass | 100 | Overall decision: ready_for_author_review. |

## Blocking Items

- None

## Recommended Next Actions

- Add dialogue review after dialogue exists in the draft.

## Source Artifacts

- screenplay: `examples/output/test1_sanguo_screenplay.enhanced_roundtrip.yaml`
- validation_report: `examples/output/test1_sanguo_screenplay.enhanced_roundtrip_validation_report.yaml`
- review_report: `examples/output/test1_sanguo_review_report.enhanced.yaml`
- fountain_roundtrip_report: `examples/output/test1_sanguo_screenplay.enhanced_roundtrip_report.yaml`
- quality_report_yaml: `examples/output/test1_sanguo_quality_report.enhanced.yaml`
- quality_dashboard_markdown: `examples/output/test1_sanguo_quality_dashboard.enhanced.md`

## Limitations

- Deterministic aggregation only; no model call or external review is used.
- Suggested patches are not applied automatically.
- Markdown is a companion view; YAML remains the source of truth.
