from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_stage13h_artifacts.py"
SEMANTIC_SCHEMA = ROOT / "schemas" / "semantic_candidates.schema.json"


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _story_map() -> dict:
    return {
        "story_map": {
            "schema_version": "0.1.0",
            "source": {
                "type": "novel",
                "input_file": "examples/input/test1_sanguo.txt",
                "chapter_count": 1,
                "trace_unit": "chapter_paragraph",
            },
            "chapters": [
                {
                    "id": "ch_001",
                    "index": 1,
                    "title": "Fixture",
                    "source_heading": "第一回 Fixture",
                    "paragraphs": [
                        {
                            "id": "p_001",
                            "index": 1,
                            "text_preview": "刘备来到桃园。",
                        }
                    ],
                }
            ],
            "characters_detected": [],
            "locations_detected": [],
            "props_detected": [],
            "key_events": [],
            "timeline": [],
            "psychological_passages": [],
            "uncertainties": [],
        }
    }


def _semantic_candidates(story_path: Path, run_log_path: Path) -> dict:
    return {
        "semantic_candidates": {
            "schema_version": "0.1.0",
            "source_story_map": str(story_path),
            "agent_id": "story_semantic_parser",
            "provider_profile": "qwen_long",
            "dry_run": False,
            "candidates": [
                {
                    "id": "semcand_001",
                    "type": "event_candidate",
                    "confidence": "medium",
                    "evidence": {"summary": "A grounded event candidate."},
                    "source_trace_ids": {
                        "chapter_id": "ch_001",
                        "paragraph_ids": ["p_001"],
                    },
                    "target_story_map_field": "key_events",
                    "proposed_fields": {"summary": "刘备来到桃园。"},
                    "merge_policy": "human_approval_required",
                }
            ],
            "errors": [],
            "human_approval_required": True,
            "run_log": str(run_log_path),
            "metadata": {"provider_finish_reason": "stop"},
        }
    }


def _run_harness(story_path: Path, semantic_path: Path, run_log_path: Path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--story-map",
            str(story_path),
            "--semantic-candidates",
            str(semantic_path),
            "--run-log",
            str(run_log_path),
            "--semantic-schema",
            str(SEMANTIC_SCHEMA),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_stage13h_validation_harness_accepts_valid_artifacts(tmp_path: Path) -> None:
    story_path = tmp_path / "story_map.yaml"
    semantic_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    _write_yaml(story_path, _story_map())
    _write_yaml(semantic_path, _semantic_candidates(story_path, run_log_path))
    _write_yaml(
        run_log_path,
        {
            "llm_run_records": [
                {
                    "agent_id": "story_semantic_parser",
                    "stored_prompt": False,
                    "prompt_hash": "sha256:test",
                }
            ],
            "errors": [],
        },
    )

    result = _run_harness(story_path, semantic_path, run_log_path)

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["passed"] is True
    assert summary["candidate_count"] == 1
    assert summary["error_codes"] == []
    assert summary["trace_ok"] is True
    assert summary["security_scan"] == "pass"


def test_stage13h_validation_harness_rejects_run_log_prompt_leak(
    tmp_path: Path,
) -> None:
    story_path = tmp_path / "story_map.yaml"
    semantic_path = tmp_path / "semantic_candidates.yaml"
    run_log_path = tmp_path / "semantic_run_log.yaml"
    _write_yaml(story_path, _story_map())
    _write_yaml(semantic_path, _semantic_candidates(story_path, run_log_path))
    _write_yaml(
        run_log_path,
        {
            "llm_run_records": [
                {
                    "agent_id": "story_semantic_parser",
                    "stored_prompt": False,
                    "prompt": "Agent: story_semantic_parser\n刘备来到桃园。",
                }
            ],
            "errors": [],
        },
    )

    result = _run_harness(story_path, semantic_path, run_log_path)

    assert result.returncode != 0
    summary = json.loads(result.stdout)
    assert "run_log_prompt_or_raw_response_leak" in summary["failures"]
    assert "刘备来到桃园" not in result.stdout
