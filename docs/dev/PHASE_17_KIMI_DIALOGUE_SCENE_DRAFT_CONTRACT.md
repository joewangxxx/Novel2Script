# Phase 17: Kimi Dialogue Scene Draft Contract

## Goal

Stage 17 defines the contract for future Kimi dialogue and scene-action creative
drafting. It converts the Stage 16 author authorization into a bounded sidecar
artifact called `creative_draft_candidates`. Every candidate remains subject to
human approval before any later screenplay update.

Stage 17 is contract-only. It does not call Kimi, does not call any real LLM,
does not modify screenplay, must not modify source_trace, does not edit Stage
15 or Stage 16 artifacts, and does not apply creative results.

## Background

Stage 16 produced:

- `examples/output/test1_sanguo_author_review_decisions.yaml`
- `examples/output/test1_sanguo_author_review_report.yaml`

The author approved structure, characters, beats, and the quality gate. The
author requested dialogue drafting and authorized
`next_stage_authorization: kimi_dialogue_draft`.

The Stage 15 quality report is already `ready_for_author_review`. Its main warn
is that `dialogue_naturalness` cannot be meaningfully reviewed until dialogue
exists. Stage 17 therefore defines a Kimi creative candidate layer for dialogue
and scene-action enhancement only.

## Agent Definition

- `agent_id`: `kimi_dialogue_scene_drafter`
- `provider_profile`: `kimi_creative`
- `fallback_profile`: `mock_dry_run`
- `prompt_file`: `docs/prompts/kimi_dialogue_scene_drafter.md`
- `output_policy`: `human_approval_required`

The agent may later propose candidate text. It must never write directly into
`screenplay.yaml`.

## Inputs

Required inputs for a future implementation:

- `screenplay.yaml`
- `author_review_report.yaml`
- `author_review_decisions.yaml`
- `quality_report.yaml`
- `review_report.yaml`

Optional inputs:

- `story_map.merged.yaml`
- `character_bible.yaml`

## Input Priority

1. `author_review_report`: decides whether Kimi drafting is allowed.
2. `screenplay`: provides target scene, beat, and element IDs.
3. `quality_report`: locates warn/fail dimensions.
4. `review_report`: locates dialogue or scene-action issues.
5. `character_bible`: constrains role voice and consistency.
6. `story_map.merged`: source-grounded reference only; it must not be rewritten.

If `author_review_report.next_stage_authorization` is not
`kimi_dialogue_draft`, the agent must fail closed and write no creative
candidates.

## Output Artifact

Schema file:

- `schemas/creative_draft_candidates.schema.json`

Root shape:

```yaml
creative_draft_candidates:
  schema_version: "0.1.0"
  source_screenplay: "examples/output/test1_sanguo_screenplay.yaml"
  source_author_review_report: "examples/output/test1_sanguo_author_review_report.yaml"
  agent_id: "kimi_dialogue_scene_drafter"
  provider_profile: "kimi_creative"
  dry_run: false
  human_approval_required: true
  authorization:
    source: "author_review_report"
    next_stage_authorization: "kimi_dialogue_draft"
    scope:
      - "dialogue"
      - "scene_action"
  candidates: []
  errors: []
  metadata:
    prompt_retained: false
    model_response_retained: false
    provider_body_retained: false
    full_source_text_retained: false
```

## Candidate Types

Supported candidate types:

- `dialogue_insert`
- `dialogue_rewrite`
- `scene_action_enhancement`
- `beat_externalization`
- `pacing_trim_suggestion`
- `reviewer_note`

Every candidate must contain:

- `id`
- `type`
- `target.scene_id`
- optional `target.beat_id`
- optional `target.element_id`
- optional `target.character_id`
- `proposed_text`
- `rationale`
- `source_trace`
- `source_trace_ids`
- `constraints_observed`
- `risks`
- `confidence`
- `merge_policy: human_approval_required`
- `requires_author_approval: true`

## Candidate Boundaries

- `dialogue_insert` can only add proposed dialogue for an existing scene or
  beat.
- `dialogue_rewrite` can only reference an existing `element_id`; it must not
  replace or overwrite the source element.
- `scene_action_enhancement` can make action more shootable, but cannot add a
  new major event unsupported by source evidence.
- `beat_externalization` can turn existing psychology, objective, conflict, or
  stakes into action or dialogue candidates.
- `pacing_trim_suggestion` can recommend trims, but cannot delete content.
- `reviewer_note` is used when evidence is insufficient or the request would
  violate author-approved structure.

## Prohibited Changes

The Kimi drafter must not:

- add main-plot events;
- change character relationships;
- change character goals;
- change event order;
- delete or alter `source_trace`;
- output complete novel passages;
- output prompts, raw responses, API keys, provider body, or `.env` content;
- write merged screenplay YAML;
- trigger Fountain export;
- automatically apply a creative patch;
- override Stage 16 author approvals.

## Human Review Flow

The future flow is:

1. Stage 16 author review report authorizes `kimi_dialogue_draft`.
2. Stage 18 mock-first implementation generates `creative_draft_candidates`.
3. A human reviews each candidate.
4. Only a later human-approved application stage may decide whether and how to
   create an updated screenplay.

Stage 17 does not define automatic merge behavior. It only defines a candidate
sidecar and the safety gates around it.

## Prompt Requirements

`docs/prompts/kimi_dialogue_scene_drafter.md` must state:

- only generate candidates;
- do not modify screenplay;
- process only the scope authorized by `author_review_report`;
- output JSON or YAML parseable structure;
- do not output Markdown;
- do not reveal chain-of-thought;
- every candidate must bind to `scene_id` or `element_id`;
- every candidate must preserve `source_trace`;
- insufficient evidence must become `reviewer_note`, not invention.

## QA Gates

Stage 17 passes only when:

- `schemas/creative_draft_candidates.schema.json` loads successfully;
- a minimal mock fixture validates against the schema;
- `docs/prompts/kimi_dialogue_scene_drafter.md` contains no real API key;
- `config/agent_routing.example.yaml` maps
  `kimi_dialogue_scene_drafter` to `kimi_creative`;
- routing output policy is `human_approval_required`;
- `docs/prompts/agent-routing.md` documents the new agent;
- this document states that Stage 17 must not modify screenplay;
- `docs/blackboard/state.yaml` is updated;
- `docs/qa/report.md` records Stage 17 contract QA;
- full regression tests pass.

Security scan scope must include all new or modified Stage 17 files and check
for:

- API key patterns;
- Bearer tokens;
- Authorization header values;
- retained raw model response markers;
- provider body retention;
- `.env` content;
- full novel text.

## Non-Goals

- No real Kimi call.
- No real LLM call.
- No screenplay mutation.
- No source trace mutation.
- No Stage 15 or Stage 16 artifact changes.
- No final dialogue generation.
- No automatic patch application.
- No Fountain export.
- No schema changes outside the new creative draft sidecar.

## Stage 18 Readiness

If Stage 17 passes, Stage 18 may implement a mock-first
`kimi_dialogue_scene_drafter` runner. A real Kimi call is still forbidden until
mock-first behavior, schema validation, redacted run logs, safety scans, and
explicit author/network authorization all pass.

## Contract Governance

The current contract status in `docs/blackboard/state.yaml` is draft. If any
related contract is frozen before Stage 18, implementation work must not
silently edit the schema or routing contract. It must create an architecture
change request under `docs/architecture/change-requests/`.
