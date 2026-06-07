from __future__ import annotations

from typing import Any


AUTHOR_REVIEW_SCHEMA_VERSION = "0.1.0"


def render_author_review_packet(
    screenplay: dict[str, Any],
    review_report: dict[str, Any],
    quality_report: dict[str, Any],
    quality_dashboard: str,
    *,
    source_paths: dict[str, str],
) -> str:
    review = review_report.get("review_report", review_report)
    quality = quality_report.get("quality_report", quality_report)
    readiness = quality.get("overall_readiness", {})
    dimensions = quality.get("dimensions", [])
    review_summary = review.get("summary", {})
    issue_count = review_summary.get("total_issues", 0)
    hard_gate_failures = readiness.get("hard_gate_failures", [])
    next_actions = readiness.get("next_actions", [])
    title = screenplay.get("screenplay", screenplay).get("metadata", {}).get(
        "title", "Untitled"
    )

    lines = [
        "# Author Review Packet",
        "",
        "## Source Artifacts",
        "",
        f"- screenplay: `{source_paths['screenplay']}`",
        f"- review_report: `{source_paths['review_report']}`",
        f"- quality_report: `{source_paths['quality_report']}`",
        f"- quality_dashboard: `{source_paths['quality_dashboard']}`",
        "",
        "## Draft Summary",
        "",
        f"- title: {title}",
        "- purpose: human review before any creative dialogue or dramaturgy stage",
        "- model calls: none in this review step",
        "",
        "## Review Report Summary",
        "",
        f"- total issues: {issue_count}",
        f"- blocking: {review_summary.get('blocking', False)}",
        f"- requires human approval: {review_summary.get('requires_human_approval_count', 0)}",
        "",
        "## Quality Readiness",
        "",
        f"- status: {readiness.get('status', '')}",
        f"- score: {readiness.get('score', '')}",
        f"- decision: {readiness.get('decision', '')}",
        f"- hard gate failures: {', '.join(hard_gate_failures) if hard_gate_failures else 'none'}",
        "",
        "## Dimension Status",
        "",
        "| dimension | status | score | summary |",
        "| --- | --- | ---: | --- |",
    ]
    for dimension in dimensions:
        lines.append(
            "| {id} | {status} | {score} | {summary} |".format(
                id=dimension.get("id", ""),
                status=dimension.get("status", ""),
                score=dimension.get("score", ""),
                summary=dimension.get("summary", "").replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Next Actions",
            "",
        ]
    )
    if next_actions:
        lines.extend(f"- {action}" for action in next_actions)
    else:
        lines.append("- none")

    dialogue_status = next(
        (
            dimension
            for dimension in dimensions
            if dimension.get("id") == "dialogue_naturalness"
        ),
        {},
    )
    lines.extend(
        [
            "",
            "## Dialogue Warn Explanation",
            "",
            (
                "- dialogue_naturalness is {status}: {summary}".format(
                    status=dialogue_status.get("status", "unknown"),
                    summary=dialogue_status.get("summary", ""),
                )
            ),
            "- If the author wants richer dialogue, choose request_dialogue_draft.",
            "",
            "## Author Decisions To Confirm",
            "",
            "- Structure Decision: approve / request_changes / block",
            "- Character Decision: approve / request_changes / block",
            "- Beat Decision: approve / request_changes / block",
            "- Dialogue Decision: approve / request_dialogue_draft / block",
            "- Quality Decision: approve / request_changes / block",
            "- Next Stage Authorization: none / kimi_dialogue_draft / dramaturgy_review",
            "",
            "## Boundary",
            "",
            "- This packet does not modify screenplay YAML.",
            "- This packet does not apply review suggestions.",
            "- Kimi or dramaturgy authorization records intent for a future stage only.",
        ]
    )
    # Keep the dashboard as an input dependency without copying it in full.
    if "# Quality Dashboard" not in quality_dashboard:
        lines.extend(["", "## Packet Warning", "", "- quality dashboard heading was not found."])
    return "\n".join(lines) + "\n"


def build_author_review_decisions_template(
    *,
    source_paths: dict[str, str],
    reviewer: str = "author",
    reviewed_at: str = "2026-06-06T18:30:00+08:00",
) -> dict[str, Any]:
    artifacts = {
        "screenplay": source_paths["screenplay"],
        "review_report": source_paths["review_report"],
        "quality_report": source_paths["quality_report"],
        "quality_dashboard": source_paths["quality_dashboard"],
    }

    def standard(decision: str, note: str, linked: list[str]) -> dict[str, Any]:
        return {
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "decision": decision,
            "notes": [note],
            "linked_artifacts": linked,
            "linked_issue_ids": [],
            "human_approval_required": True,
        }

    return {
        "author_review_decisions": {
            "schema_version": AUTHOR_REVIEW_SCHEMA_VERSION,
            "source_artifacts": artifacts,
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "structure_decision": standard(
                "approve",
                "Structure is ready for author review.",
                [artifacts["screenplay"], artifacts["quality_report"]],
            ),
            "character_decision": standard(
                "approve",
                "Character handling is acceptable for this draft.",
                [artifacts["screenplay"], artifacts["review_report"]],
            ),
            "beat_decision": standard(
                "approve",
                "Beat structure is acceptable for this draft.",
                [artifacts["screenplay"], artifacts["quality_report"]],
            ),
            "dialogue_decision": standard(
                "request_dialogue_draft",
                "Draft lacks enough dialogue for naturalness review; request dialogue drafting.",
                [artifacts["quality_report"], artifacts["quality_dashboard"]],
            ),
            "quality_decision": standard(
                "approve",
                "Quality report is accepted as the gate evidence.",
                [artifacts["quality_report"], artifacts["quality_dashboard"]],
            ),
            "next_stage_authorization": standard(
                "kimi_dialogue_draft",
                "Authorize a future Kimi dialogue drafting stage plan.",
                [artifacts["quality_report"], artifacts["quality_dashboard"]],
            ),
            "overall_notes": [
                "Editable template generated by deterministic author review CLI."
            ],
        }
    }
