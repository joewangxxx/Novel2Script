import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main
from novel2script.quality.llm_evaluator import run_llm_quality_evaluator
from novel2script.quality.quality_report import build_quality_report


ROOT = Path(__file__).resolve().parents[1]
QUALITY_SCHEMA = ROOT / "schemas" / "quality_report.schema.json"
SAMPLE_NOVEL = ROOT / "examples" / "input" / "sample_novel_3_chapters.md"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_llm_quality_evaluator_dry_run(tmp_path: Path) -> None:
    run_log_path = tmp_path / "quality_run_log.yaml"
    screenplay = {"metadata": {}, "scenes": []}

    scores = run_llm_quality_evaluator(
        screenplay,
        dry_run=True,
        run_log_path=run_log_path,
    )

    assert "dialogue_naturalness" in scores
    assert "character_goal_clarity" in scores
    assert "dramatic_conflict_intensity" in scores
    
    assert scores["dialogue_naturalness"]["score"] == 92
    assert scores["character_goal_clarity"]["score"] == 88
    assert scores["dramatic_conflict_intensity"]["score"] == 85

    assert run_log_path.exists()
    log_data = _load_yaml(run_log_path)
    assert "notes" in log_data


def test_quality_report_conforms_to_schema_with_llm_scores() -> None:
    screenplay = {"metadata": {}}
    validation_report = {
        "schema_validity": {"passed": True, "errors": []},
        "source_coverage": {
            "score": 1.0,
            "checked_targets": 10,
            "missing_targets": [],
            "invalid_targets": [],
        },
        "beat_completeness": {"score": 1.0, "total_beats": 3, "incomplete_beats": []},
        "reference_integrity": {"passed": True, "missing_references": []},
        "overall_passed": True,
    }
    review_report = {
        "review_report": {
            "schema_version": "0.1.0",
            "source_screenplay": "screenplay.yaml",
            "generated_at": "2026-06-05",
            "reviewers": [
                "character_consistency",
                "pacing",
                "dialogue_naturalness",
                "shootability",
            ],
            "reviewer_results": [
                {"reviewer": "character_consistency", "status": "completed", "issues_found": 0},
                {"reviewer": "pacing", "status": "completed", "issues_found": 0},
                {"reviewer": "dialogue_naturalness", "status": "completed", "issues_found": 0},
                {"reviewer": "shootability", "status": "completed", "issues_found": 0},
            ],
            "summary": {"total_issues": 0, "blocking": False},
            "issues": [],
        }
    }
    
    llm_scores = {
        "dialogue_naturalness": {"score": 90, "summary": "N1", "reasoning": "R1"},
        "character_goal_clarity": {"score": 85, "summary": "N2", "reasoning": "R2"},
        "dramatic_conflict_intensity": {"score": 80, "summary": "N3", "reasoning": "R3"},
    }

    report = build_quality_report(
        screenplay,
        validation_report,
        review_report,
        llm_scores=llm_scores,
    )

    schema = json.loads(QUALITY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(report)
    
    quality = report["quality_report"]
    dimensions = {item["id"]: item for item in quality["dimensions"]}
    
    assert "character_goal_clarity" in dimensions
    assert "dramatic_conflict_intensity" in dimensions
    assert "dialogue_naturalness" in dimensions

    assert dimensions["dialogue_naturalness"]["score"] == 90
    assert dimensions["character_goal_clarity"]["score"] == 85
    assert dimensions["dramatic_conflict_intensity"]["score"] == 80


def test_evaluate_quality_cli_with_run_log(tmp_path: Path) -> None:
    screenplay_file = tmp_path / "screenplay.yaml"
    validation_file = tmp_path / "validation.yaml"
    review_file = tmp_path / "review.yaml"
    out_file = tmp_path / "quality_report.yaml"
    run_log_file = tmp_path / "quality_run_log.yaml"

    yaml.safe_dump({"metadata": {}}, screenplay_file.open("w", encoding="utf-8"))
    yaml.safe_dump(
        {
            "schema_validity": {"passed": True},
            "source_coverage": {"score": 1.0},
            "beat_completeness": {"score": 1.0},
            "reference_integrity": {"passed": True},
        },
        validation_file.open("w", encoding="utf-8"),
    )
    yaml.safe_dump(
        {
            "review_report": {
                "reviewer_results": [],
                "summary": {"total_issues": 0, "blocking": False},
            }
        },
        review_file.open("w", encoding="utf-8"),
    )

    exit_code = main(
        [
            "evaluate-quality",
            "--screenplay",
            str(screenplay_file),
            "--validation-report",
            str(validation_file),
            "--review-report",
            str(review_file),
            "--out",
            str(out_file),
            "--run-log",
            str(run_log_file),
        ]
    )

    assert exit_code == 0
    assert out_file.exists()
    assert run_log_file.exists()
    
    report_data = _load_yaml(out_file)
    schema = json.loads(QUALITY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(report_data)


def test_pipeline_e2e_incorporates_llm_scores(tmp_path: Path) -> None:
    out_dir = tmp_path / "pipeline_out"
    
    exit_code = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    
    quality_file = out_dir / "quality_report.yaml"
    assert quality_file.exists()
    
    quality_data = _load_yaml(quality_file)
    schema = json.loads(QUALITY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(quality_data)
    
    dimensions = {item["id"]: item for item in quality_data["quality_report"]["dimensions"]}
    assert "character_goal_clarity" in dimensions
    assert "dramatic_conflict_intensity" in dimensions
    assert dimensions["character_goal_clarity"]["score"] == 88
    assert dimensions["dramatic_conflict_intensity"]["score"] == 85
