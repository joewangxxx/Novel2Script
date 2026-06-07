# Phase 7: Fountain Limited Roundtrip Contract

Stage 7 defines a limited, deterministic Fountain import/sync workflow. The goal
is to let users make small text edits in an exported Fountain file and safely
sync only mapped, low-risk text fields back into `screenplay.yaml`.

This is intentionally not a full Fountain parser. It does not create screenplay
YAML from arbitrary Fountain, infer new scenes, rebuild beats, rewrite source
traces, call LLMs, or apply semantic edits.

## Why Limited Roundtrip

Fountain is a prose-oriented format. Users can insert blank lines, reorder
scenes, change character cues, add transitions, or create entirely new material
with no stable YAML identity. Novel2Script screenplay YAML carries structured
fields such as source traces, beats, `ai_tags`, characters, and adaptation
policy. A full parser would have to guess which edited prose maps to which
semantic object, and wrong guesses could silently corrupt traceability.

Stage 7 therefore uses the existing sidecar map from Fountain export as the
source of truth. If the map proves that a Fountain line range corresponds to a
safe YAML text field, that text can be synchronized. If line counts drift,
mapped regions disappear, order changes, or the map no longer matches, the
importer must produce a report and stop or skip the unsafe region.

## Current Sidecar Map

`export-fountain` currently writes a sidecar JSON file with this shape:

```json
{
  "source_yaml": "examples/output/generated_screenplay.yaml",
  "fountain_file": "examples/output/generated_screenplay.fountain",
  "mappings": [
    {
      "line_start": 5,
      "line_end": 5,
      "scene_id": "scene_001",
      "beat_id": null,
      "element_index": null,
      "yaml_path": "scenes[0].heading"
    },
    {
      "line_start": 6,
      "line_end": 6,
      "scene_id": "scene_001",
      "beat_id": null,
      "element_index": 0,
      "yaml_path": "scenes[0].elements[0].text"
    }
  ]
}
```

Map rules:

- `source_yaml` identifies the screenplay YAML used to export Fountain.
- `fountain_file` identifies the exported Fountain file.
- `mappings[]` is ordered by Fountain line number.
- `line_start` and `line_end` are 1-based inclusive line ranges.
- `yaml_path` is the only field target the importer may consider.
- `scene_id`, `beat_id`, and `element_index` are evidence for identity checks;
  they do not authorize broader updates.

The current map does not store original line hashes, total exported line count,
or element type. Stage 7B may derive those by re-exporting the source YAML to a
temporary baseline and comparing it with the edited Fountain file.

## Safe Sync Fields

Only these YAML paths are eligible:

- `scenes[i].heading`
- `scenes[i].elements[j].text`

No other path may be modified by Fountain roundtrip, even if it appears in a
future sidecar map.

Safe field rules:

- The YAML path must match exactly one of the allowed path patterns.
- The target scene and element index must exist in the current source YAML.
- The mapped Fountain line range must still exist.
- The importer must compare against a baseline export from the same source YAML
  and sidecar map before applying changes.
- A safe change is text-only. It must not create or delete scenes, elements,
  beats, characters, traces, or metadata facts except the allowed roundtrip
  metadata record.

## Forbidden Fields

The importer must never update:

- `source_trace`
- `source_trace_ids`
- `beats.objective`
- `beats.tactic`
- `beats.obstacle`
- `beats.conflict`
- `beats.stakes`
- `beats.turn`
- `beats.turning_point`
- `beats.externalized_action`
- `characters`
- `adaptation_policy`
- existing factual `ai_tags` fields
- source artifacts such as `story_map`, `outline`, or `character_bible`

If a Fountain edit appears to imply one of these changes, the importer must
record an issue in the roundtrip report instead of mutating YAML.

## Element Type Normalization

When `yaml_path` targets `scenes[i].elements[j].text`, the importer may inspect
the element type in YAML and normalize only the text value:

- `action`: synchronize the mapped Fountain lines joined with `\n`, trimmed at
  the outer edges.
- `dialogue`: skip the character cue line and synchronize only the dialogue text
  lines that belong to the mapped dialogue block. Do not modify
  `character_id`.
- `parenthetical`: remove one outer pair of parentheses from the mapped text
  before synchronizing. Do not infer actor direction semantics.
- `transition`: preserve edited text as text, but do not infer or change any
  semantic transition field.
- `note`: currently not exported or mapped. If a future map points to a note,
  skip it unless Stage 7 contract is amended.

If the importer cannot determine the element type from the source YAML, it must
skip the change and report `unsupported_element_type` or `map_mismatch`.

## Drift And Mismatch Policy

The importer must be conservative:

- If total Fountain line count differs from the baseline export, set
  `line_drift_detected: true`.
- If a mapped range no longer exists, block or skip the range.
- If scene or element order changed, report `structure_changed`.
- If the sidecar `source_yaml` or `fountain_file` does not match the import
  arguments, report `map_mismatch`.
- If `yaml_path` targets an unsafe field, report `unsafe_yaml_path`.
- If new scenes, elements, headings, or dialogue blocks appear outside mapped
  regions, do not import them.
- If multiple mapped regions overlap or are out of order, block the import.

Recommended Stage 7B behavior:

- Global line drift blocks applying all changes by default.
- Per-region mismatch can be skipped while other regions are applied only when
  the global map still matches and the unchanged regions are stable.
- Every block or skip must be recorded in the import report.

## Roundtrip Report Contract

The report schema is `schemas/fountain_roundtrip_report.schema.json`.

```yaml
fountain_roundtrip_report:
  schema_version: "0.1.0"
  source_yaml: "examples/output/generated_screenplay.yaml"
  fountain_file: "examples/output/generated_screenplay.fountain"
  map_file: "examples/output/generated_screenplay.fountain.map.json"
  generated_at: "2026-06-05"
  status: "applied"
  summary:
    mapped_regions: 12
    changed_regions: 1
    applied_changes: 1
    skipped_changes: 0
    blocking_issues: 0
  line_policy:
    expected_line_count: 22
    actual_line_count: 22
    line_drift_detected: false
    map_match: true
  changes:
    - id: "rt_change_001"
      yaml_path: "scenes[0].elements[0].text"
      target_type: "element_text"
      scene_id: "scene_001"
      element_index: 0
      line_start: 6
      line_end: 6
      original_text: "Original action."
      new_text: "Edited action."
      normalized_text: "Edited action."
      action: "applied"
      safe_field: true
  issues: []
  metadata_update:
    semantic_fields_stale: true
    roundtrip:
      imported_at: "2026-06-05"
      fountain_file: "examples/output/generated_screenplay.fountain"
      map_file: "examples/output/generated_screenplay.fountain.map.json"
      applied_changes: 1
```

Report status:

- `applied`: at least one change applied and no skipped or blocking issues.
- `partial`: some safe changes applied and some regions skipped.
- `skipped`: no changes applied, but no global blocking issue.
- `blocked`: no changes applied because map or line drift makes import unsafe.
- `dry_run`: report generated without writing synced YAML.

## Metadata Update

If any text is synced back into screenplay YAML, the importer may add metadata:

```yaml
metadata:
  semantic_fields_stale: true
  roundtrip:
    imported_at: "2026-06-05"
    fountain_file: "examples/output/generated_screenplay.fountain"
    map_file: "examples/output/generated_screenplay.fountain.map.json"
    applied_changes: 1
```

This is allowed because `schemas/screenplay.schema.json` permits additional
metadata properties. Stage 7A does not modify the screenplay schema.

`semantic_fields_stale: true` means prose changed after beat generation, so
semantic fields such as beat objectives, conflict, stakes, turns, and
externalized actions may need regeneration or review. The importer must not
update those fields itself.

## Stage 7 Implementation Files

Stage 7B adds the importer core:

- `src/novel2script/importers/__init__.py`
- `src/novel2script/importers/fountain_importer.py`
- `tests/test_fountain_importer.py`

Stage 7C adds CLI and sample outputs:

- `src/novel2script/cli.py`
- `tests/test_fountain_roundtrip_cli.py`
- `examples/output/generated_screenplay_roundtrip.yaml`
- `examples/output/generated_screenplay_roundtrip_report.yaml`

## Import CLI

Run limited Fountain import:

```bash
python -m novel2script.cli import-fountain \
  --screenplay examples/output/generated_screenplay.yaml \
  --fountain examples/output/generated_screenplay.fountain \
  --map examples/output/generated_screenplay.fountain.map.json \
  --out examples/output/generated_screenplay_roundtrip.yaml \
  --report examples/output/generated_fountain_roundtrip_report.yaml
```

`export-fountain` keeps its existing `--map` option. The importer reads that
sidecar map through its own `--map` option. Input files are required; missing
files return a non-zero CLI exit code. Unsafe mapped edits are reported in the
roundtrip report and do not silently mutate YAML.

Stage 7C sample generation uses a temporary copy of the exported Fountain file
and temporary map, edits one mapped line, then writes:

- `examples/output/generated_screenplay_roundtrip.yaml`
- `examples/output/generated_screenplay_roundtrip_report.yaml`

The original `examples/output/generated_screenplay.fountain` is not modified.

## Stage 7B Test Plan

Tests should cover:

- Heading text edit syncs to `scenes[i].heading`.
- Action text edit syncs to `scenes[i].elements[j].text`.
- Parenthetical outer parentheses are removed before sync.
- Dialogue character cue is ignored and only dialogue text is synced.
- Transition text sync does not mutate semantic fields.
- Line insertion or deletion causes `line_drift` and blocks import.
- New scene or element in Fountain is skipped or blocked, not guessed.
- Unsafe map path is reported and not applied.
- `source_trace`, `beats`, `characters`, `adaptation_policy`, and existing
  `ai_tags` facts remain unchanged.
- Applied text changes add `metadata.semantic_fields_stale: true`.
- No LLM or HTTP calls.

## Gate For Stage 7A

Stage 7A passes if:

- Limited roundtrip scope is documented.
- Current sidecar map shape is documented.
- Safe and forbidden YAML fields are explicit.
- Drift and mismatch behavior is explicit.
- Roundtrip report schema is defined.
- No importer code, full Fountain parser, LLM integration, or screenplay schema
  modification is added.
