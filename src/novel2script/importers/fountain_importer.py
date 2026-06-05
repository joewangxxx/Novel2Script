from __future__ import annotations

import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from novel2script.exporters.fountain_exporter import export_fountain
from novel2script.io import read_json, read_text, read_yaml, write_yaml


SCHEMA_VERSION = "0.1.0"
DEFAULT_GENERATED_AT = "2026-06-05"
SAFE_HEADING_RE = re.compile(r"^scenes\[(\d+)\]\.heading$")
SAFE_ELEMENT_TEXT_RE = re.compile(r"^scenes\[(\d+)\]\.elements\[(\d+)\]\.text$")


def sync_fountain_to_yaml(
    screenplay_path: str,
    fountain_path: str,
    map_path: str,
    out_path: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Sync safe mapped Fountain text changes back into screenplay YAML."""
    screenplay = read_yaml(screenplay_path)
    sidecar = read_json(map_path)
    edited_lines = read_text(fountain_path).splitlines()
    baseline_lines = _baseline_lines(screenplay_path)
    mappings = _valid_mappings(sidecar.get("mappings", []))

    issues: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    line_drift = len(edited_lines) != len(baseline_lines)
    map_match = not line_drift

    if line_drift:
        issues.append(
            _issue(
                len(issues) + 1,
                "high",
                "line_drift",
                "Fountain line count differs from the baseline export.",
                "blocked",
            )
        )

    if not _same_file(sidecar.get("source_yaml"), screenplay_path) or not _same_file(
        sidecar.get("fountain_file"), fountain_path
    ):
        map_match = False
        issues.append(
            _issue(
                len(issues) + 1,
                "high",
                "map_mismatch",
                "Sidecar map source_yaml or fountain_file does not match import arguments.",
                "blocked",
            )
        )

    issues.extend(_mapping_order_issues(mappings, len(issues)))

    if issues:
        report = _report(
            screenplay_path,
            fountain_path,
            map_path,
            mappings,
            changes,
            issues,
            expected_line_count=len(baseline_lines),
            actual_line_count=len(edited_lines),
            line_drift=line_drift,
            map_match=map_match and not issues,
        )
        _write_report(report, report_path)
        return report

    updated = deepcopy(screenplay)
    for mapping in mappings:
        issue = _validate_mapping(mapping, updated, len(edited_lines))
        if issue:
            issues.append({**issue, "id": f"rt_issue_{len(issues) + 1:03d}"})
            continue
        change = _change_from_mapping(
            len(changes) + 1,
            mapping,
            updated,
            baseline_lines,
            edited_lines,
        )
        if change and change["original_text"] != change["normalized_text"]:
            _apply_change(updated, mapping, change["normalized_text"])
            changes.append(change)

    if any(issue["severity"] == "high" for issue in issues):
        report = _report(
            screenplay_path,
            fountain_path,
            map_path,
            mappings,
            changes=[],
            issues=issues,
            expected_line_count=len(baseline_lines),
            actual_line_count=len(edited_lines),
            line_drift=line_drift,
            map_match=False,
        )
        _write_report(report, report_path)
        return report

    if changes:
        metadata = updated.setdefault("metadata", {})
        metadata["semantic_fields_stale"] = True
        metadata["roundtrip"] = {
            "imported_at": DEFAULT_GENERATED_AT,
            "fountain_file": fountain_path,
            "map_file": map_path,
            "applied_changes": len(changes),
        }

    write_yaml(updated, out_path)
    report = _report(
        screenplay_path,
        fountain_path,
        map_path,
        mappings,
        changes,
        issues,
        expected_line_count=len(baseline_lines),
        actual_line_count=len(edited_lines),
        line_drift=line_drift,
        map_match=not issues,
    )
    _write_report(report, report_path)
    return report


def _baseline_lines(screenplay_path: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_path = Path(tmpdir) / "baseline.fountain"
        export_fountain(screenplay_path, str(baseline_path))
        return baseline_path.read_text(encoding="utf-8").splitlines()


def _valid_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _mapping_order_issues(mappings: list[dict[str, Any]], offset: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    previous_end = 0
    for mapping in mappings:
        line_start = int(mapping.get("line_start", 0) or 0)
        line_end = int(mapping.get("line_end", 0) or 0)
        if line_start < 1 or line_end < line_start or line_start <= previous_end:
            issues.append(
                _issue(
                    offset + len(issues) + 1,
                    "high",
                    "map_mismatch",
                    "Mapped line ranges are invalid, overlapping, or out of order.",
                    "blocked",
                    yaml_path=mapping.get("yaml_path"),
                    line_start=line_start if line_start >= 1 else None,
                    line_end=line_end if line_end >= 1 else None,
                )
            )
        previous_end = max(previous_end, line_end)
    return issues


def _validate_mapping(
    mapping: dict[str, Any], screenplay: dict[str, Any], line_count: int
) -> dict[str, Any] | None:
    yaml_path = str(mapping.get("yaml_path", ""))
    line_start = int(mapping.get("line_start", 0) or 0)
    line_end = int(mapping.get("line_end", 0) or 0)
    if line_start < 1 or line_end < line_start or line_end > line_count:
        return _issue(
            0,
            "high",
            "line_drift",
            "Mapped Fountain line range is outside the edited Fountain file.",
            "blocked",
            yaml_path=yaml_path,
            line_start=line_start if line_start >= 1 else None,
            line_end=line_end if line_end >= 1 else None,
        )

    heading_match = SAFE_HEADING_RE.match(yaml_path)
    if heading_match:
        scene_index = int(heading_match.group(1))
        scene = _scene(screenplay, scene_index)
        if not scene or scene.get("id") != mapping.get("scene_id"):
            return _issue_for_mapping(mapping, "structure_changed", "Mapped scene does not match current screenplay.")
        return None

    element_match = SAFE_ELEMENT_TEXT_RE.match(yaml_path)
    if not element_match:
        return _issue_for_mapping(mapping, "unsafe_yaml_path", "Mapped YAML path is not safe for Fountain import.")

    scene_index = int(element_match.group(1))
    element_index = int(element_match.group(2))
    scene = _scene(screenplay, scene_index)
    element = _element(screenplay, scene_index, element_index)
    if not scene or scene.get("id") != mapping.get("scene_id"):
        return _issue_for_mapping(mapping, "structure_changed", "Mapped scene does not match current screenplay.")
    if element is None or mapping.get("element_index") != element_index:
        return _issue_for_mapping(mapping, "structure_changed", "Mapped element index does not match current screenplay.")
    if element.get("type") == "note":
        return _issue_for_mapping(mapping, "unsupported_element_type", "Note elements are not safe for Fountain import.")
    return None


def _change_from_mapping(
    index: int,
    mapping: dict[str, Any],
    screenplay: dict[str, Any],
    baseline_lines: list[str],
    edited_lines: list[str],
) -> dict[str, Any] | None:
    yaml_path = str(mapping["yaml_path"])
    line_start = int(mapping["line_start"])
    line_end = int(mapping["line_end"])
    baseline_text = "\n".join(baseline_lines[line_start - 1 : line_end]).strip()
    edited_text = "\n".join(edited_lines[line_start - 1 : line_end]).strip()
    normalized_text = _normalize_text(mapping, screenplay, edited_lines[line_start - 1 : line_end])
    original_text = _yaml_text(screenplay, yaml_path)
    if baseline_text == edited_text or original_text == normalized_text:
        return None
    return {
        "id": f"rt_change_{index:03d}",
        "yaml_path": yaml_path,
        "target_type": "scene_heading" if SAFE_HEADING_RE.match(yaml_path) else "element_text",
        "scene_id": mapping.get("scene_id"),
        "element_index": mapping.get("element_index"),
        "line_start": line_start,
        "line_end": line_end,
        "original_text": original_text,
        "new_text": edited_text,
        "normalized_text": normalized_text,
        "action": "applied",
        "safe_field": True,
    }


def _normalize_text(
    mapping: dict[str, Any], screenplay: dict[str, Any], mapped_lines: list[str]
) -> str:
    yaml_path = str(mapping["yaml_path"])
    if SAFE_HEADING_RE.match(yaml_path):
        return "\n".join(mapped_lines).strip()

    element_match = SAFE_ELEMENT_TEXT_RE.match(yaml_path)
    if not element_match:
        return "\n".join(mapped_lines).strip()
    scene_index = int(element_match.group(1))
    element_index = int(element_match.group(2))
    element = _element(screenplay, scene_index, element_index) or {}
    element_type = element.get("type")
    text = "\n".join(mapped_lines).strip()
    if element_type == "dialogue":
        return "\n".join(mapped_lines[1:]).strip()
    if element_type == "parenthetical":
        stripped = text.strip()
        if stripped.startswith("(") and stripped.endswith(")") and len(stripped) >= 2:
            return stripped[1:-1].strip()
        return stripped
    return text


def _apply_change(screenplay: dict[str, Any], mapping: dict[str, Any], text: str) -> None:
    yaml_path = str(mapping["yaml_path"])
    heading_match = SAFE_HEADING_RE.match(yaml_path)
    if heading_match:
        scene = _scene(screenplay, int(heading_match.group(1)))
        if scene is not None:
            scene["heading"] = text
        return
    element_match = SAFE_ELEMENT_TEXT_RE.match(yaml_path)
    if element_match:
        element = _element(screenplay, int(element_match.group(1)), int(element_match.group(2)))
        if element is not None:
            element["text"] = text


def _report(
    screenplay_path: str,
    fountain_path: str,
    map_path: str,
    mappings: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    *,
    expected_line_count: int,
    actual_line_count: int,
    line_drift: bool,
    map_match: bool,
) -> dict[str, Any]:
    applied = [change for change in changes if change["action"] == "applied"]
    skipped = [change for change in changes if change["action"] == "skipped"]
    blocking = [issue for issue in issues if issue["action"] == "blocked"]
    status = _status(applied, skipped, blocking)
    report: dict[str, Any] = {
        "fountain_roundtrip_report": {
            "schema_version": SCHEMA_VERSION,
            "source_yaml": screenplay_path,
            "fountain_file": fountain_path,
            "map_file": map_path,
            "generated_at": DEFAULT_GENERATED_AT,
            "status": status,
            "summary": {
                "mapped_regions": len(mappings),
                "changed_regions": len(changes),
                "applied_changes": len(applied),
                "skipped_changes": len(skipped),
                "blocking_issues": len(blocking),
            },
            "line_policy": {
                "expected_line_count": expected_line_count,
                "actual_line_count": actual_line_count,
                "line_drift_detected": line_drift,
                "map_match": map_match,
            },
            "changes": changes,
            "issues": issues,
        }
    }
    if applied:
        report["fountain_roundtrip_report"]["metadata_update"] = {
            "semantic_fields_stale": True,
            "roundtrip": {
                "imported_at": DEFAULT_GENERATED_AT,
                "fountain_file": fountain_path,
                "map_file": map_path,
                "applied_changes": len(applied),
            },
        }
    return report


def _status(
    applied: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    blocking: list[dict[str, Any]],
) -> str:
    if blocking:
        return "blocked"
    if applied and skipped:
        return "partial"
    if applied:
        return "applied"
    return "skipped"


def _issue(
    index: int,
    severity: str,
    code: str,
    message: str,
    action: str,
    *,
    yaml_path: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
) -> dict[str, Any]:
    issue = {
        "id": f"rt_issue_{index:03d}",
        "severity": severity,
        "code": code,
        "message": message,
        "action": action,
    }
    if yaml_path:
        issue["yaml_path"] = yaml_path
    if line_start is not None:
        issue["line_start"] = line_start
    if line_end is not None:
        issue["line_end"] = line_end
    return issue


def _issue_for_mapping(mapping: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    return _issue(
        0,
        "high",
        code,
        message,
        "blocked",
        yaml_path=str(mapping.get("yaml_path", "")),
        line_start=int(mapping.get("line_start", 0) or 0) or None,
        line_end=int(mapping.get("line_end", 0) or 0) or None,
    )


def _yaml_text(screenplay: dict[str, Any], yaml_path: str) -> str:
    heading_match = SAFE_HEADING_RE.match(yaml_path)
    if heading_match:
        scene = _scene(screenplay, int(heading_match.group(1)))
        return str((scene or {}).get("heading", "")).strip()
    element_match = SAFE_ELEMENT_TEXT_RE.match(yaml_path)
    if element_match:
        element = _element(screenplay, int(element_match.group(1)), int(element_match.group(2)))
        return str((element or {}).get("text", "")).strip()
    return ""


def _scene(screenplay: dict[str, Any], scene_index: int) -> dict[str, Any] | None:
    scenes = screenplay.get("scenes", [])
    if not isinstance(scenes, list) or scene_index < 0 or scene_index >= len(scenes):
        return None
    scene = scenes[scene_index]
    return scene if isinstance(scene, dict) else None


def _element(
    screenplay: dict[str, Any], scene_index: int, element_index: int
) -> dict[str, Any] | None:
    scene = _scene(screenplay, scene_index)
    if not scene:
        return None
    elements = scene.get("elements", [])
    if not isinstance(elements, list) or element_index < 0 or element_index >= len(elements):
        return None
    element = elements[element_index]
    return element if isinstance(element, dict) else None


def _same_file(left: Any, right: str) -> bool:
    if not left:
        return False
    try:
        return Path(str(left)).resolve() == Path(right).resolve()
    except OSError:
        return str(left).replace("\\", "/") == str(right).replace("\\", "/")


def _write_report(report: dict[str, Any], report_path: str | None) -> None:
    if report_path:
        write_yaml(report, report_path)
