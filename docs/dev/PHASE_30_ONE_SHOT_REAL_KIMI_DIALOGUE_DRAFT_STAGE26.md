# Phase 30: One-Shot Real Kimi Dialogue Draft For Stage 26 Package

## Goal

Stage 30 executes one explicitly authorized real Kimi dialogue draft call for
the Stage 26 package and retains only a schema-valid candidate sidecar plus a
redacted run log.

## Boundaries

- One real Kimi call maximum.
- `max_attempts=1`.
- No automatic retry.
- No provider fallback to mock as real success.
- No Qwen or DeepSeek call.
- No source screenplay mutation.
- No apply step.
- No prompt text retention.
- No raw model text retention.
- No provider request or response payload retention.
- No credential or HTTP auth secret retention.

## Source Package

- Screenplay: `examples/output/test1_sanguo_screenplay.stage26.yaml`
- Author review report:
  `examples/output/test1_sanguo_author_review_report.stage26.yaml`
- Review report: `examples/output/test1_sanguo_review_report.stage26.yaml`
- Quality report: `examples/output/test1_sanguo_quality_report.stage26.yaml`

## Command

```powershell
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.stage26.yaml --author-review-report examples/output/test1_sanguo_author_review_report.stage26.yaml --review-report examples/output/test1_sanguo_review_report.stage26.yaml --quality-report examples/output/test1_sanguo_quality_report.stage26.yaml --out examples/output/test1_sanguo_creative_draft_candidates.stage26.real_kimi.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.stage26.real_kimi.yaml --allow-network
```

## Result

- Real call executed: true.
- Provider profile: `kimi_creative`.
- Model: `kimi-k2.6`.
- Finish reason: `stop`.
- Candidate count: 1.
- Candidate schema errors: 0.
- Unresolved targets: 0.
- Run log status: `completed`.
- Retained prompt: false.
- Retained model response: false.
- Retained provider payload: false.

## Generated Artifacts

- Real candidates:
  `examples/output/test1_sanguo_creative_draft_candidates.stage26.real_kimi.yaml`
- Redacted run log:
  `examples/output/test1_sanguo_creative_draft_run_log.stage26.real_kimi.yaml`
- Stage 30 report:
  `examples/output/test1_sanguo_stage30_real_kimi_dialogue_draft_report.yaml`

## Next Stage

Stage 31 may prepare human review for the retained Stage 30 real Kimi candidate.
The candidate must not be applied automatically. Any application requires a
separate author decision stage and a new output artifact.
