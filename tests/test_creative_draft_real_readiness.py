from pathlib import Path
import json
import re
import subprocess
import sys

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples/output/test1_sanguo_screenplay.yaml"
AUTHOR_REVIEW_REPORT = (
    ROOT / "examples/output/test1_sanguo_author_review_report.yaml"
)
MOCK_CANDIDATES = (
    ROOT / "examples/output/test1_sanguo_creative_draft_candidates.mock.yaml"
)
ROUTING_CONFIG = ROOT / "config/agent_routing.example.yaml"


def test_stage19_readiness_contract_lists_real_kimi_hard_gates():
    doc = (
        ROOT / "docs/dev/PHASE_19_KIMI_REAL_CREATIVE_DRAFT_READINESS.md"
    ).read_text(encoding="utf-8")
    required_phrases = [
        "does not call real Kimi",
        "author_review_report",
        "kimi_dialogue_draft",
        "max_attempts=1",
        "at most one real Kimi call",
        "stop without retry",
        "schema-invalid",
        "finish_reason=length",
        "candidate_count > 0",
        "do not save prompt",
        "do not save model response",
        "do not save provider request payload",
        "do not auto-apply candidates",
        "source_screenplay_hash_before",
        "source_screenplay_hash_after",
    ]
    for phrase in required_phrases:
        assert phrase in doc


def test_mock_fixture_and_routing_are_valid_stage19_prerequisites():
    schema = json.loads(
        (ROOT / "schemas/creative_draft_candidates.schema.json").read_text(
            encoding="utf-8"
        )
    )
    fixture = yaml.safe_load(
        (
            ROOT / "examples/output/test1_sanguo_creative_draft_candidates.mock.yaml"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(fixture)
    creative = fixture["creative_draft_candidates"]
    assert creative["provider_profile"] == "mock_dry_run"
    assert creative["dry_run"] is True
    assert creative["human_approval_required"] is True
    assert creative["candidates"]

    routing = yaml.safe_load(
        (ROOT / "config/agent_routing.example.yaml").read_text(encoding="utf-8")
    )
    route = routing["agents"]["kimi_dialogue_scene_drafter"]
    assert route["provider_profile"] == "kimi_creative"
    assert route["fallback_profile"] == "mock_dry_run"
    assert route["output_policy"] == "human_approval_required"


def test_stage19_contract_does_not_embed_secrets_or_response_payloads():
    paths = [
        ROOT / "docs/dev/PHASE_19_KIMI_REAL_CREATIVE_DRAFT_READINESS.md",
    ]
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
        re.compile(r"Authorization\s*:\s*Bearer", re.IGNORECASE),
        re.compile(r"provider_body_retained\s*[:=]\s*true", re.IGNORECASE),
        re.compile(r"prompt_retained\s*[:=]\s*true", re.IGNORECASE),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            assert not pattern.search(text)


def test_readiness_gate_reports_ready_pending_network_authorization(monkeypatch):
    from novel2script.agents.creative_draft_readiness import (
        build_creative_draft_readiness_report,
    )

    monkeypatch.setenv("N2S_KIMI_API_KEY", "unit-test-kimi-key")
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")

    report = build_creative_draft_readiness_report(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        mock_candidates_path=MOCK_CANDIDATES,
        routing_config_path=ROUTING_CONFIG,
    )["creative_draft_readiness_report"]

    assert report["status"] == "ready_pending_network_authorization"
    assert report["checks"]["author_review_authorized"]["status"] == "pass"
    assert report["checks"]["mock_candidates_schema_valid"]["status"] == "pass"
    assert report["checks"]["candidate_targets_resolve"]["status"] == "pass"
    assert report["checks"]["agent_routing"]["status"] == "pass"
    assert report["checks"]["kimi_key_present"]["kimi_key_present"] is True
    assert report["checks"]["real_call_policy"]["max_attempts"] == 1
    assert report["checks"]["real_call_policy"]["allow_network"] is False
    assert report["checks"]["real_call_policy"]["real_run_authorized"] is False
    assert report["retention_policy"]["prompt_retention_allowed"] is False
    assert report["retention_policy"]["model_response_retention_allowed"] is False
    assert report["retention_policy"]["provider_body_retention_allowed"] is False
    assert report["retention_policy"]["auto_apply_allowed"] is False


def test_readiness_gate_blocks_when_author_review_not_authorized(
    tmp_path, monkeypatch
):
    from novel2script.agents.creative_draft_readiness import (
        build_creative_draft_readiness_report,
    )

    monkeypatch.setenv("N2S_KIMI_API_KEY", "unit-test-kimi-key")
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")
    blocked_report = tmp_path / "author_review_report.yaml"
    doc = yaml.safe_load(AUTHOR_REVIEW_REPORT.read_text(encoding="utf-8"))
    doc["author_review_report"]["next_stage_authorization"] = "none"
    blocked_report.write_text(yaml.safe_dump(doc), encoding="utf-8")

    report = build_creative_draft_readiness_report(
        screenplay_path=SCREENPLAY,
        author_review_report_path=blocked_report,
        mock_candidates_path=MOCK_CANDIDATES,
        routing_config_path=ROUTING_CONFIG,
    )["creative_draft_readiness_report"]

    assert report["status"] == "blocked"
    assert report["checks"]["author_review_authorized"]["status"] == "fail"
    assert "author_review_not_authorized" in report["blocking_codes"]


def test_readiness_gate_blocks_invalid_mock_candidate_schema(
    tmp_path, monkeypatch
):
    from novel2script.agents.creative_draft_readiness import (
        build_creative_draft_readiness_report,
    )

    monkeypatch.setenv("N2S_KIMI_API_KEY", "unit-test-kimi-key")
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")
    invalid_candidates = tmp_path / "invalid_candidates.yaml"
    doc = yaml.safe_load(MOCK_CANDIDATES.read_text(encoding="utf-8"))
    del doc["creative_draft_candidates"]["candidates"][0]["source_trace"]
    invalid_candidates.write_text(yaml.safe_dump(doc), encoding="utf-8")

    report = build_creative_draft_readiness_report(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        mock_candidates_path=invalid_candidates,
        routing_config_path=ROUTING_CONFIG,
    )["creative_draft_readiness_report"]

    assert report["status"] == "blocked"
    assert report["checks"]["mock_candidates_schema_valid"]["status"] == "fail"
    assert "mock_candidates_schema_invalid" in report["blocking_codes"]


def test_readiness_gate_blocks_unresolved_candidate_target(tmp_path, monkeypatch):
    from novel2script.agents.creative_draft_readiness import (
        build_creative_draft_readiness_report,
    )

    monkeypatch.setenv("N2S_KIMI_API_KEY", "unit-test-kimi-key")
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")
    bad_target = tmp_path / "bad_target.yaml"
    doc = yaml.safe_load(MOCK_CANDIDATES.read_text(encoding="utf-8"))
    doc["creative_draft_candidates"]["candidates"][0]["target"][
        "scene_id"
    ] = "missing_scene"
    bad_target.write_text(yaml.safe_dump(doc), encoding="utf-8")

    report = build_creative_draft_readiness_report(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        mock_candidates_path=bad_target,
        routing_config_path=ROUTING_CONFIG,
    )["creative_draft_readiness_report"]

    assert report["status"] == "blocked"
    assert report["checks"]["candidate_targets_resolve"]["status"] == "fail"
    assert "candidate_target_unresolved" in report["blocking_codes"]


def test_readiness_gate_blocks_missing_kimi_key(monkeypatch):
    from novel2script.agents.creative_draft_readiness import (
        build_creative_draft_readiness_report,
    )

    monkeypatch.delenv("N2S_KIMI_API_KEY", raising=False)
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")

    report = build_creative_draft_readiness_report(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        mock_candidates_path=MOCK_CANDIDATES,
        routing_config_path=ROUTING_CONFIG,
    )["creative_draft_readiness_report"]

    assert report["status"] == "blocked"
    assert report["checks"]["kimi_key_present"]["status"] == "fail"
    assert report["checks"]["kimi_key_present"]["kimi_key_present"] is False
    assert "N2S_KIMI_API_KEY" in report["checks"]["kimi_key_present"]["env_var"]
    assert "unit-test-kimi-key" not in yaml.safe_dump(report)


def test_readiness_cli_writes_report_without_leaking_key(tmp_path, monkeypatch):
    monkeypatch.setenv("N2S_KIMI_API_KEY", "unit-test-kimi-key")
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")
    out_path = tmp_path / "readiness.yaml"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "novel2script.cli",
            "check-real-creative-draft-readiness",
            "--screenplay",
            str(SCREENPLAY),
            "--author-review-report",
            str(AUTHOR_REVIEW_REPORT),
            "--mock-candidates",
            str(MOCK_CANDIDATES),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    text = out_path.read_text(encoding="utf-8")
    report = yaml.safe_load(text)["creative_draft_readiness_report"]
    assert report["status"] == "ready_pending_network_authorization"
    assert "unit-test-kimi-key" not in text
    assert "unit-test-kimi-key" not in result.stderr


def test_readiness_cli_missing_input_returns_nonzero(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "novel2script.cli",
            "check-real-creative-draft-readiness",
            "--screenplay",
            str(tmp_path / "missing.yaml"),
            "--author-review-report",
            str(AUTHOR_REVIEW_REPORT),
            "--mock-candidates",
            str(MOCK_CANDIDATES),
            "--out",
            str(tmp_path / "readiness.yaml"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "check-real-creative-draft-readiness failed" in result.stderr
