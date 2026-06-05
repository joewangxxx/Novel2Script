import json
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.exporters.fountain_exporter import export_fountain
from novel2script.importers.fountain_importer import sync_fountain_to_yaml


ROOT = Path(__file__).resolve().parents[1]
ROUNDTRIP_SCHEMA = ROOT / "schemas" / "fountain_roundtrip_report.schema.json"


def _trace():
    return {"chapter": 1, "paragraph_range": [1, 1], "note": "fixture"}


def _tags():
    return {"inferred": True, "confidence": "medium", "needs_human_review": True}


def _screenplay() -> dict:
    return {
        "schema_version": "0.1.0",
        "metadata": {
            "title": "Roundtrip Fixture",
            "language": "en",
            "created_by": "test",
            "created_at": "2026-06-05",
        },
        "source": {"type": "novel", "chapter_count": 1, "trace_unit": "chapter_paragraph"},
        "adaptation_policy": {"allow_inference": True},
        "characters": [{"id": "char_001", "name": "Lin"}],
        "scenes": [
            {
                "id": "scene_001",
                "heading": "INT. POST OFFICE - NIGHT",
                "source_trace": _trace(),
                "beats": [
                    {
                        "id": "beat_001",
                        "objective": "Keep the letter safe.",
                        "tactic": "Hide it.",
                        "obstacle": "The lights flicker.",
                        "conflict": "Someone knocks.",
                        "stakes": "The letter may vanish.",
                        "turn": "The bell rings.",
                        "externalized_action": "Lin hides the letter.",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
                "elements": [
                    {
                        "type": "action",
                        "text": "Lin opens the blue envelope.",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    },
                    {
                        "type": "dialogue",
                        "character_id": "char_001",
                        "text": "I heard the bell.",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    },
                    {
                        "type": "parenthetical",
                        "text": "quietly",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    },
                    {
                        "type": "transition",
                        "text": "Cut to:",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    },
                ],
            }
        ],
    }


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _export_fixture(tmp_path: Path, screenplay: dict | None = None) -> tuple[Path, Path, Path]:
    screenplay_path = tmp_path / "screenplay.yaml"
    fountain_path = tmp_path / "screenplay.fountain"
    map_path = tmp_path / "screenplay.fountain.map.json"
    _write_yaml(screenplay_path, screenplay or _screenplay())
    export_fountain(str(screenplay_path), str(fountain_path), str(map_path))
    return screenplay_path, fountain_path, map_path


def _replace_mapped_text(fountain_path: Path, map_path: Path, yaml_path: str, lines: list[str]) -> None:
    fountain_lines = fountain_path.read_text(encoding="utf-8").splitlines()
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))
    mapping = next(item for item in sidecar["mappings"] if item["yaml_path"] == yaml_path)
    start = mapping["line_start"] - 1
    end = mapping["line_end"]
    fountain_lines[start:end] = lines
    fountain_path.write_text("\n".join(fountain_lines).rstrip() + "\n", encoding="utf-8")


def test_syncs_heading_and_action_text_without_touching_semantic_fields(tmp_path):
    screenplay = _screenplay()
    original_beats = deepcopy(screenplay["scenes"][0]["beats"])
    original_characters = deepcopy(screenplay["characters"])
    screenplay_path, fountain_path, map_path = _export_fixture(tmp_path, screenplay)
    _replace_mapped_text(fountain_path, map_path, "scenes[0].heading", ["INT. POST OFFICE - DAWN"])
    _replace_mapped_text(
        fountain_path,
        map_path,
        "scenes[0].elements[0].text",
        ["Lin tears open the blue envelope."],
    )
    out_path = tmp_path / "roundtrip.yaml"
    report_path = tmp_path / "roundtrip_report.yaml"

    report = sync_fountain_to_yaml(
        str(screenplay_path),
        str(fountain_path),
        str(map_path),
        str(out_path),
        str(report_path),
    )

    updated = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert updated["scenes"][0]["heading"] == "INT. POST OFFICE - DAWN"
    assert updated["scenes"][0]["elements"][0]["text"] == "Lin tears open the blue envelope."
    assert updated["scenes"][0]["beats"] == original_beats
    assert updated["characters"] == original_characters
    assert updated["scenes"][0]["source_trace"] == _trace()
    assert updated["metadata"]["semantic_fields_stale"] is True
    assert updated["metadata"]["roundtrip"]["applied_changes"] == 2
    assert report["fountain_roundtrip_report"]["status"] == "applied"
    assert report["fountain_roundtrip_report"]["summary"]["applied_changes"] == 2
    schema = json.loads(ROUNDTRIP_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(yaml.safe_load(report_path.read_text(encoding="utf-8")))


def test_syncs_dialogue_and_parenthetical_with_type_aware_normalization(tmp_path):
    screenplay_path, fountain_path, map_path = _export_fixture(tmp_path)
    _replace_mapped_text(
        fountain_path,
        map_path,
        "scenes[0].elements[1].text",
        ["LIN", "I saw the lighthouse."],
    )
    _replace_mapped_text(
        fountain_path,
        map_path,
        "scenes[0].elements[2].text",
        ["(under her breath)"],
    )
    out_path = tmp_path / "roundtrip.yaml"

    report = sync_fountain_to_yaml(
        str(screenplay_path),
        str(fountain_path),
        str(map_path),
        str(out_path),
    )

    updated = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert updated["scenes"][0]["elements"][1]["character_id"] == "char_001"
    assert updated["scenes"][0]["elements"][1]["text"] == "I saw the lighthouse."
    assert updated["scenes"][0]["elements"][2]["text"] == "under her breath"
    assert report["fountain_roundtrip_report"]["summary"]["applied_changes"] == 2


def test_syncs_transition_text_without_changing_beats(tmp_path):
    screenplay = _screenplay()
    original_beats = deepcopy(screenplay["scenes"][0]["beats"])
    screenplay_path, fountain_path, map_path = _export_fixture(tmp_path, screenplay)
    _replace_mapped_text(
        fountain_path,
        map_path,
        "scenes[0].elements[3].text",
        ["FADE TO:"],
    )
    out_path = tmp_path / "roundtrip.yaml"

    report = sync_fountain_to_yaml(
        str(screenplay_path),
        str(fountain_path),
        str(map_path),
        str(out_path),
    )

    updated = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert updated["scenes"][0]["elements"][3]["text"] == "FADE TO:"
    assert updated["scenes"][0]["beats"] == original_beats
    assert report["fountain_roundtrip_report"]["summary"]["applied_changes"] == 1


def test_line_drift_blocks_sync_and_writes_report_without_output_yaml(tmp_path):
    screenplay_path, fountain_path, map_path = _export_fixture(tmp_path)
    fountain_lines = fountain_path.read_text(encoding="utf-8").splitlines()
    fountain_lines.insert(6, "A NEW UNSAFE LINE")
    fountain_path.write_text("\n".join(fountain_lines) + "\n", encoding="utf-8")
    out_path = tmp_path / "roundtrip.yaml"
    report_path = tmp_path / "roundtrip_report.yaml"

    report = sync_fountain_to_yaml(
        str(screenplay_path),
        str(fountain_path),
        str(map_path),
        str(out_path),
        str(report_path),
    )

    assert not out_path.exists()
    roundtrip = report["fountain_roundtrip_report"]
    assert roundtrip["status"] == "blocked"
    assert roundtrip["line_policy"]["line_drift_detected"] is True
    assert roundtrip["issues"][0]["code"] == "line_drift"
    assert yaml.safe_load(report_path.read_text(encoding="utf-8")) == report


def test_unsafe_yaml_path_is_reported_and_not_applied(tmp_path):
    screenplay_path, fountain_path, map_path = _export_fixture(tmp_path)
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))
    sidecar["mappings"][0]["yaml_path"] = "scenes[0].beats[0].objective"
    map_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    out_path = tmp_path / "roundtrip.yaml"

    report = sync_fountain_to_yaml(
        str(screenplay_path),
        str(fountain_path),
        str(map_path),
        str(out_path),
    )

    assert not out_path.exists()
    issue = report["fountain_roundtrip_report"]["issues"][0]
    assert report["fountain_roundtrip_report"]["status"] == "blocked"
    assert issue["code"] == "unsafe_yaml_path"
