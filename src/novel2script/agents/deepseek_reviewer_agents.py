from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from novel2script.io import read_json, read_yaml, write_yaml
from novel2script.llm.router import LLMRouter
from novel2script.llm.types import LLMRequest


SCHEMA_VERSION = "0.1.0"
INTENDED_PROVIDER_PROFILE = "deepseek_reasoning"
MOCK_PROVIDER_PROFILE = "mock_dry_run"
DEEPSEEK_REVIEWER_AGENT_IDS = (
    "beat_dramaturgy_agent",
    "source_fidelity_reviewer",
    "yaml_repair_agent",
)

AGENT_SPECS: dict[str, dict[str, Any]] = {
    "beat_dramaturgy_agent": {
        "root": "beat_dramaturgy_agent_candidates",
        "task_type": "beat_dramaturgy_candidates",
        "required_paths": ("screenplay_path",),
        "types": (
            "beat_objective_revision",
            "conflict_enhancement",
            "externalization_rewrite",
            "stakes_adjustment",
            "reviewer_note",
        ),
        "target_artifact": "screenplay",
        "mock_type": "externalization_rewrite",
        "mock_text": "建议重写第1场第2节拍动作：使角色的犹豫更明显，通过手指抓紧裙角的细节外化。",
    },
    "source_fidelity_reviewer": {
        "root": "source_fidelity_reviewer_candidates",
        "task_type": "source_fidelity_candidates",
        "required_paths": ("story_map_path", "outline_path", "screenplay_path"),
        "types": (
            "fidelity_warning",
            "missing_event_proposal",
            "hallucination_exclusion",
            "reviewer_note",
        ),
        "target_artifact": "screenplay",
        "mock_type": "fidelity_warning",
        "mock_text": "复核发现剧本第2场中新增的侍卫对话未在小说原文第1章查到依据，涉嫌轻微幻觉。",
    },
    "yaml_repair_agent": {
        "root": "yaml_repair_agent_candidates",
        "task_type": "yaml_repair_candidates",
        "required_paths": ("screenplay_path",),
        "types": (
            "syntax_repair",
            "field_alignment",
            "reference_fix",
            "reviewer_note",
        ),
        "target_artifact": "screenplay",
        "mock_type": "field_alignment",
        "mock_text": "检测到 screenplay.yaml 中的 validation_report 拼写错误，建议更正为规范结构。",
    },
}


def run_deepseek_reviewer_agent(
    *,
    agent_id: str,
    out_path: str | Path,
    run_log_path: str | Path,
    dry_run: bool = True,
    router: Any | None = None,
    story_map_path: str | Path | None = None,
    outline_path: str | Path | None = None,
    character_bible_path: str | Path | None = None,
    screenplay_path: str | Path | None = None,
    review_report_path: str | Path | None = None,
) -> dict[str, Any]:
    if agent_id not in AGENT_SPECS:
        raise ValueError(f"Unknown DeepSeek reviewer agent: {agent_id}")
    spec = AGENT_SPECS[agent_id]
    paths = {
        "story_map_path": story_map_path,
        "outline_path": outline_path,
        "character_bible_path": character_bible_path,
        "screenplay_path": screenplay_path,
        "review_report_path": review_report_path,
    }
    missing = [name for name in spec["required_paths"] if not paths.get(name)]
    if missing:
        raise ValueError(f"{agent_id} missing required inputs: {', '.join(missing)}")
    docs = {
        name.removesuffix("_path"): read_yaml(value)
        for name, value in paths.items()
        if value is not None
    }
    target = _target_for(agent_id, docs)
    if not target:
        errors = [_error("missing_candidate_target", "No review target found.")]
        report = _sidecar_doc(
            agent_id=agent_id,
            paths=paths,
            out_path=out_path,
            run_log_path=run_log_path,
            dry_run=dry_run,
            provider_profile=MOCK_PROVIDER_PROFILE,
            candidates=[],
            errors=errors,
            metadata={},
        )
        write_yaml(report, out_path)
        write_yaml(
            _run_log(
                agent_id=agent_id,
                paths=paths,
                dry_run=dry_run,
                provider_profile=MOCK_PROVIDER_PROFILE,
                candidate_count=0,
                errors=errors,
            ),
            run_log_path,
        )
        return report

    if dry_run:
        candidates = [_mock_candidate(agent_id, target)]
        errors: list[dict[str, Any]] = []
        provider_profile = MOCK_PROVIDER_PROFILE
        prompt_hash = ""
        model = ""
        finish_reason = ""
        usage: dict[str, int] = {}
    else:
        prompt = _real_prompt(agent_id, target, docs)
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        request = LLMRequest(
            agent_id=agent_id,
            task_type=spec["task_type"],
            prompt=prompt,
            response_format="json_object",
            temperature=0.2,
            max_tokens=4096,
            trace_id=f"{agent_id}_{_hash([str(out_path)])[:12]}",
            metadata={"max_attempts": 1, "source_artifacts": _source_artifacts(paths)},
        )
        real_router = router or LLMRouter.from_environment(
            allow_network=True, max_attempts=1
        )
        routed = real_router.dispatch(request)
        response = routed.response
        provider_profile = response.provider
        model = response.model
        finish_reason = response.finish_reason
        usage = response.usage
        candidates, errors = _parse_model_candidates(agent_id, target, response)
        if errors:
            Path(out_path).unlink(missing_ok=True)
            write_yaml(
                _run_log(
                    agent_id=agent_id,
                    paths=paths,
                    dry_run=False,
                    provider_profile=provider_profile,
                    candidate_count=0,
                    errors=errors,
                    model=model,
                    finish_reason=finish_reason,
                    usage=usage,
                    prompt_hash=prompt_hash,
                    status="blocked",
                ),
                run_log_path,
            )
            return _sidecar_doc(
                agent_id=agent_id,
                paths=paths,
                out_path=out_path,
                run_log_path=run_log_path,
                dry_run=False,
                provider_profile=INTENDED_PROVIDER_PROFILE,
                candidates=[],
                errors=errors,
                metadata={"retained_as_fixture": False},
            )

    report = _sidecar_doc(
        agent_id=agent_id,
        paths=paths,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=dry_run,
        provider_profile=provider_profile,
        candidates=candidates,
        errors=errors,
        metadata={
            "intended_provider_profile": INTENDED_PROVIDER_PROFILE,
            "resolved_provider_profile": provider_profile,
            "model": model,
            "finish_reason": finish_reason,
            "usage": usage,
        },
    )
    _validate_report(agent_id, report)
    write_yaml(report, out_path)
    write_yaml(
        _run_log(
            agent_id=agent_id,
            paths=paths,
            dry_run=dry_run,
            provider_profile=provider_profile,
            candidate_count=len(candidates),
            errors=errors,
            model=model,
            finish_reason=finish_reason,
            usage=usage,
            prompt_hash=prompt_hash,
        ),
        run_log_path,
    )
    return report


def _sidecar_doc(
    *,
    agent_id: str,
    paths: dict[str, str | Path | None],
    out_path: str | Path,
    run_log_path: str | Path,
    dry_run: bool,
    provider_profile: str,
    candidates: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    root = AGENT_SPECS[agent_id]["root"]
    return {
        root: {
            "schema_version": SCHEMA_VERSION,
            "agent_id": agent_id,
            "provider_profile": provider_profile,
            "dry_run": dry_run,
            "human_approval_required": True,
            "source_artifacts": _source_artifacts(paths),
            "candidates": candidates,
            "errors": errors,
            "metadata": {
                "prompt_retained": False,
                "model_response_retained": False,
                "provider_payload_retained": False,
                "full_source_text_retained": False,
                "run_log": str(run_log_path),
                "output": str(out_path),
                **metadata,
            },
        }
    }


def _run_log(
    *,
    agent_id: str,
    paths: dict[str, str | Path | None],
    dry_run: bool,
    provider_profile: str,
    candidate_count: int,
    errors: list[dict[str, Any]],
    model: str = "",
    finish_reason: str = "",
    usage: dict[str, int] | None = None,
    prompt_hash: str = "",
    status: str | None = None,
) -> dict[str, Any]:
    return {
        f"{agent_id}_run_log": {
            "schema_version": SCHEMA_VERSION,
            "agent_id": agent_id,
            "provider_profile": provider_profile,
            "intended_provider_profile": INTENDED_PROVIDER_PROFILE,
            "dry_run": dry_run,
            "trace_id": f"trace_{agent_id}_{_hash(list(_source_artifacts(paths).values()))[:12]}",
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
            "source_artifacts": _source_artifacts(paths),
            "errors": errors,
        }
    }


def _source_artifacts(paths: dict[str, str | Path | None]) -> dict[str, str]:
    return {
        name.removesuffix("_path"): str(value)
        for name, value in paths.items()
        if value is not None
    }


def _target_for(agent_id: str, docs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if agent_id == "yaml_repair_agent":
        return {
            "artifact": "screenplay",
            "path": "screenplay.metadata",
            "source_trace": {},
            "source_trace_ids": {},
        }
    screenplay = docs.get("screenplay", {})
    if not screenplay:
        return None
    scenes = screenplay.get("scenes", [])
    if not scenes:
        return None
    scene = scenes[0]
    scene_id = scene.get("id", "scene_001")
    trace = _first_trace(scene.get("source_trace_ids") or scene.get("source_trace"))
    target = {
        "artifact": "screenplay",
        "scene_id": scene_id,
        "path": "scenes[0]",
        "source_trace": trace or {},
        "source_trace_ids": _trace_ids(trace) if trace else {},
    }
    beats = scene.get("beats", [])
    if beats:
        target["beat_id"] = beats[0].get("id", "beat_001")
        target["path"] = "scenes[0].beats[0]"
    elements = scene.get("elements", [])
    if elements:
        target["element_id"] = elements[0].get("id", "elem_001")
        if elements[0].get("character_id"):
            target["character_id"] = elements[0]["character_id"]
    return target


def _first_trace(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list) and value:
        return value[0] if isinstance(value[0], dict) else None
    if isinstance(value, dict):
        return value
    return None


def _trace_ids(trace: dict[str, Any]) -> dict[str, Any]:
    if trace.get("chapter_id"):
        return {
            "chapter_id": str(trace.get("chapter_id")),
            "paragraph_ids": [str(item) for item in trace.get("paragraph_ids", [])],
        }
    if trace.get("chapter") and trace.get("paragraph_range"):
        paragraph_range = trace["paragraph_range"]
        start = int(paragraph_range[0])
        return {
            "chapter_id": f"ch_{int(trace['chapter']):03d}",
            "paragraph_ids": [f"p_{start:03d}"],
        }
    return {}


def _mock_candidate(agent_id: str, target: dict[str, Any]) -> dict[str, Any]:
    spec = AGENT_SPECS[agent_id]
    candidate_target = {
        key: value
        for key, value in target.items()
        if key
        in {
            "artifact",
            "path",
            "scene_id",
            "beat_id",
            "element_id",
            "character_id",
        }
        and value
    }
    return {
        "id": f"{_prefix(agent_id)}_001",
        "type": spec["mock_type"],
        "target": candidate_target,
        "proposed_text": spec["mock_text"],
        "proposed_change": {"summary": spec["mock_text"]},
        "rationale": "Mock dry-run reviewer candidate requires human approval before merge.",
        "source_trace": target.get("source_trace", {}),
        "source_trace_ids": target.get("source_trace_ids", {}),
        "ai_tags": {
            "inferred": True,
            "confidence": "medium",
            "needs_human_review": True,
            "notes": ["Mock dry-run reviewer tag."],
        },
        "constraints_observed": [
            "preserved_source_trace",
            "did_not_modify_source_artifacts",
            "requires_author_approval",
        ],
        "risks": ["requires review before merge"],
        "confidence": "medium",
        "merge_policy": "human_approval_required",
        "requires_author_approval": True,
    }


def _real_prompt(
    agent_id: str, target: dict[str, Any], docs: dict[str, dict[str, Any]]
) -> str:
    spec = AGENT_SPECS[agent_id]
    payload = {
        "agent_id": agent_id,
        "task": f"Analyze screenplay and generate exactly 1 {agent_id} review candidate.",
        "allowed_types": list(spec["types"]),
        "target": {
            key: target.get(key)
            for key in (
                "artifact",
                "path",
                "scene_id",
                "beat_id",
                "element_id",
                "character_id",
                "source_trace",
                "source_trace_ids",
            )
            if target.get(key)
        },
        "output_contract": {
            "root": {"candidates": []},
            "candidate_required_fields": [
                "type",
                "target",
                "proposed_text",
                "rationale",
                "source_trace",
                "source_trace_ids",
                "ai_tags",
                "constraints_observed",
                "risks",
                "confidence",
            ],
            "ai_tags": {
                "inferred": True,
                "confidence": ["low", "medium", "high"],
                "needs_human_review": True,
            },
        },
        "rules": [
            "Return only minified JSON.",
            "Do not output Markdown fences.",
            "Do not modify screenplay directly.",
            "Generate patch suggestion in proposed_text.",
        ],
        "context_info": {
            "story_map_keys": list(docs.get("story_map", {}).keys()),
            "screenplay_keys": list(docs.get("screenplay", {}).keys()),
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _parse_model_candidates(
    agent_id: str, target: dict[str, Any], response: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if response.finish_reason == "length":
        return [], [_error("truncated_model_output", "DeepSeek output was truncated.")]
    try:
        model_doc = _parse_model_json(response.text)
    except json.JSONDecodeError:
        return [], [_error("malformed_model_output", "DeepSeek output was not valid JSON.")]
    raw_candidates = model_doc.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        return [], [_error("invalid_model_candidate", "DeepSeek returned no candidates.")]
    candidates: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates[:1], start=1):
        if not isinstance(raw, dict):
            return [], [_error("invalid_model_candidate", "Candidate is not an object.")]
        for field in (
            "type",
            "target",
            "proposed_text",
            "rationale",
            "source_trace",
            "source_trace_ids",
            "ai_tags",
            "constraints_observed",
            "risks",
            "confidence",
        ):
            if field not in raw:
                return [], [_error("invalid_model_candidate", f"Missing {field}.")]
        if raw["type"] not in AGENT_SPECS[agent_id]["types"]:
            return [], [_error("invalid_model_candidate", "Unsupported candidate type.")]
        ai_tags = raw.get("ai_tags")
        if not isinstance(ai_tags, dict):
            return [], [_error("invalid_model_candidate", "Missing ai_tags object.")]
        candidate = {
            "id": f"{_prefix(agent_id)}_{index:03d}",
            "type": str(raw["type"]),
            "target": _safe_target(raw.get("target"), target),
            "proposed_text": str(raw["proposed_text"]).strip(),
            "proposed_change": raw.get("proposed_change", {}),
            "rationale": str(raw["rationale"]).strip(),
            "source_trace": raw.get("source_trace", {}),
            "source_trace_ids": raw.get("source_trace_ids", {}),
            "ai_tags": {
                "inferred": bool(ai_tags.get("inferred", True)),
                "confidence": str(ai_tags.get("confidence") or raw["confidence"]),
                "needs_human_review": True,
                "notes": _string_list(ai_tags.get("notes", [])),
            },
            "constraints_observed": _string_list(raw["constraints_observed"]),
            "risks": _string_list(raw["risks"]),
            "confidence": str(raw["confidence"]),
            "merge_policy": "human_approval_required",
            "requires_author_approval": True,
        }
        if not candidate["proposed_text"] or not candidate["rationale"]:
            return [], [_error("invalid_model_candidate", "Candidate text is empty.")]
        candidates.append(candidate)
    report = _sidecar_doc(
        agent_id=agent_id,
        paths={},
        out_path="",
        run_log_path="",
        dry_run=False,
        provider_profile=INTENDED_PROVIDER_PROFILE,
        candidates=candidates,
        errors=[],
        metadata={},
    )
    validation_errors = list(
        Draft202012Validator(_schema(agent_id)).iter_errors(report)
    )
    if validation_errors:
        return [], [_error("invalid_agent_schema", "Candidate failed schema validation.")]
    return candidates, []


def _parse_model_json(text: str) -> dict[str, Any]:
    content = text.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return json.loads(content.strip())


def _safe_target(raw_target: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    target = raw_target if isinstance(raw_target, dict) else {}
    allowed = {
        "artifact",
        "path",
        "scene_id",
        "beat_id",
        "element_id",
        "character_id",
    }
    safe = {
        key: str(value)
        for key, value in target.items()
        if key in allowed and value is not None and str(value)
    }
    for key in allowed:
        if key not in safe and fallback.get(key):
            safe[key] = str(fallback[key])
    return safe


def _validate_report(agent_id: str, report: dict[str, Any]) -> None:
    Draft202012Validator(_schema(agent_id)).validate(report)


def _schema(agent_id: str) -> dict[str, Any]:
    return read_json(Path("schemas") / f"{agent_id}_candidates.schema.json")


def _error(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "severity": "blocking"}


def _prefix(agent_id: str) -> str:
    return {
        "beat_dramaturgy_agent": "drambeat",
        "source_fidelity_reviewer": "fidrev",
        "yaml_repair_agent": "yamlrep",
    }[agent_id]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _hash(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
