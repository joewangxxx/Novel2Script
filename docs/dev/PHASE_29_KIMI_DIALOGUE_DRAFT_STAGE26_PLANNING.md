# Phase 29: Kimi Dialogue Draft Planning For Stage 26 Package

## Goal

Stage 29 prepares the Stage 26 package for a future one-shot real Kimi dialogue
draft run. It confirms that the approved Stage 26 screenplay, Stage 28 author
review report, Stage 26 review report, and Stage 26 quality report can drive the
existing `kimi_dialogue_scene_drafter` contract without mutating source
artifacts.

Stage 29 is a planning and dry-run gate. It does not call Kimi, does not call
any real LLM, does not read or retain API credentials, does not save prompts,
does not save model responses, and does not apply candidates.

## Source Package

- Screenplay: `examples/output/test1_sanguo_screenplay.stage26.yaml`
- Author review report:
  `examples/output/test1_sanguo_author_review_report.stage26.yaml`
- Review report: `examples/output/test1_sanguo_review_report.stage26.yaml`
- Quality report: `examples/output/test1_sanguo_quality_report.stage26.yaml`
- Quality dashboard:
  `examples/output/test1_sanguo_quality_dashboard.stage26.md`

## Authorization Boundary

Stage 28 approved the Stage 26 package and set:

- `author_review_report.status: approved`
- `author_review_report.next_stage_authorization: kimi_dialogue_draft`
- `author_review_report.metadata.ready_for_next_stage: true`

This authorizes planning for a future Kimi dialogue draft stage. It does not
authorize a network call in Stage 29.

## Dry-Run Outputs

Stage 29 generated:

- Mock candidates:
  `examples/output/test1_sanguo_creative_draft_candidates.stage26.mock.yaml`
- Mock run log:
  `examples/output/test1_sanguo_creative_draft_run_log.stage26.mock.yaml`

The dry-run candidate sidecar validates against
`schemas/creative_draft_candidates.schema.json`, contains three candidates, and
all candidate targets resolve against the Stage 26 screenplay.

## Future Stage 30 Real Run Rules

A future Stage 30 real Kimi run must follow these rules:

- Human must explicitly authorize the one-shot network call.
- Use `provider_profile: kimi_creative`.
- Use model `kimi-k2.6`.
- Use `max_attempts=1`.
- Do not retry automatically.
- Do not call Qwen or DeepSeek.
- Do not fall back to mock and claim real success.
- Do not modify `examples/output/test1_sanguo_screenplay.stage26.yaml`.
- Write only a new real candidate sidecar and redacted run log.
- Do not save prompt text.
- Do not save raw model text.
- Do not save provider request or response payload.
- Do not save API key, bearer token value, or HTTP auth secret.
- Stop if provider/runtime fails.
- Stop if `finish_reason=length`.
- Stop if schema validation fails.
- Stop if candidate count is zero.
- Stop if target integrity fails.
- Stop if safety scan fails.

Recommended Stage 30 command:

```powershell
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter --screenplay examples/output/test1_sanguo_screenplay.stage26.yaml --author-review-report examples/output/test1_sanguo_author_review_report.stage26.yaml --review-report examples/output/test1_sanguo_review_report.stage26.yaml --quality-report examples/output/test1_sanguo_quality_report.stage26.yaml --out examples/output/test1_sanguo_creative_draft_candidates.stage26.real_kimi.yaml --run-log examples/output/test1_sanguo_creative_draft_run_log.stage26.real_kimi.yaml --allow-network
```

## Stage 29 Pass Criteria

- Stage 28 author review report is schema-valid.
- Stage 28 author review authorizes `kimi_dialogue_draft`.
- Stage 26 dry-run candidate sidecar is schema-valid.
- Dry-run candidate targets resolve against the Stage 26 screenplay.
- Dry-run run log has `stored_prompt=false`.
- Dry-run run log has `model_response_retained=false`.
- Dry-run run log has `provider_payload_retained=false`.
- Stage 29 safety scan passes.
- Focused creative draft tests pass.
- Full pytest passes.

## Non-Goals

- No real Kimi call.
- No real LLM call.
- No credential inspection.
- No source screenplay mutation.
- No real candidate retention.
- No apply step.
- No Fountain or enhanced QA rerun.
