from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from novel2script.io import read_yaml, write_yaml


SCHEMA_VERSION = "0.1.0"


def apply_stage24_selected_candidates_to_artifacts(
    *,
    selected_candidates_path: str | Path,
    outline_path: str | Path,
    character_bible_path: str | Path,
    screenplay_path: str | Path,
    outline_out_path: str | Path,
    character_bible_out_path: str | Path,
    screenplay_out_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    selected_doc = read_yaml(selected_candidates_path)
    selected = selected_doc.get("stage24_selected_candidates", {}).get(
        "candidates", []
    )
    outline_source = read_yaml(outline_path)
    character_source = read_yaml(character_bible_path)
    screenplay_source = read_yaml(screenplay_path)
    outline = copy.deepcopy(outline_source)
    character_bible = copy.deepcopy(character_source)
    screenplay = copy.deepcopy(screenplay_source)
    report = {
        "stage26_selected_candidate_apply_report": {
            "schema_version": SCHEMA_VERSION,
            "status": "success",
            "source_selected_candidates": str(selected_candidates_path),
            "source_artifacts": {
                "outline": str(outline_path),
                "character_bible": str(character_bible_path),
                "screenplay": str(screenplay_path),
            },
            "output_artifacts": {
                "outline": str(outline_out_path),
                "character_bible": str(character_bible_out_path),
                "screenplay": str(screenplay_out_path),
            },
            "applied_count": 0,
            "skipped_count": 0,
            "blocked_count": 0,
            "applied": [],
            "skipped": [],
            "blocked": [],
            "source_hashes_before": {
                "outline": f"sha256:{_file_sha(outline_path)}",
                "character_bible": f"sha256:{_file_sha(character_bible_path)}",
                "screenplay": f"sha256:{_file_sha(screenplay_path)}",
            },
            "source_hashes_after": {},
            "output_hashes": {},
            "preserved_original_artifacts": True,
        }
    }
    for candidate in selected:
        agent_id = str(candidate.get("agent_id") or "")
        if agent_id == "adaptation_planner":
            _apply_outline_candidate(outline, candidate, report)
        elif agent_id == "character_bible_agent":
            _apply_character_candidate(character_bible, candidate, report)
        elif agent_id in {"scene_writer_agent", "dialogue_optimizer_agent"}:
            _apply_screenplay_candidate(screenplay, candidate, report)
        else:
            _skip(report, candidate, "unsupported_agent")

    write_yaml(outline, outline_out_path)
    write_yaml(character_bible, character_bible_out_path)
    write_yaml(screenplay, screenplay_out_path)
    body = report["stage26_selected_candidate_apply_report"]
    body["source_hashes_after"] = {
        "outline": f"sha256:{_file_sha(outline_path)}",
        "character_bible": f"sha256:{_file_sha(character_bible_path)}",
        "screenplay": f"sha256:{_file_sha(screenplay_path)}",
    }
    body["output_hashes"] = {
        "outline": f"sha256:{_file_sha(outline_out_path)}",
        "character_bible": f"sha256:{_file_sha(character_bible_out_path)}",
        "screenplay": f"sha256:{_file_sha(screenplay_out_path)}",
    }
    if body["blocked_count"]:
        body["status"] = "blocked"
    elif body["skipped_count"]:
        body["status"] = "partial"
    else:
        body["status"] = "success"
    write_yaml(report, report_path)
    return report


def _apply_outline_candidate(
    outline_doc: dict[str, Any], candidate: dict[str, Any], report: dict[str, Any]
) -> None:
    scenes = outline_doc.get("outline", {}).get("scene_plan", [])
    if not scenes:
        _block(report, candidate, "missing_outline_scene_plan")
        return
    scene = scenes[0]
    original = str(scene.get("purpose") or "")
    scene["purpose"] = _append_text(original, str(candidate.get("proposed_text") or ""))
    _append_ai_note(scene, candidate)
    _applied(report, candidate, "outline.scene_plan[0].purpose")


def _apply_character_candidate(
    character_doc: dict[str, Any], candidate: dict[str, Any], report: dict[str, Any]
) -> None:
    target_character_id = candidate.get("target", {}).get("character_id")
    characters = character_doc.get("character_bible", {}).get("characters", [])
    character = next(
        (item for item in characters if item.get("id") == target_character_id),
        characters[0] if characters else None,
    )
    if not character:
        _block(report, candidate, "missing_character")
        return
    flaw = character.setdefault("flaw", {})
    flaw["text"] = str(candidate.get("proposed_text") or "")
    trace = _trace_list(candidate.get("source_trace"))
    if trace:
        flaw["source_trace"] = trace
    flaw["ai_tags"] = _ai_tags(candidate)
    _applied(report, candidate, f"character_bible.characters[{character.get('id')}].flaw")


def _apply_screenplay_candidate(
    screenplay_doc: dict[str, Any], candidate: dict[str, Any], report: dict[str, Any]
) -> None:
    scene_id = candidate.get("target", {}).get("scene_id")
    scenes = screenplay_doc.get("scenes", [])
    scene = next(
        (item for item in scenes if item.get("id") == scene_id),
        scenes[0] if scenes else None,
    )
    if not scene:
        _block(report, candidate, "missing_screenplay_scene")
        return
    candidate_type = str(candidate.get("type") or "")
    element_type = "dialogue" if candidate_type.startswith("dialogue") else "action"
    element = {
        "type": element_type,
        "text": str(candidate.get("proposed_text") or ""),
        "source_trace": _screenplay_source_trace(candidate),
        "source_trace_ids": candidate.get("source_trace_ids", {}),
        "ai_tags": _ai_tags(candidate),
        "stage24_candidate_id": str(candidate.get("id") or ""),
        "stage24_agent_id": str(candidate.get("agent_id") or ""),
        "requires_author_approval": True,
        "provider_profile": "kimi_creative",
    }
    character_id = candidate.get("target", {}).get("character_id")
    if element_type == "dialogue" and character_id:
        element["character_id"] = character_id
    scene.setdefault("elements", []).append(element)
    _applied(report, candidate, f"screenplay.scenes[{scene.get('id')}].elements[]")


def _ai_tags(candidate: dict[str, Any]) -> dict[str, Any]:
    tags = candidate.get("ai_tags", {})
    notes = list(tags.get("notes", [])) if isinstance(tags.get("notes"), list) else []
    notes.append(f"stage24/{candidate.get('id')}")
    notes.append(f"Applied from stage24/{candidate.get('id')} after human acceptance.")
    return {
        "inferred": bool(tags.get("inferred", True)),
        "confidence": str(tags.get("confidence") or candidate.get("confidence") or "medium"),
        "needs_human_review": True,
        "notes": notes,
    }


def _append_ai_note(item: dict[str, Any], candidate: dict[str, Any]) -> None:
    tags = item.setdefault(
        "ai_tags",
        {"inferred": True, "confidence": "medium", "needs_human_review": True},
    )
    notes = tags.setdefault("notes", [])
    notes.append(f"stage24/{candidate.get('id')}")
    tags["inferred"] = True
    tags["needs_human_review"] = True


def _append_text(original: str, addition: str) -> str:
    if not original:
        return addition
    return f"{original}\n\nStage 24 accepted adaptation note:\n{addition}"


def _trace_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _screenplay_source_trace(candidate: dict[str, Any]) -> dict[str, Any]:
    trace = candidate.get("source_trace")
    if isinstance(trace, dict) and trace.get("chapter") and trace.get("paragraph_range"):
        return trace
    trace_ids = candidate.get("source_trace_ids", {})
    chapter_id = str(trace_ids.get("chapter_id") or "")
    paragraph_ids = trace_ids.get("paragraph_ids") or []
    chapter = _numeric_suffix(chapter_id) or 1
    paragraph = _numeric_suffix(str(paragraph_ids[0])) if paragraph_ids else 1
    paragraph = paragraph or 1
    note = ""
    if isinstance(trace, dict):
        note = str(trace.get("note") or trace.get("quote_preview") or "")
    return {
        "chapter": chapter,
        "paragraph_range": [paragraph, paragraph],
        "note": note,
    }


def _numeric_suffix(value: str) -> int | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


def _applied(report: dict[str, Any], candidate: dict[str, Any], path: str) -> None:
    body = report["stage26_selected_candidate_apply_report"]
    body["applied_count"] += 1
    body["applied"].append(
        {
            "agent_id": str(candidate.get("agent_id") or ""),
            "candidate_id": str(candidate.get("id") or ""),
            "path": path,
        }
    )


def _skip(report: dict[str, Any], candidate: dict[str, Any], code: str) -> None:
    body = report["stage26_selected_candidate_apply_report"]
    body["skipped_count"] += 1
    body["skipped"].append(_issue(candidate, code))


def _block(report: dict[str, Any], candidate: dict[str, Any], code: str) -> None:
    body = report["stage26_selected_candidate_apply_report"]
    body["blocked_count"] += 1
    body["blocked"].append(_issue(candidate, code))


def _issue(candidate: dict[str, Any], code: str) -> dict[str, str]:
    return {
        "agent_id": str(candidate.get("agent_id") or ""),
        "candidate_id": str(candidate.get("id") or ""),
        "code": code,
    }


def _file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
