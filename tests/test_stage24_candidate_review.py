from pathlib import Path

import yaml

from novel2script.agents.stage24_candidate_review import (
    apply_stage24_candidate_decisions,
    prepare_stage24_candidate_review,
)


ROOT = Path(__file__).resolve().parents[1]
STAGE24_CANDIDATES = [
    ROOT / "examples" / "output" / "test1_sanguo_adaptation_planner_candidates.real_kimi.yaml",
    ROOT / "examples" / "output" / "test1_sanguo_character_bible_agent_candidates.real_kimi.yaml",
    ROOT / "examples" / "output" / "test1_sanguo_scene_writer_agent_candidates.real_kimi.yaml",
    ROOT / "examples" / "output" / "test1_sanguo_dialogue_optimizer_agent_candidates.real_kimi.yaml",
]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_prepare_stage24_candidate_review_writes_packet_and_pending_decisions(tmp_path):
    packet_path = tmp_path / "packet.md"
    decisions_path = tmp_path / "decisions.yaml"

    decisions = prepare_stage24_candidate_review(
        candidate_paths=STAGE24_CANDIDATES,
        packet_path=packet_path,
        decisions_path=decisions_path,
    )

    assert packet_path.exists()
    assert decisions == _load_yaml(decisions_path)
    body = decisions["stage24_candidate_decisions"]
    assert body["status"] == "pending_author_review"
    assert body["decision_summary"]["pending_count"] == 4
    assert body["decision_summary"]["accepted_count"] == 0
    assert "adaptplan_001" in packet_path.read_text(encoding="utf-8")
    for decision in body["decisions"]:
        assert decision["decision"] == "pending"
        assert decision["requires_author_approval"] is True


def test_apply_stage24_candidate_decisions_does_not_apply_pending(tmp_path):
    packet_path = tmp_path / "packet.md"
    decisions_path = tmp_path / "decisions.yaml"
    selected_path = tmp_path / "selected.yaml"
    report_path = tmp_path / "apply_report.yaml"
    prepare_stage24_candidate_review(
        candidate_paths=STAGE24_CANDIDATES,
        packet_path=packet_path,
        decisions_path=decisions_path,
    )

    report = apply_stage24_candidate_decisions(
        candidate_paths=STAGE24_CANDIDATES,
        decisions_path=decisions_path,
        selected_candidates_path=selected_path,
        report_path=report_path,
    )

    body = report["stage24_candidate_apply_report"]
    assert body["status"] == "blocked_pending_author_review"
    assert body["selected_count"] == 0
    assert body["skipped_count"] == 4
    assert selected_path.exists()
    assert _load_yaml(selected_path)["stage24_selected_candidates"]["candidates"] == []


def test_apply_stage24_candidate_decisions_selects_only_accepted_candidates(tmp_path):
    packet_path = tmp_path / "packet.md"
    decisions_path = tmp_path / "decisions.yaml"
    selected_path = tmp_path / "selected.yaml"
    report_path = tmp_path / "apply_report.yaml"
    decisions = prepare_stage24_candidate_review(
        candidate_paths=STAGE24_CANDIDATES,
        packet_path=packet_path,
        decisions_path=decisions_path,
    )
    decisions["stage24_candidate_decisions"]["decisions"][0]["decision"] = "accept"
    decisions["stage24_candidate_decisions"]["decisions"][0][
        "reviewed_by"
    ] = "human_author"
    decisions["stage24_candidate_decisions"]["decisions"][0][
        "review_notes"
    ] = "Approved for downstream apply planning."
    decisions_path.write_text(
        yaml.safe_dump(decisions, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    report = apply_stage24_candidate_decisions(
        candidate_paths=STAGE24_CANDIDATES,
        decisions_path=decisions_path,
        selected_candidates_path=selected_path,
        report_path=report_path,
    )

    body = report["stage24_candidate_apply_report"]
    assert body["status"] == "partial"
    assert body["selected_count"] == 1
    assert body["skipped_count"] == 3
    selected = _load_yaml(selected_path)["stage24_selected_candidates"]
    assert len(selected["candidates"]) == 1
    assert selected["candidates"][0]["human_decision"]["decision"] == "accept"
