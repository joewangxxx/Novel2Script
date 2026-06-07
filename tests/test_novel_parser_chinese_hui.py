from pathlib import Path

import yaml

from novel2script.cli import main
from novel2script.parsers.novel_parser import parse_novel_text

ROOT = Path(__file__).resolve().parents[1]
SANGUO_FIXTURE = ROOT / "examples" / "input" / "test1_sanguo.txt"


def test_chinese_hui_chapter_headings_are_supported():
    text = """第一回 刘关张桃园结义

刘备来到桃园。

第二回 谋董卓曹操献刀

曹操入府献刀。

第1回 新章标题

众人重新出发。"""

    story_map = parse_novel_text(text, input_file="inline.txt")["story_map"]

    assert story_map["source"]["chapter_count"] == 3
    assert [chapter["title"] for chapter in story_map["chapters"]] == [
        "刘关张桃园结义",
        "谋董卓曹操献刀",
        "新章标题",
    ]


def test_markdown_chinese_hui_heading_is_supported():
    text = """# 第一回 刘关张桃园结义

刘备来到桃园。

## 第二回 谋董卓曹操献刀

曹操入府献刀。"""

    story_map = parse_novel_text(text, input_file="inline.md")["story_map"]

    assert story_map["source"]["chapter_count"] == 2
    assert [chapter["source_heading"] for chapter in story_map["chapters"]] == [
        "# 第一回 刘关张桃园结义",
        "## 第二回 谋董卓曹操献刀",
    ]
    assert [chapter["title"] for chapter in story_map["chapters"]] == [
        "刘关张桃园结义",
        "谋董卓曹操献刀",
    ]


def test_sanguo_fixture_parses_five_chapters(tmp_path):
    output_path = tmp_path / "test1_story_map.yaml"

    exit_code = main(
        [
            "parse-novel",
            str(SANGUO_FIXTURE),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    story_map = yaml.safe_load(output_path.read_text(encoding="utf-8"))["story_map"]
    assert story_map["source"]["chapter_count"] == 5
    assert [chapter["id"] for chapter in story_map["chapters"]] == [
        "ch_001",
        "ch_002",
        "ch_003",
        "ch_004",
        "ch_005",
    ]
