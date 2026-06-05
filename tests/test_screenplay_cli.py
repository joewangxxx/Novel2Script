import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
OUTLINE = ROOT / "examples" / "output" / "generated_outline.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "generated_character_bible.yaml"
SCREENPLAY_SCHEMA = ROOT / "schemas" / "screenplay.schema.json"


def test_build_screenplay_cli_writes_schema_valid_yaml(tmp_path):
    output_path = tmp_path / "nested" / "screenplay.yaml"

    exit_code = main(
        [
            "build-screenplay",
            "--story-map",
            str(STORY_MAP),
            "--outline",
            str(OUTLINE),
            "--character-bible",
            str(CHARACTER_BIBLE),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    schema = json.loads(SCREENPLAY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    assert data["source"]["story_map_file"] == str(STORY_MAP)
    assert data["source"]["outline_file"] == str(OUTLINE)
    assert data["source"]["character_bible_file"] == str(CHARACTER_BIBLE)
    assert data["characters"]
    assert data["scenes"]
    assert all(scene["beats"] and scene["elements"] for scene in data["scenes"])


def test_build_screenplay_cli_output_validates_and_exports_to_fountain(tmp_path):
    screenplay_path = tmp_path / "screenplay.yaml"
    report_path = tmp_path / "validation.yaml"
    fountain_path = tmp_path / "screenplay.fountain"
    map_path = tmp_path / "screenplay.fountain.map.json"

    build_exit = main(
        [
            "build-screenplay",
            "--story-map",
            str(STORY_MAP),
            "--outline",
            str(OUTLINE),
            "--character-bible",
            str(CHARACTER_BIBLE),
            "--out",
            str(screenplay_path),
        ]
    )
    validate_exit = main(
        [
            "validate",
            str(screenplay_path),
            "--schema",
            str(SCREENPLAY_SCHEMA),
            "--out",
            str(report_path),
        ]
    )
    export_exit = main(
        [
            "export-fountain",
            str(screenplay_path),
            "--out",
            str(fountain_path),
            "--map",
            str(map_path),
        ]
    )

    assert build_exit == 0
    assert validate_exit == 0
    assert export_exit == 0
    assert yaml.safe_load(report_path.read_text(encoding="utf-8"))["overall_passed"] is True
    assert fountain_path.read_text(encoding="utf-8").strip()
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))
    assert sidecar["mappings"]


def test_build_screenplay_cli_returns_nonzero_for_missing_input(tmp_path):
    output_path = tmp_path / "screenplay.yaml"

    exit_code = main(
        [
            "build-screenplay",
            "--story-map",
            str(tmp_path / "missing_story_map.yaml"),
            "--outline",
            str(OUTLINE),
            "--character-bible",
            str(CHARACTER_BIBLE),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code != 0
    assert not output_path.exists()
