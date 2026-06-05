from __future__ import annotations

from typing import Any

from novel2script.reviewers.common import (
    element_target_id,
    is_blank,
    iter_beats,
    iter_elements,
    iter_scenes,
    make_issue,
    reviewer_result,
)


REVIEWER = "shootability"
INTERNAL_KEYWORDS = ["想", "觉得", "意识到", "害怕", "内心", "心里", "仿佛"]
VISIBLE_ACTION_KEYWORDS = [
    "拿",
    "走",
    "看",
    "递",
    "拆",
    "打开",
    "关",
    "放",
    "拦",
    "敲",
    "写",
    "跑",
    "站",
    "坐",
    "推",
    "藏",
]


def review_shootability(screenplay: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    for scene_index, scene in iter_scenes(screenplay):
        scene_id = str(scene.get("id") or f"scene_{scene_index + 1:03d}")
        scene_path = f"scenes[{scene_index}]"
        if is_blank(scene.get("source_trace")):
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="high",
                    confidence="high",
                    issue="Scene is missing source_trace.",
                    evidence_description="Shootability review needs traceable scene evidence.",
                    suggestion="Restore source_trace before accepting this scene.",
                    blocking=True,
                )
            )
        action_elements = [
            element
            for element in scene.get("elements", [])
            if isinstance(element, dict) and element.get("type") == "action"
        ]
        if not action_elements:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="medium",
                    confidence="high",
                    issue="Scene has no action element.",
                    evidence_description="A scene with only notes or dialogue lacks a visible action anchor.",
                    suggestion="Add a source-grounded action element after review.",
                    source_trace=scene.get("source_trace"),
                    source_trace_ids=scene.get("source_trace_ids"),
                )
            )

    for scene_index, scene, beat_index, beat in iter_beats(screenplay):
        beat_id = str(beat.get("id") or f"{scene.get('id', 'scene_unknown')}.beat_{beat_index + 1:03d}")
        yaml_path = f"scenes[{scene_index}].beats[{beat_index}]"
        action = str(beat.get("externalized_action", "")).strip()
        if len(action) < 6:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="beat",
                    target_id=beat_id,
                    yaml_path=yaml_path,
                    severity="high" if is_blank(action) else "medium",
                    confidence="high",
                    issue="Beat externalized_action is empty or too short.",
                    evidence_description=f"externalized_action length is {len(action)}.",
                    suggestion="Review and add a visible action rather than an internal state.",
                    source_trace=beat.get("source_trace"),
                    source_trace_ids=beat.get("source_trace_ids"),
                    blocking=is_blank(action),
                )
            )
        elif _is_internal_without_visible_action(action):
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="beat",
                    target_id=beat_id,
                    yaml_path=yaml_path,
                    severity="medium",
                    confidence="medium",
                    issue="Beat externalized_action relies on internal-state wording.",
                    evidence_description="Internal psychology keywords appear without a clear visible action keyword.",
                    suggestion="Review whether the internal state can be expressed as visible behavior.",
                    source_trace=beat.get("source_trace"),
                    source_trace_ids=beat.get("source_trace_ids"),
                )
            )

    for scene_index, scene, element_index, element in iter_elements(screenplay):
        if element.get("type") != "action":
            continue
        text = str(element.get("text", "")).strip()
        if _is_internal_without_visible_action(text):
            yaml_path = f"scenes[{scene_index}].elements[{element_index}]"
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="element",
                    target_id=element_target_id(scene, element, element_index),
                    yaml_path=yaml_path,
                    severity="medium",
                    confidence="medium",
                    issue="Action element relies on internal-state wording.",
                    evidence_description="Psychological keywords appear without a clear observable action.",
                    suggestion="Review whether this action can be externalized.",
                    source_trace=element.get("source_trace"),
                    source_trace_ids=element.get("source_trace_ids"),
                )
            )

    return reviewer_result(REVIEWER, issues)


def _is_internal_without_visible_action(text: str) -> bool:
    return any(keyword in text for keyword in INTERNAL_KEYWORDS) and not any(
        keyword in text for keyword in VISIBLE_ACTION_KEYWORDS
    )
