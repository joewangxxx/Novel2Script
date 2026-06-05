import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.generators.screenplay_builder import build_screenplay


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "generated_story_map.yaml"
OUTLINE = ROOT / "examples" / "output" / "generated_outline.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "generated_character_bible.yaml"
SCREENPLAY_SCHEMA = ROOT / "schemas" / "screenplay.schema.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _build() -> tuple[dict, dict, dict, dict]:
    story_map_doc = _load_yaml(STORY_MAP)
    outline_doc = _load_yaml(OUTLINE)
    character_bible_doc = _load_yaml(CHARACTER_BIBLE)
    screenplay = build_screenplay(
        story_map_doc,
        outline_doc,
        character_bible_doc,
        story_map_file="examples/output/generated_story_map.yaml",
        outline_file="examples/output/generated_outline.yaml",
        character_bible_file="examples/output/generated_character_bible.yaml",
    )
    return story_map_doc, outline_doc, character_bible_doc, screenplay


def test_build_screenplay_matches_schema_and_maps_characters_from_bible():
    story_map_doc, _outline_doc, character_bible_doc, screenplay = _build()
    schema = json.loads(SCREENPLAY_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(screenplay)

    bible_characters = character_bible_doc["character_bible"]["characters"]
    assert screenplay["schema_version"] == "0.1.0"
    assert screenplay["source"]["chapter_count"] == story_map_doc["story_map"]["source"]["chapter_count"]
    assert [character["id"] for character in screenplay["characters"]] == [
        character["id"] for character in bible_characters
    ]
    assert all(character["source_trace"] for character in screenplay["characters"])
    assert all(character["source_trace_ids"] for character in screenplay["characters"])
    assert all(character["locked"] is False for character in screenplay["characters"])


def test_build_screenplay_creates_stable_scenes_from_outline_scene_plan():
    _story_map_doc, outline_doc, _character_bible_doc, screenplay = _build()
    scene_plan = outline_doc["outline"]["scene_plan"]

    assert len(screenplay["scenes"]) == len(scene_plan)
    assert [scene["id"] for scene in screenplay["scenes"]] == [
        f"scene_{index:03d}" for index in range(1, len(scene_plan) + 1)
    ]

    for generated_scene, planned_scene in zip(screenplay["scenes"], scene_plan):
        assert generated_scene["source_outline_scene_id"] == planned_scene["id"]
        assert generated_scene["source_trace"]["chapter"] >= 1
        assert len(generated_scene["source_trace"]["paragraph_range"]) == 2
        assert generated_scene["source_trace_ids"]["outline_scene_ids"] == [planned_scene["id"]]
        assert generated_scene["beats"]
        assert generated_scene["elements"]


def test_build_screenplay_populates_required_beat_fields_with_trace_and_ai_tags():
    _story_map_doc, _outline_doc, _character_bible_doc, screenplay = _build()
    required_fields = {
        "objective",
        "tactic",
        "obstacle",
        "conflict",
        "stakes",
        "turn",
        "externalized_action",
    }

    for scene in screenplay["scenes"]:
        for beat in scene["beats"]:
            assert required_fields <= set(beat)
            assert all(beat[field] for field in required_fields)
            assert beat["source_trace"]
            assert beat["source_trace_ids"]
            assert beat["ai_tags"]["inferred"] is True
            assert beat["ai_tags"]["needs_human_review"] is True


def test_build_screenplay_creates_conservative_elements_with_trace_and_ai_tags():
    _story_map_doc, _outline_doc, _character_bible_doc, screenplay = _build()

    for scene in screenplay["scenes"]:
        for element in scene["elements"]:
            assert element["type"] in {"action", "note"}
            assert element["text"]
            assert element["source_trace"]
            assert element["source_trace_ids"]
            assert element["ai_tags"]["confidence"] in {"low", "medium", "high"}
