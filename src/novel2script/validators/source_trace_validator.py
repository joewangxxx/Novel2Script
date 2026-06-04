from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from novel2script.io import read_yaml


def validate_source_trace(yaml_path: str) -> dict[str, Any]:
    screenplay = read_yaml(yaml_path)
    missing_targets: list[dict[str, Any]] = []
    invalid_targets: list[dict[str, Any]] = []
    checked_targets = 0
    valid_targets = 0

    for yaml_path_text, target in _iter_trace_targets(screenplay):
        checked_targets += 1
        trace = target.get("source_trace") if isinstance(target, dict) else None
        trace_path = f"{yaml_path_text}.source_trace"
        if trace is None:
            missing_targets.append(
                {
                    "yaml_path": trace_path,
                    "message": "Missing source_trace.",
                }
            )
            continue

        errors = _validate_trace(trace)
        if errors:
            invalid_targets.append(
                {
                    "yaml_path": trace_path,
                    "messages": errors,
                }
            )
            continue

        valid_targets += 1

    score = valid_targets / checked_targets if checked_targets else 1.0
    return {
        "source_coverage": {
            "score": round(score, 4),
            "checked_targets": checked_targets,
            "missing_targets": missing_targets,
            "invalid_targets": invalid_targets,
        }
    }


def _iter_trace_targets(screenplay: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for scene_index, scene in enumerate(screenplay.get("scenes", [])):
        if not isinstance(scene, dict):
            continue
        scene_path = f"scenes[{scene_index}]"
        yield scene_path, scene
        for beat_index, beat in enumerate(scene.get("beats", [])):
            if isinstance(beat, dict):
                yield f"{scene_path}.beats[{beat_index}]", beat
        for element_index, element in enumerate(scene.get("elements", [])):
            if isinstance(element, dict):
                yield f"{scene_path}.elements[{element_index}]", element


def _validate_trace(trace: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(trace, dict):
        return ["source_trace must be an object."]

    if "chapter" not in trace and "chapter_id" not in trace:
        errors.append("source_trace must include chapter or chapter_id.")
    if "paragraph_range" not in trace and "paragraph_ids" not in trace:
        errors.append("source_trace must include paragraph_range or paragraph_ids.")

    if "paragraph_range" in trace:
        errors.extend(_validate_paragraph_range(trace["paragraph_range"]))
    if "paragraph_ids" in trace:
        errors.extend(_validate_paragraph_ids(trace["paragraph_ids"]))

    return errors


def _validate_paragraph_range(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) != 2:
        return ["paragraph_range must contain exactly two integers."]
    start, end = value
    if not isinstance(start, int) or not isinstance(end, int):
        return ["paragraph_range values must be integers."]
    if start < 1 or end < 1:
        return ["paragraph_range values must be positive."]
    if start > end:
        return ["paragraph_range start must be less than or equal to end."]
    return []


def _validate_paragraph_ids(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["paragraph_ids must be a non-empty list."]
    if any(not isinstance(item, int) or item < 1 for item in value):
        return ["paragraph_ids values must be positive integers."]
    return []
