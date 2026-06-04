from pathlib import Path

import yaml

from novel2script.validators.schema_validator import validate_schema


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_YAML = ROOT / "examples" / "output" / "sample_screenplay.yaml"
SCHEMA = ROOT / "schemas" / "screenplay.schema.json"


def test_sample_yaml_passes_schema_validation():
    report = validate_schema(str(SAMPLE_YAML), str(SCHEMA))

    assert report["schema_validity"]["passed"] is True
    assert report["schema_validity"]["errors"] == []


def test_schema_validation_reports_field_path_and_suggested_fix(tmp_path):
    data = yaml.safe_load(SAMPLE_YAML.read_text(encoding="utf-8"))
    data.pop("metadata")
    invalid_yaml = tmp_path / "missing_metadata.yaml"
    invalid_yaml.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    report = validate_schema(str(invalid_yaml), str(SCHEMA))

    assert report["schema_validity"]["passed"] is False
    assert report["schema_validity"]["errors"]
    assert {
        "field_path",
        "message",
        "validator",
        "suggested_fix",
    } <= set(report["schema_validity"]["errors"][0])
