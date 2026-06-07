from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.creative_draft_apply import apply_creative_draft


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples/output/test1_sanguo_screenplay.yaml"
SCHEMA = ROOT / "schemas/screenplay.schema.json"


def _candidate_doc(candidate_type: str = "dialogue_insert") -> dict:
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
                    "type": candidate_type,
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


def test_apply_creative_draft_appends_dialogue_without_modifying_original(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(
        yaml.safe_dump(_candidate_doc(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"
    before = SCREENPLAY.read_bytes()

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
    )

    assert SCREENPLAY.read_bytes() == before
    assert report["creative_draft_apply_report"]["applied_count"] == 1
    enhanced = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        enhanced
    )
    new_element = enhanced["scenes"][0]["elements"][-1]
    assert new_element["type"] == "dialogue"
    assert new_element["character_id"] == "char_001"
    assert new_element["creative_draft_candidate_id"] == "crecand_001"
    assert new_element["requires_author_approval"] is True
    assert new_element["provider_profile"] == "kimi_creative"
    assert new_element["source_trace_ids"]["chapter_id"] == "ch_001"


def test_apply_creative_draft_writes_note_for_reviewer_note(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    doc = _candidate_doc("reviewer_note")
    candidates_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
    )

    assert report["creative_draft_apply_report"]["applied_count"] == 0
    assert report["creative_draft_apply_report"]["skipped_count"] == 1
    enhanced = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert enhanced["scenes"][0]["elements"][-1]["type"] == "note"


def test_apply_creative_draft_blocks_unresolved_target(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    doc = _candidate_doc()
    doc["creative_draft_candidates"]["candidates"][0]["target"][
        "scene_id"
    ] = "missing_scene"
    candidates_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    report = apply_creative_draft(
        screenplay_path=SCREENPLAY,
        creative_candidates_path=candidates_path,
        out_path=out_path,
        report_path=report_path,
    )

    assert report["creative_draft_apply_report"]["blocked_count"] == 1
    assert not out_path.exists()
