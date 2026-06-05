# QA Report

## Scope

Stage 3 deterministic novel parsing QA covered the parser, `parse-novel` CLI,
generated `story_map` sample output, Phase 3 documentation, and Phase 2
regression commands. The QA pass did not add new product behavior, did not
change the `story_map` schema contract, did not add LLM integration, and did not
implement Agent or Web API workflows.

## Commands Run

```bash
python -m pytest
python -m novel2script.cli parse-novel examples/input/sample_novel_3_chapters.md --out examples/output/generated_story_map.yaml
python -m novel2script.cli validate examples/output/sample_screenplay.yaml --schema schemas/screenplay.schema.json --out examples/output/generated_validation_report.yaml
python -m novel2script.cli export-fountain examples/output/sample_screenplay.yaml --out examples/output/generated_screenplay.fountain --map examples/output/generated_screenplay.fountain.map.json
git status --short
```

Additional structural check:

```bash
python - <<'PY'
from pathlib import Path
import yaml

path = Path("examples/output/generated_story_map.yaml")
assert path.exists()
assert path.stat().st_size > 0
data = yaml.safe_load(path.read_text(encoding="utf-8"))
story_map = data["story_map"]
assert len(story_map["chapters"]) >= 3
assert all(chapter.get("id") for chapter in story_map["chapters"])
assert all(item.get("source_trace") for item in story_map["key_events"])
assert all(item.get("source_trace") for item in story_map["psychological_passages"])
assert all(item.get("source_trace") or item.get("reason") for item in story_map["uncertainties"])
PY
```

## Results

- `python -m pytest`: passed, 15 tests collected and 15 passed.
- `parse-novel` CLI: passed, regenerated `examples/output/generated_story_map.yaml`.
- `validate` CLI regression: passed, regenerated `examples/output/generated_validation_report.yaml`.
- `export-fountain` CLI regression: passed, regenerated `examples/output/generated_screenplay.fountain` and sidecar map.
- `generated_story_map.yaml` structure: passed. File exists, is non-empty, contains 3 chapters, every chapter has an `id`, and `key_events`, `psychological_passages`, and `uncertainties` include source trace coverage as required.

## Generated Artifacts

- `examples/output/generated_story_map.yaml`
- `examples/output/generated_validation_report.yaml`
- `examples/output/generated_screenplay.fountain`
- `examples/output/generated_screenplay.fountain.map.json`

## Tests Not Run

- Static type checking was not run because the project does not configure a type checker.
- Linting was not run because the project does not configure a lint command.
- External model, Agent, Web API, and Fountain round-trip tests were not run because those capabilities are outside Stage 3 scope.

## Risks

- Character, location, prop, event, timeline, and psychological passage extraction remain heuristic and may produce false positives or miss subtle text cues.
- `story_map` is still marked as contract draft in the blackboard; schema changes after freeze must go through `docs/architecture/change-requests/`.
- The parser intentionally avoids full NLP and LLM understanding, so downstream phases must treat low-confidence entries and `uncertainties` as review signals.

## Gate Decision

Passed. Stage 3 deterministic novel parsing meets the current parser, CLI,
sample output, documentation, and regression requirements. The project is ready
for Stage 4 outline and character bible work, subject to normal contract review
governance.
