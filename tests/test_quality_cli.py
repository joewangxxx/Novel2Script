import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "generated_screenplay_roundtrip.yaml"
VALIDATION_REPORT = ROOT / "examples" / "output" / "generated_screenplay_validation_report.yaml"
REVIEW_REPORT = ROOT / "examples" / "output" / "generated_review_report.yaml"
ROUNDTRIP_REPORT = ROOT / "examples" / "output" / "generated_screenplay_roundtrip_report.yaml"
QUALITY_SCHEMA = ROOT / "schemas" / "quality_report.schema.json"


def test_evaluate_quality_cli_writes_yaml_and_markdown(tmp_path):
    quality_path = tmp_path / "nested" / "quality_report.yaml"
    markdown_path = tmp_path / "nested" / "quality_dashboard.md"

    exit_code = main(
        [
            "evaluate-quality",
            "--screenplay",
            str(SCREENPLAY),
            "--validation-report",
            str(VALIDATION_REPORT),
            "--review-report",
            str(REVIEW_REPORT),
            "--roundtrip-report",
            str(ROUNDTRIP_REPORT),
            "--out",
            str(quality_path),
            "--markdown",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    data = yaml.safe_load(quality_path.read_text(encoding="utf-8"))
    schema = json.loads(QUALITY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    assert markdown_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Quality Dashboard" in markdown
    assert "semantic_staleness" in markdown
    assert data["quality_report"]["source_artifacts"]["quality_dashboard_markdown"] == str(markdown_path)


def test_evaluate_quality_cli_returns_nonzero_for_missing_required_input(tmp_path):
    quality_path = tmp_path / "quality_report.yaml"

    exit_code = main(
        [
            "evaluate-quality",
            "--screenplay",
            str(tmp_path / "missing.yaml"),
            "--validation-report",
            str(VALIDATION_REPORT),
            "--review-report",
            str(REVIEW_REPORT),
            "--out",
            str(quality_path),
        ]
    )

    assert exit_code != 0
    assert not quality_path.exists()
