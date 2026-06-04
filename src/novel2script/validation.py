from __future__ import annotations

from typing import Any

from novel2script.validators.beat_validator import validate_beats
from novel2script.validators.reference_validator import validate_references
from novel2script.validators.schema_validator import validate_schema
from novel2script.validators.source_trace_validator import validate_source_trace


def validate_screenplay(yaml_path: str, schema_path: str) -> dict[str, Any]:
    report: dict[str, Any] = {}
    report.update(validate_schema(yaml_path, schema_path))
    report.update(validate_source_trace(yaml_path))
    report.update(validate_beats(yaml_path))
    report.update(validate_references(yaml_path))
    report["overall_passed"] = (
        report["schema_validity"]["passed"]
        and report["source_coverage"]["score"] == 1.0
        and report["beat_completeness"]["score"] == 1.0
        and report["reference_integrity"]["passed"]
    )
    return report
