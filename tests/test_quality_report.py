import json
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.quality.quality_report import (
    build_quality_report,
    render_quality_dashboard,
)


ROOT = Path(__file__).resolve().parents[1]
QUALITY_SCHEMA = ROOT / "schemas" / "quality_report.schema.json"


def _screenplay() -> dict:
    return {"metadata": {}}


def _validation_report() -> dict:
    return {
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


def _review_report() -> dict:
    return {
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
                {
                    "reviewer": "character_consistency",
                    "status": "completed",
                    "issues_found": 0,
                    "notes": [],
                },
                {"reviewer": "pacing", "status": "completed", "issues_found": 0, "notes": []},
                {
                    "reviewer": "dialogue_naturalness",
                    "status": "skipped",
                    "issues_found": 0,
                    "notes": ["No dialogue or parenthetical elements to review."],
                },
                {"reviewer": "shootability", "status": "completed", "issues_found": 0, "notes": []},
            ],
            "summary": {
                "total_issues": 0,
                "by_severity": {"low": 0, "medium": 0, "high": 0},
                "blocking": False,
                "requires_human_approval_count": 0,
            },
            "issues": [],
        }
    }


def _roundtrip_report() -> dict:
    return {
        "fountain_roundtrip_report": {
            "schema_version": "0.1.0",
            "source_yaml": "screenplay.yaml",
            "fountain_file": "edited.fountain",
            "map_file": "screenplay.fountain.map.json",
            "generated_at": "2026-06-05",
            "status": "applied",
            "summary": {
                "mapped_regions": 2,
                "changed_regions": 1,
                "applied_changes": 1,
                "skipped_changes": 0,
                "blocking_issues": 0,
            },
            "line_policy": {
                "expected_line_count": 12,
                "actual_line_count": 12,
                "line_drift_detected": False,
                "map_match": True,
            },
            "changes": [],
            "issues": [],
        }
    }


def _dimension(report: dict, dimension_id: str) -> dict:
    return next(
        item
        for item in report["quality_report"]["dimensions"]
        if item["id"] == dimension_id
    )


def test_build_quality_report_aggregates_existing_reports_and_matches_schema():
    report = build_quality_report(
        _screenplay(),
        _validation_report(),
        _review_report(),
        roundtrip_report_doc=_roundtrip_report(),
        source_paths={
            "screenplay": "screenplay.yaml",
            "validation_report": "validation.yaml",
            "review_report": "review.yaml",
            "fountain_roundtrip_report": "roundtrip.yaml",
            "quality_report_yaml": "quality.yaml",
            "quality_dashboard_markdown": "quality.md",
        },
    )

    schema = json.loads(QUALITY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(report)
    quality = report["quality_report"]
    assert quality["overall_readiness"]["status"] == "pass"
    assert quality["overall_readiness"]["decision"] == "ready_for_author_review"
    assert quality["overall_readiness"]["score"] >= 90
    assert {item["id"] for item in quality["dimensions"]} == {
        "schema_validity",
        "source_trace_coverage",
        "beat_completeness",
        "reference_integrity",
        "character_consistency",
        "pacing",
        "dialogue_naturalness",
        "shootability",
        "fountain_roundtrip_safety",
        "semantic_staleness",
        "character_goal_clarity",
        "dramatic_conflict_intensity",
        "overall_readiness",
    }
    assert _dimension(report, "schema_validity")["score"] == 100
    assert _dimension(report, "dialogue_naturalness")["status"] == "warn"


def test_quality_report_hard_gates_block_overall_readiness():
    validation = _validation_report()
    validation["schema_validity"] = {
        "passed": False,
        "errors": [{"path": "scenes[0]", "message": "required field missing"}],
    }
    review = _review_report()
    review["review_report"]["summary"]["blocking"] = True
    roundtrip = _roundtrip_report()
    roundtrip["fountain_roundtrip_report"]["status"] = "blocked"
    roundtrip["fountain_roundtrip_report"]["summary"]["blocking_issues"] = 1

    report = build_quality_report(
        _screenplay(),
        validation,
        review,
        roundtrip_report_doc=roundtrip,
    )

    readiness = report["quality_report"]["overall_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["decision"] == "blocked"
    assert set(readiness["hard_gate_failures"]) >= {
        "schema_validity",
        "fountain_roundtrip_safety",
    }


def test_semantic_staleness_warns_when_screenplay_metadata_is_stale():
    screenplay = {"metadata": {"semantic_fields_stale": True}}

    report = build_quality_report(
        screenplay,
        _validation_report(),
        _review_report(),
        roundtrip_report_doc=_roundtrip_report(),
    )

    dimension = _dimension(report, "semantic_staleness")
    assert dimension["status"] == "warn"
    assert dimension["score"] == 70
    assert any(
        "semantic fields" in recommendation["action"]
        for recommendation in dimension["recommendations"]
    )


def test_render_quality_dashboard_contains_readiness_table_and_next_actions():
    report = build_quality_report(
        _screenplay(),
        _validation_report(),
        _review_report(),
        roundtrip_report_doc=_roundtrip_report(),
    )

    markdown = render_quality_dashboard(report)

    assert "# Quality Dashboard" in markdown
    assert "## Gate Decision" in markdown
    assert "| Dimension | Status | Score | Summary |" in markdown
    assert "dialogue_naturalness" in markdown
    assert "## Recommended Next Actions" in markdown
