# Phase 16: Author Review UX And CLI Contract

## Goal

Stage 16 defines a human author review layer for the Stage 15 real-enhanced
screenplay draft. The author reviews structure, character handling, beats,
dialogue readiness, quality findings, and next-stage authorization before any
creative LLM drafting begins.

Stage 16A is contract-only. It does not call an LLM, change the screenplay,
apply review suggestions, enter Kimi creative drafting, modify Stage 15
artifacts, or commit files.

## Background

Stage 15 generated a traceable end-to-end sample package from the Stage 14
merged story map. The quality report says:

- `overall_readiness.status: pass`;
- `overall_readiness.decision: ready_for_author_review`;
- no hard gate failures;
- the main warning is `dialogue_naturalness`, because the deterministic draft
  has too little dialogue for a meaningful dialogue review.

Stage 16 therefore asks the author to confirm whether the structured draft is
good enough to move into a creative enhancement stage, especially dialogue and
scene polish.

## Inputs

Required Stage 15 inputs:

- `examples/output/test1_sanguo_screenplay.yaml`
- `examples/output/test1_sanguo_review_report.yaml`
- `examples/output/test1_sanguo_quality_report.yaml`
- `examples/output/test1_sanguo_quality_dashboard.md`

Optional context inputs:

- `examples/output/test1_sanguo_screenplay.fountain`
- `examples/output/test1_sanguo_screenplay_validation_report.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip_report.yaml`
- `examples/output/test1_sanguo_outline.yaml`
- `examples/output/test1_sanguo_character_bible.yaml`

Stage 16 tools must treat these artifacts as read-only. Author decisions are
recorded in new files.

## Outputs

Stage 16B may generate:

- `examples/output/test1_sanguo_author_review_packet.md`
- `examples/output/test1_sanguo_author_review_decisions.yaml`
- `examples/output/test1_sanguo_author_review_report.yaml`

`test1_sanguo_author_review_packet.md` is a readable packet for the author. It
should summarize evidence and decisions to make, but it is not the source of
truth. It must not copy the full novel, prompt, model response, provider body,
or unbounded source excerpts.

`test1_sanguo_author_review_decisions.yaml` and
`test1_sanguo_author_review_report.yaml` validate against
`schemas/author_review.schema.json`.

## Author Review Schema

The schema file is `schemas/author_review.schema.json`, contract version
`0.1.0`.

The schema accepts two root objects:

- `author_review_decisions`
- `author_review_report`

The decisions file records the author's explicit choices. The report is a
derived summary that later stages may use as a gate.

## Decision Areas

The decisions file must contain exactly these decision areas:

- `structure_decision`
- `character_decision`
- `beat_decision`
- `dialogue_decision`
- `quality_decision`
- `next_stage_authorization`

Standard decision areas use:

```yaml
decision: approve | request_changes | block
```

`dialogue_decision` uses:

```yaml
decision: approve | request_dialogue_draft | block
```

`next_stage_authorization` uses:

```yaml
decision: none | kimi_dialogue_draft | dramaturgy_review
```

`request_dialogue_draft` means the author accepts that current dialogue is not
final and explicitly asks for a later dialogue drafting stage. It does not call
Kimi by itself.

`kimi_dialogue_draft` authorizes a future stage to prepare a Kimi creative
dialogue or scene drafting plan. It is not model execution approval unless the
future stage explicitly asks for network/model authorization.

`dramaturgy_review` authorizes a future DeepSeek dramaturgy review plan for
beats, objective, conflict, stakes, and turns. It is not model execution
approval by itself.

## Decision Record Fields

Every decision entry must support:

```yaml
reviewer: "author_or_editor_id"
reviewed_at: "2026-06-06T18:30:00+08:00"
decision: "approve"
notes:
  - "Short human note."
linked_artifacts:
  - "examples/output/test1_sanguo_screenplay.yaml"
linked_issue_ids: []
human_approval_required: true
```

Rules:

- `reviewer` identifies the human reviewer.
- `reviewed_at` records when the decision was made.
- `decision` must match the enum for the decision area.
- `notes` explain the decision in human-readable form.
- `linked_artifacts` points to the screenplay, review report, quality report,
  dashboard, or other Stage 15 artifact that supports the decision.
- `linked_issue_ids` references `review_report.issues[].id` when relevant.
- `human_approval_required` is always `true` because Stage 16 is a human gate.

## Decisions File Shape

```yaml
author_review_decisions:
  schema_version: "0.1.0"
  source_artifacts:
    screenplay: "examples/output/test1_sanguo_screenplay.yaml"
    review_report: "examples/output/test1_sanguo_review_report.yaml"
    quality_report: "examples/output/test1_sanguo_quality_report.yaml"
    quality_dashboard: "examples/output/test1_sanguo_quality_dashboard.md"
    fountain: "examples/output/test1_sanguo_screenplay.fountain"
    validation_report: "examples/output/test1_sanguo_screenplay_validation_report.yaml"
    roundtrip_report: "examples/output/test1_sanguo_screenplay_roundtrip_report.yaml"
  reviewed_by: "author"
  reviewed_at: "2026-06-06T18:30:00+08:00"
  structure_decision: {}
  character_decision: {}
  beat_decision: {}
  dialogue_decision: {}
  quality_decision: {}
  next_stage_authorization: {}
  overall_notes: []
```

## Report File Shape

```yaml
author_review_report:
  schema_version: "0.1.0"
  source_decisions: "examples/output/test1_sanguo_author_review_decisions.yaml"
  source_artifacts:
    screenplay: "examples/output/test1_sanguo_screenplay.yaml"
    review_report: "examples/output/test1_sanguo_review_report.yaml"
    quality_report: "examples/output/test1_sanguo_quality_report.yaml"
    quality_dashboard: "examples/output/test1_sanguo_quality_dashboard.md"
  generated_at: "2026-06-06T18:31:00+08:00"
  status: "approved"
  summary: "Author approved structure and requested dialogue drafting."
  decision_outcomes:
    structure_decision: "approve"
    character_decision: "approve"
    beat_decision: "approve"
    dialogue_decision: "request_dialogue_draft"
    quality_decision: "approve"
  next_stage_authorization: "kimi_dialogue_draft"
  blocking_reasons: []
  requested_changes: []
```

Report status rules:

- `approved`: no decision is `block`; at least structure, character, beat, and
  quality are approved.
- `changes_requested`: one or more standard decisions request changes, but no
  decision blocks.
- `blocked`: any decision is `block`, or the report cannot interpret the
  decisions file.

## Author Review Packet

The packet Markdown should include:

- title and source artifact list;
- screenplay summary;
- quality readiness summary;
- review report issue summary;
- dimension status table from the quality report;
- decision checklist for structure, character, beat, dialogue, quality, and
  next stage;
- explicit note that no LLM is called by author review;
- explicit note that approving Kimi or dramaturgy work only authorizes a future
  stage plan, not automatic model execution.

The packet must stay concise. It may quote short titles, scene headings, issue
IDs, status values, and next actions, but it must not include full screenplay,
full novel text, prompt text, or raw model output.

## CLI Boundary For Later Stage 16B

Suggested future commands:

```bash
python -m novel2script.cli prepare-author-review \
  --screenplay examples/output/test1_sanguo_screenplay.yaml \
  --review-report examples/output/test1_sanguo_review_report.yaml \
  --quality-report examples/output/test1_sanguo_quality_report.yaml \
  --quality-dashboard examples/output/test1_sanguo_quality_dashboard.md \
  --out examples/output/test1_sanguo_author_review_packet.md
```

```bash
python -m novel2script.cli summarize-author-review \
  --decisions examples/output/test1_sanguo_author_review_decisions.yaml \
  --out examples/output/test1_sanguo_author_review_report.yaml
```

Stage 16A does not require these commands to exist. Stage 16B may implement
them using deterministic local code only.

## Gating Rules

Stage 16 should stop when:

- the screenplay, review report, quality report, or dashboard is missing;
- `quality_report.overall_readiness.decision` is not
  `ready_for_author_review` or `ready_with_warnings`;
- the author decisions file fails `schemas/author_review.schema.json`;
- any decision is `block`;
- next-stage authorization is `none`;
- a generated packet or report leaks prompt text, raw model output, provider
  body, API key, `.env` content, or unbounded source text.

Stage 16 may proceed to a future planning stage when:

- structure, character, beat, and quality decisions are `approve`;
- dialogue is `approve` or `request_dialogue_draft`;
- next-stage authorization is `kimi_dialogue_draft` or `dramaturgy_review`;
- the author review report is schema-valid and not blocked.

## Non-Goals

- No LLM calls.
- No screenplay mutation.
- No automatic review patch application.
- No automatic Kimi creative drafting.
- No automatic DeepSeek dramaturgy review.
- No Stage 15 artifact modification.
- No prompt changes.
- No commit during Stage 16A.

## Stage Plan

Stage 16A:

- define this contract;
- add `schemas/author_review.schema.json`;
- update `docs/blackboard/state.yaml`;
- do not generate packet, decisions, or report artifacts.

Stage 16B:

- implement deterministic packet/report CLI if requested;
- generate packet and sample author decisions/report artifacts;
- validate schema and update QA/blackboard.

Stage 16C:

- run closeout QA;
- decide whether next stage should be Kimi dialogue drafting or DeepSeek
  dramaturgy review based on author decisions.

## Governance

Current relevant contracts are draft according to
`docs/blackboard/state.yaml`. If contracts become frozen before Stage 16B, any
schema or CLI contract changes must go through
`docs/architecture/change-requests/`.
