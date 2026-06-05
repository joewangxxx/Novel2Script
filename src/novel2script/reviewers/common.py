from __future__ import annotations

from collections.abc import Iterator
from typing import Any


SCREENPLAY_TRACE_KEYS = {"chapter", "paragraph_range", "note"}
TRACE_ID_KEYS = {"chapter_id", "paragraph_ids", "event_ids", "outline_scene_ids"}


def reviewer_result(
    reviewer: str,
    issues: list[dict[str, Any]],
    *,
    status: str = "completed",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "reviewer": reviewer,
        "status": status,
        "issues": issues,
        "notes": notes or [],
    }


def make_issue(
    index: int,
    *,
    reviewer: str,
    target_type: str,
    target_id: str,
    yaml_path: str,
    severity: str,
    confidence: str,
    issue: str,
    evidence_description: str,
    suggestion: str,
    source_trace: dict[str, Any] | None = None,
    source_trace_ids: dict[str, Any] | None = None,
    related_ids: list[str] | None = None,
    operation: str = "note_only",
    value: Any = None,
    blocking: bool | None = None,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {"description": evidence_description}
    clean_trace = _clean_dict(source_trace, SCREENPLAY_TRACE_KEYS)
    clean_trace_ids = _clean_dict(source_trace_ids, TRACE_ID_KEYS)
    if clean_trace:
        evidence["source_trace"] = clean_trace
    if clean_trace_ids:
        evidence["source_trace_ids"] = clean_trace_ids
    if related_ids:
        evidence["related_ids"] = related_ids

    result = {
        "id": f"issue_{index:03d}",
        "reviewer": reviewer,
        "target_id": target_id,
        "target": {
            "type": target_type,
            "id": target_id,
            "yaml_path": yaml_path,
        },
        "severity": severity,
        "confidence": confidence,
        "issue": issue,
        "evidence": evidence,
        "suggestion": suggestion,
        "suggested_patch": {
            "operation": operation,
            "yaml_path": yaml_path,
            "value": value,
        },
        "requires_human_approval": True,
    }
    if blocking is not None:
        result["blocking"] = blocking
    return result


def is_blank(value: Any) -> bool:
    return value is None or not str(value).strip()


def inner(doc: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(doc, dict):
        return {}
    value = doc.get(key, doc)
    return value if isinstance(value, dict) else {}


def iter_scenes(screenplay: dict[str, Any]) -> Iterator[tuple[int, dict[str, Any]]]:
    for scene_index, scene in enumerate(screenplay.get("scenes", [])):
        if isinstance(scene, dict):
            yield scene_index, scene


def iter_beats(screenplay: dict[str, Any]) -> Iterator[tuple[int, dict[str, Any], int, dict[str, Any]]]:
    for scene_index, scene in iter_scenes(screenplay):
        for beat_index, beat in enumerate(scene.get("beats", [])):
            if isinstance(beat, dict):
                yield scene_index, scene, beat_index, beat


def iter_elements(
    screenplay: dict[str, Any],
) -> Iterator[tuple[int, dict[str, Any], int, dict[str, Any]]]:
    for scene_index, scene in iter_scenes(screenplay):
        for element_index, element in enumerate(scene.get("elements", [])):
            if isinstance(element, dict):
                yield scene_index, scene, element_index, element


def element_target_id(scene: dict[str, Any], element: dict[str, Any], element_index: int) -> str:
    if element.get("id"):
        return str(element["id"])
    scene_id = scene.get("id") or "scene_unknown"
    return f"{scene_id}.element_{element_index + 1:03d}"


def _clean_dict(value: dict[str, Any] | None, allowed_keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in allowed_keys if key in value}
