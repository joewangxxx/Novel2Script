# Phase 2: Deterministic Validation and Fountain Export

Phase 2 adds a small, reproducible toolchain for checking an existing
Novel2Script screenplay YAML file and exporting it to Fountain. It does not
call any LLM service and does not generate screenplay content from a novel.

## Install Dependencies

```bash
python -m pip install -e ".[dev]"
```

Runtime dependencies are intentionally minimal:

- `PyYAML`
- `jsonschema`

Development tests use:

- `pytest`

## Validate A Screenplay YAML

```bash
python -m novel2script.cli validate examples/output/sample_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_validation_report.yaml
```

The generated report contains:

- `schema_validity`
- `source_coverage`
- `beat_completeness`
- `reference_integrity`
- `overall_passed`

## Export Fountain

```bash
python -m novel2script.cli export-fountain examples/output/sample_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
```

The exporter writes a Fountain file from the existing YAML structure:

- `scene.heading` becomes the Fountain scene heading.
- `action` elements become action paragraphs.
- `dialogue` elements become character cue plus dialogue text.
- `parenthetical` elements become parentheticals.
- `transition` elements become transition lines.

The exporter intentionally omits internal adaptation fields such as
`objective`, `conflict`, `stakes`, `source_trace`, and `ai_tags`.

## Sidecar Map

When `--map` is provided, the exporter writes a JSON sidecar map. The map
tracks at least scene headings and element text ranges back to YAML paths.
Elements without explicit IDs are tracked by `element_index`.

## Run Tests

```bash
pytest
```

The test suite covers schema validation, source trace validation, beat
completeness validation, character reference validation, Fountain export, and
sidecar map generation.

## Explicitly Out Of Scope

Phase 2 still does not implement:

- OpenAI, Claude, Gemini, or any other real LLM integration.
- Complete novel parsing.
- Automatic full screenplay generation.
- Multi-agent review or orchestration.
- Fountain to YAML round-tripping.
- Web frontend or backend APIs.
