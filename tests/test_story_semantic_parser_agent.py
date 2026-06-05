from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.story_semantic_parser import run_story_semantic_parser


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
