import json
from pathlib import Path

import yaml

from novel2script.exporters.fountain_exporter import export_fountain


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_YAML = ROOT / "examples" / "output" / "sample_screenplay.yaml"


def test_export_fountain_writes_non_empty_file_and_sidecar_map(tmp_path):
    out_path = tmp_path / "screenplay.fountain"
    map_path = tmp_path / "screenplay.fountain.map.json"

    export_fountain(str(SAMPLE_YAML), str(out_path), str(map_path))

    text = out_path.read_text(encoding="utf-8")
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))

    assert text.strip()
    assert "objective" not in text
    assert sidecar["source_yaml"].endswith("sample_screenplay.yaml")
    assert sidecar["fountain_file"].endswith("screenplay.fountain")
    assert sidecar["mappings"]
    assert any(mapping["yaml_path"] == "scenes[0].heading" for mapping in sidecar["mappings"])
    assert any(
        mapping["yaml_path"] == "scenes[0].elements[2].text"
        and mapping["element_index"] == 2
        for mapping in sidecar["mappings"]
    )


def test_sidecar_map_tracks_multiline_element_start_and_end(tmp_path):
    data = yaml.safe_load(SAMPLE_YAML.read_text(encoding="utf-8"))
    data["scenes"][0]["elements"][0]["text"] = "first action line\nsecond action line"
    yaml_path = tmp_path / "screenplay.yaml"
    yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    out_path = tmp_path / "screenplay.fountain"
    map_path = tmp_path / "screenplay.fountain.map.json"

    export_fountain(str(yaml_path), str(out_path), str(map_path))

    lines = out_path.read_text(encoding="utf-8").splitlines()
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))
    action_mapping = next(
        mapping
        for mapping in sidecar["mappings"]
        if mapping["yaml_path"] == "scenes[0].elements[0].text"
    )

    assert lines[action_mapping["line_start"] - 1] == "first action line"
    assert lines[action_mapping["line_end"] - 1] == "second action line"
