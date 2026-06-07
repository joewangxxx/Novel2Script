from pathlib import Path
import time
from unittest.mock import patch

import pytest
import yaml

from novel2script.cli import main

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_NOVEL = ROOT / "examples" / "input" / "sample_novel_3_chapters.md"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_run_pipeline_e2e_dry_run_generates_all_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "pipeline_out"
    
    # 第一次运行：完整生成所有中间与最终产物
    exit_code = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    
    # 检查 11 步关键产物是否存在
    expected_files = [
        "story_map.yaml",
        "semantic_candidates.yaml",
        "semantic_run_log.yaml",
        "decisions.yaml",
        "story_map.merged.yaml",
        "semantic_candidate_merge_report.yaml",
        "outline.yaml",
        "character_bible.yaml",
        "screenplay.yaml",
        "review_report.yaml",
        "validation_report.yaml",
        "screenplay.fountain",
        "screenplay.fountain.map.json",
        "quality_report.yaml",
        "quality_dashboard.md",
        "author_review_packet.md",
        "author_review_decisions.yaml",
    ]
    
    for filename in expected_files:
        path = out_dir / filename
        assert path.exists(), f"Expected file {filename} does not exist"

    # 验证最终合并出的 story_map.merged.yaml 确实包含合并后的字段
    merged = _load_yaml(out_dir / "story_map.merged.yaml")
    assert merged["story_map"]["chapters"]


def test_run_pipeline_breakpoint_skips_existing_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "pipeline_out"
    
    # 第一次运行，生成全部产物
    exit_code = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert exit_code == 0
    
    story_map_path = out_dir / "story_map.yaml"
    assert story_map_path.exists()
    
    # 手动在 story_map.yaml 中注入一个特殊标记，以识别是否被跳过
    original_content = story_map_path.read_text(encoding="utf-8")
    modified_content = original_content + "\n# WORKBENCH_BREAKPOINT_TEST_TAG\n"
    story_map_path.write_text(modified_content, encoding="utf-8")
    
    # 再次运行，不加 --force，理应跳过第一步，保留标记
    exit_code2 = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert exit_code2 == 0
    assert "# WORKBENCH_BREAKPOINT_TEST_TAG" in story_map_path.read_text(encoding="utf-8")


def test_run_pipeline_force_rewrites_all(tmp_path: Path) -> None:
    out_dir = tmp_path / "pipeline_out"
    
    # 第一次运行
    exit_code = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert exit_code == 0
    
    story_map_path = out_dir / "story_map.yaml"
    
    # 手动注入标记
    original_content = story_map_path.read_text(encoding="utf-8")
    modified_content = original_content + "\n# WORKBENCH_BREAKPOINT_TEST_TAG\n"
    story_map_path.write_text(modified_content, encoding="utf-8")
    
    # 再次运行并指定 --force，理应强行重刷，清除标记
    exit_code2 = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
            "--force",
        ]
    )
    assert exit_code2 == 0
    assert "# WORKBENCH_BREAKPOINT_TEST_TAG" not in story_map_path.read_text(encoding="utf-8")


def test_run_pipeline_resumes_from_failure(tmp_path: Path) -> None:
    out_dir = tmp_path / "pipeline_out"
    
    # 模拟在 Step 4 (build-outline) 时抛出异常
    with patch("novel2script.cli.build_outline", side_effect=ValueError("Simulated Outline Builder Failure")):
        exit_code = main(
            [
                "run-pipeline",
                "--novel",
                str(SAMPLE_NOVEL),
                "--out-dir",
                str(out_dir),
            ]
        )
        assert exit_code == 1  # 应该退出状态码为 1
        
    # 校验前三步已成功产出，但第四步未成功产出
    assert (out_dir / "story_map.merged.yaml").exists()
    assert not (out_dir / "outline.yaml").exists()
    
    # 第二次无 Patch 正常续跑运行
    exit_code2 = main(
        [
            "run-pipeline",
            "--novel",
            str(SAMPLE_NOVEL),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert exit_code2 == 0
    
    # 校验后续生成的所有最终产物是否存在
    assert (out_dir / "outline.yaml").exists()
    assert (out_dir / "author_review_packet.md").exists()
