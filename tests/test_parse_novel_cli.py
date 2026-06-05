from pathlib import Path

import yaml

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_NOVEL = ROOT / "examples" / "input" / "sample_novel_3_chapters.md"


def test_parse_novel_cli_writes_story_map_yaml(tmp_path):
    output_path = tmp_path / "nested" / "story_map.yaml"

    exit_code = main(
        [
            "parse-novel",
            str(SAMPLE_NOVEL),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    output_text = output_path.read_text(encoding="utf-8")
    assert "&id" not in output_text
    assert "*id" not in output_text
    data = yaml.safe_load(output_text)
    story_map = data["story_map"]
    assert story_map["source"]["input_file"] == str(SAMPLE_NOVEL)
    assert story_map["source"]["chapter_count"] == 3
    assert story_map["chapters"]
    assert story_map["characters_detected"]
    assert story_map["locations_detected"]
    assert story_map["props_detected"]
    assert story_map["key_events"]
    assert story_map["timeline"]
    assert story_map["psychological_passages"]
    assert story_map["uncertainties"]


def test_parse_novel_cli_returns_nonzero_for_missing_input(tmp_path):
    output_path = tmp_path / "story_map.yaml"

    exit_code = main(
        [
            "parse-novel",
            str(tmp_path / "missing.md"),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code != 0
    assert not output_path.exists()
