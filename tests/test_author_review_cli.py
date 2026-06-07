import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"
QUALITY_REPORT = ROOT / "examples" / "output" / "test1_sanguo_quality_report.yaml"
QUALITY_DASHBOARD = ROOT / "examples" / "output" / "test1_sanguo_quality_dashboard.md"
AUTHOR_REVIEW_SCHEMA = ROOT / "schemas" / "author_review.schema.json"


def test_prepare_author_review_cli_writes_packet_and_schema_valid_decisions(tmp_path):
    packet_path = tmp_path / "nested" / "author_review_packet.md"
    decisions_path = tmp_path / "nested" / "author_review_decisions.yaml"

    exit_code = main(
        [
            "prepare-author-review",
            "--screenplay",
            str(SCREENPLAY),
            "--review-report",
            str(REVIEW_REPORT),
            "--quality-report",
            str(QUALITY_REPORT),
            "--quality-dashboard",
            str(QUALITY_DASHBOARD),
            "--packet",
            str(packet_path),
            "--decisions",
            str(decisions_path),
        ]
    )

    assert exit_code == 0
    packet = packet_path.read_text(encoding="utf-8")
    assert "# Author Review Packet" in packet
    assert "ready_for_author_review" in packet
    assert "raw_response" not in packet

    decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
    schema = json.loads(AUTHOR_REVIEW_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(decisions)
    assert decisions["author_review_decisions"]["source_artifacts"]["screenplay"] == str(SCREENPLAY)


def test_prepare_author_review_cli_returns_nonzero_for_missing_input(tmp_path):
    packet_path = tmp_path / "author_review_packet.md"
    decisions_path = tmp_path / "author_review_decisions.yaml"

    exit_code = main(
        [
            "prepare-author-review",
            "--screenplay",
            str(tmp_path / "missing.yaml"),
            "--review-report",
            str(REVIEW_REPORT),
            "--quality-report",
            str(QUALITY_REPORT),
            "--quality-dashboard",
            str(QUALITY_DASHBOARD),
            "--packet",
            str(packet_path),
            "--decisions",
            str(decisions_path),
        ]
    )

    assert exit_code != 0
    assert not packet_path.exists()
    assert not decisions_path.exists()
