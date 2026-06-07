# Quality Dashboard

## Summary

- Readiness: pass
- Score: 97
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
| shootability | pass | 100 | shootability reported no issues. |
| fountain_roundtrip_safety | warn | 100 | No Fountain roundtrip report was provided. |
| semantic_staleness | pass | 100 | Semantic fields are not marked stale. |
| dialogue_naturalness | pass | 92 | 对白口语化及历史符合度良好，部分行文可精简。 |
| character_goal_clarity | warn | 88 | 绝大部分场景目标清晰，动作外化程度高。 |
| dramatic_conflict_intensity | warn | 85 | 戏剧冲突设计有效，动作与对白具有良好张力。 |
| overall_readiness | pass | 97 | Overall decision: ready_for_author_review. |

## Blocking Items

- None

## Recommended Next Actions

- Run import-fountain before relying on roundtrip safety.
- Review LLM reasoning for character_goal_clarity: 各 Scene 与 Beat 中人物目的性明确，外化动作充分，角色内驱力合理。
- Review LLM reasoning for dramatic_conflict_intensity: 招兵与结义等核心场景中冲突设计有效，可以通过更精细的戏剧化设计进一步放大阻碍。

## Source Artifacts

- screenplay: `tmp_codex_audit\pipeline\screenplay.yaml`
- validation_report: `tmp_codex_audit\pipeline\validation_report.yaml`
- review_report: `tmp_codex_audit\pipeline\review_report.yaml`
- quality_report_yaml: `tmp_codex_audit\pipeline\quality_report.yaml`
- quality_dashboard_markdown: `tmp_codex_audit\pipeline\quality_dashboard.md`

## Limitations

- Deterministic aggregation only; no model call or external review is used.
- Suggested patches are not applied automatically.
- Markdown is a companion view; YAML remains the source of truth.
