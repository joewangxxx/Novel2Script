from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.story_semantic_parser import run_story_semantic_parser
from novel2script.llm.router import RoutedLLMResult
from novel2script.llm.types import LLMRequest, LLMResponse


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
SCHEMA = ROOT / "schemas" / "semantic_candidates.schema.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_story_semantic_parser_uses_mock_router_and_writes_schema_valid_outputs(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"

    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=out_path,
        run_log_path=run_log_path,
    )

    assert result == _load_yaml(out_path)
    semantic = result["semantic_candidates"]
    assert semantic["agent_id"] == "story_semantic_parser"
    assert semantic["provider_profile"] == "mock_dry_run"
    assert semantic["dry_run"] is True
    assert semantic["human_approval_required"] is True
    assert semantic["run_log"] == str(run_log_path)
    assert semantic["candidates"]
    assert semantic["errors"] == []
    assert all(
        candidate["merge_policy"] == "human_approval_required"
        for candidate in semantic["candidates"]
    )
    assert all(
        candidate["source_trace_ids"]["chapter_id"].startswith("ch_")
        and candidate["source_trace_ids"]["paragraph_ids"]
        for candidate in semantic["candidates"]
    )

    schema = _load_yaml(SCHEMA)
    Draft202012Validator(schema).validate(result)

    run_log = _load_yaml(run_log_path)
    assert run_log["llm_run_records"][0]["agent_id"] == "story_semantic_parser"
    assert run_log["llm_run_records"][0]["intended_profile"] == "qwen_long"
    assert run_log["llm_run_records"][0]["resolved_profile"] == "mock_dry_run"
    assert run_log["llm_run_records"][0]["stored_prompt"] is False
    assert "prompt" not in run_log["llm_run_records"][0]


def test_story_semantic_parser_run_log_does_not_store_bounded_excerpt_text(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    story_map = _load_yaml(STORY_MAP)
    excerpt = story_map["story_map"]["chapters"][0]["paragraphs"][0]["text_preview"]

    run_story_semantic_parser(STORY_MAP, out_path=out_path, run_log_path=run_log_path)

    run_log_text = run_log_path.read_text(encoding="utf-8")
    assert excerpt not in run_log_text
    assert "prompt_hash" in run_log_text


def test_story_semantic_parser_returns_structured_error_for_missing_trace(
    tmp_path: Path,
) -> None:
    story_map = deepcopy(_load_yaml(STORY_MAP))
    del story_map["story_map"]["chapters"][0]["id"]
    invalid_path = tmp_path / "invalid_story_map.yaml"
    invalid_path.write_text(
        yaml.safe_dump(story_map, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"

    result = run_story_semantic_parser(
        invalid_path,
        out_path=out_path,
        run_log_path=run_log_path,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "missing_source_trace"
    assert "chapter_id" in semantic["errors"][0]["message"]
    assert semantic["provider_profile"] == "mock_dry_run"
    assert semantic["human_approval_required"] is True

    schema = _load_yaml(SCHEMA)
    Draft202012Validator(schema).validate(result)
    run_log = _load_yaml(run_log_path)
    assert run_log["llm_run_records"] == []
    assert run_log["errors"][0]["code"] == "missing_source_trace"


def _model_candidate(
    *,
    chapter_id: str = "ch_001",
    paragraph_ids: list[str] | None = None,
    summary: str = "A source-grounded event from Qwen.",
) -> dict:
    return {
        "type": "event_candidate",
        "confidence": "high",
        "evidence": {
            "summary": "The excerpt contains a concrete event.",
            "quote_preview": "bounded evidence",
        },
        "source_trace_ids": {
            "chapter_id": chapter_id,
            "paragraph_ids": paragraph_ids or ["p_001"],
        },
        "target_story_map_field": "key_events",
        "proposed_fields": {
            "summary": summary,
            "event_type": "discovery",
        },
    }


class RealLikeRouter:
    def __init__(self, *, text: str | None = None, finish_reason: str = "stop") -> None:
        self.requests: list[LLMRequest] = []
        self.text = text or json.dumps(
            {"candidates": [_model_candidate()]},
            ensure_ascii=False,
        )
        self.finish_reason = finish_reason

    def dispatch(self, request: LLMRequest) -> RoutedLLMResult:
        self.requests.append(request)
        response = LLMResponse(
            text=self.text,
            model="qwen-long",
            provider="qwen_long",
            usage={"input_tokens": 13, "output_tokens": 5, "total_tokens": 18},
            latency_ms=44,
            finish_reason=self.finish_reason,
            run_id="llm_run_qwen_001",
        )
        return RoutedLLMResult(
            response=response,
            run_record={
                "run_id": response.run_id,
                "trace_id": request.trace_id,
                "agent_id": request.agent_id,
                "task_type": request.task_type,
                "provider": response.provider,
                "model": response.model,
                "status": "completed",
                "finish_reason": response.finish_reason,
                "prompt_hash": "sha256:test",
                "prompt_chars": len(request.prompt),
                "stored_prompt": False,
                "usage": response.usage,
                "latency_ms": response.latency_ms,
                "intended_profile": "qwen_long",
                "resolved_profile": "qwen_long",
            },
            intended_profile="qwen_long",
            resolved_profile="qwen_long",
        )


def test_story_semantic_parser_records_real_provider_metadata_without_mutating_story_map(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    before = STORY_MAP.read_bytes()
    router = RealLikeRouter()

    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=out_path,
        run_log_path=run_log_path,
        router=router,
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert STORY_MAP.read_bytes() == before
    assert semantic["provider_profile"] == "qwen_long"
    assert semantic["dry_run"] is False
    assert semantic["metadata"]["resolved_provider_profile"] == "qwen_long"
    assert semantic["metadata"]["provider_finish_reason"] == "stop"
    assert router.requests[0].metadata["dry_run"] is False
    assert router.requests[0].response_format == "json_object"
    assert router.requests[0].max_tokens == 2048
    prompt = router.requests[0].prompt
    assert '{"candidates": [' in prompt
    assert "0 to 3 candidates" in prompt
    assert "Keep every field concise" in prompt
    assert "thinking process" in prompt
    for field in (
        "type",
        "confidence",
        "evidence",
        "source_trace_ids",
        "target_story_map_field",
        "proposed_fields",
    ):
        assert field in prompt
    for prohibited_field in (
        "semantic_traces",
        "semantic_concept",
        "description",
        "sources",
        "candidate ID",
        "merge_policy",
        "Markdown fences",
    ):
        assert prohibited_field in prompt
    assert "event_candidate -> key_events" in prompt
    assert '"type": "event_candidate"' in prompt
    assert '"target_story_map_field": "key_events"' in prompt
    assert "Only return the JSON object" in prompt
    assert semantic["errors"] == []
    assert semantic["candidates"] == [
        {
            "id": "semcand_001",
            **_model_candidate(),
            "merge_policy": "human_approval_required",
        }
    ]

    run_log = _load_yaml(run_log_path)
    assert run_log["llm_run_records"][0]["provider"] == "qwen_long"
    assert run_log["llm_run_records"][0]["stored_prompt"] is False
    assert router.text not in run_log_path.read_text(encoding="utf-8")


def test_story_semantic_parser_rejects_malformed_real_json(tmp_path: Path) -> None:
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text='{"candidates": [}'),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "malformed_model_json"


def test_story_semantic_parser_rejects_empty_real_response(tmp_path: Path) -> None:
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text=" "),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "empty_model_output"


def test_story_semantic_parser_rejects_truncated_real_response(tmp_path: Path) -> None:
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text='{"candidates": [{"type":', finish_reason="length"),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "truncated_model_output"


def test_story_semantic_parser_excludes_hallucinated_trace(tmp_path: Path) -> None:
    text = json.dumps(
        {"candidates": [_model_candidate(chapter_id="ch_999")]},
        ensure_ascii=False,
    )
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text=text),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "hallucinated_source_trace"


def test_story_semantic_parser_deduplicates_real_candidates(tmp_path: Path) -> None:
    candidate = _model_candidate()
    text = json.dumps(
        {"candidates": [candidate, deepcopy(candidate)]},
        ensure_ascii=False,
    )
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text=text),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert [item["id"] for item in semantic["candidates"]] == ["semcand_001"]
    assert semantic["errors"][0]["code"] == "duplicate_candidate"


def test_story_semantic_parser_rejects_unknown_model_output_field(
    tmp_path: Path,
) -> None:
    candidate = _model_candidate()
    candidate["model_generated_id"] = "semcand_999"
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(
            text=json.dumps({"candidates": [candidate]}, ensure_ascii=False)
        ),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "invalid_model_output_schema"


def test_story_semantic_parser_redacts_schema_validation_instance(
    tmp_path: Path,
) -> None:
    marker = "SENSITIVE_MODEL_RESPONSE_MARKER_9f7a"
    candidate = _model_candidate()
    candidate["description"] = marker
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"

    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=out_path,
        run_log_path=run_log_path,
        router=RealLikeRouter(
            text=json.dumps({"candidates": [candidate]}, ensure_ascii=False)
        ),
        dry_run=False,
    )

    error = result["semantic_candidates"]["errors"][0]
    assert error == {
        "code": "invalid_model_output_schema",
        "message": "Provider JSON did not match qwen semantic model-output schema.",
        "retryable": False,
    }
    assert marker not in json.dumps(result, ensure_ascii=False)
    assert marker not in out_path.read_text(encoding="utf-8")
    assert marker not in run_log_path.read_text(encoding="utf-8")


def test_story_semantic_parser_rejects_more_than_three_real_candidates(
    tmp_path: Path,
) -> None:
    candidates = [
        _model_candidate(summary=f"Candidate event {index}.")
        for index in range(1, 5)
    ]
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(
            text=json.dumps({"candidates": candidates}, ensure_ascii=False)
        ),
        dry_run=False,
    )

    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"] == [
        {
            "code": "invalid_model_output_schema",
            "message": (
                "Provider JSON did not match qwen semantic model-output schema."
            ),
            "retryable": False,
        }
    ]


def test_story_semantic_parser_repairs_json_with_trailing_comma(tmp_path: Path) -> None:
    text = '{"candidates": [{"type": "event_candidate", "confidence": "high", "evidence": {"summary": "A concrete event."}, "source_trace_ids": {"chapter_id": "ch_001", "paragraph_ids": ["p_001"]}, "target_story_map_field": "key_events", "proposed_fields": {"summary": "Event summary", "event_type": "discovery"}},]}'
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text=text),
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert semantic["errors"] == []
    assert len(semantic["candidates"]) == 1
    assert semantic["candidates"][0]["proposed_fields"]["summary"] == "Event summary"


def test_story_semantic_parser_repairs_json_with_missing_brackets(tmp_path: Path) -> None:
    text = '{"candidates": [{"type": "event_candidate", "confidence": "high", "evidence": {"summary": "A concrete event."}, "source_trace_ids": {"chapter_id": "ch_001", "paragraph_ids": ["p_001"]}, "target_story_map_field": "key_events", "proposed_fields": {"summary": "Event summary", "event_type": "discovery"}}]'
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text=text),
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert semantic["errors"] == []
    assert len(semantic["candidates"]) == 1


def test_story_semantic_parser_repairs_truncated_json_recovering_partial_candidates(tmp_path: Path) -> None:
    text = (
        '{"candidates": ['
        '{"type": "event_candidate", "confidence": "high", "evidence": {"summary": "A concrete event."}, "source_trace_ids": {"chapter_id": "ch_001", "paragraph_ids": ["p_001"]}, "target_story_map_field": "key_events", "proposed_fields": {"summary": "Event 1", "event_type": "discovery"}}, '
        '{"type": "event_candidate", "confidence": "low", "evidence": {"summary": "Truncated eve'
    )
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=RealLikeRouter(text=text, finish_reason="length"),
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert any(err["code"] == "truncated_model_output" for err in semantic["errors"])
    assert len(semantic["candidates"]) == 1
    assert semantic["candidates"][0]["proposed_fields"]["summary"] == "Event 1"


class FaultyRouter:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def dispatch(self, request: LLMRequest) -> RoutedLLMResult:
        raise self.exc


def test_story_semantic_parser_degrades_gracefully_on_auth_failure(tmp_path: Path) -> None:
    from novel2script.llm.openai_compatible_provider import ProviderConfigurationError
    router = FaultyRouter(ProviderConfigurationError("Missing N2S_QWEN_API_KEY"))
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=router,  # type: ignore
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert len(semantic["errors"]) == 1
    assert semantic["errors"][0]["code"] == "provider_authentication_failed"
    assert "Missing N2S_QWEN_API_KEY" in semantic["errors"][0]["message"]


def test_story_semantic_parser_degrades_gracefully_on_rate_limit(tmp_path: Path) -> None:
    from novel2script.llm.openai_compatible_provider import ProviderRuntimeError
    err = ProviderRuntimeError(category="rate_limited", status_code=429)
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=FaultyRouter(err),  # type: ignore
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert len(semantic["errors"]) == 1
    assert semantic["errors"][0]["code"] == "provider_rate_limited"


def test_story_semantic_parser_degrades_gracefully_on_timeout(tmp_path: Path) -> None:
    from novel2script.llm.openai_compatible_provider import ProviderRuntimeError
    err = ProviderRuntimeError(category="timeout")
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=FaultyRouter(err),  # type: ignore
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert len(semantic["errors"]) == 1
    assert semantic["errors"][0]["code"] == "provider_timeout"


def test_story_semantic_parser_degrades_gracefully_on_connection_error(tmp_path: Path) -> None:
    from novel2script.llm.openai_compatible_provider import ProviderRuntimeError
    err = ProviderRuntimeError(category="connection_error")
    result = run_story_semantic_parser(
        STORY_MAP,
        out_path=tmp_path / "semantic_candidates.yaml",
        run_log_path=tmp_path / "semantic_run_log.yaml",
        router=FaultyRouter(err),  # type: ignore
        dry_run=False,
    )
    semantic = result["semantic_candidates"]
    assert semantic["candidates"] == []
    assert len(semantic["errors"]) == 1
    assert semantic["errors"][0]["code"] == "provider_connection_failed"
