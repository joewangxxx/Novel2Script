from __future__ import annotations

from pathlib import Path
import json

import pytest
import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main
from novel2script.llm.router import RoutedLLMResult
from novel2script.llm.types import LLMResponse


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
SCHEMA = ROOT / "schemas" / "semantic_candidates.schema.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_run_agent_story_semantic_parser_defaults_to_dry_run_and_valid_schema(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
        ]
    )

    assert exit_code == 0
    data = _load_yaml(out_path)
    semantic = data["semantic_candidates"]
    assert semantic["agent_id"] == "story_semantic_parser"
    assert semantic["provider_profile"] == "mock_dry_run"
    assert semantic["dry_run"] is True
    assert semantic["run_log"] == str(run_log_path)
    assert semantic["candidates"]
    Draft202012Validator(_load_yaml(SCHEMA)).validate(data)


def test_run_agent_story_semantic_parser_redacts_prompt_and_keeps_story_map(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    before = STORY_MAP.read_bytes()
    story_map_doc = _load_yaml(STORY_MAP)
    excerpt = story_map_doc["story_map"]["chapters"][0]["paragraphs"][0][
        "text_preview"
    ]

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert STORY_MAP.read_bytes() == before
    run_log_text = run_log_path.read_text(encoding="utf-8")
    assert "prompt_hash" in run_log_text
    assert "stored_prompt: false" in run_log_text
    assert "Agent: story_semantic_parser" not in run_log_text
    assert excerpt not in run_log_text


def test_run_agent_story_semantic_parser_returns_nonzero_for_missing_input(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(tmp_path / "missing_story_map.yaml"),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
        ]
    )

    assert exit_code != 0
    assert not out_path.exists()
    assert not run_log_path.exists()


def test_run_agent_story_semantic_parser_allow_network_requires_qwen_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("N2S_QWEN_API_KEY", raising=False)
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--allow-network",
        ]
    )

    assert exit_code != 0
    assert out_path.exists()
    assert run_log_path.exists()
    data = _load_yaml(out_path)
    assert data["semantic_candidates"]["errors"][0]["code"] == "provider_authentication_failed"


class CLIFakeRealRouter:
    def __init__(
        self,
        *,
        text: str | None = None,
        finish_reason: str = "stop",
    ) -> None:
        self.text = text
        self.finish_reason = finish_reason

    def dispatch(self, request):
        text = self.text if self.text is not None else _valid_model_json()
        response = LLMResponse(
            text=text,
            model="qwen-long",
            provider="qwen_long",
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            latency_ms=1,
            finish_reason=self.finish_reason,
            run_id="llm_run_cli_fake",
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


def _valid_model_json() -> str:
    return json.dumps(
        {
            "candidates": [
                {
                    "type": "event_candidate",
                    "confidence": "medium",
                    "evidence": {"summary": "A CLI fake response."},
                    "source_trace_ids": {
                        "chapter_id": "ch_001",
                        "paragraph_ids": ["p_001"],
                    },
                    "target_story_map_field": "key_events",
                    "proposed_fields": {"summary": "CLI parsed event."},
                }
            ]
        }
    )


def test_run_agent_story_semantic_parser_cli_parses_fake_real_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    monkeypatch.setattr(
        "novel2script.cli.LLMRouter.from_environment",
        lambda allow_network: CLIFakeRealRouter(),
    )

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--allow-network",
        ]
    )

    assert exit_code == 0
    semantic = _load_yaml(out_path)["semantic_candidates"]
    assert semantic["candidates"][0]["id"] == "semcand_001"
    assert semantic["candidates"][0]["proposed_fields"]["summary"] == (
        "CLI parsed event."
    )
    assert "CLI fake response" not in run_log_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "finish_reason", "expected_code"),
    [
        ('{"candidates": [}', "stop", "malformed_model_json"),
        (" ", "stop", "empty_model_output"),
        ('{"candidates": [{"type":', "length", "truncated_model_output"),
    ],
)
def test_run_agent_story_semantic_parser_cli_returns_nonzero_for_blocked_real_output(
    tmp_path: Path,
    monkeypatch,
    text: str,
    finish_reason: str,
    expected_code: str,
) -> None:
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    before = STORY_MAP.read_bytes()
    monkeypatch.setattr(
        "novel2script.cli.LLMRouter.from_environment",
        lambda allow_network: CLIFakeRealRouter(
            text=text,
            finish_reason=finish_reason,
        ),
    )

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--allow-network",
        ]
    )

    assert exit_code != 0
    assert STORY_MAP.read_bytes() == before
    assert out_path.exists()
    assert run_log_path.exists()
    data = _load_yaml(out_path)
    Draft202012Validator(_load_yaml(SCHEMA)).validate(data)
    semantic = data["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == expected_code


def test_run_agent_story_semantic_parser_cli_redacts_schema_invalid_response(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    marker = "SENSITIVE_MODEL_RESPONSE_MARKER_9f7a"
    invalid = json.loads(_valid_model_json())
    invalid["candidates"][0]["description"] = marker
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    monkeypatch.setattr(
        "novel2script.cli.LLMRouter.from_environment",
        lambda allow_network: CLIFakeRealRouter(text=json.dumps(invalid)),
    )

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--allow-network",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code != 0
    assert marker not in captured.err
    assert marker not in out_path.read_text(encoding="utf-8")
    assert marker not in run_log_path.read_text(encoding="utf-8")
    data = _load_yaml(out_path)
    Draft202012Validator(_load_yaml(SCHEMA)).validate(data)
    assert data["semantic_candidates"]["errors"][0]["code"] == (
        "invalid_model_output_schema"
    )


def test_run_agent_story_semantic_parser_cli_returns_nonzero_when_all_candidates_excluded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    invalid_trace = json.loads(_valid_model_json())
    invalid_trace["candidates"][0]["source_trace_ids"]["chapter_id"] = "ch_999"
    out_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    monkeypatch.setattr(
        "novel2script.cli.LLMRouter.from_environment",
        lambda allow_network: CLIFakeRealRouter(text=json.dumps(invalid_trace)),
    )

    exit_code = main(
        [
            "run-agent",
            "story-semantic-parser",
            "--story-map",
            str(STORY_MAP),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--allow-network",
        ]
    )

    assert exit_code != 0
    semantic = _load_yaml(out_path)["semantic_candidates"]
    assert semantic["candidates"] == []
    assert semantic["errors"][0]["code"] == "hallucinated_source_trace"
