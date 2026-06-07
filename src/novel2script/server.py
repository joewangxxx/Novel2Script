from __future__ import annotations

import http.server
import json
import os
import sys
import threading
import time
import urllib.parse
import webbrowser
import yaml
from typing import Any

# 路径计算
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # src/novel2script
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))  # Novel2Script
WORKBENCH_DIR = os.path.join(PROJECT_ROOT, "workbench")
INPUT_DIR = os.path.join(PROJECT_ROOT, "examples", "input")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "examples", "output")

# 全局流水线状态
PIPELINE_STATUS = {
    "status": "idle",       # "idle", "running", "success", "failed"
    "progress": 0,
    "text": "就绪",
    "error_msg": ""
}

# 用于在内存中缓存/同步被修改的 patch 状态，避免每次重算重置
PATCH_STATUS_CACHE: dict[str, str] = {}  # patch_id -> status ("accepted", "rejected", "pending")


def format_size(bytes_size: int) -> str:
    if bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    return f"{bytes_size / 1024:.1f} KB"


def run_pipeline_task(novel_name: str, out_dir: str):
    global PIPELINE_STATUS
    PIPELINE_STATUS["status"] = "running"
    PIPELINE_STATUS["progress"] = 0
    PIPELINE_STATUS["text"] = "正在初始化端到端流水线..."
    PIPELINE_STATUS["error_msg"] = ""

    novel_path = os.path.join(INPUT_DIR, novel_name)

    # 监控物理文件生成进度，动态推进进度条
    def monitor_progress():
        steps = [
            ("story_map.yaml", 15, "正在读取并解析小说原文..."),
            ("story_map.merged.yaml", 35, "正在提取剧情语义与角色圣经..."),
            ("outline.yaml", 55, "正在自动规划戏剧章节大纲..."),
            ("screenplay.yaml", 75, "正在运行 Kimi/DeepSeek 协同改编与对白优化..."),
            ("quality_report.yaml", 90, "正在进行剧本格式与质量契约评估..."),
        ]
        while PIPELINE_STATUS["status"] == "running":
            for filename, prog, text in steps:
                filepath = os.path.join(out_dir, filename)
                if os.path.exists(filepath):
                    if PIPELINE_STATUS["progress"] < prog:
                        PIPELINE_STATUS["progress"] = prog
                        PIPELINE_STATUS["text"] = text
            time.sleep(0.5)

    monitor_thread = threading.Thread(target=monitor_progress)
    monitor_thread.daemon = True
    monitor_thread.start()

    try:
        from novel2script.cli import main as cli_main
        # 执行 run-pipeline
        argv = ["run-pipeline", "--novel", novel_path, "--out-dir", out_dir, "--force"]
        if os.environ.get("N2S_ALLOW_NETWORK") == "1":
            argv.append("--allow-network")

        exit_code = cli_main(argv)

        if exit_code == 0:
            # 重算成功后，同步重置内存中的 patch 缓存
            global PATCH_STATUS_CACHE
            PATCH_STATUS_CACHE.clear()
            PIPELINE_STATUS["status"] = "success"
            PIPELINE_STATUS["progress"] = 100
            PIPELINE_STATUS["text"] = "端到端流水线运行成功！"
        else:
            PIPELINE_STATUS["status"] = "failed"
            PIPELINE_STATUS["text"] = "流水线执行失败"
            PIPELINE_STATUS["error_msg"] = "流水线在某个子步骤出错，请查看命令行控制台输出。"
    except Exception as e:
        PIPELINE_STATUS["status"] = "failed"
        PIPELINE_STATUS["text"] = "流水线异常"
        PIPELINE_STATUS["error_msg"] = str(e)


class WorkbenchHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # 强制设置托管目录为 Novel2Script/workbench
        super().__init__(*args, directory=WORKBENCH_DIR, **kwargs)

    def end_headers(self):
        # 允许跨域请求以及缓存控制
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            self.handle_api_get(path, urllib.parse.parse_qs(parsed_url.query))
        else:
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            # 读取 POST Body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b""
            try:
                payload = json.loads(post_data.decode("utf-8")) if post_data else {}
            except json.JSONDecodeError:
                self.send_error_json(400, "Invalid JSON payload")
                return
            self.handle_api_post(path, payload)
        else:
            self.send_error_json(404, "Not Found")

    # ==========================================
    # API 处理逻辑
    # ==========================================

    def handle_api_get(self, path: str, params: dict[str, list[str]]):
        if path == "/api/project":
            self.get_project()
        elif path == "/api/file":
            self.get_file(params)
        elif path == "/api/pipeline-status":
            self.get_pipeline_status()
        else:
            self.send_error_json(404, f"API endpoint {path} not found")

    def handle_api_post(self, path: str, payload: dict[str, Any]):
        if path == "/api/run-pipeline":
            self.run_pipeline(payload)
        elif path == "/api/patch/apply":
            self.apply_patch(payload)
        elif path == "/api/patch/reject":
            self.reject_patch(payload)
        elif path == "/api/save-screenplay":
            self.save_screenplay(payload)
        else:
            self.send_error_json(404, f"API endpoint {path} not found")

    # ==========================================
    # GET 接口实现
    # ==========================================

    def get_project(self):
        # 扫描文件列表
        files_list = []
        
        # 1. 扫描输入目录（小说原文）
        if os.path.exists(INPUT_DIR):
            for name in os.listdir(INPUT_DIR):
                if name.endswith((".txt", ".md")):
                    path = os.path.join(INPUT_DIR, name)
                    stat = os.stat(path)
                    files_list.append({
                        "name": name,
                        "type": "novel",
                        "status": "source",
                        "size": format_size(stat.st_size)
                    })

        # 2. 扫描输出目录（中间与最终 YAML）
        if os.path.exists(OUTPUT_DIR):
            for name in os.listdir(OUTPUT_DIR):
                if not name.endswith(".yaml"):
                    continue
                path = os.path.join(OUTPUT_DIR, name)
                stat = os.stat(path)
                size_str = format_size(stat.st_size)

                # 根据名字区分类型
                if "story_map.merged" in name:
                    files_list.append({"name": name, "type": "story_map", "status": "human_confirmed", "size": size_str})
                elif "story_map" in name:
                    files_list.append({"name": name, "type": "story_map", "status": "source", "size": size_str})
                elif "outline" in name:
                    files_list.append({"name": name, "type": "outline", "status": "human_confirmed", "size": size_str})
                elif "character_bible" in name:
                    files_list.append({"name": name, "type": "character_bible", "status": "human_confirmed", "size": size_str})
                elif "quality_report" in name:
                    files_list.append({"name": name, "type": "quality_report", "status": "system_generated", "size": size_str})
                elif "review_report" in name:
                    files_list.append({"name": name, "type": "review_report", "status": "system_generated", "size": size_str})
                elif "screenplay" in name:
                    status = "human_confirmed" if "enhanced" in name else "ai_inferred"
                    files_list.append({"name": name, "type": "screenplay", "status": status, "size": size_str})

        # 获取项目最后修改时间与版本信息
        last_modified = "2026-06-07T20:00:00+08:00"
        screenplay_path = os.path.join(OUTPUT_DIR, "test1_sanguo_screenplay.yaml")
        if os.path.exists(screenplay_path):
            stat = os.stat(screenplay_path)
            last_modified = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(stat.st_mtime))

        project_name = "小说剧本智能改编项目"
        if os.path.exists(screenplay_path):
            try:
                with open(screenplay_path, encoding="utf-8") as f:
                    sp = yaml.safe_load(f)
                    if sp and "metadata" in sp and "title" in sp["metadata"]:
                        project_name = f"{sp['metadata']['title']} 改编项目"
            except Exception:
                pass

        data = {
            "project_info": {
                "name": project_name,
                "last_modified": last_modified,
                "version": "Novel2Script MVP V0.2"
            },
            "files": files_list
        }
        self.send_json_response(200, data)

    def get_file(self, params: dict[str, list[str]]):
        names = params.get("name")
        if not names:
            self.send_error_json(400, "Missing 'name' query parameter")
            return
        filename = os.path.basename(names[0])  # 防止目录穿越安全防御

        # 查找物理路径
        file_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(file_path):
            file_path = os.path.join(OUTPUT_DIR, filename)

        if not os.path.exists(file_path):
            self.send_error_json(404, f"File {filename} not found")
            return

        # 1. 处理小说原文类型 (txt / md)
        if filename.endswith((".txt", ".md")):
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                
                # 按双换行符将小说段落化
                paragraphs = []
                p_idx = 1
                for block in content.split("\n\n"):
                    cleaned = block.strip()
                    if cleaned:
                        # 兼容单换行拆分段落
                        paragraphs.append({
                            "id": f"p_{p_idx:03d}",
                            "text": cleaned
                        })
                        p_idx += 1

                data = {
                    "chapters": [
                        {
                            "id": "ch_001",
                            "title": filename,
                            "paragraphs": paragraphs
                        }
                    ]
                }
                self.send_json_response(200, data)
            except Exception as e:
                self.send_error_json(500, f"Error parsing novel: {str(e)}")
            return

        # 2. 处理 YAML 类型
        if filename.endswith(".yaml"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f)

                # 特殊逻辑：如果是 screenplay 类型，转换 source_trace_ids 格式以向下兼容前端
                if "screenplay" in filename:
                    yaml_data = self.adapt_screenplay_to_frontend(yaml_data)
                
                self.send_json_response(200, yaml_data)
            except Exception as e:
                self.send_error_json(500, f"Error parsing YAML: {str(e)}")
            return

        self.send_error_json(400, "Unsupported file format")

    def get_pipeline_status(self):
        self.send_json_response(200, PIPELINE_STATUS)

    # ==========================================
    # POST 接口实现
    # ==========================================

    def run_pipeline(self, payload: dict[str, Any]):
        global PIPELINE_STATUS
        if PIPELINE_STATUS["status"] == "running":
            self.send_error_json(400, "Pipeline is already running")
            return

        novel = payload.get("novel")
        if not novel:
            # 默认选用 examples/input 目录下的第一个 txt / md
            novels = [n for n in os.listdir(INPUT_DIR) if n.endswith((".txt", ".md"))]
            novel = novels[0] if novels else ""

        if not novel or not os.path.exists(os.path.join(INPUT_DIR, novel)):
            self.send_error_json(400, f"No source novel file found: {novel}")
            return

        # 启动线程异步跑 Pipeline
        t = threading.Thread(target=run_pipeline_task, args=(novel, OUTPUT_DIR))
        t.daemon = True
        t.start()

        self.send_json_response(200, {"status": "started"})

    def apply_patch(self, payload: dict[str, Any]):
        patch_id = payload.get("patch_id")
        proposed_text = payload.get("proposed_text")
        target = payload.get("target")  # 包含 scene_id, beat_id, element_id 等定位

        if not patch_id or not target:
            self.send_error_json(400, "Missing patch_id or target")
            return

        screenplay_name = payload.get("screenplay_file", "test1_sanguo_screenplay.yaml")
        screenplay_path = os.path.join(OUTPUT_DIR, screenplay_name)
        if not os.path.exists(screenplay_path):
            # 兼容默认生成的名字
            screenplay_path = os.path.join(OUTPUT_DIR, "generated_screenplay.yaml")

        if not os.path.exists(screenplay_path):
            self.send_error_json(404, f"Screenplay file not found for apply-patch")
            return

        # 1. 修改 screenplay.yaml 里的对应节点
        try:
            with open(screenplay_path, encoding="utf-8") as f:
                sp = yaml.safe_load(f)

            modified = self.modify_screenplay_element(sp, target, proposed_text, status="accepted")
            if not modified:
                self.send_error_json(400, "Failed to locate target element in screenplay")
                return

            # 写回 YAML 文件
            with open(screenplay_path, "w", encoding="utf-8") as f:
                yaml.dump(sp, f, allow_unicode=True, sort_keys=False)

            # 2. 缓存状态
            global PATCH_STATUS_CACHE
            PATCH_STATUS_CACHE[patch_id] = "accepted"

            # 3. 触发质量评估重新评估
            self.trigger_quality_evaluation(screenplay_name)

            self.send_json_response(200, {"status": "success", "message": "Patch applied successfully"})
        except Exception as e:
            self.send_error_json(500, f"Failed to apply patch: {str(e)}")

    def reject_patch(self, payload: dict[str, Any]):
        patch_id = payload.get("patch_id")
        target = payload.get("target")

        if not patch_id or not target:
            self.send_error_json(400, "Missing patch_id or target")
            return

        screenplay_name = payload.get("screenplay_file", "test1_sanguo_screenplay.yaml")
        screenplay_path = os.path.join(OUTPUT_DIR, screenplay_name)
        if not os.path.exists(screenplay_path):
            screenplay_path = os.path.join(OUTPUT_DIR, "generated_screenplay.yaml")

        # 将剧本中该元素的 needs_human_review 设为 false，防止继续报错
        try:
            with open(screenplay_path, encoding="utf-8") as f:
                sp = yaml.safe_load(f)

            modified = self.modify_screenplay_element(sp, target, proposed_text=None, status="rejected")
            if modified:
                with open(screenplay_path, "w", encoding="utf-8") as f:
                    yaml.dump(sp, f, allow_unicode=True, sort_keys=False)

            global PATCH_STATUS_CACHE
            PATCH_STATUS_CACHE[patch_id] = "rejected"

            self.trigger_quality_evaluation(screenplay_name)
            self.send_json_response(200, {"status": "success", "message": "Patch rejected successfully"})
        except Exception as e:
            self.send_error_json(500, f"Failed to reject patch: {str(e)}")

    def save_screenplay(self, payload: dict[str, Any]):
        # 允许就地编辑保存
        target = payload.get("target")
        text = payload.get("text")
        screenplay_name = payload.get("screenplay_file", "test1_sanguo_screenplay.yaml")
        screenplay_path = os.path.join(OUTPUT_DIR, screenplay_name)

        if not os.path.exists(screenplay_path):
            screenplay_path = os.path.join(OUTPUT_DIR, "generated_screenplay.yaml")

        if not os.path.exists(screenplay_path):
            self.send_error_json(404, "Screenplay file not found")
            return

        try:
            with open(screenplay_path, encoding="utf-8") as f:
                sp = yaml.safe_load(f)

            modified = self.modify_screenplay_element(sp, target, text, status="accepted")
            if not modified:
                self.send_error_json(400, "Target element not found")
                return

            with open(screenplay_path, "w", encoding="utf-8") as f:
                yaml.dump(sp, f, allow_unicode=True, sort_keys=False)

            self.trigger_quality_evaluation(screenplay_name)
            self.send_json_response(200, {"status": "success", "message": "Screenplay saved"})
        except Exception as e:
            self.send_error_json(500, f"Save failed: {str(e)}")

    # ==========================================
    # 辅助方法
    # ==========================================

    def send_json_response(self, status: int, data: Any):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_error_json(self, status: int, message: str):
        self.send_json_response(status, {"error": message})

    def adapt_screenplay_to_frontend(self, sp_data: dict[str, Any]) -> dict[str, Any]:
        """向下兼容转换 source_trace_ids 为前端使用的 source_trace"""
        if not sp_data or "scenes" not in sp_data:
            return sp_data

        # 遍历场景与元素
        for scene in sp_data.get("scenes", []):
            if "source_trace_ids" in scene and scene["source_trace_ids"]:
                trace = scene["source_trace_ids"]
                scene["source_trace"] = {
                    "chapter_id": trace.get("chapter_id", "ch_001"),
                    "paragraph_ids": trace.get("paragraph_ids", [])
                }
            
            for beat in scene.get("beats", []):
                if "source_trace_ids" in beat and beat["source_trace_ids"]:
                    trace = beat["source_trace_ids"]
                    beat["source_trace"] = {
                        "chapter_id": trace.get("chapter_id", "ch_001"),
                        "paragraph_ids": trace.get("paragraph_ids", [])
                    }

            for el in scene.get("elements", []):
                if "source_trace_ids" in el and el["source_trace_ids"]:
                    trace = el["source_trace_ids"]
                    el["source_trace"] = {
                        "chapter_id": trace.get("chapter_id", "ch_001"),
                        "paragraph_ids": trace.get("paragraph_ids", [])
                    }

        return sp_data

    def modify_screenplay_element(self, sp: dict[str, Any], target: dict[str, Any], proposed_text: str | None, status: str) -> bool:
        """物理改写剧本指定元素的内容，并更新 AI 状态"""
        scene_id = target.get("scene_id")
        element_id = target.get("element_id")
        beat_id = target.get("beat_id")

        for scene in sp.get("scenes", []):
            if scene["id"] != scene_id:
                continue

            # 1. 如果是修改 Beat 节奏目标
            if beat_id:
                for beat in scene.get("beats", []):
                    if beat["id"] == beat_id:
                        if proposed_text is not None:
                            beat["objective"] = proposed_text
                        if "ai_tags" in beat:
                            beat["ai_tags"]["needs_human_review"] = False
                            beat["ai_tags"]["inferred"] = False
                        return True

            # 2. 如果是修改具体的行 (elements)
            if element_id:
                # element_id 通常格式为 "el-{scene_id}-{index}"
                try:
                    parts = element_id.split("-")
                    idx = int(parts[-1])
                except (ValueError, IndexError):
                    idx = -1

                elements = scene.get("elements", [])
                if 0 <= idx < len(elements):
                    el = elements[idx]
                    if proposed_text is not None:
                        el["text"] = proposed_text
                    if "ai_tags" in el:
                        el["ai_tags"]["needs_human_review"] = False
                        el["ai_tags"]["inferred"] = False
                    else:
                        el["ai_tags"] = {"inferred": False, "confidence": "high", "needs_human_review": False}
                    return True

        return False

    def trigger_quality_evaluation(self, screenplay_name: str):
        """调用 CLI 重新算质量报告，确保物理文件与分数同步"""
        try:
            # 找到对应项目的报告与校验文件
            prefix = screenplay_name.replace("_screenplay.yaml", "")
            if prefix == screenplay_name:
                prefix = "test1_sanguo"

            screenplay_path = os.path.join(OUTPUT_DIR, screenplay_name)
            if not os.path.exists(screenplay_path):
                screenplay_path = os.path.join(OUTPUT_DIR, "generated_screenplay.yaml")
                prefix = "generated"

            validation_path = os.path.join(OUTPUT_DIR, f"{prefix}_validation_report.yaml")
            review_path = os.path.join(OUTPUT_DIR, f"{prefix}_review_report.yaml")
            out_quality_path = os.path.join(OUTPUT_DIR, f"{prefix}_quality_report.yaml")
            out_dashboard_path = os.path.join(OUTPUT_DIR, f"{prefix}_quality_dashboard.md")

            # 检查校验和审校文件是否存在，如不存在则使用通用模板
            if not os.path.exists(validation_path):
                validation_path = os.path.join(OUTPUT_DIR, "generated_validation_report.yaml")
            if not os.path.exists(review_path):
                review_path = os.path.join(OUTPUT_DIR, "generated_review_report.yaml")

            from novel2script.cli import main as cli_main
            # 组装参数
            argv = [
                "evaluate-quality",
                "--screenplay", screenplay_path,
                "--validation-report", validation_path,
                "--review-report", review_path,
                "--out", out_quality_path,
                "--markdown", out_dashboard_path
            ]
            cli_main(argv)
        except Exception as e:
            print(f"[Server ERROR] Failed to run quality evaluation: {e}", file=sys.stderr)


def start_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    server_address = (host, port)
    httpd = http.server.HTTPServer(server_address, WorkbenchHTTPHandler)
    print(f"Novel2Script AI Workbench running at http://{host}:{port}/")

    if open_browser:
        # 打开默认浏览器
        def open_web():
            time.sleep(1.0)
            webbrowser.open_new_tab(f"http://{host}:{port}/")
        t = threading.Thread(target=open_web)
        t.daemon = True
        t.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Novel2Script AI Workbench...")
        httpd.server_close()


if __name__ == "__main__":
    start_server()
