from __future__ import annotations

from typing import Any

from novel2script.io import read_yaml


REQUIRED_BEAT_FIELDS = [
    "objective",
    "tactic",
    "obstacle",
    "conflict",
    "stakes",
    "turn",
    "externalized_action",
    "source_trace",
    "ai_tags",
]


def validate_beats(yaml_path: str) -> dict[str, Any]:
    screenplay = read_yaml(yaml_path)
    incomplete_beats: list[dict[str, Any]] = []
    total_beats = 0
    complete_beats = 0

    for scene_index, scene in enumerate(screenplay.get("scenes", [])):
        if not isinstance(scene, dict):
            continue
        scene_id = scene.get("id")
        for beat_index, beat in enumerate(scene.get("beats", [])):
            if not isinstance(beat, dict):
                continue
            total_beats += 1
            missing_fields = [
                field
                for field in REQUIRED_BEAT_FIELDS
                if field not in beat or beat[field] in (None, "")
            ]
            if missing_fields:
                incomplete_beats.append(
                    {
                        "scene_id": scene_id,
                        "beat_id": beat.get("id"),
                        "yaml_path": f"scenes[{scene_index}].beats[{beat_index}]",
                        "missing_fields": missing_fields,
                    }
                )
            else:
                complete_beats += 1

    score = complete_beats / total_beats if total_beats else 1.0
    return {
        "beat_completeness": {
            "score": round(score, 4),
            "total_beats": total_beats,
            "incomplete_beats": incomplete_beats,
        }
    }
