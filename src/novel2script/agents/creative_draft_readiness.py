from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from novel2script.io import read_json, read_yaml, write_yaml
from novel2script.llm.openai_compatible_provider import provider_env_value


SCHEMA_VERSION = "0.1.0"
AGENT_ID = "kimi_dialogue_scene_drafter"
PROVIDER_PROFILE = "kimi_creative"
FALLBACK_PROFILE = "mock_dry_run"
KIMI_KEY_ENV = "N2S_KIMI_API_KEY"


def build_creative_draft_readiness_report(
    *,
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    mock_candidates_path: str | Path,
    routing_config_path: str | Path = "config/agent_routing.example.yaml",
    schema_path: str | Path = "schemas/creative_draft_candidates.schema.json",
) -> dict[str, Any]:
    screenplay = read_yaml(screenplay_path)
    author_review_report = read_yaml(author_review_report_path)
    mock_candidates = read_yaml(mock_candidates_path)
    routing_config = read_yaml(routing_config_path)
    schema = read_json(schema_path)

    checks = {
        "author_review_authorized": _check_author_review(author_review_report),
        "mock_candidates_schema_valid": _check_mock_schema(mock_candidates, schema),
        "candidate_targets_resolve": _check_targets(screenplay, mock_candidates),
        "agent_routing": _check_routing(routing_config),
        "kimi_key_present": _check_kimi_key(),
        "real_call_policy": {
            "status": "pass",
            "max_attempts": 1,
            "allow_network": False,
            "real_run_authorized": False,
        },
        "output_policy": {
            "status": "pass",
            "prompt_retention_allowed": False,
            "model_response_retention_allowed": False,
            "provider_body_retention_allowed": False,
            "auto_apply_allowed": False,
        },
    }
    blocking_codes = _blocking_codes(checks)
    status = (
        "blocked"
        if blocking_codes
        else "ready_pending_network_authorization"
    )
    report = {
        "creative_draft_readiness_report": {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "agent_id": AGENT_ID,
            "provider_profile": PROVIDER_PROFILE,
            "fallback_profile": FALLBACK_PROFILE,
            "source_artifacts": {
                "screenplay": str(screenplay_path),
                "author_review_report": str(author_review_report_path),
                "mock_candidates": str(mock_candidates_path),
                "routing_config": str(routing_config_path),
                "creative_draft_schema": str(schema_path),
            },
            "checks": checks,
            "blocking_codes": blocking_codes,
            "retention_policy": {
                "prompt_retention_allowed": False,
                "model_response_retention_allowed": False,
                "provider_body_retention_allowed": False,
                "auto_apply_allowed": False,
            },
            "next_required_authorization": {
                "network_authorization_required": True,
                "real_run_authorized": False,
                "max_attempts": 1,
                "at_most_one_real_call": True,
            },
        }
    }
    return report


def write_creative_draft_readiness_report(
    *,
    screenplay_path: str | Path,
    author_review_report_path: str | Path,
    mock_candidates_path: str | Path,
    out_path: str | Path,
    routing_config_path: str | Path = "config/agent_routing.example.yaml",
    schema_path: str | Path = "schemas/creative_draft_candidates.schema.json",
) -> dict[str, Any]:
    report = build_creative_draft_readiness_report(
        screenplay_path=screenplay_path,
        author_review_report_path=author_review_report_path,
        mock_candidates_path=mock_candidates_path,
        routing_config_path=routing_config_path,
        schema_path=schema_path,
    )
    write_yaml(report, out_path)
    return report


def _check_author_review(author_review_report: dict[str, Any]) -> dict[str, Any]:
    report = author_review_report.get("author_review_report", {})
    authorization = str(report.get("next_stage_authorization") or "none")
    ready = bool(report.get("metadata", {}).get("ready_for_next_stage", False))
    passed = authorization == "kimi_dialogue_draft" and ready
    return {
        "status": "pass" if passed else "fail",
        "code": "" if passed else "author_review_not_authorized",
        "next_stage_authorization": authorization,
        "ready_for_next_stage": ready,
    }


def _check_mock_schema(
    mock_candidates: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    errors = list(Draft202012Validator(schema).iter_errors(mock_candidates))
    if not errors:
        return {"status": "pass", "code": "", "error_count": 0}
    first = errors[0]
    return {
        "status": "fail",
        "code": "mock_candidates_schema_invalid",
        "error_count": len(errors),
        "schema_path": "/".join(str(part) for part in first.schema_path),
        "validator": first.validator,
    }


def _check_targets(
    screenplay: dict[str, Any], mock_candidates: dict[str, Any]
) -> dict[str, Any]:
    scenes = {scene.get("id"): scene for scene in screenplay.get("scenes", [])}
    characters = {character.get("id") for character in screenplay.get("characters", [])}
    unresolved: list[dict[str, str]] = []
    creative = mock_candidates.get("creative_draft_candidates", {})
    for candidate in creative.get("candidates", []):
        target = candidate.get("target", {})
        scene_id = target.get("scene_id")
        scene = scenes.get(scene_id)
        if not scene:
            unresolved.append(_unresolved(candidate, "scene_id"))
            continue
        if target.get("beat_id") and not _scene_has_id(scene, "beats", target["beat_id"]):
            unresolved.append(_unresolved(candidate, "beat_id"))
        if target.get("element_id") and not _scene_has_id(
            scene, "elements", target["element_id"]
        ):
            unresolved.append(_unresolved(candidate, "element_id"))
        if target.get("character_id") and target["character_id"] not in characters:
            unresolved.append(_unresolved(candidate, "character_id"))
    return {
        "status": "pass" if not unresolved else "fail",
        "code": "" if not unresolved else "candidate_target_unresolved",
        "candidate_count": len(creative.get("candidates", [])),
        "unresolved": unresolved,
    }


def _check_routing(routing_config: dict[str, Any]) -> dict[str, Any]:
    route = routing_config.get("agents", {}).get(AGENT_ID, {})
    passed = (
        route.get("provider_profile") == PROVIDER_PROFILE
        and route.get("fallback_profile") == FALLBACK_PROFILE
        and route.get("output_policy") == "human_approval_required"
    )
    return {
        "status": "pass" if passed else "fail",
        "code": "" if passed else "agent_routing_invalid",
        "provider_profile": str(route.get("provider_profile") or ""),
        "fallback_profile": str(route.get("fallback_profile") or ""),
        "output_policy": str(route.get("output_policy") or ""),
    }


def _check_kimi_key() -> dict[str, Any]:
    present = bool(provider_env_value(KIMI_KEY_ENV))
    return {
        "status": "pass" if present else "fail",
        "code": "" if present else "kimi_key_missing",
        "env_var": KIMI_KEY_ENV,
        "kimi_key_present": present,
    }


def _blocking_codes(checks: dict[str, dict[str, Any]]) -> list[str]:
    codes: list[str] = []
    for check in checks.values():
        if check.get("status") == "fail" and check.get("code"):
            codes.append(str(check["code"]))
    return codes


def _scene_has_id(scene: dict[str, Any], field: str, item_id: str) -> bool:
    return any(item.get("id") == item_id for item in scene.get(field, []))


def _unresolved(candidate: dict[str, Any], field: str) -> dict[str, str]:
    return {
        "candidate_id": str(candidate.get("id") or ""),
        "field": field,
    }
