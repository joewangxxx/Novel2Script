# Phase 8: Quality Eval Dashboard Contract

Stage 8 defines a deterministic quality evaluation layer for Novel2Script. It
aggregates existing validation, review, and Fountain roundtrip reports into one
machine-readable quality report and one human-readable Markdown dashboard.

Stage 8A is contract-only. It does not implement builders, call LLMs, rewrite
screenplay YAML, apply review patches, change prior schemas, or create a Web UI.

## Goals

- Give authors a compact answer to whether a screenplay draft is trustworthy,
  traceable, shootable, and safe to keep editing.
- Give later agents a stable `quality_report` contract for gate decisions.
- Reuse Stage 2 validation, Stage 6 review, and Stage 7 roundtrip evidence.
- Keep scoring deterministic and reproducible.
- Make hard gates override weighted averages.

## Non-Goals

- No Web dashboard or frontend.
- No LLM, embedding, HTTP, or external model calls.
- No screenplay rewrite or automatic patch application.
- No modification to `screenplay`, `review_report`, or
  `fountain_roundtrip_report` contracts.
- No new creative judgment beyond interpreting existing deterministic reports.

## Output Artifacts

Stage 8B/8C should generate:

- `examples/output/generated_quality_report.yaml`
- `examples/output/generated_quality_dashboard.md`

The YAML is the source of truth for downstream tooling. The Markdown dashboard is
for authors and reviewers who need a readable snapshot without opening multiple
YAML files.

## Quality Report Structure

The schema file is `schemas/quality_report.schema.json`. The initial contract
version is `0.1.0`.

```yaml
quality_report:
  schema_version: "0.1.0"
  generated_at: "2026-06-05"
  report_profile: "deterministic_quality_eval_v0"
  source_artifacts:
    screenplay: "examples/output/generated_screenplay.yaml"
    validation_report: "examples/output/generated_screenplay_validation_report.yaml"
    review_report: "examples/output/generated_review_report.yaml"
    fountain_roundtrip_report: "examples/output/generated_screenplay_roundtrip_report.yaml"
    quality_report_yaml: "examples/output/generated_quality_report.yaml"
    quality_dashboard_markdown: "examples/output/generated_quality_dashboard.md"
  status_policy:
    allowed_statuses: ["pass", "warn", "fail", "blocked"]
    hard_gates_precede_average_score: true
  scoring_policy:
    score_min: 0
    score_max: 100
    default_pass_threshold: 90
    default_warn_threshold: 70
  dimensions: []
  overall_readiness:
    status: "pass"
    score: 100
    decision: "ready_for_author_review"
    hard_gate_failures: []
    next_actions: []
  dashboard:
    format: "markdown"
    path: "examples/output/generated_quality_dashboard.md"
    sections:
      - "summary"
      - "gate_decision"
      - "dimension_scores"
      - "blocking_items"
      - "recommended_next_actions"
      - "source_artifacts"
      - "limitations"
```

## Status Enum

All dimensions and the overall readiness object use the same status values:

- `pass`: Evidence is clean enough for the current stage gate.
- `warn`: The draft can continue, but the user or a later agent should review
  the listed concerns.
- `fail`: A non-blocking quality threshold failed; revision is recommended
  before user-facing output.
- `blocked`: A hard gate failed or the input reports are unsafe to trust.

`blocked` has priority over all numeric scores.

## Dimensions

Every quality report must include these dimension IDs:

- `schema_validity`
- `source_trace_coverage`
- `beat_completeness`
- `reference_integrity`
- `character_consistency`
- `pacing`
- `dialogue_naturalness`
- `shootability`
- `fountain_roundtrip_safety`
- `semantic_staleness`
- `overall_readiness`

Each dimension contains:

```yaml
id: "schema_validity"
status: "pass"
score: 100
hard_gate: true
summary: "Screenplay schema validation passed."
evidence:
  - source: "validation_report"
    path: "schema_validity.passed"
    summary: "Validation report says schema_validity.passed is true."
    value: true
metrics:
  errors: 0
recommendations: []
blocking_reasons: []
```

Evidence points to fields in the existing reports. It should not copy full
screenplay, novel, or Fountain text.

## Scoring Rules

Scores are integers from 0 to 100. Implementations should compute dimension
scores first, then apply hard gates before producing `overall_readiness`.

Default thresholds:

- `pass`: score >= 90 and no blocking condition.
- `warn`: 70 <= score < 90 and no blocking condition.
- `fail`: score < 70 and no hard block.
- `blocked`: hard gate failure or unsafe report state.

Hard gates override averages:

- If `schema_validity` is blocked, `overall_readiness.status` is `blocked`.
- If `reference_integrity` is blocked, `overall_readiness.status` is `blocked`.
- If `source_trace_coverage` is blocked because required trace data is missing
  or invalid, `overall_readiness.status` is `blocked`.
- If `fountain_roundtrip_safety` is blocked because the roundtrip report status
  is `blocked`, map match failed, line drift was detected, or blocking issues
  exist, `overall_readiness.status` is `blocked`.

If no hard gate blocks, `overall_readiness.score` is the weighted or unweighted
average of the dimension scores excluding the `overall_readiness` dimension
itself. Implementations may add explicit weights in `scoring_policy.weights`;
otherwise all dimensions except `overall_readiness` have equal weight.

## Dimension Inputs And Rules

### schema_validity

Input: Stage 2 validation report.

Rules:

- `validation_report.schema_validity.passed: true` maps to 100/pass.
- Any schema errors map to 0/blocked.
- This is a hard gate.

### source_trace_coverage

Input: Stage 2 validation report.

Rules:

- `source_coverage.score` maps to `round(score * 100)`.
- Missing or invalid targets lower status to warn/fail based on count.
- Invalid trace targets may block when they make provenance untrustworthy.
- This is a hard gate when score is 0 or invalid trace targets exist.

### beat_completeness

Input: Stage 2 validation report.

Rules:

- `beat_completeness.score` maps to `round(score * 100)`.
- Empty or incomplete beats become recommendations for regeneration or manual
  repair.
- This is not a hard gate unless later policy explicitly marks it as one.

### reference_integrity

Input: Stage 2 validation report.

Rules:

- `reference_integrity.passed: true` maps to 100/pass.
- Missing references map to 0/blocked.
- This is a hard gate because broken IDs can corrupt review, export, and
  roundtrip behavior.

### character_consistency

Input: Stage 6 review report.

Rules:

- Start at 100.
- Subtract 40 for each high issue from `character_consistency`.
- Subtract 20 for each medium issue.
- Subtract 5 for each low issue.
- Any blocking issue maps to blocked.

### pacing

Input: Stage 6 review report.

Rules:

- Start at 100 and apply the same severity deductions as reviewer dimensions.
- A skipped pacing reviewer is warn unless a clear reason says the target was
  not applicable.
- Blocking pacing issues block overall readiness only when the review report
  marks them blocking.

### dialogue_naturalness

Input: Stage 6 review report.

Rules:

- Start at 100 and deduct by issue severity.
- If the dialogue reviewer is skipped because the draft has no dialogue, score
  remains 100 but status becomes warn with a note that dialogue quality is not
  yet meaningfully evaluated.
- Dialogue issues remain advisory; they do not rewrite text.

### shootability

Input: Stage 6 review report.

Rules:

- Start at 100 and deduct by issue severity.
- High shootability issues normally fail the dimension.
- Blocking shootability issues block overall readiness only when marked
  blocking by the review report.

### fountain_roundtrip_safety

Input: Stage 7 roundtrip report.

Rules:

- `status: applied` or `skipped` with no issues maps to 100/pass.
- `status: partial` maps to 70/warn unless high issues exist.
- `status: blocked`, line drift, map mismatch, or blocking issues map to
  0/blocked.
- Missing roundtrip report maps to warn, not blocked, when no Fountain import
  was requested.

### semantic_staleness

Inputs: screenplay metadata and Stage 7 roundtrip report.

Rules:

- If `metadata.semantic_fields_stale` is absent or false, score is 100/pass.
- If it is true because Fountain text was synced after beat generation, score is
  70/warn.
- This warning tells later agents that beats, objectives, conflict, stakes, and
  externalized actions may need review. The quality evaluator must not update
  those semantic fields.

### overall_readiness

Inputs: all dimensions.

Rules:

- Hard gate failures decide `blocked` before score averaging.
- If not blocked, compute the average score across all other dimensions.
- Map the score to pass/warn/fail using the configured thresholds.
- Record concrete `next_actions`, such as rerun validation, inspect high review
  issues, rerun review after roundtrip edits, or regenerate stale semantic
  fields in a future approved phase.

## Markdown Dashboard

The Markdown dashboard should mirror the YAML without becoming the source of
truth. Recommended sections:

- `# Quality Dashboard`
- `## Summary`
- `## Gate Decision`
- `## Dimension Scores`
- `## Blocking Items`
- `## Recommended Next Actions`
- `## Source Artifacts`
- `## Limitations`

The dashboard may use simple tables. It must not include full screenplay,
Fountain, or novel text.

## Deterministic Boundary

Stage 8 may use:

- YAML loading.
- JSON Schema validation for `quality_report`.
- Existing validation, review, and roundtrip report fields.
- Fixed severity deductions and threshold rules.
- Screenplay metadata flags such as `semantic_fields_stale`.

Stage 8 must not use:

- LLMs, embeddings, external HTTP, or API keys.
- New creative review beyond existing deterministic reports.
- Automatic application of Stage 6 suggested patches.
- Rewrite or mutation of screenplay, review, validation, or roundtrip outputs.
- Silent contract edits to prior schemas.

## Stage 8 File Plan

Stage 8A adds:

- `schemas/quality_report.schema.json`
- `docs/dev/PHASE_8_QUALITY_EVAL_DASHBOARD.md`
- Updates to `docs/architecture/schema.md`
- Updates to `docs/architecture/folder-plan.md`

Stage 8B may add deterministic report builders:

- `src/novel2script/quality/__init__.py`
- `src/novel2script/quality/quality_report.py`
- `src/novel2script/quality/markdown_dashboard.py`
- `tests/test_quality_report.py`
- `tests/test_quality_dashboard.py`

Stage 8C may add CLI and sample outputs:

- `src/novel2script/cli.py`
- `tests/test_quality_cli.py`
- `examples/output/generated_quality_report.yaml`
- `examples/output/generated_quality_dashboard.md`

## Gate For Stage 8A

Stage 8A passes if:

- `quality_report` schema defines machine-readable status, scores, evidence,
  hard gates, overall readiness, and dashboard metadata.
- Stage 8 documentation explains each quality dimension and scoring rule.
- The contract clearly states that hard gates override average score.
- Markdown dashboard output is defined as a human-readable companion artifact.
- No Web UI, LLM integration, screenplay rewrite, or prior contract mutation is
  introduced.
