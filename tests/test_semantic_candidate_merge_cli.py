from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
SEMANTIC_CANDIDATES = ROOT / "examples" / "output" / "generated_semantic_candidates.yaml"
STORY_MAP_SCHEMA = ROOT / "schemas" / "story_map.schema.json"
MERGE_REPORT_SCHEMA = ROOT / "schemas" / "semantic_candidate_merge_report.schema.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _decisions_doc() -> dict:
    approval = {
        "approved": True,
        "reviewer_id": "author",
        "approved_at": "2026-06-06T10:00:00+08:00",
    }
    return {
        "semantic_candidate_decisions": {
            "schema_version": "0.1.0",
            "source_story_map": str(STORY_MAP),
            "source_semantic_candidates": str(SEMANTIC_CANDIDATES),
            "reviewed_by": "author",
            "reviewed_at": "2026-06-06T10:00:00+08:00",
            "decisions": [
                {
                    "decision_id": "dec_001",
                    "candidate_id": "semcand_001",
                    "decision": "accept",
                    "target_story_map_field": "key_events",
                    "human_approval": approval,
                },
                {
                    "decision_id": "dec_002",
                    "candidate_id": "semcand_002",
                    "decision": "reject",
                    "target_story_map_field": "psychological_passages",
                    "human_approval": {
                        **approval,
                        "approved": False,
                    },
                },
                {
                    "decision_id": "dec_003",
                    "candidate_id": "semcand_003",
                    "decision": "edit",
                    "target_story_map_field": "timeline",
                    "edited_fields": {
                        "label": "人工确认的连续三晚",
                        "time_text": "人工确认的连续三晚",
                    },
                    "human_approval": approval,
                },
            ],
        }
    }


def test_merge_semantic_candidates_cli_writes_outputs_and_preserves_input(
    tmp_path: Path,
) -> None:
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(decisions_path, _decisions_doc())
    before = STORY_MAP.read_bytes()

    exit_code = main(
        [
            "merge-semantic-candidates",
            "--story-map",
            str(STORY_MAP),
            "--semantic-candidates",
            str(SEMANTIC_CANDIDATES),
            "--decisions",
            str(decisions_path),
            "--out",
            str(out_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert STORY_MAP.read_bytes() == before
    Draft202012Validator(_load_yaml(STORY_MAP_SCHEMA)).validate(_load_yaml(out_path))
    report = _load_yaml(report_path)
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)
    assert report["semantic_candidate_merge_report"]["status"] == "success"


def test_merge_semantic_candidates_cli_returns_nonzero_for_blocked_merge(
    tmp_path: Path,
) -> None:
    decisions = _decisions_doc()
    decisions["semantic_candidate_decisions"]["decisions"][0]["human_approval"][
        "approved"
    ] = False
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(decisions_path, decisions)
    out_path.write_text("stale output", encoding="utf-8")

    exit_code = main(
        [
            "merge-semantic-candidates",
            "--story-map",
            str(STORY_MAP),
            "--semantic-candidates",
            str(SEMANTIC_CANDIDATES),
            "--decisions",
            str(decisions_path),
            "--out",
            str(out_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code != 0
    assert not out_path.exists()
    report = _load_yaml(report_path)
    assert report["semantic_candidate_merge_report"]["status"] == "blocked"
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)
