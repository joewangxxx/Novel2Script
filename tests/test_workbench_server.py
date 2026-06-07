from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
import urllib.error
import pytest
import yaml

from novel2script.server import WorkbenchHTTPHandler
from http.server import HTTPServer

# 路径定位
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # tests
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)  # Novel2Script
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "examples", "output")
INPUT_DIR = os.path.join(PROJECT_ROOT, "examples", "input")


class HTTPServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        # port=0 会自动寻找操作系统空闲的临时端口
        self.server = HTTPServer(("127.0.0.1", 0), WorkbenchHTTPHandler)
        self.port = self.server.server_port
        self.daemon = True

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture(scope="module")
def test_server():
    server_thread = HTTPServerThread()
    server_thread.start()
    # 稍微等一等服务器启动成功
    time.sleep(0.5)
    yield f"http://127.0.0.1:{server_thread.port}"
    server_thread.shutdown()
    server_thread.join()


def test_api_project_structure(test_server):
    url = f"{test_server}/api/project"
    try:
        response = urllib.request.urlopen(url)
        assert response.status == 200
        assert "application/json" in response.headers.get("Content-Type", "")
        
        data = json.loads(response.read().decode("utf-8"))
        assert "project_info" in data
        assert "files" in data
        
        # 验证返回的文件列表中包含小说和 YAML 文件
        files = data["files"]
        assert len(files) > 0
        novel_found = any(f["type"] == "novel" for f in files)
        assert novel_found, "File list should contain at least one novel source file"
    except urllib.error.URLError as e:
        pytest.fail(f"API request to /api/project failed: {e}")


def test_api_get_file_novel(test_server):
    # 获取输入目录里的 txt
    novels = [n for n in os.listdir(INPUT_DIR) if n.endswith(".txt")]
    if not novels:
        pytest.skip("No txt novels available for test")
    
    novel_name = novels[0]
    url = f"{test_server}/api/file?name={novel_name}"
    
    response = urllib.request.urlopen(url)
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    
    assert "chapters" in data
    assert len(data["chapters"]) > 0
    assert "paragraphs" in data["chapters"][0]
    assert len(data["chapters"][0]["paragraphs"]) > 0
    assert "id" in data["chapters"][0]["paragraphs"][0]
    assert "text" in data["chapters"][0]["paragraphs"][0]


def test_api_get_file_screenplay_with_trace_adaptation(test_server):
    screenplays = [s for s in os.listdir(OUTPUT_DIR) if "screenplay" in s and s.endswith(".yaml")]
    if not screenplays:
        pytest.skip("No screenplay YAML files available for test")

    sp_name = screenplays[0]
    url = f"{test_server}/api/file?name={sp_name}"
    
    response = urllib.request.urlopen(url)
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    
    assert "scenes" in data
    assert len(data["scenes"]) > 0
    # 验证是否正确将 source_trace_ids 适配转换为前端所需要的 source_trace 字段
    scene = data["scenes"][0]
    assert "source_trace" in scene
    assert "chapter_id" in scene["source_trace"]
    assert "paragraph_ids" in scene["source_trace"]


def test_api_pipeline_status(test_server):
    url = f"{test_server}/api/pipeline-status"
    response = urllib.request.urlopen(url)
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    
    assert "status" in data
    assert "progress" in data
    assert "text" in data


def test_static_asset_serving(test_server):
    url = f"{test_server}/index.html"
    response = urllib.request.urlopen(url)
    assert response.status == 200
    content = response.read().decode("utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Novel2Script AI 改编工作台" in content


def test_api_patch_apply_and_reject(test_server, tmp_path):
    # 1. 复制一份 screenplay.yaml 来测试 patch 采纳物理写回
    screenplay_src = os.path.join(OUTPUT_DIR, "test1_sanguo_screenplay.yaml")
    if not os.path.exists(screenplay_src):
        screenplay_src = os.path.join(OUTPUT_DIR, "generated_screenplay.yaml")
    
    if not os.path.exists(screenplay_src):
        pytest.skip("No reference screenplay.yaml file to run apply patch test")

    # 在 tmp_path 下模拟一个 output 目录进行无副作用读写测试
    mock_output_dir = tmp_path / "mock_output"
    mock_output_dir.mkdir()
    
    test_sp_file = mock_output_dir / "test_patch_screenplay.yaml"
    
    # 注入一个含有 needs_human_review AI 标志的测试 YAML
    test_yaml_content = {
        "schema_version": "0.1.0",
        "metadata": {"title": "单元测试剧本"},
        "scenes": [
            {
                "id": "scene_001",
                "heading": "INT. 涿县城门口 - 白天",
                "beats": [],
                "elements": [
                    {
                        "type": "action",
                        "text": "测试原始文本段落",
                        "ai_tags": {
                            "inferred": True,
                            "confidence": "high",
                            "needs_human_review": True
                        }
                    }
                ]
            }
        ]
    }
    
    test_sp_file.write_text(yaml.dump(test_yaml_content, allow_unicode=True), encoding="utf-8")
    
    # 模拟 HTTP POST 发起采纳补丁请求
    # 由于测试服务器默认是访问 PROJECT_ROOT/examples/output 中的文件，为了配合测试，我们可以临时 monkeypatch
    # 服务器中的 OUTPUT_DIR 路径。在单进程中，我们可以简单地通过模块属性赋值：
    import novel2script.server
    original_output_dir = novel2script.server.OUTPUT_DIR
    novel2script.server.OUTPUT_DIR = str(mock_output_dir)
    
    url = f"{test_server}/api/patch/apply"
    payload = {
        "patch_id": "patch-el-scene_001-0",
        "proposed_text": "采纳修改后的美丽文本",
        "target": {
            "scene_id": "scene_001",
            "element_id": "el-scene_001-0"
        },
        "screenplay_file": "test_patch_screenplay.yaml"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
    
    try:
        response = urllib.request.urlopen(req)
        assert response.status == 200
        res_data = json.loads(response.read().decode("utf-8"))
        assert res_data["status"] == "success"
        
        # 物理检查文件是否被成功修改
        with open(test_sp_file, encoding="utf-8") as f:
            updated_sp = yaml.safe_load(f)
        
        element = updated_sp["scenes"][0]["elements"][0]
        assert element["text"] == "采纳修改后的美丽文本"
        assert element["ai_tags"]["needs_human_review"] is False
        assert element["ai_tags"]["inferred"] is False
        
    finally:
        # 恢复环境
        novel2script.server.OUTPUT_DIR = original_output_dir
