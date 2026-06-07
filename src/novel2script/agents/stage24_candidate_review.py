from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from novel2script.io import read_yaml, write_yaml


SCHEMA_VERSION = "0.1.0"
AGENT_ROOTS = (
    "adaptation_planner_candidates",
    "character_bible_agent_candidates",
    "scene_writer_agent_candidates",
    "dialogue_optimizer_agent_candidates",
)
ACCEPTED_DECISIONS = {"accept", "edit"}


def prepare_stage24_candidate_review(
    *,
    candidate_paths: list[str | Path],
    packet_path: str | Path,
    decisions_path: str | Path,
) -> dict[str, Any]:
    records = _candidate_records(candidate_paths)
    decisions = {
        "stage24_candidate_decisions": {
            "schema_version": SCHEMA_VERSION,
            "status": "pending_author_review",
            "source_candidate_sidecars": [str(path) for path in candidate_paths],
            "decision_summary": {
                "total_count": len(records),
                "accepted_count": 0,
                "edited_count": 0,
                "rejected_count": 0,
                "pending_count": len(records),
            },
            "decisions": [
                {
                    "agent_id": record["agent_id"],
                    "candidate_id": record["candidate"]["id"],
                    "candidate_type": record["candidate"]["type"],
                    "requires_author_approval": True,
                    "decision": "pending",
                    "reviewed_by": "",
                    "review_notes": "",
                    "edited_text": "",
                }
                for record in records
            ],
            "metadata": {
                "prompt_retained": False,
                "raw_response_retained": False,
                "provider_body_retained": False,
                "full_source_text_retained": False,
                "packet": str(packet_path),
            },
        }
    }
    Path(packet_path).parent.mkdir(parents=True, exist_ok=True)
    Path(packet_path).write_text(_render_packet(records), encoding="utf-8", newline="\n")
    write_yaml(decisions, decisions_path)
    return decisions


def apply_stage24_candidate_decisions(
    *,
    candidate_paths: list[str | Path],
    decisions_path: str | Path,
    selected_candidates_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    records = _candidate_records(candidate_paths)
    decisions_doc = read_yaml(decisions_path)
    decisions = decisions_doc.get("stage24_candidate_decisions", {}).get(
        "decisions", []
    )
    decision_map = {
        (decision.get("agent_id"), decision.get("candidate_id")): decision
        for decision in decisions
    }
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    for record in records:
        key = (record["agent_id"], record["candidate"]["id"])
        decision = decision_map.get(key)
        if not decision:
            blocked.append(_issue(record, "missing_decision"))
            continue
        value = str(decision.get("decision") or "pending")
        if value in ACCEPTED_DECISIONS:
            if not decision.get("reviewed_by"):
                blocked.append(_issue(record, "missing_human_reviewer"))
                continue
            selected_candidate = _candidate_with_decision(record["candidate"], decision)
            selected_candidate["agent_id"] = record["agent_id"]
            selected_candidate["source_sidecar"] = record["source_sidecar"]
            selected.append(selected_candidate)
        else:
            skipped.append(_issue(record, value))
    status = "success" if selected and not blocked and not skipped else "partial"
    if not selected and not blocked:
        status = "blocked_pending_author_review"
    if blocked:
        status = "blocked"
    selected_doc = {
        "stage24_selected_candidates": {
            "schema_version": SCHEMA_VERSION,
            "source_decisions": str(decisions_path),
            "source_candidate_sidecars": [str(path) for path in candidate_paths],
            "human_approval_required": True,
            "selected_count": len(selected),
            "candidates": selected,
            "metadata": {
                "prompt_retained": False,
                "raw_response_retained": False,
                "provider_body_retained": False,
                "full_source_text_retained": False,
            },
        }
    }
    write_yaml(selected_doc, selected_candidates_path)
    report = {
        "stage24_candidate_apply_report": {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "source_decisions": str(decisions_path),
            "selected_candidates": str(selected_candidates_path),
            "source_candidate_sidecars": [str(path) for path in candidate_paths],
            "selected_count": len(selected),
            "skipped_count": len(skipped),
            "blocked_count": len(blocked),
            "selected_candidate_ids": [
                item["id"] for item in selected
            ],
            "skipped": skipped,
            "blocked": blocked,
            "selected_candidates_hash": f"sha256:{_file_sha(selected_candidates_path)}",
            "metadata": {
                "prompt_retained": False,
                "raw_response_retained": False,
                "provider_body_retained": False,
            },
        }
    }
    write_yaml(report, report_path)
    return report


def _candidate_records(candidate_paths: list[str | Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in candidate_paths:
        doc = read_yaml(path)
        root = next((name for name in AGENT_ROOTS if name in doc), "")
        if not root:
            continue
        body = doc[root]
        agent_id = body.get("agent_id", root.removesuffix("_candidates"))
        for candidate in body.get("candidates", []):
            records.append(
                {
                    "agent_id": agent_id,
                    "source_sidecar": str(path),
                    "candidate": candidate,
                }
            )
    return records


def _render_packet(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage 24 Kimi Candidate Author Review",
        "",
        "Review each candidate and edit the decisions YAML. Valid decisions: `accept`, `edit`, `reject`, `pending`.",
        "",
    ]
    for record in records:
        candidate = record["candidate"]
        lines.extend(
            [
                f"## {record['agent_id']} / {candidate.get('id')}",
                "",
                f"- Type: `{candidate.get('type')}`",
                f"- Target: `{candidate.get('target')}`",
                f"- Requires author approval: `{candidate.get('requires_author_approval')}`",
                f"- AI inferred: `{candidate.get('ai_tags', {}).get('inferred')}`",
                f"- Confidence: `{candidate.get('confidence')}`",
                f"- Proposed text: {candidate.get('proposed_text')}",
                f"- Rationale: {candidate.get('rationale')}",
                "",
            ]
        )
    return "\n".join(lines)


def _candidate_with_decision(
    candidate: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    selected = dict(candidate)
    if decision.get("decision") == "edit" and decision.get("edited_text"):
        selected["proposed_text"] = str(decision["edited_text"])
    selected["human_decision"] = {
        "decision": decision.get("decision"),
        "reviewed_by": decision.get("reviewed_by", ""),
        "review_notes": decision.get("review_notes", ""),
    }
    return selected


def _issue(record: dict[str, Any], code: str) -> dict[str, str]:
    return {
        "agent_id": str(record["agent_id"]),
        "candidate_id": str(record["candidate"].get("id", "")),
        "code": code,
    }


def _file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
