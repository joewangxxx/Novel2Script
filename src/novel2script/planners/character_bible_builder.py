from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "0.1.0"


def build_character_bible(
    story_map_doc: dict[str, Any], story_map_file: str = ""
) -> dict[str, Any]:
    """Build a deterministic character bible draft from a story_map document."""
    story_map = story_map_doc.get("story_map", story_map_doc)
    characters = story_map.get("characters_detected", [])
    events = story_map.get("key_events", [])
    bible_characters = [
        _character_profile(character, events)
        for character in characters
    ]
    return {
        "character_bible": {
            "schema_version": SCHEMA_VERSION,
            "source_story_map": {
                "schema_version": str(story_map.get("schema_version", "")),
                "story_map_file": story_map_file,
            },
            "characters": bible_characters,
            "uncertainties": _character_uncertainties(bible_characters),
        }
    }


def _character_profile(
    character: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    character_events = [
        event for event in events if character["id"] in event.get("character_ids", [])
    ]
    source_trace = [_trace(character)]
    if character_events:
        source_trace = [_trace(event) for event in character_events[:3]]
    return {
        "id": character["id"],
        "name": character["name"],
        "aliases": character.get("aliases", []),
        "want": _empty_evidence_text(source_trace, "External want is not explicit in story_map."),
        "need": _empty_evidence_text(source_trace, "Internal need is not explicit in story_map."),
        "flaw": _empty_evidence_text(source_trace, "Character flaw is not explicit in story_map."),
        "relationships": _relationships(character, character_events),
        "voice": {
            "summary": "",
            "dialogue_rules": [],
            "source_trace": source_trace,
            "ai_tags": _ai_tags(
                "low",
                ["Voice evidence is limited to source event participation; no full voice model is generated."],
            ),
        },
        "arc": _arc(character_events, source_trace),
        "locked": False,
        "source_trace": source_trace,
        "ai_tags": _ai_tags(
            "low",
            ["Character bible profile is a deterministic shell and requires human review."],
        ),
    }


def _empty_evidence_text(source_trace: list[dict[str, Any]], note: str) -> dict[str, Any]:
    return {
        "text": "",
        "source_trace": source_trace,
        "ai_tags": _ai_tags("low", [note]),
    }


def _relationships(
    character: dict[str, Any], character_events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    related_ids: list[str] = []
    relationship_events: dict[str, dict[str, Any]] = {}
    for event in character_events:
        for other_id in event.get("character_ids", []):
            if other_id == character["id"] or other_id in related_ids:
                continue
            related_ids.append(other_id)
            relationship_events[other_id] = event
    return [
        {
            "character_id": related_id,
            "relationship_type": "co_occurs_in_event",
            "description": "Relationship is only evidenced by co-occurrence in a key event.",
            "source_trace": [_trace(relationship_events[related_id])],
            "ai_tags": _ai_tags(
                "low",
                ["Co-occurrence is not a confirmed relationship and requires review."],
            ),
        }
        for related_id in related_ids
    ]


def _arc(
    character_events: list[dict[str, Any]], source_trace: list[dict[str, Any]]
) -> dict[str, Any]:
    turning_points = [
        {
            "event_id": event["id"],
            "description": _short(event.get("summary", "")),
        }
        for event in character_events[:3]
    ]
    if not turning_points:
        turning_points = [{"event_id": "evt_001", "description": ""}]
    return {
        "start": "",
        "turning_points": turning_points,
        "end": "",
        "source_trace": source_trace,
        "ai_tags": _ai_tags(
            "low",
            ["Arc is a placeholder linked to visible key events, not a complete psychological inference."],
        ),
    }


def _character_uncertainties(characters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    uncertainties = []
    categories = [
        ("weak_want_evidence", "External want is not explicit enough for deterministic confirmation."),
        ("weak_need_evidence", "Internal need is not explicit enough for deterministic confirmation."),
        ("weak_voice_evidence", "Voice rules are not explicit enough for deterministic confirmation."),
    ]
    for character in characters:
        for category, description in categories:
            uncertainties.append(
                {
                    "id": _make_id("cb_unc", len(uncertainties) + 1),
                    "character_id": character["id"],
                    "category": category,
                    "description": description,
                    "source_trace": character["source_trace"],
                    "severity": "low",
                    "suggested_resolution": "Review source text before using this field in scene generation.",
                }
            )
    return uncertainties


def _trace(item: dict[str, Any]) -> dict[str, Any]:
    trace = dict(item.get("source_trace", _empty_trace()))
    if item.get("id", "").startswith("evt_"):
        trace["event_ids"] = [item["id"]]
    return trace


def _empty_trace() -> dict[str, Any]:
    return {
        "chapter_id": "ch_001",
        "paragraph_ids": ["p_001"],
        "note": "No stronger source trace was available.",
    }


def _ai_tags(confidence: str, notes: list[str]) -> dict[str, Any]:
    return {
        "inferred": True,
        "confidence": confidence,
        "needs_human_review": True,
        "notes": notes,
    }


def _short(text: str, limit: int = 72) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _make_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:03d}"
