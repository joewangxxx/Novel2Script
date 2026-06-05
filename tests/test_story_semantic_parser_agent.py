from __future__ import annotations

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


class RealLikeRouter:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def dispatch(self, request: LLMRequest) -> RoutedLLMResult:
        self.requests.append(request)
        response = LLMResponse(
            text="real semantic parser response",
            model="qwen-long",
            provider="qwen_long",
            usage={"input_tokens": 13, "output_tokens": 5, "total_tokens": 18},
            latency_ms=44,
            finish_reason="stop",
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

    run_log = _load_yaml(run_log_path)
    assert run_log["llm_run_records"][0]["provider"] == "qwen_long"
    assert run_log["llm_run_records"][0]["stored_prompt"] is False
    assert "real semantic parser response" not in run_log_path.read_text(encoding="utf-8")
