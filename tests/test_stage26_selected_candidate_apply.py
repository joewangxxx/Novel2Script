from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.stage26_selected_candidate_apply import (
    apply_stage24_selected_candidates_to_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / "examples" / "output" / "test1_sanguo_stage24_selected_candidates.yaml"
OUTLINE = ROOT / "examples" / "output" / "test1_sanguo_outline.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "test1_sanguo_character_bible.yaml"
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.enhanced.yaml"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate(path: Path, schema_name: str) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(_load_yaml(path))


def test_apply_stage24_selected_candidates_to_new_schema_valid_artifacts(tmp_path):
    outline_out = tmp_path / "outline.stage26.yaml"
    character_out = tmp_path / "character_bible.stage26.yaml"
    screenplay_out = tmp_path / "screenplay.stage26.yaml"
    report_path = tmp_path / "stage26_report.yaml"
    before_outline = OUTLINE.read_bytes()
    before_character = CHARACTER_BIBLE.read_bytes()
    before_screenplay = SCREENPLAY.read_bytes()

    report = apply_stage24_selected_candidates_to_artifacts(
        selected_candidates_path=SELECTED,
        outline_path=OUTLINE,
        character_bible_path=CHARACTER_BIBLE,
        screenplay_path=SCREENPLAY,
        outline_out_path=outline_out,
        character_bible_out_path=character_out,
        screenplay_out_path=screenplay_out,
        report_path=report_path,
    )

    assert OUTLINE.read_bytes() == before_outline
    assert CHARACTER_BIBLE.read_bytes() == before_character
    assert SCREENPLAY.read_bytes() == before_screenplay
    assert report == _load_yaml(report_path)
    body = report["stage26_selected_candidate_apply_report"]
    assert body["status"] == "success"
    assert body["applied_count"] == 4
    assert body["blocked_count"] == 0
    assert body["preserved_original_artifacts"] is True
    _validate(outline_out, "outline.schema.json")
    _validate(character_out, "character_bible.schema.json")
    _validate(screenplay_out, "screenplay.schema.json")
    outline = _load_yaml(outline_out)["outline"]
    assert "stage24/adaptplan_001" in outline["scene_plan"][0]["ai_tags"]["notes"]
    bible = _load_yaml(character_out)["character_bible"]
    assert "stage24/charbible_001" in bible["characters"][0]["flaw"]["ai_tags"]["notes"]
    screenplay = _load_yaml(screenplay_out)
    applied_elements = [
        element
        for scene in screenplay["scenes"]
        for element in scene.get("elements", [])
        if element.get("stage24_candidate_id")
    ]
    assert {element["stage24_candidate_id"] for element in applied_elements} == {
        "scenewrite_001",
        "dialogueopt_001",
    }
    for element in applied_elements:
        assert element["requires_author_approval"] is True
        assert element["provider_profile"] == "kimi_creative"
