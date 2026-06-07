# Phase 12: Semantic Candidate Review And Merge

## Goal

Stage 12 defines the human review and merge boundary for
`semantic_candidates`. Candidates may come from mock dry runs or explicit real
LLM calls, but none of them may be merged into `story_map` without an explicit
human decision.

The merge process produces a new story map file and an auditable merge report.
It must not silently modify the original `story_map.yaml`.

## Non-Goals

- Do not build a full frontend review UI.
- Do not call a real LLM.
- Do not automatically accept model candidates.
- Do not implement Kimi, DeepSeek, or additional creative agents.
- Do not change unrelated schemas or downstream screenplay contracts.

## Artifacts

Stage 12 introduces two contracts:

- `schemas/semantic_candidate_decisions.schema.json`
- `schemas/semantic_candidate_merge_report.schema.json`

Planned implementation artifacts for Stage 12B:

- `examples/output/generated_semantic_candidate_decisions.yaml`
- `examples/output/generated_story_map.merged.yaml`
- `examples/output/generated_semantic_candidate_merge_report.yaml`

The original input story map remains unchanged.

## Inputs

The merge flow consumes:

- deterministic story map: `examples/output/generated_story_map.yaml`
- semantic candidates: `examples/output/generated_semantic_candidates.yaml`
- human decisions file: `examples/output/generated_semantic_candidate_decisions.yaml`

The semantic candidates file remains governed by
`schemas/semantic_candidates.schema.json`. Every mergeable candidate must have:

- `id`
- `type`
- `target_story_map_field`
- `source_trace_ids.chapter_id`
- `source_trace_ids.paragraph_ids`
- `proposed_fields`
- `merge_policy: human_approval_required`

## Human Decision Contract

Human decisions are explicit records:

```yaml
semantic_candidate_decisions:
  schema_version: "0.1.0"
  source_story_map: "examples/output/generated_story_map.yaml"
  source_semantic_candidates: "examples/output/generated_semantic_candidates.yaml"
  reviewed_by: "author"
  reviewed_at: "2026-06-06T10:00:00+08:00"
  decisions:
    - decision_id: "dec_001"
      candidate_id: "semcand_001"
      decision: "accept"
      target_story_map_field: "key_events"
      reviewer_note: "Matches the source evidence."
      human_approval:
        approved: true
        reviewer_id: "author"
        approved_at: "2026-06-06T10:00:00+08:00"
```

Allowed decisions:

- `accept`: merge candidate `proposed_fields` as-is after validation.
- `reject`: record rejection, apply no story map change.
- `edit`: merge human-edited fields, not raw model fields.

`edit` must include `edited_fields`. `accept` and `edit` require
`human_approval.approved: true`. Every decision must have a stable
`decision_id` so merge reports can link applied or rejected changes back to the
exact human review record.

## Allowed Merge Targets

Only these `target_story_map_field` values may be merged:

- `characters_detected`
- `locations_detected`
- `props_detected`
- `key_events`
- `timeline`
- `psychological_passages`

The merger must not modify:

- `story_map.source`
- `story_map.chapters`
- `story_map.chapters[].paragraphs`
- existing `source_trace`
- existing accepted deterministic items
- screenplay, outline, character bible, review, quality, or Fountain artifacts

If a target field is absent, misspelled, outside the allowed set, or mismatched
with candidate `type`, the candidate must be skipped or blocked in the merge
report.

## Candidate Type Mapping

The Stage 12B merger should map candidate types to story map arrays as follows:

| Candidate Type | Target Field | New ID Prefix |
| --- | --- | --- |
| `character_candidate` | `characters_detected` | `char_###` |
| `location_candidate` | `locations_detected` | `loc_###` |
| `prop_candidate` | `props_detected` | `prop_###` |
| `event_candidate` | `key_events` | `evt_###` |
| `timeline_candidate` | `timeline` | `tl_###` |
| `psychological_passage_candidate` | `psychological_passages` | `psy_###` |

Generated IDs must be stable for a deterministic input pair. The recommended
rule is to append accepted or edited items in candidate order and allocate the
next available ID in the target array.

## Field Mapping Rules

The merger must produce objects that validate against
`schemas/story_map.schema.json`; because that schema uses
`additionalProperties: false`, AI metadata must stay in the merge report rather
than being inserted into the story map.

Shared merge rules:

- Convert `source_trace_ids` into story map `source_trace`.
- Keep short `quote_preview` only when supplied by candidate evidence.
- Add a `source_trace.note` such as
  `Human-approved semantic candidate semcand_001`.
- Set `confidence` from candidate `confidence`.
- Record candidate hash, decision, and reviewer note in the merge report.
- Record `candidate_id`, `decision_id`, reviewer, reviewed_at, and
  `source_trace_ids` for every merge result.

Target-specific minimum fields:

- `characters_detected`: requires `name`, `source_trace`, `confidence`; may use
  `aliases`, `description_hint`, and `first_seen`.
- `locations_detected`: requires `name`, `source_trace`, `confidence`; may use
  `location_type` and `description_hint`.
- `props_detected`: requires `name`, `source_trace`, `confidence`; may use
  `prop_type` and `description_hint`.
- `key_events`: requires `sequence_index`, `summary`, `source_trace`, and
  `confidence`; may use character, location, prop, and uncertainty references
  only when they exist in the story map.
- `timeline`: requires `order`, `label`, `source_trace`, and `confidence`; may
  reference existing event IDs.
- `psychological_passages`: requires `summary`, `source_trace`, and
  `confidence`; may use `character_ids`, `passage_type`, and
  `externalization_hint`.

If `proposed_fields` or `edited_fields` do not contain enough data to create a
schema-valid target item, the candidate must not be merged.

## Merge Report Contract

Every merge attempt writes:

```yaml
semantic_candidate_merge_report:
  schema_version: "0.1.0"
  source_story_map: "examples/output/generated_story_map.yaml"
  source_semantic_candidates: "examples/output/generated_semantic_candidates.yaml"
  decision_file: "examples/output/generated_semantic_candidate_decisions.yaml"
  output_story_map: "examples/output/generated_story_map.merged.yaml"
  generated_at: "2026-06-06T10:00:00+08:00"
  merge_profile: "deterministic_semantic_candidate_merge_v0"
  status: "success"
  summary:
    candidates_total: 3
    decisions_total: 3
    accepted: 1
    rejected: 1
    edited: 1
    skipped: 0
    blocked: 0
    applied_changes: 2
  decisions: []
  errors: []
  audit:
    preserved_original_story_map: true
    story_map_hash_before: "sha256:..."
    story_map_hash_after: "sha256:..."
    semantic_candidates_hash: "sha256:..."
    decision_file_hash: "sha256:..."
```

`decisions[]` records one result per candidate when possible. Candidates without
a human decision must be recorded as `outcome: skipped` or `outcome: blocked`.
Rejected candidates must also appear in the report.

## Error Handling

The merger must fail closed. It should emit a report and avoid writing a merged
story map when global integrity cannot be trusted.

Blocking errors:

- story map, semantic candidates, or decisions file does not validate;
- candidate lacks `source_trace_ids`;
- `source_trace_ids` do not match chapters and paragraphs in the source story
  map;
- `merge_policy` is not `human_approval_required`;
- `accept` or `edit` lacks explicit human approval;
- target field or candidate type is outside the allowed mapping;
- proposed or edited item cannot validate against `story_map.schema.json`;
- attempted merge would modify disallowed story map fields.

Skippable errors:

- candidate has no decision;
- decision references an unknown candidate;
- candidate duplicates an existing deterministic item and the implementation
  policy chooses to skip rather than append;
- optional reference IDs do not exist and can be omitted without changing the
  approved summary or trace.

The report status should be:

- `success`: all decided candidates were handled and no blocking errors exist.
- `partial`: at least one candidate was skipped, but safe changes were applied.
- `blocked`: no output story map should be trusted.

## AI Inference Boundary

Accepted or edited LLM-origin facts remain AI-assisted. Since
`story_map.schema.json` does not allow arbitrary `ai_tags`, AI provenance must
be stored in the merge report and in short `source_trace.note` text only.

The merger must not upgrade model confidence into truth. It can record:

- candidate ID;
- provider profile and dry-run status from semantic candidates metadata;
- candidate hash;
- human decision;
- reviewer note;
- applied YAML path and created ID.

## Future CLI Shape

Suggested Stage 12B CLI:

```powershell
python -m novel2script.cli merge-semantic-candidates `
  --story-map examples/output/generated_story_map.yaml `
  --semantic-candidates examples/output/generated_semantic_candidates.yaml `
  --decisions examples/output/generated_semantic_candidate_decisions.yaml `
  --out examples/output/generated_story_map.merged.yaml `
  --report examples/output/generated_semantic_candidate_merge_report.yaml
```

The CLI must return non-zero for blocked merges and must not modify the input
story map file.

## Stage 12B Test Plan

Tests should cover:

- accept decision appends a schema-valid story map item;
- reject decision records no story map change;
- edit decision uses `edited_fields`, not original `proposed_fields`;
- every candidate receives an audit result;
- missing human approval blocks accept/edit;
- missing or invalid source trace blocks merge;
- disallowed target fields are rejected;
- original story map bytes remain unchanged;
- merged story map validates against `schemas/story_map.schema.json`;
- merge report validates against
  `schemas/semantic_candidate_merge_report.schema.json`;
- no LLM calls, HTTP calls, or API keys are used.

## Governance

The Stage 12A contracts are draft. After freeze, FE, BE, QA, agents, and tooling
must not silently edit the decision or merge report schemas. Any schema/API
conflict must be proposed under `docs/architecture/change-requests/`.
