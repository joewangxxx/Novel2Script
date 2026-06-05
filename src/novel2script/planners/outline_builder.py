from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "0.1.0"


def build_outline(
    story_map_doc: dict[str, Any], story_map_file: str = ""
) -> dict[str, Any]:
    """Build a deterministic outline draft from a story_map document."""
    story_map = _inner_story_map(story_map_doc)
    events = story_map.get("key_events", [])
    characters = story_map.get("characters_detected", [])
    locations = story_map.get("locations_detected", [])
    primary_character = characters[0]["name"] if characters else "主角"
    primary_location = locations[0]["name"] if locations else "核心地点"

    scene_plan = [
        _scene_from_event(event, index)
        for index, event in enumerate(events, start=1)
    ]
    acts = _build_acts(events, scene_plan)
    event_ids = [event["id"] for event in events]

    outline = {
        "schema_version": SCHEMA_VERSION,
        "source_story_map": _source_story_map(story_map, story_map_file),
        "logline": {
            "text": _logline(primary_character, primary_location, events),
            "source_trace": _traces_for_events(events[:3] or events),
            "ai_tags": _ai_tags(
                confidence="medium",
                notes=["Heuristic logline assembled from primary character, location, and key events."],
            ),
        },
        "theme_candidates": _theme_candidates(story_map),
        "act_structure": acts,
        "scene_plan": scene_plan,
        "source_coverage": {
            "story_event_count": len(events),
            "covered_event_ids": event_ids,
            "uncovered_event_ids": [],
            "notes": ["Each key_event is represented by one outline scene candidate."],
        },
        "uncertainties": _outline_uncertainties(story_map),
    }
    return {"outline": outline}


def _inner_story_map(story_map_doc: dict[str, Any]) -> dict[str, Any]:
    return story_map_doc.get("story_map", story_map_doc)


def _source_story_map(story_map: dict[str, Any], story_map_file: str) -> dict[str, Any]:
    return {
        "schema_version": str(story_map.get("schema_version", "")),
        "story_map_file": story_map_file,
    }


def _logline(primary_character: str, primary_location: str, events: list[dict[str, Any]]) -> str:
    if not events:
        return f"{primary_character}在{primary_location}面对一个尚待确认的核心事件。"
    first_event = events[0].get("summary", "")
    last_event = events[-1].get("summary", "")
    return f"{primary_character}在{primary_location}被卷入异常事件，并必须回应最终转折：{_short(last_event or first_event)}"


def _theme_candidates(story_map: dict[str, Any]) -> list[dict[str, Any]]:
    events = story_map.get("key_events", [])
    psychological = story_map.get("psychological_passages", [])
    if not events:
        return []
    traces = _traces_for_events(events[:2])
    if psychological:
        traces.append(_trace_with_optional_event(psychological[0]))
    return [
        {
            "id": "theme_001",
            "theme": "未知威胁下的信任与选择",
            "rationale": "Based on repeated warnings, uncertain figures, and the protagonist's response to danger.",
            "source_trace": traces,
            "ai_tags": _ai_tags(
                confidence="low",
                notes=["Theme is heuristic and must be reviewed before use as canon."],
            ),
        }
    ]


def _scene_from_event(event: dict[str, Any], index: int) -> dict[str, Any]:
    trace = _trace_with_optional_event(event)
    return {
        "id": _make_id("osp", index),
        "order": index,
        "title": f"Scene candidate {index}",
        "purpose": _short(event.get("summary", "")),
        "source_event_ids": [event["id"]],
        "character_ids": event.get("character_ids", []),
        "location_ids": event.get("location_ids", []),
        "source_trace": [trace],
        "ai_tags": _ai_tags(
            confidence="medium",
            notes=["Scene candidate mirrors a Stage 3 key_event; it is not screenplay scene output."],
        ),
        "uncertainty_ids": event.get("uncertainty_ids", []),
    }


def _build_acts(
    events: list[dict[str, Any]], scene_plan: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not events:
        return [
            _act(
                1,
                "act_1",
                "Setup",
                "No key events were available for deterministic act grouping.",
                [],
                [],
                "low",
            )
        ]
    chunks = _chunk_events(events, 3)
    act_types = ["act_1", "act_2", "act_3"]
    titles = ["Setup", "Confrontation", "Resolution"]
    acts = []
    for index, chunk in enumerate(chunks, start=1):
        scene_ids = [
            scene["id"]
            for scene in scene_plan
            if scene["source_event_ids"][0] in {event["id"] for event in chunk}
        ]
        acts.append(
            _act(
                index,
                act_types[index - 1],
                titles[index - 1],
                _short(" / ".join(event.get("summary", "") for event in chunk)),
                _traces_for_events(chunk),
                scene_ids,
                "medium",
            )
        )
    return acts


def _act(
    index: int,
    act_type: str,
    title: str,
    summary: str,
    source_trace: list[dict[str, Any]],
    scene_ids: list[str],
    confidence: str,
) -> dict[str, Any]:
    return {
        "id": _make_id("act", index),
        "index": index,
        "act_type": act_type,
        "title": title,
        "summary": summary,
        "source_trace": source_trace or [_empty_trace()],
        "ai_tags": _ai_tags(
            confidence=confidence,
            notes=["Act grouping is deterministic and based on key_event order."],
        ),
        "scene_ids": scene_ids,
    }


def _outline_uncertainties(story_map: dict[str, Any]) -> list[dict[str, Any]]:
    uncertainties = []
    for index, item in enumerate(story_map.get("uncertainties", []), start=1):
        uncertainties.append(
            {
                "id": _make_id("out_unc", index),
                "category": "other",
                "description": item.get("description", "Inherited story_map uncertainty."),
                "source_trace": [_trace_with_optional_event(item)],
                "severity": item.get("severity", "low"),
                "suggested_resolution": item.get("suggested_resolution", "Review before outline use."),
            }
        )
    return uncertainties


def _chunk_events(events: list[dict[str, Any]], chunk_count: int) -> list[list[dict[str, Any]]]:
    chunks = [[] for _ in range(chunk_count)]
    for index, event in enumerate(events):
        chunk_index = min(index * chunk_count // len(events), chunk_count - 1)
        chunks[chunk_index].append(event)
    return [chunk or [events[min(index, len(events) - 1)]] for index, chunk in enumerate(chunks)]


def _traces_for_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_trace_with_optional_event(event) for event in events if event.get("source_trace")]


def _trace_with_optional_event(item: dict[str, Any]) -> dict[str, Any]:
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
