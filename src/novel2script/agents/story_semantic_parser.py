from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from novel2script.io import read_json, read_yaml, write_yaml
from novel2script.llm.openai_compatible_provider import (
    ProviderConfigurationError,
    ProviderRuntimeError,
)
from novel2script.llm.router import LLMRouter
from novel2script.llm.types import LLMRequest


AGENT_ID = "story_semantic_parser"
SCHEMA_VERSION = "0.1.0"
MAX_EXCERPTS = 8
MAX_EXCERPT_CHARS = 120
ROOT = Path(__file__).resolve().parents[3]
MODEL_OUTPUT_SCHEMA = ROOT / "schemas" / "qwen_semantic_model_output.schema.json"


def run_story_semantic_parser(
    story_map_path: str | Path,
    *,
    out_path: str | Path,
    run_log_path: str | Path,
    quality_report_path: str | Path | None = None,
    router: LLMRouter | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Run the story semantic agent and write sidecar artifacts."""
    story_map_doc = read_yaml(story_map_path)
    quality_report_doc = read_yaml(quality_report_path) if quality_report_path else None
    errors = _trace_errors(story_map_doc)

    if errors:
        report = _semantic_candidates_doc(
            story_map_path,
            run_log_path,
            candidates=[],
            errors=errors,
            provider_profile="mock_dry_run",
            dry_run=True,
            metadata={
                "intended_provider_profile": "qwen_long",
                "resolved_provider_profile": "mock_dry_run",
                "quality_report": str(quality_report_path or ""),
            },
        )
        write_yaml(report, out_path)
        write_yaml({"llm_run_records": [], "errors": errors}, run_log_path)
        return report

    request = _build_request(
        story_map_doc,
        story_map_path=story_map_path,
        quality_report_doc=quality_report_doc,
        dry_run=dry_run,
    )
    try:
        routed = (router or LLMRouter.default()).dispatch(request)
    except ProviderConfigurationError as exc:
        errors = [
            _model_error(
                "provider_authentication_failed",
                f"LLM provider authentication failed or key missing. Details: {str(exc)}",
            )
        ]
        return _write_fallback_report(
            story_map_path, out_path, run_log_path, errors, intended_profile="qwen_long", dry_run=dry_run, quality_report_path=quality_report_path
        )
    except ProviderRuntimeError as exc:
        category = exc.category
        code = "provider_service_error"
        if category == "authentication":
            code = "provider_authentication_failed"
        elif category == "rate_limited":
            code = "provider_rate_limited"
        elif category == "timeout":
            code = "provider_timeout"
        elif category in ("dns_error", "tls_error", "connection_error", "transport_failure"):
            code = "provider_connection_failed"
            
        errors = [
            _model_error(
                code,
                f"LLM provider error occurred: {category}. Details: {str(exc)}",
            )
        ]
        return _write_fallback_report(
            story_map_path, out_path, run_log_path, errors, intended_profile="qwen_long", dry_run=dry_run, quality_report_path=quality_report_path, runtime_error=exc
        )
    except Exception as exc:
        errors = [
            _model_error(
                "provider_service_error",
                f"An unexpected LLM service error occurred. Details: {str(exc)}",
            )
        ]
        return _write_fallback_report(
            story_map_path, out_path, run_log_path, errors, intended_profile="qwen_long", dry_run=dry_run, quality_report_path=quality_report_path
        )

    if dry_run:
        candidates = _build_candidates(story_map_doc)
        errors = _candidate_trace_errors(candidates)
        if errors:
            candidates = []
    else:
        candidates, errors = _parse_real_candidates(
            routed.response.text,
            finish_reason=routed.response.finish_reason,
            excerpts=_bounded_excerpts(story_map_doc),
        )

    report = _semantic_candidates_doc(
        story_map_path,
        run_log_path,
        candidates=candidates,
        errors=errors,
        provider_profile=routed.resolved_profile,
        dry_run=dry_run,
        metadata={
            "intended_provider_profile": routed.intended_profile,
            "resolved_provider_profile": routed.resolved_profile,
            "llm_run_id": routed.response.run_id,
            "quality_report": str(quality_report_path or ""),
            "provider_finish_reason": routed.response.finish_reason,
        },
    )
    write_yaml(report, out_path)
    write_yaml(
        {
            "llm_run_records": [routed.run_record],
            "errors": errors,
            "provider_response": {
                "run_id": routed.response.run_id,
                "provider": routed.response.provider,
                "model": routed.response.model,
                "finish_reason": routed.response.finish_reason,
            },
        },
        run_log_path,
    )
    return report


def _semantic_candidates_doc(
    story_map_path: str | Path,
    run_log_path: str | Path,
    *,
    candidates: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    provider_profile: str,
    dry_run: bool,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "semantic_candidates": {
            "schema_version": SCHEMA_VERSION,
            "source_story_map": str(story_map_path),
            "agent_id": AGENT_ID,
            "provider_profile": provider_profile,
            "dry_run": dry_run,
            "candidates": candidates,
            "errors": errors,
            "human_approval_required": True,
            "run_log": str(run_log_path),
            "metadata": metadata,
        }
    }


def _write_fallback_report(
    story_map_path: str | Path,
    out_path: str | Path,
    run_log_path: str | Path,
    errors: list[dict[str, Any]],
    intended_profile: str,
    dry_run: bool,
    quality_report_path: str | Path | None = None,
    runtime_error: ProviderRuntimeError | None = None,
) -> dict[str, Any]:
    metadata = {
        "intended_provider_profile": intended_profile,
        "resolved_provider_profile": "mock_dry_run" if dry_run else intended_profile,
        "quality_report": str(quality_report_path or ""),
    }
    if runtime_error:
        metadata["runtime_error_details"] = runtime_error.to_dict()

    report = _semantic_candidates_doc(
        story_map_path,
        run_log_path,
        candidates=[],
        errors=errors,
        provider_profile="mock_dry_run" if dry_run else intended_profile,
        dry_run=dry_run,
        metadata=metadata,
    )
    write_yaml(report, out_path)

    run_record_err = {
        "status": "failed",
        "error": errors[0],
    }
    if runtime_error:
        run_record_err["runtime_error"] = runtime_error.to_dict()

    write_yaml(
        {
            "llm_run_records": [run_record_err],
            "errors": errors,
        },
        run_log_path,
    )
    return report


def _build_request(
    story_map_doc: dict[str, Any],
    *,
    story_map_path: str | Path,
    quality_report_doc: dict[str, Any] | None,
    dry_run: bool,
) -> LLMRequest:
    excerpts = _bounded_excerpts(story_map_doc)
    quality_status = _quality_status(quality_report_doc)
    prompt_lines = [
        "Agent: story_semantic_parser",
        "Task: return source-grounded semantic candidate drafts.",
        'The only allowed root structure is {"candidates": [...]}.',
        "Return 0 to 3 candidates. Never return more than 3 candidates.",
        (
            "Every candidate must contain exactly these fields: type, confidence, "
            "evidence, source_trace_ids, target_story_map_field, proposed_fields."
        ),
        "confidence must be one of: low, medium, high.",
        (
            "evidence must contain summary and may contain only quote_preview "
            "and reasoning_note."
        ),
        (
            "source_trace_ids must contain chapter_id and paragraph_ids. Use only "
            "the chapter_id and paragraph_id values in Bounded excerpts below."
        ),
        "Allowed type -> target_story_map_field mappings:",
        "- character_candidate -> characters_detected",
        "- location_candidate -> locations_detected",
        "- prop_candidate -> props_detected",
        "- event_candidate -> key_events",
        "- psychological_passage_candidate -> psychological_passages",
        "- timeline_candidate -> timeline",
        "Allowed proposed_fields by type:",
        "- character_candidate: name; optional aliases, description_hint",
        "- location_candidate: name; optional location_type, description_hint",
        "- prop_candidate: name; optional prop_type, description_hint",
        "- event_candidate: summary; optional event_type",
        (
            "- psychological_passage_candidate: summary; optional passage_type, "
            "externalization_hint"
        ),
        "- timeline_candidate: label; optional time_text",
        (
            "Do not output semantic_traces, semantic_concept, description, "
            "sources, candidate ID, merge_policy, file paths, run metadata, "
            "Markdown fences, explanatory prose, or a thinking process."
        ),
        "Keep every field concise.",
        "Valid event_candidate JSON example:",
        (
            '{"candidates": [{"type": "event_candidate", "confidence": "medium", '
            '"evidence": {"summary": "A concrete source-grounded event occurs."}, '
            '"source_trace_ids": {"chapter_id": "ch_001", '
            '"paragraph_ids": ["p_001"]}, '
            '"target_story_map_field": "key_events", '
            '"proposed_fields": {"summary": "The event changes the situation.", '
            '"event_type": "discovery"}}]}'
        ),
        (
            "Replace example trace IDs only with IDs listed below. Do not add "
            "fields that are not shown in the contract."
        ),
        "Safety rules: do not merge and do not generate screenplay content.",
        f"Dry run: {dry_run}",
        f"Quality status: {quality_status}",
        "Bounded excerpts:",
    ]
    for excerpt in excerpts:
        prompt_lines.append(
            f"- {excerpt['chapter_id']}/{excerpt['paragraph_id']}: {excerpt['text']}"
        )
    prompt_lines.append(
        "Only return the JSON object. Do not return Markdown or explanatory text."
    )
    prompt = "\n".join(prompt_lines)
    return LLMRequest(
        agent_id=AGENT_ID,
        task_type="semantic_candidate_generation",
        prompt=prompt,
        response_format="semantic_candidates.yaml" if dry_run else "json_object",
        temperature=0.0,
        max_tokens=1024 if dry_run else 2048,
        trace_id=_trace_id(story_map_path, excerpts),
        metadata={
            "source_story_map": str(story_map_path),
            "excerpt_count": len(excerpts),
            "dry_run": dry_run,
        },
    )


def _parse_real_candidates(
    text: str,
    *,
    finish_reason: str,
    excerpts: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []

    if finish_reason == "length":
        errors.append(
            _model_error(
                "truncated_model_output",
                "Provider stopped because the output token limit was reached. Partial candidates might be recovered.",
            )
        )

    if not text.strip():
        return [], errors + [_model_error("empty_model_output", "Provider returned no JSON content.")]

    try:
        model_doc = _attempt_json_repair(text)
    except Exception as exc:
        return [], errors + [
            _model_error(
                "malformed_model_json",
                f"Provider response was not valid JSON and could not be repaired. Details: {str(exc)}",
            )
        ]

    try:
        Draft202012Validator(read_json(MODEL_OUTPUT_SCHEMA)).validate(model_doc)
    except ValidationError:
        return [], errors + [
            _model_error(
                "invalid_model_output_schema",
                "Provider JSON did not match qwen semantic model-output schema.",
            )
        ]

    whitelist: dict[str, set[str]] = {}
    for excerpt in excerpts:
        whitelist.setdefault(excerpt["chapter_id"], set()).add(
            excerpt["paragraph_id"]
        )

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for draft in model_doc["candidates"]:
        trace = draft["source_trace_ids"]
        chapter_id = trace["chapter_id"]
        paragraph_ids = trace["paragraph_ids"]
        if chapter_id not in whitelist or any(
            paragraph_id not in whitelist[chapter_id]
            for paragraph_id in paragraph_ids
        ):
            errors.append(
                _model_error(
                    "hallucinated_source_trace",
                    "Candidate referenced a chapter or paragraph outside the sent excerpts.",
                )
            )
            continue
        fingerprint = _candidate_fingerprint(draft)
        if fingerprint in seen:
            errors.append(
                _model_error(
                    "duplicate_candidate",
                    "Duplicate model candidate was excluded.",
                )
            )
            continue
        seen.add(fingerprint)
        candidates.append(
            {
                "id": f"semcand_{len(candidates) + 1:03d}",
                **draft,
                "merge_policy": "human_approval_required",
            }
        )
    return candidates, errors


def _candidate_fingerprint(candidate: dict[str, Any]) -> str:
    canonical = {
        "type": candidate["type"],
        "target_story_map_field": candidate["target_story_map_field"],
        "source_trace_ids": candidate["source_trace_ids"],
        "proposed_fields": candidate["proposed_fields"],
    }
    return hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _model_error(code: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "retryable": False,
    }


def _bounded_excerpts(story_map_doc: dict[str, Any]) -> list[dict[str, str]]:
    excerpts: list[dict[str, str]] = []
    for chapter in story_map_doc.get("story_map", {}).get("chapters", []):
        chapter_id = chapter.get("id", "")
        for paragraph in chapter.get("paragraphs", []):
            paragraph_id = paragraph.get("id", "")
            text = _preview(paragraph.get("text_preview", ""), MAX_EXCERPT_CHARS)
            excerpts.append(
                {
                    "chapter_id": chapter_id,
                    "paragraph_id": paragraph_id,
                    "text": text,
                }
            )
            if len(excerpts) >= MAX_EXCERPTS:
                return excerpts
    return excerpts


def _build_candidates(story_map_doc: dict[str, Any]) -> list[dict[str, Any]]:
    story_map = story_map_doc.get("story_map", {})
    candidates: list[dict[str, Any]] = []
    _append_from_item(
        candidates,
        story_map.get("key_events", []),
        candidate_type="event_candidate",
        target_field="key_events",
        summary_prefix="Mock dry-run semantic pass flagged a plot event candidate.",
        proposed_field_builder=lambda item: {
            "summary": item.get("summary", ""),
            "event_type": item.get("event_type", "semantic_candidate"),
            "source_event_id": item.get("id", ""),
        },
    )
    _append_from_item(
        candidates,
        story_map.get("psychological_passages", []),
        candidate_type="psychological_passage_candidate",
        target_field="psychological_passages",
        summary_prefix="Mock dry-run semantic pass flagged an interiority candidate.",
        proposed_field_builder=lambda item: {
            "summary": item.get("summary", ""),
            "passage_type": item.get("passage_type", "other"),
            "source_psychological_passage_id": item.get("id", ""),
        },
    )
    _append_from_item(
        candidates,
        story_map.get("timeline", []),
        candidate_type="timeline_candidate",
        target_field="timeline",
        summary_prefix="Mock dry-run semantic pass flagged a timeline candidate.",
        proposed_field_builder=lambda item: {
            "time_text": item.get("time_text", item.get("label", "")),
            "label": item.get("label", ""),
            "source_timeline_id": item.get("id", ""),
        },
    )
    return candidates


def _append_from_item(
    candidates: list[dict[str, Any]],
    items: list[dict[str, Any]],
    *,
    candidate_type: str,
    target_field: str,
    summary_prefix: str,
    proposed_field_builder: Any,
) -> None:
    if not items:
        return
    item = items[0]
    trace = item.get("source_trace", {})
    candidates.append(
        {
            "id": f"semcand_{len(candidates) + 1:03d}",
            "type": candidate_type,
            "confidence": "medium",
            "evidence": {
                "summary": summary_prefix,
                "quote_preview": _preview(trace.get("quote_preview", ""), 120),
                "reasoning_note": "Generated through mock_dry_run for contract verification.",
            },
            "source_trace_ids": {
                "chapter_id": trace.get("chapter_id", ""),
                "paragraph_ids": list(trace.get("paragraph_ids", [])),
            },
            "proposed_fields": proposed_field_builder(item),
            "merge_policy": "human_approval_required",
            "target_story_map_field": target_field,
        }
    )


def _trace_errors(story_map_doc: dict[str, Any]) -> list[dict[str, Any]]:
    story_map = story_map_doc.get("story_map")
    if not isinstance(story_map, dict):
        return [
            {
                "code": "missing_story_map",
                "message": "Input does not contain a story_map root.",
                "retryable": False,
            }
        ]
    chapters = story_map.get("chapters", [])
    if not chapters:
        return [
            {
                "code": "missing_source_trace",
                "message": "Cannot propose semantic candidates without chapters.",
                "retryable": False,
            }
        ]
    errors: list[dict[str, Any]] = []
    for chapter_index, chapter in enumerate(chapters, start=1):
        chapter_id = chapter.get("id")
        if not chapter_id:
            errors.append(
                {
                    "code": "missing_source_trace",
                    "message": f"Chapter {chapter_index} is missing chapter_id.",
                    "retryable": False,
                }
            )
            continue
        paragraphs = chapter.get("paragraphs", [])
        if not paragraphs:
            errors.append(
                {
                    "code": "missing_source_trace",
                    "message": f"Chapter {chapter_id} has no paragraph_ids.",
                    "retryable": False,
                }
            )
            continue
        for paragraph_index, paragraph in enumerate(paragraphs, start=1):
            if not paragraph.get("id"):
                errors.append(
                    {
                        "code": "missing_source_trace",
                        "message": (
                            f"Chapter {chapter_id} paragraph {paragraph_index} "
                            "is missing paragraph_ids."
                        ),
                        "retryable": False,
                    }
                )
    return errors


def _candidate_trace_errors(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for candidate in candidates:
        trace = candidate.get("source_trace_ids", {})
        if not trace.get("chapter_id") or not trace.get("paragraph_ids"):
            errors.append(
                {
                    "code": "missing_source_trace",
                    "message": (
                        f"Candidate {candidate.get('id', '')} is missing "
                        "chapter_id or paragraph_ids."
                    ),
                    "retryable": False,
                }
            )
    return errors


def _quality_status(quality_report_doc: dict[str, Any] | None) -> str:
    if not quality_report_doc:
        return "not_provided"
    readiness = quality_report_doc.get("quality_report", {}).get(
        "overall_readiness", {}
    )
    return str(readiness.get("status") or readiness.get("decision") or "provided")


def _trace_id(story_map_path: str | Path, excerpts: list[dict[str, str]]) -> str:
    seed = str(story_map_path) + "|" + "|".join(
        f"{item['chapter_id']}/{item['paragraph_id']}" for item in excerpts
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"trace_sem_{digest}"


def _preview(text: str, limit: int) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "..."


def _attempt_json_repair(text: str) -> Any:
    """尝试智能强修复损坏的 JSON 结构。"""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Empty response text")

    # 1. 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2. 提取 markdown 代码块
    import re
    block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if block_match:
        cleaned = block_match.group(1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # 3. 正则修复对象或数组尾部的多余逗号
    cleaned = re.sub(r",\s*\}", "}", cleaned)
    cleaned = re.sub(r",\s*\]", "]", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 4. 堆栈补足闭合括号
    try:
        repaired = _close_unmatched_brackets(cleaned)
        return json.loads(repaired)
    except Exception:
        pass

    # 5. 截断残破修复：丢弃尾部残残不全的候选对象
    for i in range(len(cleaned) - 1, -1, -1):
        if cleaned[i] == '}':
            candidate_part = cleaned[:i+1]
            for suffix in ("]}", "}"):
                try:
                    return json.loads(candidate_part + suffix)
                except json.JSONDecodeError:
                    pass

    # 兜底：若修复均失败，抛出原始解析错
    return json.loads(text)


def _close_unmatched_brackets(text: str) -> str:
    stack = []
    in_string = False
    escape = False
    for char in text:
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char in ('{', '['):
                stack.append(char)
            elif char == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif char == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
    repaired = text
    while stack:
        op = stack.pop()
        if op == '{':
            repaired += '}'
        elif op == '[':
            repaired += ']'
    return repaired
