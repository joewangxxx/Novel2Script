from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from novel2script.agents.story_semantic_parser import _bounded_excerpts  # noqa: E402


SAFE_RUN_LOG_FORBIDDEN_PATTERNS = [
    "Agent: story_semantic_parser",
    "Bounded excerpts:",
    "The only allowed root structure",
    "raw_response",
    "provider_response_text",
    "provider raw response",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(r"Authorization", re.IGNORECASE),
    re.compile(r"HTTP body", re.IGNORECASE),
    re.compile(r"raw_response", re.IGNORECASE),
    re.compile(r"provider_response_text", re.IGNORECASE),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Stage 13H semantic smoke artifacts safely."
    )
    parser.add_argument("--story-map", required=True)
    parser.add_argument("--semantic-candidates", required=True)
    parser.add_argument("--run-log", required=True)
    parser.add_argument("--semantic-schema", required=True)
    args = parser.parse_args(argv)

    story_path = Path(args.story_map)
    semantic_path = Path(args.semantic_candidates)
    run_log_path = Path(args.run_log)
    schema_path = Path(args.semantic_schema)

    failures: list[str] = []
    story_doc: dict[str, Any] = {}
    semantic_doc: dict[str, Any] = {}
    run_log_doc: dict[str, Any] = {}

    try:
        story_doc = _read_yaml(story_path)
    except OSError:
        failures.append("story_map_unreadable")

    try:
        semantic_doc = _read_yaml(semantic_path)
    except OSError:
        failures.append("semantic_candidates_unreadable")

    try:
        run_log_doc = _read_yaml(run_log_path)
    except OSError:
        failures.append("run_log_unreadable")

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(semantic_doc)
    except (OSError, json.JSONDecodeError, ValidationError):
        failures.append("semantic_candidates_schema_invalid")

    semantic = semantic_doc.get("semantic_candidates", {})
    candidates = semantic.get("candidates", [])
    errors = semantic.get("errors", [])
    error_codes = _error_codes(errors)
    finish_reason = semantic.get("metadata", {}).get("provider_finish_reason", "")
    provider_profile = semantic.get("provider_profile", "")
    dry_run = semantic.get("dry_run")

    if provider_profile != "qwen_long":
        failures.append("provider_profile_not_qwen_long")
    if dry_run is not False:
        failures.append("dry_run_not_false")
    if len(candidates) <= 0:
        failures.append("no_candidates")
    if error_codes:
        failures.append("semantic_errors_present")
    if finish_reason == "length":
        failures.append("truncated_model_output")

    trace_ok = _trace_ok(story_doc, candidates)
    if not trace_ok:
        failures.append("source_trace_outside_sent_excerpts")

    merge_policy_ok = all(
        candidate.get("merge_policy") == "human_approval_required"
        for candidate in candidates
    )
    if not merge_policy_ok:
        failures.append("merge_policy_invalid")

    run_log_text = _safe_read_text(run_log_path)
    semantic_text = _safe_read_text(semantic_path)
    if _run_log_has_prompt_or_source_leak(run_log_text, story_doc):
        failures.append("run_log_prompt_or_raw_response_leak")
    if _has_secret_or_transport_leak(run_log_text + "\n" + semantic_text):
        failures.append("sidecar_secret_or_transport_leak")

    security_failures = {
        "run_log_prompt_or_raw_response_leak",
        "sidecar_secret_or_transport_leak",
    }
    summary = {
        "passed": not failures,
        "failures": sorted(set(failures)),
        "provider_profile": provider_profile,
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "error_count": len(error_codes),
        "error_codes": error_codes,
        "finish_reason": finish_reason,
        "trace_ok": trace_ok,
        "merge_policy_ok": merge_policy_ok,
        "security_scan": (
            "fail" if security_failures.intersection(failures) else "pass"
        ),
        "run_log_records": len(run_log_doc.get("llm_run_records", []))
        if isinstance(run_log_doc, dict)
        else 0,
    }
    json.dump(summary, sys.stdout, ensure_ascii=True, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if summary["passed"] else 1


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _error_codes(errors: Any) -> list[str]:
    if not isinstance(errors, list):
        return ["invalid_errors_shape"]
    codes: list[str] = []
    for item in errors:
        if isinstance(item, dict):
            codes.append(str(item.get("code", "unknown_error")))
        else:
            codes.append("unknown_error")
    return codes


def _trace_ok(story_doc: dict[str, Any], candidates: Any) -> bool:
    if not isinstance(candidates, list):
        return False
    allowed: dict[str, set[str]] = {}
    for excerpt in _bounded_excerpts(story_doc):
        allowed.setdefault(excerpt["chapter_id"], set()).add(excerpt["paragraph_id"])

    if not allowed:
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return False
        trace = candidate.get("source_trace_ids", {})
        chapter_id = trace.get("chapter_id")
        paragraph_ids = trace.get("paragraph_ids", [])
        if chapter_id not in allowed or not paragraph_ids:
            return False
        if any(paragraph_id not in allowed[chapter_id] for paragraph_id in paragraph_ids):
            return False
    return True


def _run_log_has_prompt_or_source_leak(
    run_log_text: str, story_doc: dict[str, Any]
) -> bool:
    for forbidden in SAFE_RUN_LOG_FORBIDDEN_PATTERNS:
        if forbidden in run_log_text:
            return True
    for preview in _story_text_previews(story_doc):
        if preview and preview in run_log_text:
            return True
    return False


def _story_text_previews(story_doc: dict[str, Any]) -> list[str]:
    previews: list[str] = []
    chapters = story_doc.get("story_map", {}).get("chapters", [])
    for chapter in chapters:
        for paragraph in chapter.get("paragraphs", []):
            text = " ".join(str(paragraph.get("text_preview", "")).split())
            if len(text) >= 6:
                previews.append(text)
    return previews


def _has_secret_or_transport_leak(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


if __name__ == "__main__":
    raise SystemExit(main())
