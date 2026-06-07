# Novel2Script

Novel2Script 是一个面向小说作者的 AI 辅助剧本改编工具。项目目标是将 3 个章节以上的小说文本转换为结构化、可追溯、可编辑的剧本初稿，并支持 YAML Schema 校验、多 Agent 审校、`source_trace` 溯源和 Fountain 格式导出/回写。

当前仓库已经完成本地确定性管线、结构化剧本 YAML、Fountain 有限回写、质量评估、LLM Provider 抽象，以及真实 LLM 的显式接入门禁。默认执行仍然是 `mock_dry_run`，不会自动联网；真实模型调用必须显式传入 `--allow-network`，并且 API Key 只能通过环境变量提供。

## 当前能力

- 小说 Markdown/TXT 解析为 `story_map.yaml`
- 基于 `story_map` 生成 `outline.yaml` 和 `character_bible.yaml`
- 生成结构化 `screenplay.yaml`
- 校验剧本 Schema、source trace、beat 和引用完整性
- 导出 Fountain，并支持有限范围 Fountain 回写到 YAML
- 生成多 Agent 确定性审校报告
- 生成质量评估 YAML 和 Markdown Dashboard
- 通过统一 LLM Provider 抽象接入真实中国大模型
- 保持默认 dry-run、本地测试无网络依赖、日志不保存完整 prompt 或 API Key

## 真实 LLM 选择

| Provider Profile | API Model | 主要作用 |
| --- | --- | --- |
| `qwen_long` | `qwen-long` | 长上下文小说语义解析、source trace 保真、原文证据抽取 |
| `kimi_creative` | `kimi-k2.6` | 改编规划、人物小传、场景扩写、对白自然度优化 |
| `deepseek_reasoning` | `deepseek-v4-pro` | 戏剧节拍推理、冲突/目标分析、源文忠实度复核、YAML 修复建议 |

当前 Agent 路由：

- `story_semantic_parser` -> `qwen_long`
- `adaptation_planner` -> `kimi_creative`
- `character_bible_agent` -> `kimi_creative`
- `scene_writer_agent` -> `kimi_creative`
- `dialogue_optimizer_agent` -> `kimi_creative`
- `beat_dramaturgy_agent` -> `deepseek_reasoning`
- `source_fidelity_reviewer` -> `qwen_long` + `deepseek_reasoning`
- `yaml_repair_agent` -> `deepseek_reasoning`

## API Key 配置

不要把 API Key 写入仓库、README、YAML、日志或命令参数。推荐使用本地
`.env` 文件或系统环境变量；仓库已通过 `.gitignore` 忽略 `.env` 和
`.env.*`，只允许提交不含真实密钥的 `.env.example`。

本地 `.env` 示例：

```powershell
Copy-Item .env.example .env
```

然后把 `.env` 里的占位符替换为你自己的 Key。也可以在当前 PowerShell
会话中临时配置：

```powershell
$env:N2S_QWEN_API_KEY="你的 Qwen Key"
$env:N2S_QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

$env:N2S_KIMI_API_KEY="你的 Kimi Key"
$env:N2S_KIMI_BASE_URL="https://api.moonshot.ai/v1"

$env:N2S_DEEPSEEK_API_KEY="你的 DeepSeek Key"
$env:N2S_DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

如需永久写入当前 Windows 用户环境，可以使用 `setx`，但不要把真实 Key
提交到 Git：

```powershell
setx N2S_QWEN_API_KEY "你的 Qwen Key"
setx N2S_KIMI_API_KEY "你的 Kimi Key"
setx N2S_DEEPSEEK_API_KEY "你的 DeepSeek Key"
```

## 快速开始

```powershell
python -m pytest
```

默认 dry-run 运行语义 Agent：

```powershell
python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out examples/output/generated_semantic_candidates.yaml `
  --run-log examples/output/generated_semantic_agent_run_log.yaml
```

显式调用真实 Qwen-Long：

```powershell
python -m novel2script.cli run-agent story-semantic-parser `
  --story-map examples/output/generated_story_map.yaml `
  --out temp/semantic_candidates.real.yaml `
  --run-log temp/semantic_agent_run_log.real.yaml `
  --allow-network
```

真实模型输出仍然是 sidecar 候选结果，不会直接修改 `story_map.yaml`。后续需要通过人工审核与合并流程决定是否接受候选项。

## 目录结构

```text
Novel2Script/
├── README.md
├── config/
├── docs/
├── examples/
├── schemas/
├── src/
└── tests/
```

## 关键文档

- `docs/product/COMPLETE_PRODUCT_PLAN.md`
- `docs/architecture/llm-provider.md`
- `docs/dev/PHASE_11_REAL_LLM_PROVIDER.md`
- `docs/blackboard/state.yaml`
- `docs/qa/report.md`
- `schemas/screenplay.schema.json`
- `schemas/semantic_candidates.schema.json`

## 安全边界

- 默认不联网，真实调用必须显式使用 `--allow-network`
- API Key 只从系统环境变量或本地 `.env` 读取
- `.env` 必须保持未跟踪状态，GitHub 只提交 `.env.example`
- 测试不能依赖真实 API Key 或真实网络
- run log 只保存 `prompt_hash`、token usage、latency、provider/model 等元数据
- 不保存完整 prompt、完整小说原文、完整模型响应或 bearer token
- LLM 结果默认是建议，不自动覆盖用户稿件或确定性解析结果

## 下一阶段

下一阶段建议实现 `semantic_candidates` 的人工审核与合并流程：让作者或产品操作者逐条接受/拒绝模型提出的语义候选项，并记录审批来源、时间、目标字段和 source trace。
