# Phase 15: Real Merged Story Map End-to-End Draft

## Goal

Stage 15 defines an end-to-end, deterministic sample package built from the
Stage 14 real semantic-candidate merge output. It proves that a real Qwen
candidate fixture, after human accept/reject/edit review, can flow through the
existing Novel2Script planning, screenplay, review, Fountain, roundtrip, and
quality evaluation chain without another LLM call.

Stage 15A is contract-only. It does not generate artifacts, call a model,
modify schemas, add prompts, change provider logic, or commit files.

## Background

Stage 14 produced and QA-approved these artifacts:

- `examples/output/test1_sanguo_story_map.yaml`
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`
- `examples/output/test1_sanguo_story_map.merged.yaml`
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`

Stage 15 starts from the merged story map, not the raw model output. The model
candidates remain advisory evidence; the Stage 12 human decisions and merge
report are the approval boundary.

## Inputs

Required inputs:

- `examples/output/test1_sanguo_story_map.merged.yaml`
- `examples/output/test1_sanguo_semantic_candidate_merge_report.yaml`

Reference inputs for immutability checks:

- `examples/output/test1_sanguo_story_map.yaml`
- `examples/output/test1_sanguo_semantic_candidates.real.yaml`
- `examples/output/test1_sanguo_semantic_candidate_decisions.yaml`

The merged story map must validate against `schemas/story_map.schema.json`
before any downstream generation starts. The merge report must validate against
`schemas/semantic_candidate_merge_report.schema.json` and have either
`status: success` or a documented non-blocking `partial` status. If the merge
report is `blocked`, Stage 15 must stop.

## Output Package

Stage 15B should generate these deterministic outputs:

- `examples/output/test1_sanguo_outline.yaml`
- `examples/output/test1_sanguo_character_bible.yaml`
- `examples/output/test1_sanguo_screenplay.yaml`
- `examples/output/test1_sanguo_screenplay_validation_report.yaml`
- `examples/output/test1_sanguo_screenplay.fountain`
- `examples/output/test1_sanguo_screenplay.fountain.map.json`
- `examples/output/test1_sanguo_review_report.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip_report.yaml`
- `examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml`
- `examples/output/test1_sanguo_quality_report.yaml`
- `examples/output/test1_sanguo_quality_dashboard.md`

These files form the first real-enhanced, fully reviewable sample draft package.
They are still deterministic scaffolding, not a final literary screenplay.

## Pipeline

The Stage 15 pipeline is:

```text
Stage 14 merged story_map
  -> build-outline
  -> build-character-bible
  -> build-screenplay
  -> validate screenplay
  -> export-fountain with sidecar map
  -> review-screenplay
  -> limited import-fountain roundtrip sample
  -> validate roundtrip screenplay
  -> evaluate-quality
  -> quality dashboard
```

The pipeline must not call `run-agent`, real Qwen, mock LLM routing, or any
provider API. It consumes the Stage 14 merged artifact as ordinary YAML.

## Suggested Commands

Build planning artifacts:

```bash
python -m novel2script.cli build-outline examples/output/test1_sanguo_story_map.merged.yaml --out examples/output/test1_sanguo_outline.yaml
python -m novel2script.cli build-character-bible examples/output/test1_sanguo_story_map.merged.yaml --out examples/output/test1_sanguo_character_bible.yaml
```

Build and validate screenplay:

```bash
python -m novel2script.cli build-screenplay \
  --story-map examples/output/test1_sanguo_story_map.merged.yaml \
  --outline examples/output/test1_sanguo_outline.yaml \
  --character-bible examples/output/test1_sanguo_character_bible.yaml \
  --out examples/output/test1_sanguo_screenplay.yaml

python -m novel2script.cli validate examples/output/test1_sanguo_screenplay.yaml \
  --schema schemas/screenplay.schema.json \
  --out examples/output/test1_sanguo_screenplay_validation_report.yaml
```

Export Fountain:

```bash
python -m novel2script.cli export-fountain examples/output/test1_sanguo_screenplay.yaml \
  --out examples/output/test1_sanguo_screenplay.fountain \
  --map examples/output/test1_sanguo_screenplay.fountain.map.json
```

Review screenplay:

```bash
python -m novel2script.cli review-screenplay \
  --screenplay examples/output/test1_sanguo_screenplay.yaml \
  --character-bible examples/output/test1_sanguo_character_bible.yaml \
  --story-map examples/output/test1_sanguo_story_map.merged.yaml \
  --outline examples/output/test1_sanguo_outline.yaml \
  --out examples/output/test1_sanguo_review_report.yaml
```

Run a limited Fountain roundtrip sample:

```bash
python -m novel2script.cli import-fountain \
  --screenplay examples/output/test1_sanguo_screenplay.yaml \
  --fountain <stage15 temporary edited fountain> \
  --map examples/output/test1_sanguo_screenplay.fountain.map.json \
  --out examples/output/test1_sanguo_screenplay_roundtrip.yaml \
  --report examples/output/test1_sanguo_screenplay_roundtrip_report.yaml
```

Validate the roundtrip screenplay:

```bash
python -m novel2script.cli validate examples/output/test1_sanguo_screenplay_roundtrip.yaml \
  --schema schemas/screenplay.schema.json \
  --out examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml
```

Evaluate quality:

```bash
python -m novel2script.cli evaluate-quality \
  --screenplay examples/output/test1_sanguo_screenplay_roundtrip.yaml \
  --validation-report examples/output/test1_sanguo_screenplay_roundtrip_validation_report.yaml \
  --review-report examples/output/test1_sanguo_review_report.yaml \
  --roundtrip-report examples/output/test1_sanguo_screenplay_roundtrip_report.yaml \
  --out examples/output/test1_sanguo_quality_report.yaml \
  --markdown examples/output/test1_sanguo_quality_dashboard.md
```

## Roundtrip Sample Rule

Stage 15B may create a temporary edited Fountain file by copying
`examples/output/test1_sanguo_screenplay.fountain` and changing exactly one
mapped safe text field. The original exported Fountain file must not be edited
in place.

Allowed roundtrip edits remain the Stage 7 safe fields:

- `scenes[i].heading`
- `scenes[i].elements[j].text`

If the temporary Fountain edit causes line drift, map mismatch, or an unsafe
target, Stage 15B must preserve the blocked report and stop before quality
evaluation. It must not guess a repair.

## Trace And Mutation Policy

Stage 15 must preserve the separation between inputs and outputs:

- Do not modify `examples/output/test1_sanguo_story_map.yaml`.
- Do not modify `examples/output/test1_sanguo_story_map.merged.yaml`.
- Do not modify the Stage 14 semantic candidates, decisions, or merge report.
- Do not mutate `source_trace`, `source_trace_ids`, `ai_tags`, or approved
  Stage 12 merge metadata except through existing deterministic builders that
  create new downstream artifacts.
- If Fountain import writes a roundtrip screenplay, it may set
  `metadata.semantic_fields_stale: true` exactly as Stage 7 defines.

Stage 15 QA must capture hashes for both the original Stage 14 source story map
and the merged story map before and after the pipeline.

## Schema Validation Gates

Stage 15 outputs must be schema-valid where a schema exists:

- `test1_sanguo_outline.yaml` ->
  `schemas/outline.schema.json`
- `test1_sanguo_character_bible.yaml` ->
  `schemas/character_bible.schema.json`
- `test1_sanguo_screenplay.yaml` ->
  `schemas/screenplay.schema.json` through the `validate` CLI
- `test1_sanguo_review_report.yaml` ->
  `schemas/review_report.schema.json`
- `test1_sanguo_screenplay_roundtrip_report.yaml` ->
  `schemas/fountain_roundtrip_report.schema.json`
- `test1_sanguo_screenplay_roundtrip.yaml` ->
  `schemas/screenplay.schema.json` through the `validate` CLI
- `test1_sanguo_quality_report.yaml` ->
  `schemas/quality_report.schema.json`

The validation reports themselves are accepted as CLI evidence unless a later
schema is introduced for validation-report output.

## Quality Gate

`test1_sanguo_quality_report.yaml` must include:

- all Stage 8 quality dimensions;
- `overall_readiness.status`;
- `overall_readiness.score`;
- references to validation, review, and roundtrip reports;
- a concrete `next_actions` list;
- a machine-readable decision that is `pass`, `warn`, `fail`, or `blocked`.

`test1_sanguo_quality_dashboard.md` must be non-empty and include:

- summary;
- gate decision;
- dimension score table;
- blocking or warning items;
- next actions;
- source artifact list;
- limitations.

## Security Gate

Stage 15 artifacts and logs must not contain:

- API key or token values;
- bearer token values;
- authorization header values;
- prompt text;
- provider request or response body;
- raw model response;
- full private novel text;
- `.env` content;
- unbounded source excerpts.

Expected source-code and test references to provider field names are not Stage
15 artifact leaks, but generated Stage 15 output files must pass a strict scan.

## QA Gate Checklist

Stage 15C should pass only if:

- Stage 14 merged story map exists and validates.
- Stage 14 merge report exists, validates, and is not blocked.
- outline and character bible generation succeeds.
- screenplay generation succeeds.
- screenplay validation passes.
- Fountain export succeeds and creates a sidecar map.
- deterministic review succeeds and creates a valid review report.
- limited Fountain roundtrip succeeds or produces a non-silent blocked report
  that stops downstream quality evaluation.
- roundtrip screenplay validates when roundtrip status permits output.
- quality report and Markdown dashboard are generated.
- original Stage 14 source story map hash is unchanged.
- merged story map hash is unchanged.
- generated output files pass the Stage 15 security scan.
- no real LLM, mock LLM, HTTP provider, or new semantic candidate merge is run.

## Failure Handling

Fail closed when:

- any required input is missing;
- any schema validation fails;
- Stage 14 merge report is blocked;
- screenplay validation fails;
- Fountain export or map generation fails;
- roundtrip report is blocked and no quality report can safely summarize it;
- quality report lacks an overall readiness decision;
- an output scan finds key, prompt, provider body, raw response, or full-source
  leakage;
- either Stage 14 story map hash changes unexpectedly.

If a gate fails, update QA and blackboard, keep safe diagnostic artifacts, and
do not commit.

## Non-Goals

- No real LLM call.
- No mock-provider semantic generation.
- No new prompts.
- No schema changes.
- No Stage 13 provider changes.
- No automatic acceptance of new semantic candidates.
- No Stage 12 merge rerun except using the already approved Stage 14 merged
  story map as input.
- No Web UI or API.
- No commit unless the user explicitly requests it after Stage 15 gates pass.

## Stage Plan

Stage 15A:

- define this contract;
- update `docs/blackboard/state.yaml`;
- do not generate outputs.

Stage 15B:

- run the deterministic pipeline from the Stage 14 merged story map;
- generate the named output package;
- perform immediate schema and mutation checks;
- update QA and blackboard.

Stage 15C:

- run focused and full regression tests;
- validate all Stage 15 artifacts;
- run strict artifact security scan;
- update QA and blackboard;
- prepare commit scope only after gates pass.

## Governance

Current relevant contracts are draft according to
`docs/blackboard/state.yaml`. If any contract becomes frozen before Stage 15B or
Stage 15C, schema or API changes must go through
`docs/architecture/change-requests/` and must not be made silently.
