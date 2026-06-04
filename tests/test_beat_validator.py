from pathlib import Path

import yaml

from novel2script.validators.beat_validator import validate_beats


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_YAML = ROOT / "examples" / "output" / "sample_screenplay.yaml"


def test_missing_required_beat_field_is_reported(tmp_path):
    data = yaml.safe_load(SAMPLE_YAML.read_text(encoding="utf-8"))
    data["scenes"][0]["beats"][0].pop("stakes")
    invalid_yaml = tmp_path / "missing_beat_field.yaml"
    invalid_yaml.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    report = validate_beats(str(invalid_yaml))

    assert report["beat_completeness"]["score"] < 1.0
    assert report["beat_completeness"]["total_beats"] == 1
    assert report["beat_completeness"]["incomplete_beats"][0]["missing_fields"] == ["stakes"]
