from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.semantic_candidate_merge import merge_semantic_candidates


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
SEMANTIC_CANDIDATES = ROOT / "examples" / "output" / "generated_semantic_candidates.yaml"
STORY_MAP_SCHEMA = ROOT / "schemas" / "story_map.schema.json"
MERGE_REPORT_SCHEMA = ROOT / "schemas" / "semantic_candidate_merge_report.schema.json"
DECISIONS_SCHEMA = ROOT / "schemas" / "semantic_candidate_decisions.schema.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _approval(*, approved: bool = True) -> dict:
    return {
        "approved": approved,
        "reviewer_id": "author",
        "approved_at": "2026-06-06T10:00:00+08:00",
    }


def _decisions_doc() -> dict:
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
                    "reviewer_note": "Accept the event candidate.",
                    "human_approval": _approval(),
                },
                {
                    "decision_id": "dec_002",
                    "candidate_id": "semcand_002",
                    "decision": "reject",
                    "target_story_map_field": "psychological_passages",
                    "reviewer_note": "Too close to existing parser result.",
                    "human_approval": _approval(approved=False),
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
                    "reviewer_note": "Use a cleaner timeline label.",
                    "human_approval": _approval(),
                },
            ],
        }
    }


def test_merge_semantic_candidates_accepts_rejects_and_edits_with_audit(
    tmp_path: Path,
) -> None:
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(decisions_path, _decisions_doc())
    before = STORY_MAP.read_bytes()

    report = merge_semantic_candidates(
        STORY_MAP,
        SEMANTIC_CANDIDATES,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    assert STORY_MAP.read_bytes() == before
    assert report == _load_yaml(report_path)
    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "success"
    assert report_root["summary"]["accepted"] == 1
    assert report_root["summary"]["rejected"] == 1
    assert report_root["summary"]["edited"] == 1
    assert report_root["summary"]["applied_changes"] == 2

    results = {item["candidate_id"]: item for item in report_root["decisions"]}
    assert results["semcand_001"]["decision_id"] == "dec_001"
    assert results["semcand_001"]["outcome"] == "accepted"
    assert results["semcand_001"]["reviewer"] == "author"
    assert results["semcand_001"]["reviewed_at"] == "2026-06-06T10:00:00+08:00"
    assert results["semcand_001"]["source_trace_ids"] == {
        "chapter_id": "ch_001",
        "paragraph_ids": ["p_001"],
    }
    assert results["semcand_002"]["outcome"] == "rejected"
    assert "created_id" not in results["semcand_002"]
    assert results["semcand_003"]["outcome"] == "edited"

    merged = _load_yaml(out_path)
    original = _load_yaml(STORY_MAP)
    assert len(merged["story_map"]["key_events"]) == len(original["story_map"]["key_events"]) + 1
    assert len(merged["story_map"]["psychological_passages"]) == len(
        original["story_map"]["psychological_passages"]
    )
    assert len(merged["story_map"]["timeline"]) == len(original["story_map"]["timeline"]) + 1

    accepted_event = merged["story_map"]["key_events"][-1]
    assert accepted_event["id"] == "evt_007"
    assert accepted_event["source_trace"]["chapter_id"] == "ch_001"
    assert "semcand_001" in accepted_event["source_trace"]["note"]

    edited_timeline = merged["story_map"]["timeline"][-1]
    assert edited_timeline["id"] == "tl_005"
    assert edited_timeline["label"] == "人工确认的连续三晚"
    assert "source_timeline_id" not in edited_timeline

    Draft202012Validator(_load_yaml(STORY_MAP_SCHEMA)).validate(merged)
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)
    Draft202012Validator(_load_yaml(DECISIONS_SCHEMA)).validate(_load_yaml(decisions_path))


def test_merge_semantic_candidates_fails_closed_without_human_approval(
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

    report = merge_semantic_candidates(
        STORY_MAP,
        SEMANTIC_CANDIDATES,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "blocked"
    assert report_root["summary"]["blocked"] >= 1
    assert any(error["code"] == "missing_human_approval" for error in report_root["errors"])
    assert not out_path.exists()
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)


def test_merge_semantic_candidates_blocks_invalid_source_trace(
    tmp_path: Path,
) -> None:
    candidates = deepcopy(_load_yaml(SEMANTIC_CANDIDATES))
    candidates["semantic_candidates"]["candidates"][0]["source_trace_ids"][
        "chapter_id"
    ] = "ch_999"
    candidates_path = tmp_path / "bad_candidates.yaml"
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(candidates_path, candidates)
    _write_yaml(decisions_path, _decisions_doc())

    report = merge_semantic_candidates(
        STORY_MAP,
        candidates_path,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "blocked"
    assert any(error["code"] == "invalid_source_trace" for error in report_root["errors"])
    assert not out_path.exists()


def test_merge_semantic_candidates_blocks_missing_source_trace(
    tmp_path: Path,
) -> None:
    candidates = deepcopy(_load_yaml(SEMANTIC_CANDIDATES))
    candidates["semantic_candidates"]["candidates"][0].pop("source_trace_ids")
    candidates_path = tmp_path / "missing_trace_candidates.yaml"
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(candidates_path, candidates)
    _write_yaml(decisions_path, _decisions_doc())

    report = merge_semantic_candidates(
        STORY_MAP,
        candidates_path,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "blocked"
    assert any(
        error["code"] == "invalid_semantic_candidates_schema"
        for error in report_root["errors"]
    )
    assert not out_path.exists()
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)


def test_merge_semantic_candidates_blocks_type_target_mismatch(
    tmp_path: Path,
) -> None:
    candidates = deepcopy(_load_yaml(SEMANTIC_CANDIDATES))
    candidates["semantic_candidates"]["candidates"][0][
        "target_story_map_field"
    ] = "timeline"
    candidates_path = tmp_path / "bad_candidates.yaml"
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(candidates_path, candidates)
    _write_yaml(decisions_path, _decisions_doc())

    report = merge_semantic_candidates(
        STORY_MAP,
        candidates_path,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "blocked"
    assert any(error["code"] == "target_type_mismatch" for error in report_root["errors"])
    assert not out_path.exists()


def test_merge_semantic_candidates_counts_unknown_decision_as_skipped(
    tmp_path: Path,
) -> None:
    decisions = _decisions_doc()
    decisions["semantic_candidate_decisions"]["decisions"].append(
        {
            "decision_id": "dec_004",
            "candidate_id": "semcand_999",
            "decision": "reject",
            "target_story_map_field": "key_events",
            "human_approval": _approval(approved=False),
        }
    )
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(decisions_path, decisions)

    report = merge_semantic_candidates(
        STORY_MAP,
        SEMANTIC_CANDIDATES,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "partial"
    assert report_root["summary"]["skipped"] == 1
    assert any(error["code"] == "unknown_candidate" for error in report_root["errors"])
    assert out_path.exists()
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)


def test_merge_semantic_candidates_blocks_duplicate_candidate_decisions(
    tmp_path: Path,
) -> None:
    decisions = _decisions_doc()
    duplicate = deepcopy(decisions["semantic_candidate_decisions"]["decisions"][0])
    duplicate["decision_id"] = "dec_004"
    duplicate["decision"] = "reject"
    duplicate["human_approval"] = _approval(approved=False)
    decisions["semantic_candidate_decisions"]["decisions"].append(duplicate)
    decisions_path = tmp_path / "decisions.yaml"
    out_path = tmp_path / "story_map.merged.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(decisions_path, decisions)
    out_path.write_text("stale output", encoding="utf-8")

    report = merge_semantic_candidates(
        STORY_MAP,
        SEMANTIC_CANDIDATES,
        decisions_path,
        out_path=out_path,
        report_path=report_path,
    )

    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "blocked"
    assert report_root["summary"]["blocked"] >= 1
    assert any(error["code"] == "duplicate_candidate_decision" for error in report_root["errors"])
    assert not out_path.exists()
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)


def test_merge_semantic_candidates_never_overwrites_source_story_map(
    tmp_path: Path,
) -> None:
    story_map_path = tmp_path / "story_map.yaml"
    story_map_path.write_bytes(STORY_MAP.read_bytes())
    decisions = _decisions_doc()
    decisions["semantic_candidate_decisions"]["source_story_map"] = str(story_map_path)
    decisions_path = tmp_path / "decisions.yaml"
    report_path = tmp_path / "merge_report.yaml"
    _write_yaml(decisions_path, decisions)
    before = story_map_path.read_bytes()

    report = merge_semantic_candidates(
        story_map_path,
        SEMANTIC_CANDIDATES,
        decisions_path,
        out_path=story_map_path,
        report_path=report_path,
    )

    assert story_map_path.read_bytes() == before
    report_root = report["semantic_candidate_merge_report"]
    assert report_root["status"] == "blocked"
    assert any(
        error["code"] == "output_path_conflicts_with_source"
        for error in report_root["errors"]
    )
    Draft202012Validator(_load_yaml(MERGE_REPORT_SCHEMA)).validate(report)
