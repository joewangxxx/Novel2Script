from pathlib import Path

import yaml

from novel2script.validators.reference_validator import validate_references


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_YAML = ROOT / "examples" / "output" / "sample_screenplay.yaml"


def test_missing_dialogue_character_reference_is_reported(tmp_path):
    data = yaml.safe_load(SAMPLE_YAML.read_text(encoding="utf-8"))
    data["scenes"][0]["elements"][2]["character_id"] = "char_missing"
    invalid_yaml = tmp_path / "missing_character_ref.yaml"
    invalid_yaml.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    report = validate_references(str(invalid_yaml))

    assert report["reference_integrity"]["passed"] is False
    assert report["reference_integrity"]["missing_references"] == [
        {
            "yaml_path": "scenes[0].elements[2].character_id",
            "reference_type": "character_id",
            "missing_id": "char_missing",
            "message": "Dialogue character_id does not exist in characters.",
        }
    ]
