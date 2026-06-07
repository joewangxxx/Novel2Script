from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "test1_sanguo_story_map.merged.yaml"
OUTLINE = ROOT / "examples" / "output" / "test1_sanguo_outline.yaml"
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_run_agent_beat_dramaturgy_cli_writes_outputs(tmp_path):
    out_path = tmp_path / "beat_dramaturgy.yaml"
    run_log_path = tmp_path / "beat_dramaturgy.run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "beat-dramaturgy-agent",
            "--screenplay",
            str(SCREENPLAY),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert out_path.exists()
    assert run_log_path.exists()
    doc = _load_yaml(out_path)
    schema = json.loads(
        (ROOT / "schemas" / "beat_dramaturgy_agent_candidates.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(doc)
    assert doc["beat_dramaturgy_agent_candidates"]["candidates"]
    assert "stored_prompt: false" in run_log_path.read_text(encoding="utf-8")


def test_run_agent_source_fidelity_cli_writes_outputs(tmp_path):
    out_path = tmp_path / "source_fidelity.yaml"
    run_log_path = tmp_path / "source_fidelity.run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "source-fidelity-reviewer",
            "--story-map",
            str(STORY_MAP),
            "--outline",
            str(OUTLINE),
            "--screenplay",
            str(SCREENPLAY),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert out_path.exists()
    assert run_log_path.exists()
    doc = _load_yaml(out_path)
    schema = json.loads(
        (ROOT / "schemas" / "source_fidelity_reviewer_candidates.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(doc)
    assert doc["source_fidelity_reviewer_candidates"]["candidates"]


def test_run_agent_yaml_repair_cli_writes_outputs(tmp_path):
    out_path = tmp_path / "yaml_repair.yaml"
    run_log_path = tmp_path / "yaml_repair.run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "yaml-repair-agent",
            "--screenplay",
            str(SCREENPLAY),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert out_path.exists()
    assert run_log_path.exists()
    doc = _load_yaml(out_path)
    schema = json.loads(
        (ROOT / "schemas" / "yaml_repair_agent_candidates.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(doc)
    assert doc["yaml_repair_agent_candidates"]["candidates"]


def test_run_agent_deepseek_reviewer_cli_requires_inputs(tmp_path):
    # Missing --screenplay for yaml-repair-agent
    exit_code = main(
        [
            "run-agent",
            "yaml-repair-agent",
            "--out",
            str(tmp_path / "out.yaml"),
            "--run-log",
            str(tmp_path / "run.yaml"),
            "--dry-run",
        ]
    )
    assert exit_code != 0
