from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "test1_sanguo_story_map.merged.yaml"
OUTLINE = ROOT / "examples" / "output" / "test1_sanguo_outline.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "test1_sanguo_character_bible.yaml"
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"
QUALITY_REPORT = ROOT / "examples" / "output" / "test1_sanguo_quality_report.yaml"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_run_agent_stage24_kimi_creative_agent_cli_writes_outputs(tmp_path):
    out_path = tmp_path / "scene_writer.yaml"
    run_log_path = tmp_path / "scene_writer.run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "scene-writer-agent",
            "--story-map",
            str(STORY_MAP),
            "--outline",
            str(OUTLINE),
            "--character-bible",
            str(CHARACTER_BIBLE),
            "--screenplay",
            str(SCREENPLAY),
            "--quality-report",
            str(QUALITY_REPORT),
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
        (ROOT / "schemas" / "scene_writer_agent_candidates.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(doc)
    assert doc["scene_writer_agent_candidates"]["candidates"]
    assert "stored_prompt: false" in run_log_path.read_text(encoding="utf-8")


def test_run_agent_stage24_kimi_creative_agent_cli_requires_inputs(tmp_path):
    exit_code = main(
        [
            "run-agent",
            "character-bible-agent",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(tmp_path / "out.yaml"),
            "--run-log",
            str(tmp_path / "run.yaml"),
            "--dry-run",
        ]
    )

    assert exit_code != 0
