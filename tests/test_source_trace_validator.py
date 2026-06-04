from pathlib import Path

import yaml

from novel2script.validators.source_trace_validator import validate_source_trace


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_YAML = ROOT / "examples" / "output" / "sample_screenplay.yaml"


def test_missing_source_trace_is_reported(tmp_path):
    data = yaml.safe_load(SAMPLE_YAML.read_text(encoding="utf-8"))
    data["scenes"][0]["elements"][0].pop("source_trace")
    invalid_yaml = tmp_path / "missing_source_trace.yaml"
    invalid_yaml.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    report = validate_source_trace(str(invalid_yaml))

    assert report["source_coverage"]["checked_targets"] > 0
    assert report["source_coverage"]["score"] < 1.0
    assert any(
        item["yaml_path"] == "scenes[0].elements[0].source_trace"
        for item in report["source_coverage"]["missing_targets"]
    )


def test_invalid_paragraph_range_is_reported(tmp_path):
    data = yaml.safe_load(SAMPLE_YAML.read_text(encoding="utf-8"))
    data["scenes"][0]["source_trace"]["paragraph_range"] = [4, 2]
    invalid_yaml = tmp_path / "invalid_trace_range.yaml"
    invalid_yaml.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    report = validate_source_trace(str(invalid_yaml))

    assert any(
        item["yaml_path"] == "scenes[0].source_trace"
        for item in report["source_coverage"]["invalid_targets"]
    )
