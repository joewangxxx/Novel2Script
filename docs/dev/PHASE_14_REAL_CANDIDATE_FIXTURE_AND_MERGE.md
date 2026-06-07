# Phase 14: Real Candidate Fixture And Merge

## Goal

Stage 14 defines how a real Qwen semantic-candidates sidecar may be retained as
a reviewable fixture and then routed through the Stage 12 human decision merge
flow. The fixture is an audit artifact, not a silent source-of-truth upgrade.

The core flow is:

```text
external novel file
  -> deterministic story_map in a temporary path
  -> real qwen semantic_candidates sidecar
  -> human semantic_candidate_decisions
  -> Stage 12 merge
  -> new merged story_map and merge report
```

Stage 14A is contract-only. It does not call a real model, generate a fixture,
run a merge, or modify schemas.

## Non-Goals

- Do not execute a real LLM call during Stage 14A.
- Do not generate or commit a real semantic candidate fixture during Stage 14A.
- Do not run Stage 12 merge during Stage 14A.
- Do not modify `story_map.schema.json`, `semantic_candidates.schema.json`,
  `semantic_candidate_decisions.schema.json`, or
  `semantic_candidate_merge_report.schema.json`.
- Do not modify Stage 13 provider or parser logic.
- Do not commit a new full private novel text or local external input file.
- Do not save prompt text, raw provider response, API keys, Authorization
  headers, HTTP bodies, or provider request payloads.

## Fixture Retention Rule

A real semantic candidates sidecar may be saved under `examples/output/` only
when all of these are true:

- The user explicitly authorizes a real Qwen smoke or fixture-generation run.
- The input story map was generated from an external input in a temporary path
  or from a repository-approved public/fixture input.
- The semantic sidecar validates against
  `schemas/semantic_candidates.schema.json`.
- `provider_profile` is `qwen_long`.
- `dry_run` is `false`.
- `human_approval_required` is `true`.
- `candidates` contains at least one item.
- `errors` is empty.
- Every candidate has `merge_policy: human_approval_required`.
- Every candidate `source_trace_ids` references only chapter and paragraph IDs
  sent to the model by the bounded excerpt whitelist.
- The deterministic source story map hash is unchanged after the agent run.
- The saved sidecar contains no prompt text, raw response, API key,
  Authorization header, provider HTTP body, or full private novel text.

If any condition fails, the sidecar must remain temporary and must be removed
after QA captures safe metadata.

## Allowed Fixture Content

The retained fixture may contain:

- `semantic_candidates.schema_version`
- `source_story_map`
- `agent_id`
- `provider_profile`
- `dry_run`
- `candidates`
- `errors`
- `human_approval_required`
- `run_log` path metadata, if the referenced run log itself is not retained
- `metadata` values listed below
- candidate `id`, `type`, `confidence`, `evidence.summary`,
  optional `evidence.quote_preview`, optional `evidence.reasoning_note`,
  `source_trace_ids`, `target_story_map_field`, `proposed_fields`, and
  `merge_policy`

The retained fixture must not contain:

- full prompt text;
- raw model response;
- provider request or response body;
- API key, token, Authorization header, or `.env` value;
- complete private novel text;
- unbounded excerpts;
- local machine paths that reveal private directories, except repository
  relative output paths;
- Stage 12 human decisions unless stored in a separate decisions artifact.

`quote_preview` is allowed only as the bounded, schema-limited evidence preview
already accepted by `semantic_candidates.schema.json`. It must not be expanded
to full paragraphs or chapters.

## Required Fixture Metadata

Because `semantic_candidates.schema.json` allows `metadata.additionalProperties`,
Stage 14 uses metadata keys rather than changing the schema.

Recommended fixture metadata:

```yaml
metadata:
  provider_profile: "qwen_long"
  model: "qwen-long"
  dry_run: false
  human_approval_required: true
  source_story_map: "examples/output/generated_story_map.real_fixture.yaml"
  fixture_source: "authorized_real_qwen_smoke"
  created_from_external_input: true
  retained_as_fixture: true
  prompt_retained: false
  model_text_retained: false
  provider_body_retained: false
  full_source_text_retained: false
  story_map_hash_before: "sha256:..."
  story_map_hash_after: "sha256:..."
  fixture_security_scan: "pass"
```

The root fields remain authoritative when they overlap with metadata. Metadata
exists to make fixture provenance easy for humans and QA to audit.

## Expected Stage 14 Artifacts

Stage 14B may generate these files after explicit authorization:

- `examples/output/generated_story_map.real_fixture.yaml`
- `examples/output/generated_semantic_candidates.real_qwen.yaml`

Stage 14C may generate these files:

- `examples/output/generated_semantic_candidate_decisions.real_qwen.yaml`
- `examples/output/generated_story_map.real_qwen_merged.yaml`
- `examples/output/generated_semantic_candidate_merge_report.real_qwen.yaml`

Stage 14 must not commit a new full external input novel. If a real input file
is needed for repeatability, it must stay outside the repository unless the
user separately confirms it is public, authorized, and suitable as a committed
fixture.

## Human Review Flow

Real candidates enter the existing Stage 12 flow:

```text
generated_semantic_candidates.real_qwen.yaml
  -> generated_semantic_candidate_decisions.real_qwen.yaml
  -> merge-semantic-candidates
  -> generated_story_map.real_qwen_merged.yaml
  -> generated_semantic_candidate_merge_report.real_qwen.yaml
```

The Stage 14 decision sample must cover:

- at least one `accept`;
- at least one `reject`;
- at least one `edit`;
- explicit `human_approval` for `accept` and `edit`;
- reviewer and reviewed_at metadata;
- source trace IDs copied from the reviewed candidates.

The merge step must use the existing Stage 12 CLI and must not modify the
original story map in place.

## Merge Boundaries

Stage 14 inherits Stage 12 target restrictions. Only these story map arrays may
receive accepted or edited candidates:

- `characters_detected`
- `locations_detected`
- `props_detected`
- `key_events`
- `timeline`
- `psychological_passages`

Stage 14 must not merge into:

- `story_map.source`;
- `story_map.chapters`;
- `story_map.chapters[].paragraphs`;
- deterministic existing items except by appending approved new items;
- screenplay, outline, character bible, review, quality, or Fountain artifacts.

If a real candidate proposes fields that cannot validate as a Stage 12 target
item, the human decision must reject it or edit it into a schema-valid form.

## QA Gates

Stage 14B/14C QA must verify:

- `semantic_candidates` fixture validates against
  `schemas/semantic_candidates.schema.json`;
- decision file validates against
  `schemas/semantic_candidate_decisions.schema.json`;
- merge report validates against
  `schemas/semantic_candidate_merge_report.schema.json`;
- merged story map validates against `schemas/story_map.schema.json`;
- source story map hash is unchanged before and after real-agent and merge
  operations;
- merge report `audit.preserved_original_story_map` is `true`;
- accepted, rejected, and edited decisions all appear in the merge report;
- `merge_policy` remains `human_approval_required`;
- run log is not retained unless a separate QA rule confirms it contains only
  safe metadata;
- repository scan finds no API key, Authorization header, provider body, raw
  response, prompt text, full private novel text, or `.env` content;
- no unapproved external input novel file is staged or committed.

## Failure Handling

Fail closed when:

- the real provider call fails;
- `finish_reason` is `length`;
- candidate count is zero;
- sidecar schema validation fails;
- candidate source trace references an unsent chapter or paragraph;
- any sidecar/run-log/security scan finds prompt, raw response, API key,
  Authorization header, provider body, or full private text;
- Stage 12 merge status is `blocked`;
- original story map hash changes unexpectedly.

Failed real artifacts must be kept only in a temporary directory long enough to
record safe QA metadata, then removed.

## Commit Strategy

Stage 14 should be committed only after Stage 14A through Stage 14D gates pass.
Recommended split:

1. Stage 14A contract/documentation.
2. Stage 14B/14C fixture, decision, merge artifacts and any narrow tooling.
3. Stage 14D QA and blackboard update.

Do not commit real input novel files unless the user explicitly confirms that
the text is public/authorized and safe to retain in the repository.

## Governance

Current relevant contracts are draft according to
`docs/blackboard/state.yaml`. If any of these contracts become frozen before
implementation, schema/API changes must go through
`docs/architecture/change-requests/` and must not be made silently by FE, BE,
QA, or agent code.
