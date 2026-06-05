import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "generated_screenplay.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "generated_character_bible.yaml"
REVIEW_SCHEMA = ROOT / "schemas" / "review_report.schema.json"


def test_review_screenplay_cli_writes_schema_valid_report(tmp_path):
    output_path = tmp_path / "nested" / "review_report.yaml"

    exit_code = main(
        [
            "review-screenplay",
            "--screenplay",
            str(SCREENPLAY),
            "--character-bible",
            str(CHARACTER_BIBLE),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    schema = json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    report = data["review_report"]
    assert report["source_screenplay"] == str(SCREENPLAY)
    assert report["source_artifacts"]["character_bible"] == str(CHARACTER_BIBLE)
    assert report["reviewers"] == [
        "character_consistency",
        "pacing",
        "dialogue_naturalness",
        "shootability",
    ]
    assert report["summary"]["total_issues"] == len(report["issues"])
    assert all(issue["suggested_patch"]["operation"] == "note_only" for issue in report["issues"])


def test_review_screenplay_cli_returns_nonzero_for_missing_screenplay(tmp_path):
    output_path = tmp_path / "review_report.yaml"

    exit_code = main(
        [
            "review-screenplay",
            "--screenplay",
            str(tmp_path / "missing_screenplay.yaml"),
            "--character-bible",
            str(CHARACTER_BIBLE),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code != 0
    assert not output_path.exists()
