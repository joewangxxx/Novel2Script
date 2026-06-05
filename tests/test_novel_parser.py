import json
from pathlib import Path

from jsonschema import Draft202012Validator

from novel2script.parsers.novel_parser import parse_novel_text


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_NOVEL = ROOT / "examples" / "input" / "sample_novel_3_chapters.md"
STORY_MAP_SCHEMA = ROOT / "schemas" / "story_map.schema.json"


def _parse_sample() -> dict:
    return parse_novel_text(
        SAMPLE_NOVEL.read_text(encoding="utf-8"),
        input_file=str(SAMPLE_NOVEL),
    )


def test_sample_novel_parses_three_chapters_with_stable_ids():
    story_map = _parse_sample()["story_map"]

    assert story_map["source"]["chapter_count"] == 3
    assert [chapter["id"] for chapter in story_map["chapters"]] == [
        "ch_001",
        "ch_002",
        "ch_003",
    ]
    assert story_map["chapters"][0]["title"] == "雾里的钟声"


def test_paragraph_ids_are_stable_within_each_chapter():
    story_map = _parse_sample()["story_map"]

    for chapter in story_map["chapters"]:
        paragraph_ids = [paragraph["id"] for paragraph in chapter["paragraphs"]]
        assert paragraph_ids == [
            f"p_{index:03d}" for index in range(1, len(paragraph_ids) + 1)
        ]
        assert all(paragraph["text_preview"] for paragraph in chapter["paragraphs"])


def test_story_map_matches_schema_and_detects_basic_candidates():
    result = _parse_sample()
    schema = json.loads(STORY_MAP_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(result)
    story_map = result["story_map"]

    assert {item["name"] for item in story_map["characters_detected"]} >= {
        "林岚",
        "周澈",
    }
    assert "工周澈" not in {item["name"] for item in story_map["characters_detected"]}
    assert "录音机" not in {item["name"] for item in story_map["characters_detected"]}
    assert {item["name"] for item in story_map["locations_detected"]} >= {
        "邮局",
        "灯塔",
        "钟楼",
    }
    assert {item["name"] for item in story_map["props_detected"]} >= {
        "信封",
        "信",
        "船",
    }
    assert story_map["key_events"]
    assert story_map["timeline"]


def test_key_events_psychological_passages_and_uncertainties_have_source_trace():
    story_map = _parse_sample()["story_map"]

    assert story_map["key_events"]
    assert story_map["psychological_passages"]
    assert story_map["uncertainties"]

    for collection_name in [
        "key_events",
        "psychological_passages",
        "uncertainties",
    ]:
        for item in story_map[collection_name]:
            trace = item["source_trace"]
            assert trace["chapter_id"].startswith("ch_")
            assert trace["paragraph_ids"]
            assert all(paragraph_id.startswith("p_") for paragraph_id in trace["paragraph_ids"])


def test_plain_text_chapter_headings_are_supported():
    text = """第一章 起点

林岚在邮局想起旧事。

第2章 船影

周澈来到码头。

CHAPTER 3

船停在海边。
"""

    story_map = parse_novel_text(text, input_file="inline.txt")["story_map"]

    assert [chapter["id"] for chapter in story_map["chapters"]] == [
        "ch_001",
        "ch_002",
        "ch_003",
    ]
    assert [chapter["title"] for chapter in story_map["chapters"]] == [
        "起点",
        "船影",
        "CHAPTER 3",
    ]
