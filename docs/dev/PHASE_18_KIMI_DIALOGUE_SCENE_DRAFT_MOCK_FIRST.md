# Phase 18: Kimi Dialogue Scene Draft Mock-First Implementation

## Goal

Stage 18A implements a mock-first `kimi_dialogue_scene_drafter` runner and CLI.
It uses Stage 16 author authorization and Stage 15 screenplay evidence to
produce schema-valid `creative_draft_candidates` sidecars.

Stage 18A does not call Kimi, does not call any real LLM, does not modify
screenplay, does not modify story maps, does not modify source traces, and does
not apply creative draft candidates.

## Inputs

Required inputs:

- `screenplay.yaml`
- `author_review_report.yaml`
- `review_report.yaml`
- `quality_report.yaml`

The runner reads `author_review_report.next_stage_authorization` first. If the
value is not `kimi_dialogue_draft`, it writes a schema-valid blocked sidecar and
returns a nonzero CLI exit code.

## Output Artifacts

Stage 18A sample outputs:

- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`
- `examples/output/test1_sanguo_creative_draft_run_log.mock.yaml`

The candidates file validates against:

- `schemas/creative_draft_candidates.schema.json`

The run log records only metadata:

- `agent_id`
- `provider_profile`
- `intended_provider_profile`
- `dry_run`
- `trace_id`
- `status`
- `candidate_count`
- `error_count`
- `stored_prompt: false`
- source artifact paths
- structured errors when blocked

It does not store a prompt, raw response, provider body, full screenplay text,
or full novel text.

## CLI

```bash
python -m novel2script.cli run-agent kimi-dialogue-scene-drafter \
  --screenplay examples/output/test1_sanguo_screenplay.yaml \
  --author-review-report examples/output/test1_sanguo_author_review_report.yaml \
  --review-report examples/output/test1_sanguo_review_report.yaml \
  --quality-report examples/output/test1_sanguo_quality_report.yaml \
  --out examples/output/test1_sanguo_creative_draft_candidates.mock.yaml \
  --run-log examples/output/test1_sanguo_creative_draft_run_log.mock.yaml \
  --dry-run
```

`--allow-network` is rejected for this agent in Stage 18A.

## Mock Candidate Behavior

The mock runner selects the first screenplay scene that has:

- a real `scene_id`;
- at least one real `beat_id`;
- source trace;
- source trace IDs.

It does not invent target IDs. Current screenplay elements do not have stable
element IDs, so Stage 18A does not emit `element_id` in the mock candidates.
Future implementation may include `element_id` only after the screenplay
artifact actually provides one.

The mock output includes:

- `dialogue_insert`
- `beat_externalization`
- `scene_action_enhancement`

Every candidate includes:

- `id`
- `type`
- `target`
- `proposed_text`
- `rationale`
- `source_trace`
- `source_trace_ids`
- `constraints_observed`
- `risks`
- `confidence`
- `merge_policy: human_approval_required`
- `requires_author_approval: true`

## Fail-Closed Rules

The runner writes a schema-valid sidecar with no candidates and a blocking error
when:

- the author review report does not authorize `kimi_dialogue_draft`;
- the screenplay does not contain a scene/beat/source-trace target.

The CLI returns nonzero for blocked outputs.

## Tests

Focused tests:

```bash
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py
```

Full regression:

```bash
python -m pytest
```

## Non-Goals

- No real Kimi call.
- No real LLM call.
- No model prompt generation.
- No screenplay mutation.
- No story map mutation.
- No source trace mutation.
- No Stage 15, Stage 16, or Stage 17 artifact mutation other than writing the
  new Stage 18 sample outputs.
- No automatic candidate application.
- No merged screenplay generation.
- No commit.

## Stage 18B Readiness

Stage 18B may add a human-review flow for creative draft candidates or prepare a
real Kimi smoke contract. A real Kimi call remains forbidden until mock-first
tests, schema validation, leakage scans, and explicit user authorization all
pass.
