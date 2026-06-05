from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


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
