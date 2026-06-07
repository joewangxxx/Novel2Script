import json
from pathlib import Path

from jsonschema import Draft202012Validator

from novel2script.io import read_yaml
from novel2script.reviewers.author_review import (
    build_author_review_decisions_template,
    render_author_review_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"
QUALITY_REPORT = ROOT / "examples" / "output" / "test1_sanguo_quality_report.yaml"
QUALITY_DASHBOARD = ROOT / "examples" / "output" / "test1_sanguo_quality_dashboard.md"
AUTHOR_REVIEW_SCHEMA = ROOT / "schemas" / "author_review.schema.json"


def test_render_author_review_packet_summarizes_quality_without_full_screenplay():
    screenplay = read_yaml(SCREENPLAY)
    review_report = read_yaml(REVIEW_REPORT)
    quality_report = read_yaml(QUALITY_REPORT)
    dashboard = QUALITY_DASHBOARD.read_text(encoding="utf-8")

    packet = render_author_review_packet(
        screenplay,
        review_report,
        quality_report,
        dashboard,
        source_paths={
            "screenplay": str(SCREENPLAY),
            "review_report": str(REVIEW_REPORT),
            "quality_report": str(QUALITY_REPORT),
            "quality_dashboard": str(QUALITY_DASHBOARD),
        },
    )

    assert "# Author Review Packet" in packet
    assert str(SCREENPLAY) in packet
    assert "ready_for_author_review" in packet
    assert "dialogue_naturalness" in packet
    assert "Add dialogue review after dialogue exists in the draft." in packet
    assert "Structure Decision" in packet
    assert "Character Decision" in packet
    assert "Beat Decision" in packet
    assert "Dialogue Decision" in packet
    assert "raw_response" not in packet
    assert "provider body" not in packet.lower()
    assert len(packet) < len(json.dumps(screenplay, ensure_ascii=False))


def test_author_review_decisions_template_is_schema_valid():
    decisions = build_author_review_decisions_template(
        source_paths={
            "screenplay": str(SCREENPLAY),
            "review_report": str(REVIEW_REPORT),
            "quality_report": str(QUALITY_REPORT),
            "quality_dashboard": str(QUALITY_DASHBOARD),
        },
        reviewer="author",
        reviewed_at="2026-06-06T18:30:00+08:00",
    )

    schema = json.loads(AUTHOR_REVIEW_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(decisions)
    review = decisions["author_review_decisions"]
    assert review["structure_decision"]["decision"] == "approve"
    assert review["dialogue_decision"]["decision"] == "request_dialogue_draft"
    assert review["next_stage_authorization"]["decision"] == "kimi_dialogue_draft"
    assert review["quality_decision"]["human_approval_required"] is True
