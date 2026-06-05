from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "0.1.0"
DEFAULT_CREATED_AT = "2026-06-05"


def build_screenplay(
    story_map_doc: dict[str, Any],
    outline_doc: dict[str, Any],
    character_bible_doc: dict[str, Any],
    *,
    story_map_file: str = "",
    outline_file: str = "",
    character_bible_file: str = "",
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    """Build a deterministic screenplay draft from Stage 3 and Stage 4 artifacts."""
    story_map = _inner(story_map_doc, "story_map")
    outline = _inner(outline_doc, "outline")
    character_bible = _inner(character_bible_doc, "character_bible")

    events_by_id = {event.get("id"): event for event in story_map.get("key_events", [])}
    locations_by_id = {
        location.get("id"): location for location in story_map.get("locations_detected", [])
    }
    timeline = story_map.get("timeline", [])

    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "title": _title(story_map, outline),
            "language": "zh-CN",
            "created_by": "Novel2Script stage-five deterministic generator",
            "created_at": created_at,
        },
        "source": {
            "type": story_map.get("source", {}).get("type", "novel"),
            "chapter_count": story_map.get("source", {}).get("chapter_count", 1),
            "trace_unit": story_map.get("source", {}).get("trace_unit", "chapter_paragraph"),
            "story_map_file": story_map_file,
            "outline_file": outline_file,
            "character_bible_file": character_bible_file,
            "source_trace_strategy": "numeric_plus_ids",
        },
        "adaptation_policy": {
            "target_format": "short_screenplay",
            "allow_inference": True,
            "preserve_source_order": True,
            "generator_profile": "deterministic_screenplay_builder_v0",
        },
        "characters": _characters(character_bible, story_map),
        "scenes": _scenes(outline, story_map, events_by_id, locations_by_id, timeline),
    }


def _inner(doc: dict[str, Any], key: str) -> dict[str, Any]:
    return doc.get(key, doc)


def _title(story_map: dict[str, Any], outline: dict[str, Any]) -> str:
    chapters = story_map.get("chapters", [])
    if chapters and chapters[0].get("title"):
        return str(chapters[0]["title"])
    logline = outline.get("logline", {})
    text = str(logline.get("text", "")).strip()
    return _short(text, 40) if text else "Untitled Adaptation"


def _characters(character_bible: dict[str, Any], story_map: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _character(character, story_map)
        for character in character_bible.get("characters", [])
    ]


def _character(character: dict[str, Any], story_map: dict[str, Any]) -> dict[str, Any]:
    traces = _ensure_trace_list(character.get("source_trace"))
    numeric_trace = _numeric_trace(traces, story_map, "character profile evidence")
    return {
        "id": character.get("id", ""),
        "name": character.get("name", ""),
        "role": character.get("role", ""),
        "source_trace": numeric_trace,
        "source_trace_ids": _trace_ids(traces),
        "ai_tags": character.get("ai_tags", _ai_tags("low", ["Character profile needs review."])),
        "locked": bool(character.get("locked", False)),
    }


def _scenes(
    outline: dict[str, Any],
    story_map: dict[str, Any],
    events_by_id: dict[str | None, dict[str, Any]],
    locations_by_id: dict[str | None, dict[str, Any]],
    timeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scene_plan = sorted(outline.get("scene_plan", []), key=lambda item: item.get("order", 0))
    return [
        _scene(scene, index, story_map, events_by_id, locations_by_id, timeline)
        for index, scene in enumerate(scene_plan, start=1)
    ]


def _scene(
    planned_scene: dict[str, Any],
    index: int,
    story_map: dict[str, Any],
    events_by_id: dict[str | None, dict[str, Any]],
    locations_by_id: dict[str | None, dict[str, Any]],
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    source_event_ids = planned_scene.get("source_event_ids", [])
    event = _first_event(source_event_ids, events_by_id)
    traces = _ensure_trace_list(planned_scene.get("source_trace")) or _ensure_trace_list(
        event.get("source_trace") if event else None
    )
    location = _location(planned_scene, event, locations_by_id)
    time = _time(source_event_ids, timeline)
    source_trace = _numeric_trace(traces, story_map, f"outline scene {planned_scene.get('id', '')}")
    source_trace_ids = _trace_ids(
        traces,
        event_ids=source_event_ids,
        outline_scene_ids=[planned_scene.get("id", "")],
    )
    beat = _beat(index, planned_scene, event, story_map, source_trace, source_trace_ids)
    elements = _elements(planned_scene, event, source_trace, source_trace_ids)
    return {
        "id": _make_id("scene", index),
        "heading": _heading(location, time),
        "location": location,
        "time": time,
        "source_trace": source_trace,
        "source_trace_ids": source_trace_ids,
        "source_outline_scene_id": planned_scene.get("id", ""),
        "source_event_ids": source_event_ids,
        "beats": [beat],
        "elements": elements,
    }


def _first_event(
    event_ids: list[str], events_by_id: dict[str | None, dict[str, Any]]
) -> dict[str, Any] | None:
    for event_id in event_ids:
        event = events_by_id.get(event_id)
        if event:
            return event
    return None


def _location(
    planned_scene: dict[str, Any],
    event: dict[str, Any] | None,
    locations_by_id: dict[str | None, dict[str, Any]],
) -> str:
    location_ids = planned_scene.get("location_ids") or (event or {}).get("location_ids", [])
    for location_id in location_ids:
        location = locations_by_id.get(location_id)
        if location and location.get("name"):
            return str(location["name"])
    return ""


def _time(source_event_ids: list[str], timeline: list[dict[str, Any]]) -> str:
    source_ids = set(source_event_ids)
    for item in timeline:
        if source_ids.intersection(item.get("event_ids", [])):
            return str(item.get("time_text") or item.get("label") or "")
    return ""


def _heading(location: str, time: str) -> str:
    safe_location = location or "UNKNOWN"
    safe_time = time or "TIME UNKNOWN"
    return f"INT./EXT. {safe_location} - {safe_time}"


def _beat(
    index: int,
    planned_scene: dict[str, Any],
    event: dict[str, Any] | None,
    story_map: dict[str, Any],
    source_trace: dict[str, Any],
    source_trace_ids: dict[str, Any],
) -> dict[str, Any]:
    purpose = _short(planned_scene.get("purpose", ""))
    event_summary = _short((event or {}).get("summary", ""))
    source_text = event_summary or purpose or "Review source evidence for this scene."
    externalized = _externalized_action(story_map, source_trace_ids, source_text)
    return {
        "id": _make_id("beat", index),
        "objective": _nonempty(purpose, "Clarify the scene objective from source evidence."),
        "tactic": f"Use visible source action: {_short(source_text, 96)}",
        "obstacle": "Source evidence is incomplete or requires adaptation review.",
        "conflict": "The visible scene action must be shaped into screen conflict without adding unsupported facts.",
        "stakes": "Review the source event consequence before treating stakes as canon.",
        "turn": _nonempty(event_summary, "The scene changes the adaptation plan state."),
        "externalized_action": externalized,
        "source_trace": source_trace,
        "source_trace_ids": source_trace_ids,
        "ai_tags": _ai_tags(
            "medium",
            ["Beat fields are deterministic adaptation scaffolding and require human review."],
        ),
    }


def _externalized_action(
    story_map: dict[str, Any], source_trace_ids: dict[str, Any], fallback: str
) -> str:
    paragraph_ids = set(source_trace_ids.get("paragraph_ids", []))
    chapter_id = source_trace_ids.get("chapter_id")
    for passage in story_map.get("psychological_passages", []):
        trace = passage.get("source_trace", {})
        if trace.get("chapter_id") != chapter_id:
            continue
        if paragraph_ids.intersection(trace.get("paragraph_ids", [])):
            return _nonempty(
                _short(passage.get("externalization_hint", "")),
                _short(passage.get("summary", "")),
            )
    return _nonempty(_short(fallback), "Externalize the visible source action.")


def _elements(
    planned_scene: dict[str, Any],
    event: dict[str, Any] | None,
    source_trace: dict[str, Any],
    source_trace_ids: dict[str, Any],
) -> list[dict[str, Any]]:
    action_text = _short((event or {}).get("summary", "") or planned_scene.get("purpose", ""), 140)
    action = {
        "type": "action",
        "text": _nonempty(action_text, "Source-grounded action requires review."),
        "source_trace": source_trace,
        "source_trace_ids": source_trace_ids,
        "ai_tags": _ai_tags(
            "medium",
            ["Action element is derived from key_event or outline purpose."],
        ),
    }
    note = {
        "type": "note",
        "text": "Review this deterministic scene draft before treating it as final screenplay prose.",
        "source_trace": source_trace,
        "source_trace_ids": source_trace_ids,
        "ai_tags": _ai_tags(
            "low",
            ["Note element records adaptation uncertainty instead of inventing dialogue."],
        ),
    }
    return [action, note]


def _numeric_trace(
    traces: list[dict[str, Any]], story_map: dict[str, Any], note: str
) -> dict[str, Any]:
    primary = traces[0] if traces else {}
    chapter_id = primary.get("chapter_id", "ch_001")
    paragraph_ids = primary.get("paragraph_ids", ["p_001"])
    chapter_index = _chapter_index(story_map, chapter_id)
    paragraph_indexes = _paragraph_indexes(story_map, chapter_id, paragraph_ids)
    return {
        "chapter": chapter_index,
        "paragraph_range": [min(paragraph_indexes), max(paragraph_indexes)],
        "note": primary.get("note") or note,
    }


def _chapter_index(story_map: dict[str, Any], chapter_id: str) -> int:
    for chapter in story_map.get("chapters", []):
        if chapter.get("id") == chapter_id:
            return int(chapter.get("index", 1))
    return 1


def _paragraph_indexes(
    story_map: dict[str, Any], chapter_id: str, paragraph_ids: list[str]
) -> list[int]:
    indexes = []
    wanted = set(paragraph_ids)
    for chapter in story_map.get("chapters", []):
        if chapter.get("id") != chapter_id:
            continue
        for paragraph in chapter.get("paragraphs", []):
            if paragraph.get("id") in wanted:
                indexes.append(int(paragraph.get("index", 1)))
    return indexes or [1]


def _trace_ids(
    traces: list[dict[str, Any]],
    *,
    event_ids: list[str] | None = None,
    outline_scene_ids: list[str] | None = None,
) -> dict[str, Any]:
    primary = traces[0] if traces else {}
    ids = {
        "chapter_id": primary.get("chapter_id", "ch_001"),
        "paragraph_ids": primary.get("paragraph_ids", ["p_001"]),
    }
    collected_event_ids = list(event_ids or [])
    for trace in traces:
        for event_id in trace.get("event_ids", []):
            if event_id not in collected_event_ids:
                collected_event_ids.append(event_id)
    if collected_event_ids:
        ids["event_ids"] = collected_event_ids
    clean_outline_ids = [item for item in (outline_scene_ids or []) if item]
    if clean_outline_ids:
        ids["outline_scene_ids"] = clean_outline_ids
    if primary.get("quote_preview"):
        ids["quote_preview"] = primary["quote_preview"]
    if primary.get("note"):
        ids["note"] = primary["note"]
    return ids


def _ensure_trace_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _ai_tags(confidence: str, notes: list[str]) -> dict[str, Any]:
    return {
        "inferred": True,
        "confidence": confidence,
        "needs_human_review": True,
        "notes": notes,
    }


def _short(text: Any, limit: int = 120) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _nonempty(value: str, fallback: str) -> str:
    return value if value.strip() else fallback


def _make_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:03d}"
