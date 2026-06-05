import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.reviewers.review_report import build_review_report


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "generated_screenplay.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "generated_character_bible.yaml"
REVIEW_SCHEMA = ROOT / "schemas" / "review_report.schema.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_build_review_report_matches_schema_for_generated_screenplay():
    report = build_review_report(
        _load_yaml(SCREENPLAY),
        character_bible_doc=_load_yaml(CHARACTER_BIBLE),
        source_screenplay="examples/output/generated_screenplay.yaml",
        source_artifacts={
            "character_bible": "examples/output/generated_character_bible.yaml",
        },
        generated_at="2026-06-05",
    )
    schema = json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(report)

    review_report = report["review_report"]
    assert review_report["schema_version"] == "0.1.0"
    assert review_report["reviewers"] == [
        "character_consistency",
        "pacing",
        "dialogue_naturalness",
        "shootability",
    ]
    assert len(review_report["reviewer_results"]) == 4
    assert review_report["summary"]["total_issues"] == len(review_report["issues"])


def test_build_review_report_assigns_stable_global_issue_ids_and_counts():
    screenplay = _load_yaml(SCREENPLAY)
    screenplay["scenes"][0]["beats"][0]["externalized_action"] = ""
    report = build_review_report(screenplay, generated_at="2026-06-05")
    issues = report["review_report"]["issues"]

    assert [issue["id"] for issue in issues] == [
        f"issue_{index:03d}" for index in range(1, len(issues) + 1)
    ]
    assert all(issue["target_id"] == issue["target"]["id"] for issue in issues)
    assert all(issue["requires_human_approval"] is True for issue in issues)
    assert report["review_report"]["summary"]["by_severity"]["high"] >= 1
