from __future__ import annotations

from typing import Any

from novel2script.reviewers.common import (
    element_target_id,
    inner,
    is_blank,
    iter_elements,
    make_issue,
    reviewer_result,
)


REVIEWER = "character_consistency"


def review_character_consistency(
    screenplay: dict[str, Any],
    character_bible_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    character_ids = {
        character.get("id")
        for character in screenplay.get("characters", [])
        if isinstance(character, dict) and character.get("id")
    }
    bible = inner(character_bible_doc, "character_bible")
    bible_by_id = {
        character.get("id"): character
        for character in bible.get("characters", [])
        if isinstance(character, dict) and character.get("id")
    }

    for character_index, character in enumerate(screenplay.get("characters", [])):
        if not isinstance(character, dict):
            continue
        character_id = str(character.get("id") or f"character_{character_index + 1:03d}")
        yaml_path = f"characters[{character_index}]"
        if is_blank(character.get("source_trace")):
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="character",
                    target_id=character_id,
                    yaml_path=yaml_path,
                    severity="medium",
                    confidence="high",
                    issue="Character is missing source_trace evidence.",
                    evidence_description="Every generated character should remain traceable to source evidence.",
                    suggestion="Add source evidence before treating this character as accepted.",
                )
            )

        bible_character = bible_by_id.get(character_id)
        if bible_by_id and not bible_character:
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="character",
                    target_id=character_id,
                    yaml_path=yaml_path,
                    severity="medium",
                    confidence="high",
                    issue="Screenplay character is not present in character_bible.",
                    evidence_description="The character ID was not found in the supplied character bible.",
                    suggestion="Review whether this character should be added to the bible or removed from the draft.",
                    source_trace=character.get("source_trace"),
                    source_trace_ids=character.get("source_trace_ids"),
                )
            )
            continue

        if bible_character and _is_locked(character, bible_character):
            screenplay_name = str(character.get("name", "")).strip()
            bible_name = str(bible_character.get("name", "")).strip()
            if screenplay_name and bible_name and screenplay_name != bible_name:
                issues.append(
                    make_issue(
                        len(issues) + 1,
                        reviewer=REVIEWER,
                        target_type="character",
                        target_id=character_id,
                        yaml_path=yaml_path,
                        severity="medium",
                        confidence="high",
                        issue="Locked character name differs from character_bible.",
                        evidence_description=(
                            f"Screenplay uses '{screenplay_name}' while character_bible uses '{bible_name}'."
                        ),
                        suggestion="Route this through human review instead of silently renaming the character.",
                        source_trace=character.get("source_trace"),
                        source_trace_ids=character.get("source_trace_ids"),
                    )
                )

    for scene_index, scene, element_index, element in iter_elements(screenplay):
        if element.get("type") != "dialogue":
            continue
        character_id = element.get("character_id")
        if character_id not in character_ids:
            yaml_path = f"scenes[{scene_index}].elements[{element_index}]"
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="element",
                    target_id=element_target_id(scene, element, element_index),
                    yaml_path=yaml_path,
                    severity="high",
                    confidence="high",
                    issue="Dialogue references a character_id that does not exist in characters.",
                    evidence_description=f"Dialogue character_id '{character_id}' is not declared.",
                    suggestion="Review the dialogue attribution and add a valid character_id only after approval.",
                    source_trace=element.get("source_trace"),
                    source_trace_ids=element.get("source_trace_ids"),
                    related_ids=[str(character_id)] if character_id else None,
                    blocking=True,
                )
            )

    return reviewer_result(REVIEWER, issues)


def _is_locked(screenplay_character: dict[str, Any], bible_character: dict[str, Any]) -> bool:
    return bool(screenplay_character.get("locked")) or bool(bible_character.get("locked"))
