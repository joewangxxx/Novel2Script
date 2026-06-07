from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "0.1.0"
DEFAULT_GENERATED_AT = "2026-06-05"
REPORT_PROFILE = "deterministic_quality_eval_v0"
PASS_THRESHOLD = 90
WARN_THRESHOLD = 70
DIMENSION_IDS = [
    "schema_validity",
    "source_trace_coverage",
    "beat_completeness",
    "reference_integrity",
    "character_consistency",
    "pacing",
    "dialogue_naturalness",
    "shootability",
    "fountain_roundtrip_safety",
    "semantic_staleness",
    "character_goal_clarity",
    "dramatic_conflict_intensity",
    "overall_readiness",
]
REVIEWER_DIMENSIONS = {
    "character_consistency",
    "pacing",
    "dialogue_naturalness",
    "shootability",
}


def build_quality_report(
    screenplay: dict[str, Any],
    validation_report: dict[str, Any],
    review_report_doc: dict[str, Any],
    *,
    roundtrip_report_doc: dict[str, Any] | None = None,
    source_paths: dict[str, str] | None = None,
    generated_at: str = DEFAULT_GENERATED_AT,
    llm_scores: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate quality evidence including optional LLM scores without mutating inputs."""
    paths = source_paths or {}
    
    reviewer_dims = ["character_consistency", "pacing", "shootability"]
    if not llm_scores:
        reviewer_dims.append("dialogue_naturalness")

    dimensions = [
        _schema_validity(validation_report),
        _source_trace_coverage(validation_report),
        _beat_completeness(validation_report),
        _reference_integrity(validation_report),
        *[
            _reviewer_dimension(review_report_doc, reviewer)
            for reviewer in reviewer_dims
        ],
        _roundtrip_safety(roundtrip_report_doc),
        _semantic_staleness(screenplay),
    ]

    if llm_scores:
        dimensions.extend([
            _llm_dimension("dialogue_naturalness", llm_scores.get("dialogue_naturalness", {})),
            _llm_dimension("character_goal_clarity", llm_scores.get("character_goal_clarity", {})),
            _llm_dimension("dramatic_conflict_intensity", llm_scores.get("dramatic_conflict_intensity", {})),
        ])
    else:
        dimensions.extend([
            _reviewer_dimension(review_report_doc, "dialogue_naturalness"),
            _fallback_dimension("character_goal_clarity"),
            _fallback_dimension("dramatic_conflict_intensity"),
        ])
    readiness = _overall_readiness(dimensions, review_report_doc)
    dimensions.append(
        {
            "id": "overall_readiness",
            "status": readiness["status"],
            "score": readiness["score"],
            "hard_gate": False,
            "summary": f"Overall decision: {readiness['decision']}.",
            "evidence": [
                {
                    "source": "quality_policy",
                    "path": "overall_readiness",
                    "summary": "Hard gates are applied before average score.",
                    "value": readiness["decision"],
                }
            ],
            "metrics": {
                "hard_gate_failures": len(readiness["hard_gate_failures"]),
            },
            "recommendations": [
                {"priority": "medium", "action": action}
                for action in readiness["next_actions"]
            ],
            "blocking_reasons": readiness["hard_gate_failures"],
        }
    )
    return {
        "quality_report": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "report_profile": REPORT_PROFILE,
            "source_artifacts": {
                "screenplay": paths.get("screenplay", ""),
                "validation_report": paths.get("validation_report", ""),
                "review_report": paths.get("review_report", ""),
                "fountain_roundtrip_report": paths.get("fountain_roundtrip_report", ""),
                "quality_report_yaml": paths.get("quality_report_yaml", ""),
                "quality_dashboard_markdown": paths.get("quality_dashboard_markdown", ""),
            },
            "status_policy": {
                "allowed_statuses": ["pass", "warn", "fail", "blocked"],
                "hard_gates_precede_average_score": True,
                "notes": ["No model call, network call, or screenplay rewrite is used."],
            },
            "scoring_policy": {
                "score_min": 0,
                "score_max": 100,
                "default_pass_threshold": PASS_THRESHOLD,
                "default_warn_threshold": WARN_THRESHOLD,
                "weights": {
                    dimension_id: 1
                    for dimension_id in DIMENSION_IDS
                    if dimension_id != "overall_readiness"
                },
            },
            "dimensions": dimensions,
            "overall_readiness": readiness,
            "dashboard": {
                "format": "markdown",
                "path": paths.get("quality_dashboard_markdown", ""),
                "sections": [
                    "summary",
                    "gate_decision",
                    "dimension_scores",
                    "blocking_items",
                    "recommended_next_actions",
                    "source_artifacts",
                    "limitations",
                ],
            },
            "notes": [
                "Quality evaluation aggregates existing deterministic reports only.",
            ],
        }
    }


def render_quality_dashboard(report: dict[str, Any]) -> str:
    quality = report["quality_report"]
    readiness = quality["overall_readiness"]
    lines = [
        "# Quality Dashboard",
        "",
        "## Summary",
        "",
        f"- Readiness: {readiness['status']}",
        f"- Score: {readiness['score']}",
        f"- Decision: {readiness['decision']}",
        "",
        "## Gate Decision",
        "",
    ]
    if readiness["hard_gate_failures"]:
        lines.append(
            "Blocked by: " + ", ".join(readiness["hard_gate_failures"])
        )
    else:
        lines.append("No hard gate failures.")
    lines.extend(
        [
            "",
            "## Dimension Scores",
            "",
            "| Dimension | Status | Score | Summary |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for dimension in quality["dimensions"]:
        lines.append(
            f"| {dimension['id']} | {dimension['status']} | {dimension['score']} | "
            f"{_escape_markdown_table(str(dimension['summary']))} |"
        )
    lines.extend(["", "## Blocking Items", ""])
    blocking = [
        dimension
        for dimension in quality["dimensions"]
        if dimension.get("status") == "blocked" or dimension.get("blocking_reasons")
    ]
    if blocking:
        for dimension in blocking:
            reasons = ", ".join(dimension.get("blocking_reasons") or ["blocked"])
            lines.append(f"- {dimension['id']}: {reasons}")
    else:
        lines.append("- None")
    lines.extend(["", "## Recommended Next Actions", ""])
    if readiness["next_actions"]:
        for action in readiness["next_actions"]:
            lines.append(f"- {action}")
    else:
        lines.append("- Continue to the next approved phase.")
    lines.extend(["", "## Source Artifacts", ""])
    for key, value in quality["source_artifacts"].items():
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Deterministic aggregation only; no model call or external review is used.",
            "- Suggested patches are not applied automatically.",
            "- Markdown is a companion view; YAML remains the source of truth.",
            "",
        ]
    )
    return "\n".join(lines)


def _schema_validity(validation_report: dict[str, Any]) -> dict[str, Any]:
    schema = validation_report.get("schema_validity", {})
    passed = bool(schema.get("passed"))
    errors = schema.get("errors", [])
    return _dimension(
        "schema_validity",
        "pass" if passed else "blocked",
        100 if passed else 0,
        True,
        "Screenplay schema validation passed." if passed else "Screenplay schema validation failed.",
        "validation_report",
        "schema_validity.passed",
        passed,
        {"errors": len(errors) if isinstance(errors, list) else 1},
        [] if passed else ["Fix schema validation errors before continuing."],
        [] if passed else ["schema_validity"],
    )


def _source_trace_coverage(validation_report: dict[str, Any]) -> dict[str, Any]:
    coverage = validation_report.get("source_coverage", {})
    score = _score_from_ratio(coverage.get("score", 0))
    missing = coverage.get("missing_targets", [])
    invalid = coverage.get("invalid_targets", [])
    invalid_count = len(invalid) if isinstance(invalid, list) else 1
    status = _status_from_score(score)
    blocking = invalid_count > 0 or score == 0
    if blocking:
        status = "blocked"
    return _dimension(
        "source_trace_coverage",
        status,
        score,
        True,
        "Source trace coverage is complete." if score == 100 and not invalid_count else "Source trace coverage needs attention.",
        "validation_report",
        "source_coverage.score",
        coverage.get("score", 0),
        {
            "checked_targets": coverage.get("checked_targets", 0),
            "missing_targets": len(missing) if isinstance(missing, list) else 1,
            "invalid_targets": invalid_count,
        },
        [] if score == 100 and not invalid_count else ["Restore missing or invalid source_trace fields."],
        ["source_trace_coverage"] if blocking else [],
    )


def _beat_completeness(validation_report: dict[str, Any]) -> dict[str, Any]:
    beat = validation_report.get("beat_completeness", {})
    score = _score_from_ratio(beat.get("score", 0))
    incomplete = beat.get("incomplete_beats", [])
    return _dimension(
        "beat_completeness",
        _status_from_score(score),
        score,
        False,
        "Beat fields are complete." if score == 100 else "Some beats have incomplete dramatic fields.",
        "validation_report",
        "beat_completeness.score",
        beat.get("score", 0),
        {
            "total_beats": beat.get("total_beats", 0),
            "incomplete_beats": len(incomplete) if isinstance(incomplete, list) else 1,
        },
        [] if score == 100 else ["Complete missing beat objective, conflict, stakes, or turn fields."],
    )


def _reference_integrity(validation_report: dict[str, Any]) -> dict[str, Any]:
    references = validation_report.get("reference_integrity", {})
    passed = bool(references.get("passed"))
    missing = references.get("missing_references", [])
    return _dimension(
        "reference_integrity",
        "pass" if passed else "blocked",
        100 if passed else 0,
        True,
        "All references resolve." if passed else "Screenplay contains broken references.",
        "validation_report",
        "reference_integrity.passed",
        passed,
        {"missing_references": len(missing) if isinstance(missing, list) else 1},
        [] if passed else ["Fix missing character, scene, beat, or element references."],
        [] if passed else ["reference_integrity"],
    )


def _reviewer_dimension(review_report_doc: dict[str, Any], reviewer: str) -> dict[str, Any]:
    report = review_report_doc.get("review_report", {})
    issues = [
        issue for issue in report.get("issues", []) if issue.get("reviewer") == reviewer
    ]
    score = max(0, 100 - sum(_severity_penalty(issue.get("severity")) for issue in issues))
    blocking = any(issue.get("blocking") for issue in issues)
    result = _reviewer_result(report, reviewer)
    skipped = result.get("status") == "skipped"
    if blocking:
        status = "blocked"
    elif skipped and reviewer == "dialogue_naturalness":
        status = "warn"
    else:
        status = _status_from_score(score)
    summary = _reviewer_summary(reviewer, issues, skipped)
    recommendations = [
        f"Review {issue.get('id', reviewer)} from {reviewer}."
        for issue in issues
        if issue.get("severity") in {"medium", "high"}
    ]
    if skipped and reviewer == "dialogue_naturalness":
        recommendations.append("Add dialogue review after dialogue exists in the draft.")
    return _dimension(
        reviewer,
        status,
        score,
        False,
        summary,
        "review_report",
        f"issues[reviewer={reviewer}]",
        len(issues),
        {
            "issues": len(issues),
            "low": sum(1 for issue in issues if issue.get("severity") == "low"),
            "medium": sum(1 for issue in issues if issue.get("severity") == "medium"),
            "high": sum(1 for issue in issues if issue.get("severity") == "high"),
            "skipped": skipped,
        },
        recommendations,
        [reviewer] if blocking else [],
    )


def _roundtrip_safety(roundtrip_report_doc: dict[str, Any] | None) -> dict[str, Any]:
    if not roundtrip_report_doc:
        return _dimension(
            "fountain_roundtrip_safety",
            "warn",
            100,
            True,
            "No Fountain roundtrip report was provided.",
            "quality_policy",
            "fountain_roundtrip_report",
            None,
            {"report_present": False},
            ["Run import-fountain before relying on roundtrip safety."],
        )
    report = roundtrip_report_doc.get("fountain_roundtrip_report", {})
    summary = report.get("summary", {})
    line_policy = report.get("line_policy", {})
    blocked = (
        report.get("status") == "blocked"
        or bool(line_policy.get("line_drift_detected"))
        or not bool(line_policy.get("map_match", True))
        or int(summary.get("blocking_issues", 0) or 0) > 0
    )
    status = "blocked" if blocked else ("warn" if report.get("status") == "partial" else "pass")
    score = 0 if blocked else (70 if report.get("status") == "partial" else 100)
    return _dimension(
        "fountain_roundtrip_safety",
        status,
        score,
        True,
        "Fountain roundtrip is safe." if status == "pass" else "Fountain roundtrip requires attention.",
        "fountain_roundtrip_report",
        "status",
        report.get("status"),
        {
            "applied_changes": summary.get("applied_changes", 0),
            "skipped_changes": summary.get("skipped_changes", 0),
            "blocking_issues": summary.get("blocking_issues", 0),
            "line_drift_detected": bool(line_policy.get("line_drift_detected")),
            "map_match": bool(line_policy.get("map_match", True)),
        },
        [] if status == "pass" else ["Resolve roundtrip report issues before trusting imported YAML."],
        ["fountain_roundtrip_safety"] if blocked else [],
    )


def _semantic_staleness(screenplay: dict[str, Any]) -> dict[str, Any]:
    stale = bool(screenplay.get("metadata", {}).get("semantic_fields_stale"))
    return _dimension(
        "semantic_staleness",
        "warn" if stale else "pass",
        70 if stale else 100,
        False,
        "Semantic fields may be stale after Fountain import." if stale else "Semantic fields are not marked stale.",
        "screenplay_metadata",
        "metadata.semantic_fields_stale",
        stale,
        {"semantic_fields_stale": stale},
        ["Review semantic fields after roundtrip text edits."] if stale else [],
    )


def _overall_readiness(
    dimensions: list[dict[str, Any]], review_report_doc: dict[str, Any]
) -> dict[str, Any]:
    hard_failures = [
        dimension["id"]
        for dimension in dimensions
        if dimension.get("hard_gate") and dimension.get("status") == "blocked"
    ]
    review_blocking = bool(
        review_report_doc.get("review_report", {}).get("summary", {}).get("blocking")
    )
    if review_blocking and "review_report" not in hard_failures:
        hard_failures.append("review_report")
    score = round(sum(dimension["score"] for dimension in dimensions) / len(dimensions))
    force_no_pass = any(
        dimension["id"] == "source_trace_coverage" and dimension["score"] < 100
        for dimension in dimensions
    )
    if hard_failures:
        status = "blocked"
        decision = "blocked"
    else:
        status = _status_from_score(score)
        if force_no_pass and status == "pass":
            status = "warn"
        decision = {
            "pass": "ready_for_author_review",
            "warn": "ready_with_warnings",
            "fail": "needs_revision",
            "blocked": "blocked",
        }[status]
    return {
        "status": status,
        "score": score,
        "decision": decision,
        "hard_gate_failures": hard_failures,
        "next_actions": _next_actions(dimensions, hard_failures, status),
    }


def _dimension(
    dimension_id: str,
    status: str,
    score: int,
    hard_gate: bool,
    summary: str,
    evidence_source: str,
    evidence_path: str,
    evidence_value: Any,
    metrics: dict[str, Any],
    recommendation_actions: list[str],
    blocking_reasons: list[str] | None = None,
) -> dict[str, Any]:
    recommendations = [
        {"priority": "high" if status in {"blocked", "fail"} else "medium", "action": action}
        for action in recommendation_actions
    ]
    result = {
        "id": dimension_id,
        "status": status,
        "score": max(0, min(100, int(score))),
        "hard_gate": hard_gate,
        "summary": summary,
        "evidence": [
            {
                "source": evidence_source,
                "path": evidence_path,
                "summary": summary,
                "value": evidence_value,
            }
        ],
        "metrics": metrics,
        "recommendations": recommendations,
    }
    if blocking_reasons:
        result["blocking_reasons"] = blocking_reasons
    return result


def _score_from_ratio(value: Any) -> int:
    try:
        return max(0, min(100, round(float(value) * 100)))
    except (TypeError, ValueError):
        return 0


def _status_from_score(score: int) -> str:
    if score >= PASS_THRESHOLD:
        return "pass"
    if score >= WARN_THRESHOLD:
        return "warn"
    return "fail"


def _severity_penalty(severity: Any) -> int:
    return {"high": 40, "medium": 20, "low": 5}.get(severity, 0)


def _reviewer_result(report: dict[str, Any], reviewer: str) -> dict[str, Any]:
    for result in report.get("reviewer_results", []):
        if result.get("reviewer") == reviewer:
            return result
    return {}


def _reviewer_summary(reviewer: str, issues: list[dict[str, Any]], skipped: bool) -> str:
    if skipped:
        return f"{reviewer} reviewer was skipped."
    if issues:
        return f"{reviewer} reported {len(issues)} issue(s)."
    return f"{reviewer} reported no issues."


def _next_actions(
    dimensions: list[dict[str, Any]], hard_failures: list[str], status: str
) -> list[str]:
    if hard_failures:
        return [f"Resolve hard gate failure: {failure}." for failure in hard_failures]
    actions: list[str] = []
    for dimension in dimensions:
        if dimension["status"] in {"warn", "fail"}:
            actions.extend(
                recommendation["action"]
                for recommendation in dimension.get("recommendations", [])
            )
    if not actions and status == "pass":
        actions.append("Continue to author review or the next approved enhancement phase.")
    return actions[:6]


def _escape_markdown_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _llm_dimension(dimension_id: str, data: dict[str, Any]) -> dict[str, Any]:
    score = int(data.get("score", 90))
    status = _status_from_score(score)
    summary = str(data.get("summary", ""))
    reasoning = str(data.get("reasoning", ""))
    return _dimension(
        dimension_id,
        status,
        score,
        False,
        summary,
        "llm_evaluation",
        f"llm_scores.{dimension_id}",
        {"score": score, "summary": summary, "reasoning": reasoning},
        {"score": score},
        [f"Review LLM reasoning for {dimension_id}: {reasoning}"],
    )


def _fallback_dimension(dimension_id: str) -> dict[str, Any]:
    return _dimension(
        dimension_id,
        "pass",
        100,
        False,
        f"Deterministic fallback: {dimension_id} was not evaluated by LLM.",
        "quality_policy",
        f"llm_scores.{dimension_id}",
        None,
        {"score": 100},
        [],
    )
