import json
import shutil
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from novel2script.cli import main


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "generated_screenplay.yaml"
FOUNTAIN = ROOT / "examples" / "output" / "generated_screenplay.fountain"
MAP = ROOT / "examples" / "output" / "generated_screenplay.fountain.map.json"
ROUNDTRIP_SCHEMA = ROOT / "schemas" / "fountain_roundtrip_report.schema.json"


def _copy_fountain_and_map(tmp_path: Path) -> tuple[Path, Path]:
    edited_fountain = tmp_path / "edited.fountain"
    edited_map = tmp_path / "edited.fountain.map.json"
    shutil.copyfile(FOUNTAIN, edited_fountain)
    sidecar = json.loads(MAP.read_text(encoding="utf-8"))
    sidecar["fountain_file"] = str(edited_fountain)
    edited_map.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    return edited_fountain, edited_map


def _replace_mapped_text(fountain_path: Path, map_path: Path, yaml_path: str, text: str) -> None:
    lines = fountain_path.read_text(encoding="utf-8").splitlines()
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))
    mapping = next(item for item in sidecar["mappings"] if item["yaml_path"] == yaml_path)
    lines[mapping["line_start"] - 1 : mapping["line_end"]] = [text]
    fountain_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def test_import_fountain_cli_syncs_heading_and_action_and_sets_metadata(tmp_path):
    edited_fountain, edited_map = _copy_fountain_and_map(tmp_path)
    _replace_mapped_text(edited_fountain, edited_map, "scenes[0].heading", "INT./EXT. POST OFFICE - DAWN")
    _replace_mapped_text(
        edited_fountain,
        edited_map,
        "scenes[0].elements[0].text",
        "Lin studies the blue envelope under the counter light.",
    )
    output_path = tmp_path / "roundtrip.yaml"
    report_path = tmp_path / "roundtrip_report.yaml"
    original = yaml.safe_load(SCREENPLAY.read_text(encoding="utf-8"))
    original_scene = deepcopy(original["scenes"][0])

    exit_code = main(
        [
            "import-fountain",
            "--screenplay",
            str(SCREENPLAY),
            "--fountain",
            str(edited_fountain),
            "--map",
            str(edited_map),
            "--out",
            str(output_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    updated = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    schema = json.loads(ROUNDTRIP_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(report)
    assert updated["scenes"][0]["heading"] == "INT./EXT. POST OFFICE - DAWN"
    assert (
        updated["scenes"][0]["elements"][0]["text"]
        == "Lin studies the blue envelope under the counter light."
    )
    assert updated["scenes"][0]["source_trace"] == original_scene["source_trace"]
    assert updated["scenes"][0]["beats"] == original_scene["beats"]
    assert updated["characters"] == original["characters"]
    assert updated["metadata"]["semantic_fields_stale"] is True
    assert report["fountain_roundtrip_report"]["summary"]["applied_changes"] == 2


def test_import_fountain_cli_reports_unsafe_mapping_without_output_yaml(tmp_path):
    edited_fountain, edited_map = _copy_fountain_and_map(tmp_path)
    sidecar = json.loads(edited_map.read_text(encoding="utf-8"))
    sidecar["mappings"][0]["yaml_path"] = "scenes[0].beats[0].objective"
    edited_map.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    output_path = tmp_path / "roundtrip.yaml"
    report_path = tmp_path / "roundtrip_report.yaml"

    exit_code = main(
        [
            "import-fountain",
            "--screenplay",
            str(SCREENPLAY),
            "--fountain",
            str(edited_fountain),
            "--map",
            str(edited_map),
            "--out",
            str(output_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert not output_path.exists()
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert report["fountain_roundtrip_report"]["status"] == "blocked"
    assert report["fountain_roundtrip_report"]["issues"][0]["code"] == "unsafe_yaml_path"
