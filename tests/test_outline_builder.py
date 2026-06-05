import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.planners.outline_builder import build_outline


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
OUTLINE_SCHEMA = ROOT / "schemas" / "outline.schema.json"


def _load_story_map() -> dict:
    return yaml.safe_load(STORY_MAP.read_text(encoding="utf-8"))


def test_build_outline_matches_schema_and_preserves_source_trace():
    story_map_doc = _load_story_map()
    outline_doc = build_outline(
        story_map_doc,
        story_map_file="examples/output/generated_story_map.yaml",
    )
    schema = json.loads(OUTLINE_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(outline_doc)
    outline = outline_doc["outline"]

    assert outline["logline"]["text"]
    assert outline["logline"]["source_trace"]
    assert outline["logline"]["ai_tags"]["inferred"] is True
    assert outline["logline"]["ai_tags"]["confidence"] == "medium"
    assert outline["theme_candidates"]
    assert all(item["source_trace"] for item in outline["theme_candidates"])


def test_build_outline_groups_events_into_acts_and_scene_plan():
    story_map_doc = _load_story_map()
    story_map = story_map_doc["story_map"]
    outline = build_outline(story_map_doc)["outline"]
    event_ids = [event["id"] for event in story_map["key_events"]]

    assert [act["act_type"] for act in outline["act_structure"]] == [
        "act_1",
        "act_2",
        "act_3",
    ]
    assert len(outline["scene_plan"]) == len(story_map["key_events"])
    assert outline["source_coverage"]["story_event_count"] == len(event_ids)
    assert outline["source_coverage"]["covered_event_ids"] == event_ids
    assert outline["source_coverage"]["uncovered_event_ids"] == []

    for scene in outline["scene_plan"]:
        assert scene["source_event_ids"]
        assert scene["source_trace"]
        assert scene["source_trace"][0]["event_ids"] == scene["source_event_ids"]
        assert scene["ai_tags"]["inferred"] is True


def test_outline_does_not_emit_screenplay_structure():
    outline = build_outline(_load_story_map())["outline"]

    assert "scenes" not in outline
    assert "beats" not in outline
    assert "elements" not in outline
