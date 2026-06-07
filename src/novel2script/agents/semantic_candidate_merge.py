from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from novel2script.io import read_json, read_yaml, write_yaml


SCHEMA_VERSION = "0.1.0"
MERGE_PROFILE = "deterministic_semantic_candidate_merge_v0"
ROOT = Path(__file__).resolve().parents[3]

TYPE_TARGETS = {
    "character_candidate": ("characters_detected", "char"),
    "location_candidate": ("locations_detected", "loc"),
    "prop_candidate": ("props_detected", "prop"),
    "event_candidate": ("key_events", "evt"),
    "timeline_candidate": ("timeline", "tl"),
    "psychological_passage_candidate": ("psychological_passages", "psy"),
}


def merge_semantic_candidates(
    story_map_path: str | Path,
    semantic_candidates_path: str | Path,
    decisions_path: str | Path,
    *,
    out_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    story_map_path = Path(story_map_path)
    semantic_candidates_path = Path(semantic_candidates_path)
    decisions_path = Path(decisions_path)
    out_path = Path(out_path)
    report_path = Path(report_path)

    story_map_doc = read_yaml(story_map_path)
    semantic_doc = read_yaml(semantic_candidates_path)
    decisions_doc = read_yaml(decisions_path)
    original = deepcopy(story_map_doc)
    updated = deepcopy(story_map_doc)

    story_map_errors = _validate_schema(
        story_map_doc,
        "story_map.schema.json",
        "story_map",
    )
    semantic_errors = _validate_schema(
        semantic_doc,
        "semantic_candidates.schema.json",
        "semantic_candidates",
    )
    decision_schema_errors = _validate_schema(
        decisions_doc,
        "semantic_candidate_decisions.schema.json",
        "semantic_candidate_decisions",
    )
    global_errors = story_map_errors + semantic_errors + decision_schema_errors
    if _same_path(out_path, story_map_path):
        global_errors.append(
            _error(
                "output_path_conflicts_with_source",
                "Merged output path must differ from the source story map path.",
                action="blocked",
            )
        )

    semantic_root = (
        semantic_doc.get("semantic_candidates", {})
        if isinstance(semantic_doc, dict)
        else {}
    )
    decision_root = (
        decisions_doc.get("semantic_candidate_decisions", {})
        if isinstance(decisions_doc, dict)
        else {}
    )
    candidates = semantic_root.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    decision_records = decision_root.get("decisions", [])
    if not isinstance(decision_records, list):
        decision_records = []

    decisions: dict[str, dict[str, Any]] = {}
    if not decision_schema_errors:
        decision_groups: dict[str, list[dict[str, Any]]] = {}
        for decision in decision_records:
            candidate_id = decision.get("candidate_id")
            if candidate_id:
                decision_groups.setdefault(candidate_id, []).append(decision)
        for candidate_id, grouped_decisions in decision_groups.items():
            if len(grouped_decisions) > 1:
                global_errors.append(
                    _error(
                        "duplicate_candidate_decision",
                        f"Candidate {candidate_id} has multiple human decisions.",
                        action="blocked",
                    )
                )
            else:
                decisions[candidate_id] = grouped_decisions[0]

    candidate_ids = {
        candidate.get("id")
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("id")
    }
    if not semantic_errors and not decision_schema_errors:
        for decision in decision_records:
            candidate_id = decision.get("candidate_id")
            if candidate_id not in candidate_ids:
                global_errors.append(
                    _error(
                        "unknown_candidate",
                        f"Decision references unknown candidate {candidate_id}.",
                        severity="medium",
                        candidate_id=candidate_id,
                        action="skipped",
                    )
                )

    reviewer = str(decision_root.get("reviewed_by") or "unreviewed")
    reviewed_at = str(decision_root.get("reviewed_at") or "unreviewed")
    trace_index = _story_trace_index(story_map_doc)

    results: list[dict[str, Any]] = []
    preflight_blocked = any(
        error.get("action") == "blocked" or error.get("severity") == "high"
        for error in global_errors
    )
    if not preflight_blocked:
        for candidate in candidates:
            result, item = _handle_candidate(
                updated,
                candidate,
                decisions.get(candidate.get("id")),
                trace_index,
                reviewer=reviewer,
                reviewed_at=reviewed_at,
            )
            results.append(result)
            if item is not None:
                updated["story_map"][result["target_story_map_field"]].append(item)

    result_errors = [
        error for result in results for error in result.get("errors", [])
    ]
    blocking_errors = [
        error
        for error in global_errors + result_errors
        if error.get("action") == "blocked" or error.get("severity") == "high"
    ]
    should_write_story_map = not blocking_errors
    if should_write_story_map:
        validation_errors = _validate_schema(updated, "story_map.schema.json", "merged_story_map")
        if validation_errors:
            global_errors.extend(validation_errors)
            blocking_errors.extend(validation_errors)
            should_write_story_map = False

    summary = _summary(candidates, decision_records, results, global_errors)
    if blocking_errors:
        status = "blocked"
    elif summary["skipped"]:
        status = "partial"
    else:
        status = "success"

    if should_write_story_map:
        write_yaml(updated, out_path)
    else:
        _remove_stale_output(
            out_path,
            protected_paths={
                story_map_path,
                semantic_candidates_path,
                decisions_path,
            },
        )

    report = {
        "semantic_candidate_merge_report": {
            "schema_version": SCHEMA_VERSION,
            "source_story_map": str(story_map_path),
            "source_semantic_candidates": str(semantic_candidates_path),
            "decision_file": str(decisions_path),
            "output_story_map": str(out_path),
            "generated_at": _timestamp(),
            "merge_profile": MERGE_PROFILE,
            "status": status,
            "summary": summary,
            "decisions": results,
            "errors": global_errors + result_errors,
            "audit": {
                "preserved_original_story_map": True,
                "story_map_hash_before": _doc_hash(original),
                "story_map_hash_after": _doc_hash(updated if should_write_story_map else original),
                "semantic_candidates_hash": _file_hash(semantic_candidates_path),
                "decision_file_hash": _file_hash(decisions_path),
            },
        }
    }
    write_yaml(report, report_path)
    return report


def _handle_candidate(
    story_map_doc: dict[str, Any],
    candidate: dict[str, Any],
    decision: dict[str, Any] | None,
    trace_index: dict[str, set[str]],
    *,
    reviewer: str,
    reviewed_at: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    candidate_id = candidate.get("id", "")
    candidate_type = candidate.get("type", "")
    expected_target, prefix = TYPE_TARGETS.get(candidate_type, ("", ""))
    target = candidate.get("target_story_map_field", "")
    trace = candidate.get("source_trace_ids", {})
    errors: list[dict[str, Any]] = []
    requested_decision = decision.get("decision") if decision else "none"
    decision_id = decision.get("decision_id") if decision else "none"
    human_approval = (
        deepcopy(decision.get("human_approval"))
        if decision
        else {"approved": False, "reviewer_id": reviewer, "approved_at": reviewed_at}
    )

    base = {
        "decision_id": decision_id,
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "target_story_map_field": target or expected_target,
        "requested_decision": requested_decision,
        "outcome": "blocked",
        "human_approval": human_approval,
        "reviewer": human_approval.get("reviewer_id", reviewer),
        "reviewed_at": human_approval.get("approved_at", reviewed_at),
        "source_trace_ids": {
            "chapter_id": trace.get("chapter_id", ""),
            "paragraph_ids": list(trace.get("paragraph_ids", [])),
        },
        "candidate_hash": _doc_hash(candidate),
    }
    if decision and decision.get("reviewer_note"):
        base["reviewer_note"] = decision["reviewer_note"]

    if not decision:
        base["outcome"] = "skipped"
        base["errors"] = [
            _error(
                "missing_decision",
                f"Candidate {candidate_id} has no human decision.",
                severity="medium",
                candidate_id=candidate_id,
                action="skipped",
            )
        ]
        return base, None

    if target != expected_target or decision.get("target_story_map_field") != expected_target:
        errors.append(
            _error(
                "target_type_mismatch",
                f"Candidate {candidate_id} type {candidate_type} cannot merge into {target}.",
                candidate_id=candidate_id,
                action="blocked",
            )
        )
    if candidate.get("merge_policy") != "human_approval_required":
        errors.append(
            _error(
                "invalid_merge_policy",
                f"Candidate {candidate_id} does not require human approval.",
                candidate_id=candidate_id,
                action="blocked",
            )
        )
    if not _valid_trace(trace, trace_index):
        errors.append(
            _error(
                "invalid_source_trace",
                f"Candidate {candidate_id} source trace does not match story_map chapters.",
                candidate_id=candidate_id,
                action="blocked",
            )
        )

    if requested_decision == "reject":
        base["outcome"] = "rejected"
        if errors:
            base["outcome"] = "blocked"
            base["errors"] = errors
        return base, None

    if requested_decision in {"accept", "edit"} and not human_approval.get("approved"):
        errors.append(
            _error(
                "missing_human_approval",
                f"Candidate {candidate_id} cannot be merged without approval.",
                candidate_id=candidate_id,
                action="blocked",
            )
        )

    fields = (
        deepcopy(decision.get("edited_fields", {}))
        if requested_decision == "edit"
        else deepcopy(candidate.get("proposed_fields", {}))
    )
    item = None
    if not errors:
        item = _build_story_map_item(
            story_map_doc,
            candidate,
            fields,
            target=expected_target,
            prefix=prefix,
        )
        if item is None:
            errors.append(
                _error(
                    "insufficient_fields",
                    f"Candidate {candidate_id} lacks required fields for {expected_target}.",
                    candidate_id=candidate_id,
                    action="blocked",
                )
            )

    if errors:
        base["outcome"] = "blocked"
        base["errors"] = errors
        return base, None

    base["outcome"] = "edited" if requested_decision == "edit" else "accepted"
    base["created_id"] = item["id"]
    base["applied_yaml_path"] = (
        f"story_map.{expected_target}[{len(story_map_doc['story_map'][expected_target])}]"
    )
    return base, item


def _build_story_map_item(
    story_map_doc: dict[str, Any],
    candidate: dict[str, Any],
    fields: dict[str, Any],
    *,
    target: str,
    prefix: str,
) -> dict[str, Any] | None:
    item_id = _next_id(story_map_doc["story_map"].get(target, []), prefix)
    trace = _source_trace(candidate)
    confidence = candidate.get("confidence", "medium")
    if target == "key_events":
        summary = fields.get("summary")
        if not summary:
            return None
        return {
            "id": item_id,
            "sequence_index": len(story_map_doc["story_map"][target]) + 1,
            "summary": summary,
            "event_type": fields.get("event_type", "semantic_candidate"),
            "character_ids": _valid_ids(fields.get("character_ids", []), story_map_doc, "characters_detected"),
            "location_ids": _valid_ids(fields.get("location_ids", []), story_map_doc, "locations_detected"),
            "prop_ids": _valid_ids(fields.get("prop_ids", []), story_map_doc, "props_detected"),
            "source_trace": trace,
            "confidence": confidence,
        }
    if target == "timeline":
        label = fields.get("label") or fields.get("time_text")
        if not label:
            return None
        return {
            "id": item_id,
            "order": len(story_map_doc["story_map"][target]) + 1,
            "label": label,
            "time_text": fields.get("time_text", label),
            "event_ids": _valid_event_ids(fields.get("event_ids", []), story_map_doc),
            "source_trace": trace,
            "confidence": confidence,
        }
    if target == "psychological_passages":
        summary = fields.get("summary")
        if not summary:
            return None
        passage_type = fields.get("passage_type", "other")
        if passage_type not in {"emotion", "memory", "motivation", "fear", "desire", "other"}:
            passage_type = "other"
        return {
            "id": item_id,
            "character_ids": _valid_ids(fields.get("character_ids", []), story_map_doc, "characters_detected"),
            "passage_type": passage_type,
            "summary": summary,
            "externalization_hint": fields.get("externalization_hint", ""),
            "source_trace": trace,
            "confidence": confidence,
        }
    if target == "characters_detected":
        name = fields.get("name")
        if not name:
            return None
        return {
            "id": item_id,
            "name": name,
            "aliases": fields.get("aliases", []),
            "description_hint": fields.get("description_hint", ""),
            "first_seen": trace,
            "source_trace": trace,
            "confidence": confidence,
        }
    if target == "locations_detected":
        return _named_item(item_id, fields, trace, confidence, "location_type")
    if target == "props_detected":
        return _named_item(item_id, fields, trace, confidence, "prop_type")
    return None


def _named_item(
    item_id: str,
    fields: dict[str, Any],
    trace: dict[str, Any],
    confidence: str,
    type_key: str,
) -> dict[str, Any] | None:
    name = fields.get("name")
    if not name:
        return None
    item = {
        "id": item_id,
        "name": name,
        type_key: fields.get(type_key, "semantic_candidate"),
        "description_hint": fields.get("description_hint", ""),
        "source_trace": trace,
        "confidence": confidence,
    }
    return item


def _source_trace(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence = candidate.get("evidence", {})
    trace_ids = candidate.get("source_trace_ids", {})
    trace = {
        "chapter_id": trace_ids["chapter_id"],
        "paragraph_ids": list(trace_ids["paragraph_ids"]),
    }
    if evidence.get("quote_preview"):
        trace["quote_preview"] = evidence["quote_preview"]
    trace["note"] = f"Human-approved semantic candidate {candidate.get('id', '')}."
    return trace


def _story_trace_index(story_map_doc: dict[str, Any]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for chapter in story_map_doc.get("story_map", {}).get("chapters", []):
        index[chapter.get("id", "")] = {
            paragraph.get("id", "") for paragraph in chapter.get("paragraphs", [])
        }
    return index


def _valid_trace(trace: dict[str, Any], trace_index: dict[str, set[str]]) -> bool:
    chapter_id = trace.get("chapter_id")
    paragraph_ids = trace.get("paragraph_ids") or []
    return bool(
        chapter_id
        and paragraph_ids
        and chapter_id in trace_index
        and all(paragraph_id in trace_index[chapter_id] for paragraph_id in paragraph_ids)
    )


def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
    max_index = 0
    for item in items:
        item_id = str(item.get("id", ""))
        if item_id.startswith(f"{prefix}_"):
            try:
                max_index = max(max_index, int(item_id.split("_", 1)[1]))
            except ValueError:
                continue
    return f"{prefix}_{max_index + 1:03d}"


def _valid_ids(
    ids: list[str],
    story_map_doc: dict[str, Any],
    target: str,
) -> list[str]:
    existing = {item["id"] for item in story_map_doc["story_map"].get(target, [])}
    return [item_id for item_id in ids if item_id in existing]


def _valid_event_ids(ids: list[str], story_map_doc: dict[str, Any]) -> list[str]:
    return _valid_ids(ids, story_map_doc, "key_events")


def _summary(
    candidates: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    results: list[dict[str, Any]],
    global_errors: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "candidates_total": len(candidates),
        "decisions_total": len(decisions),
        "accepted": sum(1 for result in results if result["outcome"] == "accepted"),
        "rejected": sum(1 for result in results if result["outcome"] == "rejected"),
        "edited": sum(1 for result in results if result["outcome"] == "edited"),
        "skipped": (
            sum(1 for result in results if result["outcome"] == "skipped")
            + sum(1 for error in global_errors if error.get("action") == "skipped")
        ),
        "blocked": (
            sum(1 for result in results if result["outcome"] == "blocked")
            + sum(1 for error in global_errors if error.get("action") == "blocked")
        ),
        "applied_changes": sum(
            1 for result in results if result["outcome"] in {"accepted", "edited"}
        ),
    }


def _validate_schema(doc: Any, schema_name: str, label: str) -> list[dict[str, Any]]:
    schema = read_json(ROOT / "schemas" / schema_name)
    try:
        Draft202012Validator(schema).validate(doc)
    except ValidationError as exc:
        return [
            _error(
                f"invalid_{label}_schema",
                f"{label} failed schema validation: {exc.message}",
                action="blocked",
            )
        ]
    return []


def _error(
    code: str,
    message: str,
    *,
    severity: str = "high",
    candidate_id: str | None = None,
    action: str = "blocked",
) -> dict[str, Any]:
    error = {"code": code, "message": message, "severity": severity, "action": action}
    if candidate_id:
        error["candidate_id"] = candidate_id
    return error


def _doc_hash(doc: Any) -> str:
    payload = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def _remove_stale_output(out_path: Path, *, protected_paths: set[Path]) -> None:
    if any(_same_path(out_path, protected_path) for protected_path in protected_paths):
        return
    if out_path.is_file():
        out_path.unlink()


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
