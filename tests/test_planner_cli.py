import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
OUTLINE_SCHEMA = ROOT / "schemas" / "outline.schema.json"
CHARACTER_BIBLE_SCHEMA = ROOT / "schemas" / "character_bible.schema.json"


def test_build_outline_cli_writes_schema_valid_yaml(tmp_path):
    output_path = tmp_path / "nested" / "outline.yaml"

    exit_code = main(
        [
            "build-outline",
            str(STORY_MAP),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    schema = json.loads(OUTLINE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    outline = data["outline"]
    assert outline["source_story_map"]["story_map_file"] == str(STORY_MAP)
    assert outline["logline"]["text"]
    assert outline["scene_plan"]


def test_build_character_bible_cli_writes_schema_valid_yaml(tmp_path):
    output_path = tmp_path / "nested" / "character_bible.yaml"

    exit_code = main(
        [
            "build-character-bible",
            str(STORY_MAP),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    schema = json.loads(CHARACTER_BIBLE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    bible = data["character_bible"]
    assert bible["source_story_map"]["story_map_file"] == str(STORY_MAP)
    assert bible["characters"]
    assert all(character["locked"] is False for character in bible["characters"])


def test_planner_cli_returns_nonzero_for_missing_story_map(tmp_path):
    output_path = tmp_path / "outline.yaml"

    exit_code = main(
        [
            "build-outline",
            str(tmp_path / "missing.yaml"),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code != 0
    assert not output_path.exists()
