from __future__ import annotations

from copy import deepcopy
from typing import Any

from novel2script.reviewers.character_consistency import review_character_consistency
from novel2script.reviewers.dialogue_naturalness import review_dialogue_naturalness
from novel2script.reviewers.pacing import review_pacing
from novel2script.reviewers.shootability import review_shootability


SCHEMA_VERSION = "0.1.0"
DEFAULT_GENERATED_AT = "2026-06-05"
REVIEW_PROFILE = "deterministic_review_contract_v0"
REVIEWERS = [
    "character_consistency",
    "pacing",
    "dialogue_naturalness",
    "shootability",
]


def build_review_report(
    screenplay: dict[str, Any],
    *,
    character_bible_doc: dict[str, Any] | None = None,
    outline_doc: dict[str, Any] | None = None,
    story_map_doc: dict[str, Any] | None = None,
    source_screenplay: str = "",
    source_artifacts: dict[str, str] | None = None,
    generated_at: str = DEFAULT_GENERATED_AT,
) -> dict[str, Any]:
    """Build a deterministic advisory review report without mutating screenplay."""
    del story_map_doc
    reviewer_outputs = [
        review_character_consistency(screenplay, character_bible_doc),
        review_pacing(screenplay, outline_doc),
        review_dialogue_naturalness(screenplay, character_bible_doc),
        review_shootability(screenplay),
    ]
    issues = _renumber_issues(
        issue
        for output in reviewer_outputs
        for issue in output.get("issues", [])
    )

    return {
        "review_report": {
            "schema_version": SCHEMA_VERSION,
            "source_screenplay": source_screenplay,
            "source_artifacts": source_artifacts or {},
            "generated_at": generated_at,
            "review_profile": REVIEW_PROFILE,
            "reviewers": REVIEWERS,
            "reviewer_results": [
                {
                    "reviewer": output["reviewer"],
                    "status": output["status"],
                    "issues_found": len(output.get("issues", [])),
                    "notes": output.get("notes", []),
                }
                for output in reviewer_outputs
            ],
            "summary": _summary(issues),
            "issues": issues,
        }
    }


def _renumber_issues(issues: Any) -> list[dict[str, Any]]:
    numbered: list[dict[str, Any]] = []
    for index, issue in enumerate(issues, start=1):
        copied = deepcopy(issue)
        copied["id"] = f"issue_{index:03d}"
        numbered.append(copied)
    return numbered


def _summary(issues: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"low": 0, "medium": 0, "high": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return {
        "total_issues": len(issues),
        "by_severity": counts,
        "blocking": any(issue.get("severity") == "high" or issue.get("blocking") for issue in issues),
        "requires_human_approval_count": sum(
            1 for issue in issues if issue.get("requires_human_approval")
        ),
    }
