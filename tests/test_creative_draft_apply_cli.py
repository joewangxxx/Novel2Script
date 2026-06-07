from pathlib import Path

import yaml

from novel2script.cli import main

from tests.test_creative_draft_apply import SCREENPLAY, _candidate_doc


def test_apply_creative_draft_cli_writes_outputs(tmp_path):
    candidates_path = tmp_path / "creative.yaml"
    candidates_path.write_text(
        yaml.safe_dump(_candidate_doc(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "enhanced.yaml"
    report_path = tmp_path / "apply_report.yaml"

    exit_code = main(
        [
            "apply-creative-draft",
            "--screenplay",
            str(SCREENPLAY),
            "--creative-candidates",
            str(candidates_path),
            "--out",
            str(out_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert out_path.exists()
    assert report_path.exists()
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert report["creative_draft_apply_report"]["applied_count"] == 1


def test_apply_creative_draft_cli_missing_input_returns_nonzero(tmp_path):
    exit_code = main(
        [
            "apply-creative-draft",
            "--screenplay",
            str(tmp_path / "missing.yaml"),
            "--creative-candidates",
            str(tmp_path / "creative.yaml"),
            "--out",
            str(tmp_path / "enhanced.yaml"),
            "--report",
            str(tmp_path / "apply_report.yaml"),
        ]
    )

    assert exit_code != 0
