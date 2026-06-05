import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.planners.character_bible_builder import build_character_bible


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
CHARACTER_BIBLE_SCHEMA = ROOT / "schemas" / "character_bible.schema.json"


def _load_story_map() -> dict:
    return yaml.safe_load(STORY_MAP.read_text(encoding="utf-8"))


def test_build_character_bible_matches_schema_and_includes_all_detected_characters():
    story_map_doc = _load_story_map()
    bible_doc = build_character_bible(
        story_map_doc,
        story_map_file="examples/output/generated_story_map.yaml",
    )
    schema = json.loads(CHARACTER_BIBLE_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(bible_doc)
    bible = bible_doc["character_bible"]
    source_characters = story_map_doc["story_map"]["characters_detected"]

    assert [character["id"] for character in bible["characters"]] == [
        character["id"] for character in source_characters
    ]
    assert all(character["locked"] is False for character in bible["characters"])
    assert all(character["source_trace"] for character in bible["characters"])
    assert all(character["ai_tags"]["needs_human_review"] is True for character in bible["characters"])


def test_character_bible_uses_low_confidence_placeholders_instead_of_inventing():
    bible = build_character_bible(_load_story_map())["character_bible"]

    for character in bible["characters"]:
        for field_name in ["want", "need", "flaw"]:
            field = character[field_name]
            assert field["text"] == ""
            assert field["source_trace"]
            assert field["ai_tags"]["inferred"] is True
            assert field["ai_tags"]["confidence"] == "low"
            assert field["ai_tags"]["needs_human_review"] is True
        assert character["voice"]["summary"] == ""
        assert character["voice"]["dialogue_rules"] == []
        assert character["voice"]["source_trace"]
        assert character["arc"]["turning_points"]


def test_character_bible_records_uncertainties_for_weak_inference_fields():
    bible = build_character_bible(_load_story_map())["character_bible"]

    assert bible["uncertainties"]
    categories = {item["category"] for item in bible["uncertainties"]}
    assert {"weak_want_evidence", "weak_need_evidence", "weak_voice_evidence"} <= categories
    assert all(item["character_id"].startswith("char_") for item in bible["uncertainties"])
