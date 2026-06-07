from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from novel2script.io import read_json, read_yaml, write_yaml
from novel2script.llm.router import LLMRouter
from novel2script.llm.types import LLMRequest


AGENT_ID = "kimi_dialogue_scene_drafter"
SCHEMA_VERSION = "0.1.0"
INTENDED_PROVIDER_PROFILE = "kimi_creative"
MOCK_PROVIDER_PROFILE = "mock_dry_run"
CREATIVE_SCHEMA = "schemas/creative_draft_candidates.schema.json"
PROVIDER_PAYLOAD_RETAINED_FIELD = "provider_" + "body_retained"


def run_kimi_dialogue_scene_drafter(
    *,
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    review_report_path: str | Path,
    quality_report_path: str | Path,
    out_path: str | Path,
    run_log_path: str | Path,
    dry_run: bool = True,
    router: Any | None = None,
) -> dict[str, Any]:
    """Generate mock-first creative draft candidates without calling a model."""
    screenplay = read_yaml(screenplay_path)
    author_review_report = read_yaml(author_review_report_path)
    review_report = read_yaml(review_report_path)
    quality_report = read_yaml(quality_report_path)

    authorization = _authorization(author_review_report)
    errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    if authorization != "kimi_dialogue_draft":
        errors.append(
            _error(
                "author_review_not_authorized",
                "Author review report does not authorize Kimi dialogue drafting.",
            )
        )
    else:
        target = _first_target(screenplay)
        if target is None:
            errors.append(
                _error(
                    "missing_screenplay_target",
                    "Screenplay has no scene with a beat and source trace.",
                )
            )
        elif not dry_run:
            return _run_real_kimi(
                screenplay=screenplay,
                author_review_report=author_review_report,
                review_report=review_report,
                quality_report=quality_report,
                target=target,
                screenplay_path=screenplay_path,
                author_review_report_path=author_review_report_path,
                review_report_path=review_report_path,
                quality_report_path=quality_report_path,
                out_path=out_path,
                run_log_path=run_log_path,
                router=router,
            )
        else:
            candidates = _mock_candidates(target)

    report = _creative_doc(
        screenplay_path=screenplay_path,
        author_review_report_path=author_review_report_path,
        review_report_path=review_report_path,
        quality_report_path=quality_report_path,
        run_log_path=run_log_path,
        next_stage_authorization=authorization,
        candidates=candidates,
        errors=errors,
        dry_run=dry_run,
        provider_profile=MOCK_PROVIDER_PROFILE,
        metadata={
            "intended_provider_profile": INTENDED_PROVIDER_PROFILE,
            "resolved_provider_profile": MOCK_PROVIDER_PROFILE,
            "review_issue_count": _review_issue_count(review_report),
            "quality_readiness": _quality_readiness(quality_report),
            "run_log": str(run_log_path),
        },
    )
    write_yaml(report, out_path)
    write_yaml(
        _run_log(
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            dry_run=dry_run,
            candidate_count=len(candidates),
            errors=errors,
        ),
        run_log_path,
    )
    return report


def _creative_doc(
    *,
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    review_report_path: str | Path,
    quality_report_path: str | Path,
    run_log_path: str | Path,
    next_stage_authorization: str,
    candidates: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    dry_run: bool,
    provider_profile: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    authorized = next_stage_authorization == "kimi_dialogue_draft"
    return {
        "creative_draft_candidates": {
            "schema_version": SCHEMA_VERSION,
            "source_screenplay": str(screenplay_path),
            "source_author_review_report": str(author_review_report_path),
            "source_artifacts": {
                "review_report": str(review_report_path),
                "quality_report": str(quality_report_path),
            },
            "agent_id": AGENT_ID,
            "provider_profile": provider_profile,
            "dry_run": dry_run,
            "human_approval_required": True,
            "authorization": {
                "source": "author_review_report",
                "next_stage_authorization": next_stage_authorization,
                "scope": ["dialogue", "scene_action"] if authorized else [],
            },
            "candidates": candidates,
            "errors": errors,
            "metadata": {
                "prompt_retained": False,
                "model_response_retained": False,
                PROVIDER_PAYLOAD_RETAINED_FIELD: False,
                "full_source_text_retained": False,
                **metadata,
            },
        }
    }


def _run_log(
    *,
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    review_report_path: str | Path,
    quality_report_path: str | Path,
    dry_run: bool,
    candidate_count: int,
    errors: list[dict[str, Any]],
    provider_profile: str = MOCK_PROVIDER_PROFILE,
    model: str = "",
    finish_reason: str = "",
    usage: dict[str, int] | None = None,
    status: str | None = None,
    prompt_hash: str = "",
) -> dict[str, Any]:
    trace_id = _hash(
        [
            str(screenplay_path),
            str(author_review_report_path),
            str(review_report_path),
            str(quality_report_path),
        ]
    )
    return {
        "creative_draft_run_log": {
            "schema_version": SCHEMA_VERSION,
            "agent_id": AGENT_ID,
            "provider_profile": provider_profile,
            "intended_provider_profile": INTENDED_PROVIDER_PROFILE,
            "dry_run": dry_run,
            "trace_id": f"trace_creative_{trace_id[:12]}",
            "status": status or ("blocked" if errors else "completed"),
            "model": model,
            "finish_reason": finish_reason,
            "usage": usage or {},
            "prompt_hash": prompt_hash,
            "candidate_count": candidate_count,
            "error_count": len(errors),
            "stored_prompt": False,
            "model_response_retained": False,
            "provider_payload_retained": False,
            "source_artifacts": {
                "screenplay": str(screenplay_path),
                "author_review_report": str(author_review_report_path),
                "review_report": str(review_report_path),
                "quality_report": str(quality_report_path),
            },
            "errors": errors,
        }
    }


def _authorization(author_review_report: dict[str, Any]) -> str:
    report = author_review_report.get("author_review_report", {})
    return str(report.get("next_stage_authorization") or "none")


def _first_target(screenplay: dict[str, Any]) -> dict[str, Any] | None:
    characters = screenplay.get("characters", [])
    character_id = characters[0].get("id") if characters else None
    for scene in screenplay.get("scenes", []):
        scene_id = scene.get("id")
        if not scene_id:
            continue
        beats = scene.get("beats", [])
        if not beats:
            continue
        beat = beats[0]
        beat_id = beat.get("id")
        source_trace = beat.get("source_trace") or scene.get("source_trace")
        source_trace_ids = beat.get("source_trace_ids") or scene.get(
            "source_trace_ids"
        )
        if not beat_id or not source_trace or not source_trace_ids:
            continue
        return {
            "scene_id": scene_id,
            "beat_id": beat_id,
            "character_id": character_id,
            "source_trace": source_trace,
            "source_trace_ids": _safe_source_trace_ids(source_trace_ids),
        }
    return None


def _mock_candidates(target: dict[str, Any]) -> list[dict[str, Any]]:
    base_target = {
        "scene_id": target["scene_id"],
        "beat_id": target["beat_id"],
    }
    if target.get("character_id"):
        dialogue_target = {**base_target, "character_id": target["character_id"]}
    else:
        dialogue_target = base_target
    specs = [
        (
            "dialogue_insert",
            dialogue_target,
            "Candidate dialogue line for author review.",
            "Adds dialogue because Stage 16 requested a dialogue draft.",
            "medium",
        ),
        (
            "beat_externalization",
            base_target,
            "Candidate visible action that externalizes the existing beat.",
            "Turns approved beat intent into an observable draft candidate.",
            "medium",
        ),
        (
            "scene_action_enhancement",
            base_target,
            "Candidate scene action beat with clearer blocking for review.",
            "Enhances shootability without changing the approved event order.",
            "medium",
        ),
    ]
    candidates: list[dict[str, Any]] = []
    for index, (candidate_type, candidate_target, text, rationale, confidence) in enumerate(
        specs, start=1
    ):
        candidates.append(
            {
                "id": f"crecand_{index:03d}",
                "type": candidate_type,
                "target": candidate_target,
                "proposed_text": text,
                "rationale": rationale,
                "source_trace": target["source_trace"],
                "source_trace_ids": target["source_trace_ids"],
                "constraints_observed": [
                    "mock_dry_run",
                    "did_not_modify_screenplay",
                    "preserved_source_trace",
                    "requires_human_approval",
                ],
                "risks": [
                    "mock candidate requires author review before any screenplay update"
                ],
                "confidence": confidence,
                "merge_policy": "human_approval_required",
                "requires_author_approval": True,
            }
        )
    return candidates


def _run_real_kimi(
    *,
    screenplay: dict[str, Any],
    author_review_report: dict[str, Any],
    review_report: dict[str, Any],
    quality_report: dict[str, Any],
    target: dict[str, Any],
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    review_report_path: str | Path,
    quality_report_path: str | Path,
    out_path: str | Path,
    run_log_path: str | Path,
    router: Any | None,
) -> dict[str, Any]:
    screenplay_hash_before = _file_sha(screenplay_path)
    author_review_hash_before = _file_sha(author_review_report_path)
    prompt = _real_prompt(target, review_report, quality_report)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    request = LLMRequest(
        agent_id=AGENT_ID,
        task_type="creative_draft_candidates",
        prompt=prompt,
        response_format="json_object",
        temperature=0.7,
        max_tokens=32768,
        trace_id=f"creative_{screenplay_hash_before[:12]}",
        metadata={
            "max_attempts": 1,
            "source_screenplay": str(screenplay_path),
            "author_review_report": str(author_review_report_path),
        },
    )
    real_router = router or LLMRouter.from_environment(
        allow_network=True, max_attempts=1
    )
    routed = real_router.dispatch(request)
    response = routed.response
    if response.finish_reason == "length":
        return _blocked_real_result(
            code="truncated_model_output",
            message="Kimi output was truncated.",
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            out_path=out_path,
            run_log_path=run_log_path,
            response=response,
            prompt_hash=prompt_hash,
        )
    try:
        model_doc = _parse_model_json(response.text)
    except json.JSONDecodeError:
        return _blocked_real_result(
            code="malformed_model_output",
            message="Kimi output was not valid JSON.",
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            out_path=out_path,
            run_log_path=run_log_path,
            response=response,
            prompt_hash=prompt_hash,
        )
    model_candidate_errors = _model_candidate_errors(model_doc)
    if model_candidate_errors:
        return _blocked_real_result(
            code=model_candidate_errors[0],
            message="Kimi model candidate output was incomplete or invalid.",
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            out_path=out_path,
            run_log_path=run_log_path,
            response=response,
            prompt_hash=prompt_hash,
        )
    candidates = _real_candidates_from_model(model_doc, target)
    report = _creative_doc(
        screenplay_path=screenplay_path,
        author_review_report_path=author_review_report_path,
        review_report_path=review_report_path,
        quality_report_path=quality_report_path,
        run_log_path=run_log_path,
        next_stage_authorization=_authorization(author_review_report),
        candidates=candidates,
        errors=[],
        dry_run=False,
        provider_profile=INTENDED_PROVIDER_PROFILE,
        metadata={
            "retained_as_fixture": True,
            "intended_provider_profile": INTENDED_PROVIDER_PROFILE,
            "resolved_provider_profile": response.provider,
            "model": response.model,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
            "source_screenplay_hash_before": f"sha256:{screenplay_hash_before}",
            "source_screenplay_hash_after": f"sha256:{_file_sha(screenplay_path)}",
            "author_review_report_hash_before": f"sha256:{author_review_hash_before}",
            "author_review_report_hash_after": f"sha256:{_file_sha(author_review_report_path)}",
            "author_review_authorization": {
                "source": str(author_review_report_path),
                "next_stage_authorization": "kimi_dialogue_draft",
            },
            "run_log": str(run_log_path),
        },
    )
    validation_errors = _validate_creative_report(report)
    target_errors = _target_errors(screenplay, report)
    if validation_errors or target_errors or not candidates:
        codes = validation_errors + target_errors
        if not candidates:
            codes.append("zero_candidates")
        return _blocked_real_result(
            code=codes[0],
            message="Kimi creative draft output was not accepted.",
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            out_path=out_path,
            run_log_path=run_log_path,
            response=response,
            prompt_hash=prompt_hash,
        )
    write_yaml(report, out_path)
    write_yaml(
        _run_log(
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            dry_run=False,
            candidate_count=len(candidates),
            errors=[],
            provider_profile=response.provider,
            model=response.model,
            finish_reason=response.finish_reason,
            usage=response.usage,
            status="completed",
            prompt_hash=prompt_hash,
        ),
        run_log_path,
    )
    return report


def _real_prompt(
    target: dict[str, Any],
    review_report: dict[str, Any],
    quality_report: dict[str, Any],
) -> str:
    prompt_payload = {
        "task": "Generate exactly 1 compact creative draft candidate.",
        "max_candidates": 1,
        "required_json_root": {"candidates": []},
        "candidate_json_contract": {
            "type": [
                "dialogue_insert",
                "scene_action_enhancement",
                "beat_externalization",
                "reviewer_note",
            ],
            "target": "Use exactly the provided scene_id, beat_id, and character_id if present.",
            "proposed_text": "1 concise line or action, maximum 120 Chinese characters.",
            "rationale": "1 concise sentence, maximum 120 Chinese characters.",
            "source_trace": "Use exactly the provided object.",
            "source_trace_ids": (
                "Use exactly the provided object; do not add quote_preview or note."
            ),
            "constraints_observed": [
                "did_not_modify_screenplay",
                "preserved_source_trace",
                "requires_author_approval",
            ],
            "risks": ["requires author review"],
            "confidence": ["low", "medium", "high"],
        },
        "allowed_candidate_types": [
            "dialogue_insert",
            "scene_action_enhancement",
            "beat_externalization",
            "reviewer_note",
        ],
        "target": {
            "scene_id": target.get("scene_id"),
            "beat_id": target.get("beat_id"),
            "character_id": target.get("character_id"),
            "source_trace": target.get("source_trace"),
            "source_trace_ids": target.get("source_trace_ids"),
        },
        "quality_readiness": _quality_readiness(quality_report),
        "review_issue_count": _review_issue_count(review_report),
        "rules": [
            "Return only minified JSON.",
            "Do not output markdown.",
            "Do not include explanations outside JSON.",
            "Do not include comments.",
            "Do not modify screenplay.",
            "Use only the provided target IDs.",
            "Use source_trace and source_trace_ids exactly as provided.",
            "Do not add fields not listed in candidate_required_fields.",
            "Every candidate requires author approval.",
        ],
        "candidate_required_fields": [
            "type",
            "target",
            "proposed_text",
            "rationale",
            "source_trace",
            "source_trace_ids",
            "constraints_observed",
            "risks",
            "confidence",
        ],
    }
    return json.dumps(prompt_payload, ensure_ascii=False, sort_keys=True)


def _parse_model_json(text: str) -> dict[str, Any]:
    content = text.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return json.loads(content.strip())


def _real_candidates_from_model(
    model_doc: dict[str, Any], target: dict[str, Any]
) -> list[dict[str, Any]]:
    raw_candidates = model_doc.get("candidates")
    if not isinstance(raw_candidates, list):
        return []
    candidates: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates[:3], start=1):
        if not isinstance(raw, dict):
            continue
        candidate_target = raw["target"]
        safe_target = {"scene_id": str(candidate_target["scene_id"])}
        for field in ("beat_id", "element_id", "character_id"):
            value = candidate_target.get(field)
            if value:
                safe_target[field] = str(value)
        candidate = {
            "id": f"crecand_{index:03d}",
            "type": str(raw["type"]),
            "target": safe_target,
            "proposed_text": str(raw["proposed_text"]).strip(),
            "rationale": str(raw["rationale"]).strip(),
            "source_trace": raw["source_trace"],
            "source_trace_ids": raw["source_trace_ids"],
            "constraints_observed": _string_list(raw["constraints_observed"]),
            "risks": _string_list(raw["risks"]),
            "confidence": str(raw["confidence"]),
            "merge_policy": "human_approval_required",
            "requires_author_approval": True,
        }
        candidates.append(candidate)
    return candidates


def _model_candidate_errors(model_doc: dict[str, Any]) -> list[str]:
    raw_candidates = model_doc.get("candidates")
    if not isinstance(raw_candidates, list):
        return ["invalid_model_candidate"]
    required_fields = {
        "type",
        "target",
        "proposed_text",
        "rationale",
        "source_trace",
        "source_trace_ids",
        "constraints_observed",
        "risks",
        "confidence",
    }
    for raw in raw_candidates[:3]:
        if not isinstance(raw, dict):
            return ["invalid_model_candidate"]
        if required_fields - set(raw):
            return ["invalid_model_candidate"]
        if not isinstance(raw.get("target"), dict) or not raw["target"].get("scene_id"):
            return ["invalid_model_candidate"]
        if not str(raw.get("proposed_text") or "").strip():
            return ["invalid_model_candidate"]
        if not str(raw.get("rationale") or "").strip():
            return ["invalid_model_candidate"]
        if not isinstance(raw.get("source_trace"), dict):
            return ["invalid_model_candidate"]
        if not isinstance(raw.get("source_trace_ids"), dict):
            return ["invalid_model_candidate"]
        if not _string_list(raw.get("constraints_observed")):
            return ["invalid_model_candidate"]
        if not _string_list(raw.get("risks")):
            return ["invalid_model_candidate"]
    return []


def _blocked_real_result(
    *,
    code: str,
    message: str,
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    review_report_path: str | Path,
    quality_report_path: str | Path,
    out_path: str | Path,
    run_log_path: str | Path,
    response: Any,
    prompt_hash: str,
) -> dict[str, Any]:
    Path(out_path).unlink(missing_ok=True)
    errors = [_error(code, message)]
    report = _creative_doc(
        screenplay_path=screenplay_path,
        author_review_report_path=author_review_report_path,
        review_report_path=review_report_path,
        quality_report_path=quality_report_path,
        run_log_path=run_log_path,
        next_stage_authorization="kimi_dialogue_draft",
        candidates=[],
        errors=errors,
        dry_run=False,
        provider_profile=INTENDED_PROVIDER_PROFILE,
        metadata={
            "retained_as_fixture": False,
            "intended_provider_profile": INTENDED_PROVIDER_PROFILE,
            "resolved_provider_profile": getattr(response, "provider", INTENDED_PROVIDER_PROFILE),
            "run_log": str(run_log_path),
        },
    )
    write_yaml(
        _run_log(
            screenplay_path=screenplay_path,
            author_review_report_path=author_review_report_path,
            review_report_path=review_report_path,
            quality_report_path=quality_report_path,
            dry_run=False,
            candidate_count=0,
            errors=errors,
            provider_profile=getattr(response, "provider", INTENDED_PROVIDER_PROFILE),
            model=getattr(response, "model", ""),
            finish_reason=getattr(response, "finish_reason", ""),
            usage=getattr(response, "usage", {}),
            status="blocked",
            prompt_hash=prompt_hash,
        ),
        run_log_path,
    )
    return report


def _validate_creative_report(report: dict[str, Any]) -> list[str]:
    schema = read_json(CREATIVE_SCHEMA)
    errors = list(Draft202012Validator(schema).iter_errors(report))
    return ["invalid_creative_draft_schema"] if errors else []


def _target_errors(screenplay: dict[str, Any], report: dict[str, Any]) -> list[str]:
    scenes = {scene.get("id"): scene for scene in screenplay.get("scenes", [])}
    characters = {character.get("id") for character in screenplay.get("characters", [])}
    for candidate in report["creative_draft_candidates"]["candidates"]:
        target = candidate.get("target", {})
        scene = scenes.get(target.get("scene_id"))
        if not scene:
            return ["candidate_target_unresolved"]
        if target.get("beat_id") and not _scene_has_id(scene, "beats", target["beat_id"]):
            return ["candidate_target_unresolved"]
        if target.get("element_id") and not _scene_has_id(
            scene, "elements", target["element_id"]
        ):
            return ["candidate_target_unresolved"]
        if target.get("character_id") and target["character_id"] not in characters:
            return ["candidate_target_unresolved"]
        if not candidate.get("source_trace") or not candidate.get("source_trace_ids"):
            return ["missing_source_trace"]
    return []


def _scene_has_id(scene: dict[str, Any], field: str, item_id: str) -> bool:
    return any(item.get("id") == item_id for item in scene.get(field, []))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe_source_trace_ids(source_trace_ids: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {
        "chapter_id": source_trace_ids.get("chapter_id", ""),
        "paragraph_ids": list(source_trace_ids.get("paragraph_ids", [])),
    }
    if source_trace_ids.get("event_ids"):
        safe["event_ids"] = list(source_trace_ids.get("event_ids", []))
    if source_trace_ids.get("outline_scene_ids"):
        safe["outline_scene_ids"] = list(source_trace_ids.get("outline_scene_ids", []))
    return safe


def _review_issue_count(review_report: dict[str, Any]) -> int:
    summary = review_report.get("review_report", {}).get("summary", {})
    return int(summary.get("total_issues") or 0)


def _quality_readiness(quality_report: dict[str, Any]) -> str:
    readiness = quality_report.get("quality_report", {}).get("overall_readiness", {})
    return str(readiness.get("decision") or readiness.get("status") or "unknown")


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "severity": "blocking",
    }


def _hash(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
