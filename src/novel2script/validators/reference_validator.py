from __future__ import annotations

from typing import Any

from novel2script.io import read_yaml


def validate_references(yaml_path: str) -> dict[str, Any]:
    screenplay = read_yaml(yaml_path)
    character_ids = {
        character.get("id")
        for character in screenplay.get("characters", [])
        if isinstance(character, dict) and character.get("id")
    }
    missing_references: list[dict[str, Any]] = []

    for scene_index, scene in enumerate(screenplay.get("scenes", [])):
        if not isinstance(scene, dict):
            continue
        for element_index, element in enumerate(scene.get("elements", [])):
            if not isinstance(element, dict) or element.get("type") != "dialogue":
                continue
            character_id = element.get("character_id")
            if character_id not in character_ids:
                missing_references.append(
                    {
                        "yaml_path": f"scenes[{scene_index}].elements[{element_index}].character_id",
                        "reference_type": "character_id",
                        "missing_id": character_id,
                        "message": "Dialogue character_id does not exist in characters.",
                    }
                )

    return {
        "reference_integrity": {
            "passed": not missing_references,
            "missing_references": missing_references,
        }
    }


def validate_location_references(screenplay: dict[str, Any]) -> list[dict[str, Any]]:
    return []


def validate_prop_references(screenplay: dict[str, Any]) -> list[dict[str, Any]]:
    return []
