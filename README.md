# Novel2Script

Novel2Script 是一个面向小说作者的 AI 辅助剧本改编工具项目。项目的长期目标是把三章以上的小说文本转换为结构化 YAML 剧本初稿，并支持 YAML Schema 校验、多 Agent 审校、source_trace 追溯和 Fountain 导出。

当前仓库只完成第一阶段：本地项目初始化、文档体系建设、文件架构设计、样例文件和 GitHub 管理准备。这里没有接入真实 LLM，也没有实现完整小说解析、剧本生成、多 Agent 工作流、前端工作台或后端 API。

## 当前阶段范围

- 建立项目目录结构和开发边界。
- 提供产品、Schema、Agent、质量评估、路线图和 GitHub 管理文档。
- 提供初版 `screenplay.schema.json` 骨架。
- 提供自造小说输入样例、YAML 剧本样例、Fountain 样例和质量报告样例。
- 提供 Prompt 模板的职责、输入、输出和限制说明。
- 创建 Python 包占位目录，便于后续实现校验器、导出器和 Agent 编排。

## 未来核心能力

- 小说文本解析与章节、段落、人物、事件抽取。
- Scene + Beat + Element 结构化剧本生成。
- YAML Schema 校验与确定性质量检查。
- 多 Agent 审校，输出 patch 建议而不是直接覆盖用户稿件。
- source_trace 溯源，支持从剧本元素回查原文章节和段落。
- Fountain 导出，以及未来可控范围内的 Fountain 回写。
- 面向作者的可视化改编工作台。

## 目录结构

```text
Novel2Script/
├── README.md
├── LICENSE
├── .gitignore
├── docs/
├── schemas/
├── prompts/
├── examples/
├── src/
├── tests/
└── scripts/
```

## 快速开始

```bash
git clone https://github.com/joewangxxx/Novel2Script.git
cd Novel2Script
```

阅读顺序建议：

1. `docs/product/COMPLETE_PRODUCT_PLAN.md`
2. `docs/schema/YAML_SCHEMA_DESIGN.md`
3. `schemas/screenplay.schema.json`
4. `examples/README.md`
5. `docs/roadmap/DEVELOPMENT_ROADMAP.md`

## 当前不包含的功能

- 不包含真实 LLM API 调用。
- 不包含完整小说解析器。
- 不包含完整 `screenplay.yaml` 自动生成器。
- 不包含完整多 Agent 工作流。
- 不包含完整前端或后端服务。
- 不包含完整 Fountain 回写能力。

## 后续开发阶段

后续开发应先稳定 Schema 和样例，再实现确定性校验器与导出器，之后逐步接入小说解析、结构化生成、多 Agent 审校和可视化工作台。详细规划见 `docs/roadmap/DEVELOPMENT_ROADMAP.md`。
