from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from novel2script.io import read_yaml, write_yaml


APPLY_TYPES = {
    "dialogue_insert",
    "dialogue_rewrite",
    "scene_action_enhancement",
    "beat_externalization",
}
NOTE_ONLY_TYPES = {"pacing_trim_suggestion", "reviewer_note"}


def apply_creative_draft(
    *,
    screenplay_path: str | Path,
    creative_candidates_path: str | Path,
    out_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    screenplay = read_yaml(screenplay_path)
    candidates_doc = read_yaml(creative_candidates_path)
    enhanced = copy.deepcopy(screenplay)
    source_hash = _file_sha(screenplay_path)
    report = {
        "creative_draft_apply_report": {
            "schema_version": "0.1.0",
            "source_screenplay": str(screenplay_path),
            "source_creative_candidates": str(creative_candidates_path),
            "output_screenplay": str(out_path),
            "applied_count": 0,
            "skipped_count": 0,
            "blocked_count": 0,
            "candidate_ids": [],
            "source_screenplay_hash_before": f"sha256:{source_hash}",
            "source_screenplay_hash_after": f"sha256:{_file_sha(screenplay_path)}",
            "enhanced_screenplay_hash": "",
            "preserved_original_screenplay": True,
            "errors": [],
        }
    }
    scenes = {scene.get("id"): scene for scene in enhanced.get("scenes", [])}
    original_scenes = {scene.get("id"): scene for scene in screenplay.get("scenes", [])}
    candidates = candidates_doc.get("creative_draft_candidates", {}).get(
        "candidates", []
    )
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "")
        report["creative_draft_apply_report"]["candidate_ids"].append(candidate_id)
        scene = scenes.get(candidate.get("target", {}).get("scene_id"))
        original_scene = original_scenes.get(candidate.get("target", {}).get("scene_id"))
        if scene is None or original_scene is None or not _target_resolves(
            original_scene, candidate
        ):
            _block(report, candidate_id, "candidate_target_unresolved")
            continue
        candidate_type = str(candidate.get("type") or "")
        if candidate_type in APPLY_TYPES:
            scene.setdefault("elements", []).append(_element_for(candidate))
            report["creative_draft_apply_report"]["applied_count"] += 1
        elif candidate_type in NOTE_ONLY_TYPES:
            scene.setdefault("elements", []).append(_note_for(candidate))
            report["creative_draft_apply_report"]["skipped_count"] += 1
        else:
            _block(report, candidate_id, "unsupported_candidate_type")

    if report["creative_draft_apply_report"]["blocked_count"]:
        Path(out_path).unlink(missing_ok=True)
    else:
        write_yaml(enhanced, out_path)
        report["creative_draft_apply_report"][
            "enhanced_screenplay_hash"
        ] = f"sha256:{_file_sha(out_path)}"
    report["creative_draft_apply_report"][
        "source_screenplay_hash_after"
    ] = f"sha256:{_file_sha(screenplay_path)}"
    write_yaml(report, report_path)
    return report


def _target_resolves(scene: dict[str, Any], candidate: dict[str, Any]) -> bool:
    target = candidate.get("target", {})
    if target.get("beat_id") and not any(
        beat.get("id") == target["beat_id"] for beat in scene.get("beats", [])
    ):
        return False
    if target.get("element_id") and not any(
        element.get("id") == target["element_id"]
        for element in scene.get("elements", [])
    ):
        return False
    return True


def _element_for(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_type = str(candidate.get("type") or "")
    element_type = "dialogue" if candidate_type.startswith("dialogue") else "action"
    element = _base_element(candidate, element_type)
    character_id = candidate.get("target", {}).get("character_id")
    if element_type == "dialogue" and character_id:
        element["character_id"] = character_id
    return element


def _note_for(candidate: dict[str, Any]) -> dict[str, Any]:
    return _base_element(candidate, "note")


def _base_element(candidate: dict[str, Any], element_type: str) -> dict[str, Any]:
    return {
        "type": element_type,
        "text": str(candidate.get("proposed_text") or ""),
        "source_trace": candidate.get("source_trace", {}),
        "source_trace_ids": candidate.get("source_trace_ids", {}),
        "ai_tags": {
            "inferred": True,
            "confidence": str(candidate.get("confidence") or "medium"),
            "needs_human_review": True,
            "notes": [
                f"Creative draft candidate {candidate.get('id')} requires author approval."
            ],
        },
        "creative_draft_candidate_id": str(candidate.get("id") or ""),
        "requires_author_approval": True,
        "provider_profile": "kimi_creative",
    }


def _block(report: dict[str, Any], candidate_id: str, code: str) -> None:
    body = report["creative_draft_apply_report"]
    body["blocked_count"] += 1
    body["errors"].append(
        {
            "candidate_id": candidate_id,
            "code": code,
            "message": "Creative draft candidate could not be safely applied.",
        }
    )


def _file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
