from pathlib import Path

import yaml

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
STAGE24_CANDIDATES = [
    ROOT / "examples" / "output" / "test1_sanguo_adaptation_planner_candidates.real_kimi.yaml",
    ROOT / "examples" / "output" / "test1_sanguo_character_bible_agent_candidates.real_kimi.yaml",
    ROOT / "examples" / "output" / "test1_sanguo_scene_writer_agent_candidates.real_kimi.yaml",
    ROOT / "examples" / "output" / "test1_sanguo_dialogue_optimizer_agent_candidates.real_kimi.yaml",
]


def test_stage24_candidate_review_cli_prepare_and_apply_pending(tmp_path):
    packet_path = tmp_path / "packet.md"
    decisions_path = tmp_path / "decisions.yaml"
    selected_path = tmp_path / "selected.yaml"
    report_path = tmp_path / "report.yaml"
    prepare_args = ["prepare-stage24-candidate-review"]
    for path in STAGE24_CANDIDATES:
        prepare_args.extend(["--candidate-sidecar", str(path)])
    prepare_args.extend(
        ["--packet", str(packet_path), "--decisions", str(decisions_path)]
    )

    assert main(prepare_args) == 0
    assert packet_path.exists()
    assert decisions_path.exists()

    apply_args = ["apply-stage24-candidates"]
    for path in STAGE24_CANDIDATES:
        apply_args.extend(["--candidate-sidecar", str(path)])
    apply_args.extend(
        [
            "--decisions",
            str(decisions_path),
            "--selected",
            str(selected_path),
            "--report",
            str(report_path),
        ]
    )

    assert main(apply_args) == 0
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))[
        "stage24_candidate_apply_report"
    ]
    assert report["status"] == "blocked_pending_author_review"
    assert report["selected_count"] == 0
