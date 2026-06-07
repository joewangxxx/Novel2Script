import json
import shutil
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    fountain_in = root / "examples/output/test1_sanguo_screenplay.stage32.fountain"
    map_in = root / "examples/output/test1_sanguo_screenplay.stage32.fountain.map.json"
    
    fountain_out = root / "examples/output/test1_sanguo_screenplay.stage32_temp.fountain"
    map_out = root / "examples/output/test1_sanguo_screenplay.stage32_temp.fountain.map.json"
    
    # 复制 fountain
    shutil.copyfile(fountain_in, fountain_out)
    
    # 复制 map 并修改其中的 fountain_file
    sidecar = json.loads(map_in.read_text(encoding="utf-8"))
    sidecar["fountain_file"] = str(fountain_out)
    
    # 替换一个 mapped text: 将 scenes[0].heading 修改
    lines = fountain_out.read_text(encoding="utf-8").splitlines()
    mapping = next(item for item in sidecar["mappings"] if item["yaml_path"] == "scenes[0].heading")
    
    # 获取原来的 scene heading
    original_heading = "\n".join(lines[mapping["line_start"] - 1 : mapping["line_end"]])
    new_heading = original_heading + " - DAY"
    
    lines[mapping["line_start"] - 1 : mapping["line_end"]] = [new_heading]
    fountain_out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    
    map_out.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Stage 32 Roundtrip temp files prepared successfully.")

if __name__ == "__main__":
    main()
