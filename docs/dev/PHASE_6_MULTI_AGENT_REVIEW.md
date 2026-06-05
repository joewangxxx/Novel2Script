# Phase 6: Multi-Agent Review Contract

Stage 6 defines deterministic review reports for screenplay drafts. Stage 6B
implements bounded rule reviewers, and Stage 6C exposes them through a CLI. It
does not call LLMs, apply patches, overwrite user drafts, or coordinate real
custom agents.

The Stage 6A contract is draft-only. After a future freeze, schema or API
changes must go through `docs/architecture/change-requests/`; FE, BE, QA, and
tooling must not silently change the contract to fit implementation shortcuts.

## Goals

- Define one shared `review_report` output contract.
- Bound each reviewer to deterministic, evidence-backed checks.
- Preserve traceability from issues back to screenplay targets and upstream
  source traces.
- Ensure review agents only emit patch suggestions that require human approval.
- Keep Stage 6 separate from screenplay generation and Fountain export.

## Non-Goals

- No LLM or external HTTP calls.
- No automatic screenplay mutation.
- No UI, API, or real multi-agent orchestration.
- No edits to `schemas/screenplay.schema.json`.

## Review Report Structure

The schema file is `schemas/review_report.schema.json`. The root structure is:

```yaml
review_report:
  schema_version: "0.1.0"
  source_screenplay: "examples/output/generated_screenplay.yaml"
  source_artifacts:
    story_map: "examples/output/generated_story_map.yaml"
    outline: "examples/output/generated_outline.yaml"
    character_bible: "examples/output/generated_character_bible.yaml"
  generated_at: "2026-06-05"
  review_profile: "deterministic_review_contract_v0"
  reviewers:
    - "character_consistency"
    - "pacing"
    - "dialogue_naturalness"
    - "shootability"
  reviewer_results: []
  summary:
    total_issues: 0
    by_severity:
      low: 0
      medium: 0
      high: 0
    blocking: false
    requires_human_approval_count: 0
  issues: []
```

`source_screenplay` points to the reviewed screenplay YAML. `source_artifacts`
records the upstream Stage 3 and Stage 4 artifacts used as context. Reviewers
must not copy full novel text into the report.

`reviewer_results` records per-reviewer status, including `completed`,
`skipped`, or `failed`. A skipped reviewer may be valid when the screenplay has
no relevant target, such as a dialogue reviewer on a draft with no dialogue
elements.

## Issue Structure

Each issue must identify one target and explain the evidence behind the
suggestion:

```yaml
id: "issue_001"
reviewer: "shootability"
target_id: "beat_001"
target:
  type: "beat"
  id: "beat_001"
  yaml_path: "scenes[0].beats[0]"
severity: "medium"
confidence: "high"
issue: "The beat contains an internal state without a visible action."
evidence:
  description: "The beat turn is supported by source trace, but action is vague."
  source_trace:
    chapter: 1
    paragraph_range: [1, 1]
    note: "from generated screenplay beat"
  source_trace_ids:
    chapter_id: "ch_001"
    paragraph_ids: ["p_001"]
    event_ids: ["evt_001"]
    outline_scene_ids: ["osp_001"]
  related_ids: ["scene_001"]
suggestion: "Replace the internal-state wording with visible behavior."
suggested_patch:
  operation: "replace"
  yaml_path: "scenes[0].beats[0].externalized_action"
  value: "She closes the envelope and hides it under the lamp."
requires_human_approval: true
blocking: false
```

Rules:

- `target_id` must match `target.id` and exists for fast filtering.
- `target.yaml_path` uses repository YAML path notation, not JSON Pointer.
- `issue` states the problem; `suggestion` states the recommended direction.
- `evidence.description` is required even when source trace is unavailable.
- `suggested_patch.operation` is limited to `replace`, `add`, or `note_only`.
- `requires_human_approval` must be `true` for any patchable suggestion.
- Reviewers must never write the suggested patch back to screenplay YAML.

## Severity

- `high`: Structural defect, broken reference, missing required source trace, or
  a problem that blocks trustworthy downstream use.
- `medium`: Continuity, pacing, dialogue, or shootability issue that should be
  reviewed before user-facing output but does not invalidate the file.
- `low`: Style, clarity, weak-confidence, or soft adaptation warning.

`summary.blocking` is true when any issue is high severity and blocks acceptance
for the current gate.

## Confidence

- `high`: Exact schema, ID, path, or deterministic rule evidence.
- `medium`: Heuristic evidence with a clear target and reproducible rule.
- `low`: Weak signal or context-limited concern; use `note_only` unless a human
  has asked for stronger suggestions.

Low-confidence issues must not produce authoritative rewrites.

## Reviewer Scopes

### Character Consistency Reviewer

Inputs:

- `screenplay.yaml`
- `character_bible.yaml`
- Optional `story_map.yaml` for trace and detected-character grounding

Deterministic checks:

- Character IDs referenced by scenes, beats, or dialogue elements exist in
  `screenplay.characters`.
- Screenplay characters can be matched back to character bible entries.
- Locked character fields are not silently contradicted by generated screenplay
  character names, roles, or explicit relationship labels.
- Dialogue or scene references do not introduce unknown characters without a
  traceable `ai_tags` warning.
- Character-related low-confidence inferences retain `ai_tags` and human-review
  metadata.

Boundaries:

- Does not infer hidden motive, deep psychology, or relationship subtext.
- Does not rewrite the character bible.
- Does not replace character decisions accepted by the user.

### Pacing Reviewer

Inputs:

- `screenplay.yaml`
- `outline.yaml`
- Optional `story_map.yaml` for event order and coverage

Deterministic checks:

- Scene order follows `outline.scene_plan` order unless explicitly tagged as an
  adaptation decision.
- Each scene has at least one beat and each beat has required dramatic fields.
- Outline scene IDs and source event IDs are preserved where Stage 5 provided
  them.
- Large scene or beat clusters are flagged by fixed thresholds, not by taste.
- Missing turns, stakes, or externalized actions are reported as pacing risks.

Boundaries:

- Does not reorder the whole screenplay.
- Does not delete source-backed plot events.
- Does not decide target runtime or final act balance without a later contract.

### Dialogue Naturalness Reviewer

Inputs:

- `screenplay.yaml`
- `character_bible.yaml`

Deterministic checks:

- Dialogue elements use valid `character_id` values.
- Dialogue text is non-empty and below fixed length thresholds.
- Repeated dialogue lines or repeated explanatory phrases are flagged.
- Generated dialogue with low-confidence `ai_tags` requires human approval.
- If no dialogue elements exist, the reviewer reports `skipped` or completes
  with zero issues.

Boundaries:

- Does not write polished dialogue.
- Does not infer a full voiceprint from sparse evidence.
- Does not change plot facts or character relationships.

### Shootability Reviewer

Inputs:

- `screenplay.yaml`
- Optional `story_map.yaml` for original source trace context

Deterministic checks:

- Scene heading, location, and time fields are present when required by schema.
- Scene, beat, and element source traces exist.
- Beat `externalized_action` is present and avoids purely internal wording when
  simple keyword rules can detect it.
- Action elements are visible and performable enough for a first draft.
- Psychological passages that remain internal are flagged for later
  externalization.

Boundaries:

- Does not plan camera coverage, schedule, budget, props breakdown, or blocking.
- Does not rewrite action for cinematic quality.
- Does not replace internal passages unless a human accepts a suggested patch.

## Suggested Patch Rules

Suggested patches are advisory. A later approval flow may read them, but Stage 6
reviewers must not apply them directly.

Allowed operations:

- `replace`: replace a scalar or small object at `yaml_path`.
- `add`: add a scalar, list item, or small object at `yaml_path`.
- `note_only`: no direct data change; used for weak, broad, or human judgment
  issues.

Patch values should be minimal and local to the issue target. A patch must not
replace an entire screenplay, scene list, character bible, or generated artifact.

## Deterministic Review Boundary

Stage 6 deterministic reviewers may use:

- YAML loading and schema-compatible dictionary traversal.
- Stable IDs, YAML paths, and source trace fields.
- Fixed thresholds, keyword lists, enum checks, and cross-reference checks.
- Existing Stage 3, Stage 4, and Stage 5 generated artifacts.

Stage 6 reviewers must not use:

- LLM APIs, embeddings, web requests, or remote model calls.
- Broad creative rewrites.
- Hidden memory or non-reproducible judgment.
- Direct writes to `generated_screenplay.yaml`.

## Stage 6 Files

Stage 6A adds:

- `schemas/review_report.schema.json`
- `docs/dev/PHASE_6_MULTI_AGENT_REVIEW.md`
- Updates to `docs/architecture/schema.md`
- Updates to `docs/architecture/folder-plan.md`

Stage 6B adds deterministic reviewers:

- `src/novel2script/reviewers/__init__.py`
- `src/novel2script/reviewers/common.py`
- `src/novel2script/reviewers/review_report.py`
- `src/novel2script/reviewers/character_consistency.py`
- `src/novel2script/reviewers/pacing.py`
- `src/novel2script/reviewers/dialogue_naturalness.py`
- `src/novel2script/reviewers/shootability.py`
- `tests/test_character_consistency_reviewer.py`
- `tests/test_pacing_reviewer.py`
- `tests/test_dialogue_naturalness_reviewer.py`
- `tests/test_shootability_reviewer.py`
- `tests/test_review_report.py`

Stage 6C adds CLI and sample output:

- `src/novel2script/cli.py`
- `tests/test_review_cli.py`
- `examples/output/generated_review_report.yaml`

## Review CLI

Run deterministic review:

```bash
python -m novel2script.cli review-screenplay \
  --screenplay examples/output/generated_screenplay.yaml \
  --character-bible examples/output/generated_character_bible.yaml \
  --out examples/output/generated_review_report.yaml
```

Optional context arguments:

```bash
--story-map examples/output/generated_story_map.yaml
--outline examples/output/generated_outline.yaml
```

The command returns non-zero when required input files are missing. Output
directories are created automatically through the shared YAML writer.

The current `validate` CLI remains screenplay-oriented; it runs schema,
source-trace, beat, and reference checks that are specific to screenplay YAML.
To validate a review report, use `schemas/review_report.schema.json` directly
with JSON Schema tooling or tests.

## Implemented Test Coverage

Stage 6B and Stage 6C tests cover:

- A valid empty report with all summary counts set to zero.
- Each reviewer emits deterministic issue IDs and stable YAML paths.
- Character references are checked against known characters.
- Dialogue reviewer handles both no-dialogue and invalid-dialogue drafts.
- Pacing reviewer flags missing beat fields and excessive beat density.
- Shootability reviewer flags missing source trace or non-visible action.
- All issues have severity, confidence, target, evidence, suggestion, and
  `requires_human_approval`.
- `review-screenplay` writes schema-valid YAML and returns non-zero for missing
  screenplay input.
- No test or implementation calls LLM, HTTP, or external model clients.

Stage 6C regression checks must not break:

- `parse-novel`
- `build-outline`
- `build-character-bible`
- `build-screenplay`
- `validate`
- `export-fountain`

## Deterministic Reviewer Status

These reviewers are deterministic functions, not real Codex subagents and not
LLM agents. They read screenplay and optional upstream YAML artifacts, traverse
known fields, and emit advisory issues. They do not maintain hidden memory,
launch external processes, or apply `suggested_patch` values.

## Gate For Stage 6A

Stage 6A passes if:

- `review_report` structure is documented and represented as JSON Schema.
- Reviewer inputs, outputs, checks, and boundaries are documented.
- Patch suggestions are advisory and require human approval.
- No reviewer code, LLM integration, screenplay mutation, UI, or API is added.
- Existing tests still pass.
