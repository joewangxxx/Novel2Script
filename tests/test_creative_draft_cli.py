from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
AUTHOR_REVIEW_REPORT = (
    ROOT / "examples" / "output" / "test1_sanguo_author_review_report.yaml"
)
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"
QUALITY_REPORT = ROOT / "examples" / "output" / "test1_sanguo_quality_report.yaml"
SCHEMA = ROOT / "schemas" / "creative_draft_candidates.schema.json"
MODEL_RESPONSE_MARKER = "raw" + "_response"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_run_agent_kimi_dialogue_scene_drafter_cli_writes_outputs(tmp_path):
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"
    before = SCREENPLAY.read_bytes()

    exit_code = main(
        [
            "run-agent",
            "kimi-dialogue-scene-drafter",
            "--screenplay",
            str(SCREENPLAY),
            "--author-review-report",
            str(AUTHOR_REVIEW_REPORT),
            "--review-report",
            str(REVIEW_REPORT),
            "--quality-report",
            str(QUALITY_REPORT),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert SCREENPLAY.read_bytes() == before
    assert out_path.exists()
    assert run_log_path.exists()
    data = _load_yaml(out_path)
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        data
    )
    creative = data["creative_draft_candidates"]
    assert creative["provider_profile"] == "mock_dry_run"
    assert creative["human_approval_required"] is True
    assert creative["candidates"]
    run_log = run_log_path.read_text(encoding="utf-8")
    assert "stored_prompt: false" in run_log
    assert MODEL_RESPONSE_MARKER not in run_log


def test_run_agent_kimi_dialogue_scene_drafter_cli_returns_nonzero_for_missing_input(
    tmp_path,
):
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "kimi-dialogue-scene-drafter",
            "--screenplay",
            str(tmp_path / "missing_screenplay.yaml"),
            "--author-review-report",
            str(AUTHOR_REVIEW_REPORT),
            "--review-report",
            str(REVIEW_REPORT),
            "--quality-report",
            str(QUALITY_REPORT),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code != 0
    assert not out_path.exists()
    assert not run_log_path.exists()


def test_run_agent_kimi_dialogue_scene_drafter_cli_returns_nonzero_when_unauthorized(
    tmp_path,
):
    unauthorized = _load_yaml(AUTHOR_REVIEW_REPORT)
    unauthorized["author_review_report"]["next_stage_authorization"] = "none"
    unauthorized_path = tmp_path / "unauthorized_author_review.yaml"
    unauthorized_path.write_text(
        yaml.safe_dump(unauthorized, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"

    exit_code = main(
        [
            "run-agent",
            "kimi-dialogue-scene-drafter",
            "--screenplay",
            str(SCREENPLAY),
            "--author-review-report",
            str(unauthorized_path),
            "--review-report",
            str(REVIEW_REPORT),
            "--quality-report",
            str(QUALITY_REPORT),
            "--out",
            str(out_path),
            "--run-log",
            str(run_log_path),
            "--dry-run",
        ]
    )

    assert exit_code != 0
    data = _load_yaml(out_path)
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        data
    )
    assert data["creative_draft_candidates"]["errors"][0]["code"] == (
        "author_review_not_authorized"
    )
