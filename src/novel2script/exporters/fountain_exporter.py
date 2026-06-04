from __future__ import annotations

from pathlib import Path
from typing import Any

from novel2script.io import read_yaml, write_json


def export_fountain(yaml_path: str, out_path: str, map_path: str | None = None) -> None:
    screenplay = read_yaml(yaml_path)
    character_names = _character_names(screenplay)
    lines: list[str] = []
    mappings: list[dict[str, Any]] = []

    _append_title_page(lines, screenplay)

    for scene_index, scene in enumerate(screenplay.get("scenes", [])):
        if not isinstance(scene, dict):
            continue
        if lines and lines[-1] != "":
            lines.append("")
        line_start = _append_line(lines, scene.get("heading", ""))
        mappings.append(
            _mapping(
                line_start=line_start,
                line_end=line_start,
                scene_id=scene.get("id"),
                beat_id=None,
                element_index=None,
                yaml_path=f"scenes[{scene_index}].heading",
            )
        )

        for element_index, element in enumerate(scene.get("elements", [])):
            if not isinstance(element, dict):
                continue
            line_start, line_end = _append_element(lines, element, character_names)
            if line_start is None:
                continue
            mappings.append(
                _mapping(
                    line_start=line_start,
                    line_end=line_end,
                    scene_id=scene.get("id"),
                    beat_id=None,
                    element_index=element_index,
                    yaml_path=f"scenes[{scene_index}].elements[{element_index}].text",
                )
            )

    output_path = Path(out_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    if map_path:
        write_json(
            {
                "source_yaml": str(Path(yaml_path).as_posix()),
                "fountain_file": str(Path(out_path).as_posix()),
                "mappings": mappings,
            },
            map_path,
        )


def _append_title_page(lines: list[str], screenplay: dict[str, Any]) -> None:
    metadata = screenplay.get("metadata", {})
    title = metadata.get("title") if isinstance(metadata, dict) else None
    created_at = metadata.get("created_at") if isinstance(metadata, dict) else None
    if title:
        lines.append(f"Title: {title}")
    lines.append("Credit: Adapted sample from Novel2Script YAML")
    if created_at:
        lines.append(f"Draft date: {created_at}")
    lines.append("")


def _append_element(
    lines: list[str], element: dict[str, Any], character_names: dict[str, str]
) -> tuple[int | None, int | None]:
    element_type = element.get("type")
    text = str(element.get("text", "")).strip()
    if not text:
        return None, None

    if element_type == "dialogue":
        if lines and lines[-1] != "":
            lines.append("")
        line_start = len(lines) + 1
        character_id = element.get("character_id")
        lines.append(character_names.get(character_id, str(character_id or "")).upper())
        lines.extend(text.splitlines())
        lines.append("")
        return line_start, len(lines) - 1

    if element_type == "parenthetical":
        line_start = _append_line(lines, f"({text})")
        return line_start, line_start

    if element_type == "transition":
        if lines and lines[-1] != "":
            lines.append("")
        line_start = _append_line(lines, text.upper())
        lines.append("")
        return line_start, line_start

    if element_type == "note":
        return None, None

    line_start = _append_line(lines, text)
    return line_start, len(lines)


def _append_line(lines: list[str], text: str) -> int:
    line_start = len(lines) + 1
    lines.extend(str(text).strip().splitlines() or [""])
    return line_start


def _mapping(
    *,
    line_start: int,
    line_end: int | None,
    scene_id: str | None,
    beat_id: str | None,
    element_index: int | None,
    yaml_path: str,
) -> dict[str, Any]:
    return {
        "line_start": line_start,
        "line_end": line_end if line_end is not None else line_start,
        "scene_id": scene_id,
        "beat_id": beat_id,
        "element_index": element_index,
        "yaml_path": yaml_path,
    }


def _character_names(screenplay: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for character in screenplay.get("characters", []):
        if isinstance(character, dict) and character.get("id"):
            names[character["id"]] = str(character.get("name", character["id"]))
    return names
