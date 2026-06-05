from __future__ import annotations

from collections import Counter
from typing import Any

from novel2script.reviewers.common import (
    element_target_id,
    is_blank,
    iter_elements,
    make_issue,
    reviewer_result,
)


REVIEWER = "dialogue_naturalness"
MAX_DIALOGUE_CHARS = 120
MAX_PARENTHETICAL_CHARS = 40
EXPOSITORY_KEYWORDS = ["因为", "所以", "我其实", "你知道吗", "我要告诉你"]


def review_dialogue_naturalness(
    screenplay: dict[str, Any],
    character_bible_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del character_bible_doc
    issues: list[dict[str, Any]] = []
    character_ids = {
        character.get("id")
        for character in screenplay.get("characters", [])
        if isinstance(character, dict) and character.get("id")
    }
    dialogue_entries = [
        (scene_index, scene, element_index, element)
        for scene_index, scene, element_index, element in iter_elements(screenplay)
        if element.get("type") == "dialogue"
    ]
    parentheticals = [
        (scene_index, scene, element_index, element)
        for scene_index, scene, element_index, element in iter_elements(screenplay)
        if element.get("type") == "parenthetical"
    ]

    if not dialogue_entries and not parentheticals:
        return reviewer_result(
            REVIEWER,
            [],
            status="skipped",
            notes=["No dialogue or parenthetical elements to review."],
        )

    repeated_text = Counter(
        str(element.get("text", "")).strip()
        for _scene_index, _scene, _element_index, element in dialogue_entries
        if str(element.get("text", "")).strip()
    )

    for scene_index, scene, element_index, element in dialogue_entries:
        yaml_path = f"scenes[{scene_index}].elements[{element_index}]"
        target_id = element_target_id(scene, element, element_index)
        character_id = element.get("character_id")
        text = str(element.get("text", ""))
        ai_tags = element.get("ai_tags", {}) if isinstance(element.get("ai_tags"), dict) else {}

        if is_blank(character_id) or character_id not in character_ids:
            issues.append(
                _dialogue_issue(
                    len(issues) + 1,
                    target_id,
                    yaml_path,
                    "high",
                    "Dialogue element is missing a valid character_id.",
                    f"character_id '{character_id}' is not declared.",
                    "Review the attribution and assign a valid character only after approval.",
                    element,
                )
            )
        if is_blank(text):
            issues.append(
                _dialogue_issue(
                    len(issues) + 1,
                    target_id,
                    yaml_path,
                    "medium",
                    "Dialogue text is empty.",
                    "The dialogue element contains no performable text.",
                    "Remove or replace the empty dialogue after review.",
                    element,
                )
            )
        if len(text.strip()) > MAX_DIALOGUE_CHARS:
            issues.append(
                _dialogue_issue(
                    len(issues) + 1,
                    target_id,
                    yaml_path,
                    "medium",
                    "Dialogue line is very long.",
                    f"Dialogue length is {len(text.strip())}; threshold is {MAX_DIALOGUE_CHARS}.",
                    "Review whether the line should be split or compressed.",
                    element,
                )
            )
        keyword_hits = [keyword for keyword in EXPOSITORY_KEYWORDS if keyword in text]
        if len(keyword_hits) >= 3:
            issues.append(
                _dialogue_issue(
                    len(issues) + 1,
                    target_id,
                    yaml_path,
                    "medium",
                    "Dialogue contains multiple expository keywords.",
                    f"Keyword hits: {', '.join(keyword_hits)}.",
                    "Review whether exposition can be externalized through action.",
                    element,
                    confidence="medium",
                )
            )
        if repeated_text[text.strip()] > 1:
            issues.append(
                _dialogue_issue(
                    len(issues) + 1,
                    target_id,
                    yaml_path,
                    "low",
                    "Dialogue line is repeated.",
                    "The same dialogue text appears more than once.",
                    "Review whether repetition is intentional.",
                    element,
                    confidence="medium",
                )
            )
        if ai_tags.get("confidence") == "low":
            issues.append(
                _dialogue_issue(
                    len(issues) + 1,
                    target_id,
                    yaml_path,
                    "low",
                    "Dialogue is marked low confidence.",
                    "ai_tags.confidence is low and needs_human_review is expected.",
                    "Keep this line as a review candidate until human approved.",
                    element,
                    confidence="high",
                )
            )

    for scene_index, scene, element_index, element in parentheticals:
        text = str(element.get("text", "")).strip()
        if len(text) > MAX_PARENTHETICAL_CHARS:
            yaml_path = f"scenes[{scene_index}].elements[{element_index}]"
            issues.append(
                make_issue(
                    len(issues) + 1,
                    reviewer=REVIEWER,
                    target_type="element",
                    target_id=element_target_id(scene, element, element_index),
                    yaml_path=yaml_path,
                    severity="low",
                    confidence="high",
                    issue="Parenthetical is too long.",
                    evidence_description=f"Parenthetical length is {len(text)}; threshold is {MAX_PARENTHETICAL_CHARS}.",
                    suggestion="Review whether this acting note should be shortened.",
                    source_trace=element.get("source_trace"),
                    source_trace_ids=element.get("source_trace_ids"),
                )
            )

    return reviewer_result(REVIEWER, issues)


def _dialogue_issue(
    index: int,
    target_id: str,
    yaml_path: str,
    severity: str,
    issue: str,
    evidence_description: str,
    suggestion: str,
    element: dict[str, Any],
    *,
    confidence: str = "high",
) -> dict[str, Any]:
    return make_issue(
        index,
        reviewer=REVIEWER,
        target_type="element",
        target_id=target_id,
        yaml_path=yaml_path,
        severity=severity,
        confidence=confidence,
        issue=issue,
        evidence_description=evidence_description,
        suggestion=suggestion,
        source_trace=element.get("source_trace"),
        source_trace_ids=element.get("source_trace_ids"),
    )
