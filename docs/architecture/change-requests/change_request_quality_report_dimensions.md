# 架构变更申请：剧本质量报告Schema升级

## 1. 背景与上下文 (Context)
在当前版本的 `Novel2Script` 剧本质量评估中，完全缺少真实大模型（LLM）的打分维度，这限制了自动评估对戏剧性指标（如对白自然度、角色目标清晰度、戏剧冲突强度）的精准衡量。因此，需要升级质量报告契约，以容纳来自真实 LLM 的智能打分信息。

## 2. 拟议变更 (Proposed Change)
在 `schemas/quality_report.schema.json` 中：
1. 在 `dimension_id` 枚举值中加入 `"character_goal_clarity"` (角色目标清晰度) 和 `"dramatic_conflict_intensity"` (戏剧冲突强度)。
2. 在 `evidence_source` 枚举值中加入 `"llm_evaluation"` 作为合法的打分证据来源。
3. 将质量指标列表的 `minItems` 约束从 `11` 调整为 `13`。

## 3. 受影响的产物 (Affected Artifacts)
- `schemas/quality_report.schema.json`
- `docs/blackboard/state.yaml` (需同步更新契约冻结哈希)
- `src/novel2script/quality/quality_report.py`

## 4. 后端影响 (BE Impact)
- 质量评估报告生成程序将同步输出 13 个评估维度，并在 `evaluate-quality` 与一键流水线 `run-pipeline` 阶段调用新打分器收集 LLM 评分。

## 5. 前端与可视化工作台影响 (FE Impact)
- 可视化仪表盘 (Dashboard) 将能展示 3 个 LLM 专属的打分维度及详细推理说明。

## 6. 测试与质量保障影响 (QA Impact)
- 新增 `tests/test_quality_llm_eval.py` 测试打分器。
- 原有确定性评估测试做向下兼容保留，不需要网络或大模型打分参数的旧测试能够降级并照常运行。
