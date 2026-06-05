from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = "0.1.0"
PREVIEW_LIMIT = 80

PSYCHOLOGICAL_KEYWORDS = [
    "想起",
    "觉得",
    "害怕",
    "意识到",
    "心里",
    "怀疑",
    "记得",
    "仿佛",
    "以为",
]
LOCATION_KEYWORDS = ["邮局", "灯塔", "码头", "海边", "房间", "街道", "船", "钟楼"]
PROP_KEYWORDS = ["信封", "录音笔", "录音机", "钥匙", "照片", "灯", "船", "信"]
TIME_PATTERNS = [
    r"第[一二三四五六七八九十百千万\d]+天(?:傍晚|夜里|清晨|早上|上午|中午|下午|晚上)?",
    r"[一二三四五六七八九十百千万\d]+年前",
    r"连续[一二三四五六七八九十百千万\d]+晚",
    r"傍晚",
    r"夜里",
    r"清晨",
    r"早上",
    r"上午",
    r"中午",
    r"下午",
    r"晚上",
]
EVENT_CUES = [
    "听见",
    "滑出",
    "写着",
    "拆开",
    "来到",
    "递给",
    "亮",
    "停在",
    "组织",
    "拦住",
    "交给",
    "冲进",
    "敲响",
    "熄灭",
    "后退",
    "转身",
]
AMBIGUITY_CUES = ["有人影", "他们", "那可能", "像是", "仿佛", "并不只有"]
CHARACTER_VERBS = [
    "在",
    "把",
    "拆开",
    "来到",
    "说",
    "沉默",
    "冲进",
    "拦住",
    "听见",
    "以为",
    "组织",
    "交给",
    "拿不出",
]
CHARACTER_STOPWORDS = {
    "海边",
    "小镇",
    "邮局",
    "钟楼",
    "灯塔",
    "信封",
    "父亲",
    "镇上",
    "里面",
    "船上",
    "远处",
    "雾里",
    "夜里",
}


@dataclass(frozen=True)
class ParagraphUnit:
    chapter_id: str
    paragraph_id: str
    text: str


@dataclass(frozen=True)
class ChapterUnit:
    chapter_id: str
    index: int
    title: str
    source_heading: str
    paragraphs: list[ParagraphUnit]


def parse_novel_text(text: str, input_file: str = "") -> dict[str, Any]:
    """Parse Markdown or TXT novel text into a deterministic story_map dict."""
    chapters = _split_chapters(text)
    paragraph_units = [
        paragraph for chapter in chapters for paragraph in chapter.paragraphs
    ]
    characters = _detect_characters(paragraph_units)
    locations = _detect_keywords(
        paragraph_units,
        LOCATION_KEYWORDS,
        id_prefix="loc",
        type_field="location_type",
        type_value="keyword",
    )
    props = _detect_keywords(
        paragraph_units,
        PROP_KEYWORDS,
        id_prefix="prop",
        type_field="prop_type",
        type_value="keyword",
    )
    events = _detect_key_events(paragraph_units, characters, locations, props)

    story_map = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "type": "novel",
            "input_file": input_file,
            "chapter_count": len(chapters),
            "trace_unit": "chapter_paragraph",
            "parser_profile": "deterministic_heuristic_v0",
        },
        "chapters": [_chapter_to_dict(chapter) for chapter in chapters],
        "characters_detected": characters,
        "locations_detected": locations,
        "props_detected": props,
        "key_events": events,
        "timeline": _detect_timeline(paragraph_units, events),
        "psychological_passages": _detect_psychological_passages(
            paragraph_units, characters
        ),
        "uncertainties": _detect_uncertainties(paragraph_units),
    }
    return {"story_map": story_map}


def _split_chapters(text: str) -> list[ChapterUnit]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    raw_chapters: list[tuple[str, str, list[str]]] = []
    current_heading = ""
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        heading = _parse_chapter_heading(line)
        if heading:
            if current_heading or current_lines:
                raw_chapters.append((current_heading, current_title, current_lines))
            current_heading, current_title = heading
            current_lines = []
            continue
        if current_heading:
            current_lines.append(line)

    if current_heading or current_lines:
        raw_chapters.append((current_heading, current_title, current_lines))
    if not raw_chapters:
        raw_chapters.append(("", "", lines))

    chapters: list[ChapterUnit] = []
    for chapter_index, (source_heading, title, chapter_lines) in enumerate(
        raw_chapters, start=1
    ):
        chapter_id = _make_id("ch", chapter_index)
        paragraphs = [
            ParagraphUnit(chapter_id, _make_id("p", paragraph_index), paragraph)
            for paragraph_index, paragraph in enumerate(
                _split_paragraphs("\n".join(chapter_lines)), start=1
            )
        ]
        if not paragraphs:
            paragraphs = [ParagraphUnit(chapter_id, "p_001", "")]
        chapters.append(
            ChapterUnit(
                chapter_id=chapter_id,
                index=chapter_index,
                title=title,
                source_heading=source_heading,
                paragraphs=paragraphs,
            )
        )
    return chapters


def _parse_chapter_heading(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None
    markdown_match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    candidate = markdown_match.group(1).strip() if markdown_match else stripped
    if not _is_chapter_heading(candidate):
        return None
    return stripped, _normalize_chapter_title(candidate)


def _is_chapter_heading(text: str) -> bool:
    return bool(
        re.match(r"^第[一二三四五六七八九十百千万\d]+章(?:\s*[:：]?\s*.*)?$", text)
        or re.match(
            r"^[一二三四五六七八九十百千万]+章(?:\s*[:：]?\s*.*)?$", text
        )
        or re.match(r"^chapter\s+\d+(?:\s+.*)?$", text, flags=re.IGNORECASE)
    )


def _normalize_chapter_title(text: str) -> str:
    zh_match = re.match(
        r"^第?[一二三四五六七八九十百千万\d]+章\s*[:：]?\s*(.*)$", text
    )
    if zh_match:
        title = zh_match.group(1).strip()
        return title or text
    en_match = re.match(r"^(chapter\s+\d+)\s+(.+)$", text, flags=re.IGNORECASE)
    if en_match:
        return en_match.group(2).strip()
    return text


def _split_paragraphs(text: str) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]


def _chapter_to_dict(chapter: ChapterUnit) -> dict[str, Any]:
    return {
        "id": chapter.chapter_id,
        "index": chapter.index,
        "title": chapter.title,
        "source_heading": chapter.source_heading,
        "paragraphs": [
            {
                "id": paragraph.paragraph_id,
                "index": index,
                "text_preview": _preview(paragraph.text),
                "char_count": len(paragraph.text),
            }
            for index, paragraph in enumerate(chapter.paragraphs, start=1)
        ],
    }


def _detect_characters(paragraphs: list[ParagraphUnit]) -> list[dict[str, Any]]:
    seen: dict[str, ParagraphUnit] = {}
    verb_pattern = "|".join(re.escape(verb) for verb in CHARACTER_VERBS)
    pattern = re.compile(rf"([一-龥]{{2,3}})(?:{verb_pattern})")
    for paragraph in paragraphs:
        for raw_name in pattern.findall(paragraph.text):
            name = _normalize_character_candidate(raw_name)
            if name is None or name in seen:
                continue
            seen[name] = paragraph

    characters = []
    for index, (name, paragraph) in enumerate(seen.items(), start=1):
        trace = _source_trace(paragraph, note=f"角色候选：{name}")
        characters.append(
            {
                "id": _make_id("char", index),
                "name": name,
                "aliases": [],
                "description_hint": "",
                "first_seen": trace,
                "source_trace": trace,
                "confidence": "medium",
            }
        )
    return characters


def _normalize_character_candidate(candidate: str) -> str | None:
    if candidate in CHARACTER_STOPWORDS or candidate in {"像是"}:
        return None
    if any(keyword in candidate for keyword in LOCATION_KEYWORDS + PROP_KEYWORDS):
        return None
    if len(candidate) == 3 and candidate[0] in {"工", "老", "小", "新"}:
        candidate = candidate[1:]
    if candidate in CHARACTER_STOPWORDS or candidate in {"像是"}:
        return None
    return candidate


def _detect_keywords(
    paragraphs: list[ParagraphUnit],
    keywords: list[str],
    *,
    id_prefix: str,
    type_field: str,
    type_value: str,
) -> list[dict[str, Any]]:
    results = []
    for keyword in keywords:
        paragraph = next(
            (candidate for candidate in paragraphs if keyword in candidate.text), None
        )
        if paragraph is None:
            continue
        results.append(
            {
                "id": _make_id(id_prefix, len(results) + 1),
                "name": keyword,
                type_field: type_value,
                "description_hint": "",
                "source_trace": _source_trace(paragraph, note=f"关键词命中：{keyword}"),
                "confidence": "high",
            }
        )
    return results


def _detect_key_events(
    paragraphs: list[ParagraphUnit],
    characters: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    props: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events = []
    for paragraph in paragraphs:
        if not any(cue in paragraph.text for cue in EVENT_CUES):
            continue
        event = {
            "id": _make_id("evt", len(events) + 1),
            "sequence_index": len(events) + 1,
            "summary": _preview(paragraph.text),
            "event_type": "surface_action",
            "character_ids": _linked_ids(paragraph.text, characters),
            "location_ids": _linked_ids(paragraph.text, locations),
            "prop_ids": _linked_ids(paragraph.text, props),
            "source_trace": _source_trace(paragraph, note="动作或状态变化关键词命中"),
            "confidence": "medium",
        }
        events.append(event)
    return events


def _detect_timeline(
    paragraphs: list[ParagraphUnit], events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    event_by_trace = {
        (
            event["source_trace"]["chapter_id"],
            tuple(event["source_trace"]["paragraph_ids"]),
        ): event["id"]
        for event in events
    }
    timeline = []
    patterns = [re.compile(pattern) for pattern in TIME_PATTERNS]
    for paragraph in paragraphs:
        matches = []
        for pattern in patterns:
            matches.extend(match.group(0) for match in pattern.finditer(paragraph.text))
        if not matches:
            continue
        trace = _source_trace(paragraph, note="时间表达命中")
        trace_key = (trace["chapter_id"], tuple(trace["paragraph_ids"]))
        timeline.append(
            {
                "id": _make_id("tl", len(timeline) + 1),
                "order": len(timeline) + 1,
                "label": matches[0],
                "time_text": matches[0],
                "event_ids": [event_by_trace[trace_key]]
                if trace_key in event_by_trace
                else [],
                "source_trace": trace,
                "confidence": "medium",
            }
        )
    return timeline


def _detect_psychological_passages(
    paragraphs: list[ParagraphUnit], characters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    passages = []
    for paragraph in paragraphs:
        keyword = next(
            (
                candidate
                for candidate in PSYCHOLOGICAL_KEYWORDS
                if candidate in paragraph.text
            ),
            None,
        )
        if keyword is None:
            continue
        passages.append(
            {
                "id": _make_id("psy", len(passages) + 1),
                "character_ids": _linked_ids(paragraph.text, characters),
                "passage_type": _psychological_type(keyword),
                "summary": _preview(paragraph.text),
                "externalization_hint": "后续改编时需要判断是否外化为可拍摄行动。",
                "source_trace": _source_trace(paragraph, note=f"心理关键词命中：{keyword}"),
                "confidence": "medium",
            }
        )
    return passages


def _detect_uncertainties(paragraphs: list[ParagraphUnit]) -> list[dict[str, Any]]:
    uncertainties = []
    for paragraph in paragraphs:
        cue = next((candidate for candidate in AMBIGUITY_CUES if candidate in paragraph.text), None)
        if cue is None:
            continue
        uncertainties.append(
            {
                "id": _make_id("unc", len(uncertainties) + 1),
                "category": _uncertainty_category(cue),
                "description": f"启发式低置信判断：'{cue}' 可能需要人工确认。",
                "source_trace": _source_trace(paragraph, note=f"不确定性关键词命中：{cue}"),
                "suggested_resolution": "由后续人工审阅或更强解析阶段确认。",
                "severity": "low",
            }
        )
    if not uncertainties and paragraphs:
        uncertainties.append(
            {
                "id": "unc_001",
                "category": "parser_limitation",
                "description": "未命中显式歧义词，但规则解析仍无法保证完整语义理解。",
                "source_trace": _source_trace(paragraphs[0], note="规则解析边界"),
                "suggested_resolution": "后续阶段按需人工复核。",
                "severity": "low",
            }
        )
    return uncertainties


def _linked_ids(text: str, items: list[dict[str, Any]]) -> list[str]:
    return [item["id"] for item in items if item["name"] in text]


def _psychological_type(keyword: str) -> str:
    if keyword in {"想起", "记得"}:
        return "memory"
    if keyword == "害怕":
        return "fear"
    if keyword in {"觉得", "意识到", "心里", "怀疑", "以为"}:
        return "motivation"
    return "other"


def _uncertainty_category(cue: str) -> str:
    if cue in {"有人影", "他们"}:
        return "ambiguous_character"
    if cue == "那可能":
        return "ambiguous_event"
    if cue == "并不只有":
        return "implicit_causality"
    return "parser_limitation"


def _source_trace(paragraph: ParagraphUnit, *, note: str = "") -> dict[str, Any]:
    trace = {
        "chapter_id": paragraph.chapter_id,
        "paragraph_ids": [paragraph.paragraph_id],
        "quote_preview": _preview(paragraph.text, limit=40),
    }
    if note:
        trace["note"] = note
    return trace


def _preview(text: str, *, limit: int = PREVIEW_LIMIT) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _make_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:03d}"
