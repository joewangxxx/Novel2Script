from __future__ import annotations

from typing import Any

from novel2script.reviewers.common import is_blank, iter_scenes, make_issue, reviewer_result


REVIEWER = "pacing"
MAX_BEATS_PER_SCENE = 6
MAX_ELEMENTS_PER_SCENE = 10


def review_pacing(
    screenplay: dict[str, Any],
    outline_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del outline_doc
    issues: list[dict[str, Any]] = []
    previous_scene_missing_conflict = False

    for scene_index, scene in iter_scenes(screenplay):
        scene_id = str(scene.get("id") or f"scene_{scene_index + 1:03d}")
        scene_path = f"scenes[{scene_index}]"
        beats = [beat for beat in scene.get("beats", []) if isinstance(beat, dict)]
        elements = [element for element in scene.get("elements", []) if isinstance(element, dict)]

        if not beats:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="high",
                    confidence="high",
                    issue="Scene has no beats.",
                    evidence_description="A screenplay scene without beats cannot express dramatic progression.",
                    suggestion="Add at least one reviewed beat before accepting this scene.",
                    source_trace=scene.get("source_trace"),
                    source_trace_ids=scene.get("source_trace_ids"),
                    blocking=True,
                )
            )

        if len(beats) > MAX_BEATS_PER_SCENE:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="low",
                    confidence="medium",
                    issue="Scene has high beat density.",
                    evidence_description=f"Scene has {len(beats)} beats; threshold is {MAX_BEATS_PER_SCENE}.",
                    suggestion="Review whether the scene should be split or compressed.",
                    source_trace=scene.get("source_trace"),
                    source_trace_ids=scene.get("source_trace_ids"),
                )
            )

        if not elements:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="medium",
                    confidence="high",
                    issue="Scene has no elements.",
                    evidence_description="The scene has no action, dialogue, note, or transition elements.",
                    suggestion="Add source-grounded screenplay elements after review.",
                    source_trace=scene.get("source_trace"),
                    source_trace_ids=scene.get("source_trace_ids"),
                )
            )
        elif len(elements) > MAX_ELEMENTS_PER_SCENE:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="low",
                    confidence="medium",
                    issue="Scene has high element density.",
                    evidence_description=f"Scene has {len(elements)} elements; threshold is {MAX_ELEMENTS_PER_SCENE}.",
                    suggestion="Review whether the scene should be compressed.",
                    source_trace=scene.get("source_trace"),
                    source_trace_ids=scene.get("source_trace_ids"),
                )
            )

        scene_missing_conflict = bool(beats) and all(is_blank(beat.get("conflict")) for beat in beats)
        if previous_scene_missing_conflict and scene_missing_conflict:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="scene",
                    target_id=scene_id,
                    yaml_path=scene_path,
                    severity="medium",
                    confidence="medium",
                    issue="Consecutive scenes lack explicit conflict.",
                    evidence_description="This scene and the previous scene have no non-empty beat conflict.",
                    suggestion="Review whether at least one conflict should be externalized.",
                    source_trace=scene.get("source_trace"),
                    source_trace_ids=scene.get("source_trace_ids"),
                )
            )
        previous_scene_missing_conflict = scene_missing_conflict

        for beat_index, beat in enumerate(beats):
            missing = [
                field
                for field in ("turn", "stakes")
                if is_blank(beat.get(field))
            ]
            if missing:
                beat_id = str(beat.get("id") or f"{scene_id}.beat_{beat_index + 1:03d}")
                issues.append(
                    make_issue(
                        len(issues) + 1,
                        reviewer=REVIEWER,
                        target_type="beat",
                        target_id=beat_id,
                        yaml_path=f"{scene_path}.beats[{beat_index}]",
                        severity="medium",
                        confidence="high",
                        issue="Beat has empty pacing fields.",
                        evidence_description=f"Empty fields: {', '.join(missing)}.",
                        suggestion="Review the beat turn and stakes before treating pacing as complete.",
                        source_trace=beat.get("source_trace"),
                        source_trace_ids=beat.get("source_trace_ids"),
                    )
                )

    return reviewer_result(REVIEWER, issues)
