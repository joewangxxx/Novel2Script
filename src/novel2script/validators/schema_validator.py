from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from novel2script.io import read_json, read_yaml


def validate_schema(yaml_path: str, schema_path: str) -> dict[str, Any]:
    screenplay = read_yaml(yaml_path)
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(screenplay), key=_error_sort_key)

    return {
        "schema_validity": {
            "passed": not errors,
            "errors": [_format_error(error) for error in errors],
        }
    }


def _error_sort_key(error: ValidationError) -> tuple[str, str]:
    return (_field_path(error), error.message)


def _format_error(error: ValidationError) -> dict[str, str]:
    return {
        "field_path": _field_path(error),
        "message": error.message,
        "validator": error.validator,
        "suggested_fix": _suggest_fix(error),
    }


def _field_path(error: ValidationError) -> str:
    if error.path:
        parts: list[str] = []
        for part in error.path:
            if isinstance(part, int):
                if not parts:
                    parts.append(f"[{part}]")
                else:
                    parts[-1] = f"{parts[-1]}[{part}]"
            else:
                parts.append(str(part))
        return ".".join(parts)

    if error.validator == "required" and error.validator_value:
        missing = _missing_required_field(error)
        return missing or "$"

    return "$"


def _missing_required_field(error: ValidationError) -> str | None:
    if not error.message.startswith("'"):
        return None
    missing = error.message.split("'", 2)[1]
    base = _path_from_parts(error.absolute_path)
    return f"{base}.{missing}" if base else missing


def _path_from_parts(parts: Any) -> str:
    rendered: list[str] = []
    for part in parts:
        if isinstance(part, int):
            if not rendered:
                rendered.append(f"[{part}]")
            else:
                rendered[-1] = f"{rendered[-1]}[{part}]"
        else:
            rendered.append(str(part))
    return ".".join(rendered)


def _suggest_fix(error: ValidationError) -> str:
    if error.validator == "required":
        missing = _missing_required_field(error)
        if missing:
            return f"Add required field '{missing}'."
        return "Add the missing required field."
    if error.validator == "type":
        expected = error.validator_value
        return f"Use value type '{expected}'."
    if error.validator == "enum":
        return f"Use one of: {', '.join(map(str, error.validator_value))}."
    if error.validator == "minimum":
        return f"Use a value greater than or equal to {error.validator_value}."
    if error.validator == "additionalProperties":
        return "Remove unsupported fields or update the schema intentionally."
    return "Adjust the YAML value to satisfy the schema rule."
