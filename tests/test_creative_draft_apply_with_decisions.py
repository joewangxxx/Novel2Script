from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.creative_draft_apply import apply_creative_draft


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples/output/test1_sanguo_screenplay.yaml"
SCHEMA = ROOT / "schemas/screenplay.schema.json"


def _candidate_doc() -> dict:
    return {
        "creative_draft_candidates": {
            "schema_version": "0.1.0",
            "source_screenplay": str(SCREENPLAY),
            "source_author_review_report": "examples/output/test1_sanguo_author_review_report.yaml",
            "agent_id": "kimi_dialogue_scene_drafter",
            "provider_profile": "kimi_creative",
            "dry_run": False,
            "human_approval_required": True,
            "authorization": {
                "source": "author_review_report",
                "next_stage_authorization": "kimi_dialogue_draft",
                "scope": ["dialogue", "scene_action"],
            },
            "candidates": [
                {
                    "id": "crecand_001",
                    "type": "dialogue_insert",
                    "target": {
                        "scene_id": "scene_001",
                        "beat_id": "beat_001",
                        "character_id": "char_001",
                    },
                    "proposed_text": "刘备说：愿同二位为民请命。",
                    "rationale": "Adds a concise author-review dialogue candidate.",
                    "source_trace": {
                        "chapter": 1,
                        "paragraph_range": [4, 4],
                        "note": "Uses existing trace.",
                    },
                    "source_trace_ids": {
                        "chapter_id": "ch_001",
                        "paragraph_ids": ["p_004"],
                    },
                    "constraints_observed": ["preserved_source_trace"],
                    "risks": ["requires author review"],
                    "confidence": "medium",
                    "merge_policy": "human_approval_required",
                    "requires_author_approval": True,
                }
            ],
            "errors": [],
            "metadata": {
                "prompt_retained": False,
                "model_response_retained": False,
                "provider_payload_retained": False,
                "full_source_text_retained": False,
            },
        }
    }


def _decisions_doc(decision_val: str = "accept", edited_text: str = "") -> dict:
    return {
        "stage31_real_kimi_candidate_decisions": {
            "schema_version": "0.1.0",
            "status": "reviewed",
            "reviewed_by": "human_author_via_user_instruction",
            "decisions": [
                {
                    "agent_id": "kimi_dialogue_scene_drafter",
                    "candidate_id": "crecand_001",
                    "candidate_type": "dialogue_insert",
                    "decision": decision_val,
                    "edited_text": edited_text,
                    "requires_author_approval": True,
                    "reviewed_by": "human_author_via_user_instruction",
                }
            ]
        }
    }


def test_apply_creative_draft_with_decisions_accept(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(yaml.safe_dump(_candidate_doc(), allow_unicode=True), encoding="utf-8")
    
    decisions_path = tmp_path / "decisions.yaml"
    decisions_path.write_text(yaml.safe_dump(_decisions_doc("accept"), allow_unicode=True), encoding="utf-8")
    
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
        decisions_path=decisions_path,
    )

    assert report["creative_draft_apply_report"]["applied_count"] == 1
    assert report["creative_draft_apply_report"]["skipped_count"] == 0
    assert report["creative_draft_apply_report"]["blocked_count"] == 0
    assert out_path.exists()
    
    enhanced = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert enhanced["scenes"][0]["elements"][-1]["text"] == "刘备说：愿同二位为民请命。"


def test_apply_creative_draft_with_decisions_edit(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(yaml.safe_dump(_candidate_doc(), allow_unicode=True), encoding="utf-8")
    
    decisions_path = tmp_path / "decisions.yaml"
    decisions_path.write_text(yaml.safe_dump(_decisions_doc("edit", "修改后的对白文本"), allow_unicode=True), encoding="utf-8")
    
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
        decisions_path=decisions_path,
    )

    assert report["creative_draft_apply_report"]["applied_count"] == 1
    assert out_path.exists()
    
    enhanced = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert enhanced["scenes"][0]["elements"][-1]["text"] == "修改后的对白文本"


def test_apply_creative_draft_with_decisions_reject_skipped(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(yaml.safe_dump(_candidate_doc(), allow_unicode=True), encoding="utf-8")
    
    decisions_path = tmp_path / "decisions.yaml"
    decisions_path.write_text(yaml.safe_dump(_decisions_doc("reject"), allow_unicode=True), encoding="utf-8")
    
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
        decisions_path=decisions_path,
    )

    assert report["creative_draft_apply_report"]["applied_count"] == 0
    assert report["creative_draft_apply_report"]["skipped_count"] == 1
    assert report["creative_draft_apply_report"]["blocked_count"] == 0
    assert out_path.exists()
    
    enhanced = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    # 验证没有元素追加
    assert len(enhanced["scenes"][0]["elements"]) == len(yaml.safe_load(SCREENPLAY.read_text(encoding="utf-8"))["scenes"][0]["elements"])


def test_apply_creative_draft_with_decisions_missing_blocked(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(yaml.safe_dump(_candidate_doc(), allow_unicode=True), encoding="utf-8")
    
    # 一个空的 decisions
    decisions_path = tmp_path / "decisions.yaml"
    decisions_path.write_text(yaml.safe_dump({"stage31_real_kimi_candidate_decisions": {"decisions": []}}, allow_unicode=True), encoding="utf-8")
    
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
        decisions_path=decisions_path,
    )

    assert report["creative_draft_apply_report"]["blocked_count"] == 1
    assert not out_path.exists()


def test_apply_creative_draft_without_decisions_fallback(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(yaml.safe_dump(_candidate_doc(), allow_unicode=True), encoding="utf-8")
    
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    # decisions_path=None
    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
    )

    assert report["creative_draft_apply_report"]["applied_count"] == 1
    assert report["creative_draft_apply_report"]["blocked_count"] == 0
    assert out_path.exists()
