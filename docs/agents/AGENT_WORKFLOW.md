# Agent 工作流设计

## 总体原则

Novel2Script 未来会使用多个 Agent 协助完成小说改编，但 Agent 不应拥有无限制写入权。生成型 Agent 可以产出初稿，审校型 Agent 只能输出 patch 建议，最终是否接受修改由用户或确定性工具链决定。

## 角色分层

| 类型 | 角色 | 输入 | 输出 | 职责 | 边界 |
| --- | --- | --- | --- | --- | --- |
| 生成型 Agent | Story Parser | 小说章节文本 | 结构化故事摘要 | 抽取角色、事件、地点、关系和时间线 | 不生成最终剧本 |
| 生成型 Agent | Adaptation Planner | 故事摘要、改编策略 | 场景规划和角色弧线建议 | 决定哪些内容场景化、压缩或合并 | 不直接写完整对白 |
| 生成型 Agent | Character Bible Builder | 故事摘要、人物线索 | 角色圣经草案 | 统一人物目标、关系、说话方式和秘密 | 不覆盖作者原设定 |
| 生成型 Agent | Scene Writer | 场景规划、角色圣经、原文片段 | YAML 场景和 Beat 初稿 | 生成可拍摄场景结构 | 必须写入 source_trace 和 ai_tags |
| 审校型 Agent | Character Consistency Reviewer | YAML 剧本、角色圣经 | patch 建议 | 检查人物动机、称谓和行为一致性 | 不直接改写稿件 |
| 审校型 Agent | Pacing Reviewer | YAML 剧本 | patch 建议 | 检查节奏、信息密度和转折清晰度 | 不重排全部结构 |
| 审校型 Agent | Dialogue Naturalness Reviewer | YAML 剧本、人物语气说明 | patch 建议 | 检查对白自然度和角色区分度 | 不替作者定稿 |
| 确定性工具 | Schema Validator | YAML 剧本、JSON Schema | 校验报告 | 检查字段、类型、必填项和枚举 | 不做创意判断 |
| 确定性工具 | Fountain Exporter | YAML 剧本 | Fountain 文件 | 导出标准剧本文本 | 不修改主数据 |

## 推荐流程

1. Story Parser 解析小说章节。
2. Adaptation Planner 生成改编计划。
3. Character Bible Builder 生成角色圣经草案。
4. Scene Writer 生成结构化 YAML 初稿。
5. Schema Validator 做确定性校验。
6. 审校型 Agent 分别输出 patch 建议。
7. 用户审阅并接受或拒绝 patch。
8. Fountain Exporter 从最终 YAML 导出 Fountain。

## Patch 建议原则

审校型 Agent 的输出应类似：

```yaml
patches:
  - target_path: "scenes[0].beats[1].dialogue[0]"
    reason: "对白与角色此前的谨慎性格不一致。"
    suggestion: "将直接质问改为试探性提问。"
    risk: "medium"
```

这种方式能避免 AI 在用户不知情的情况下覆盖稿件，也便于后续实现变更记录、差异对比和人工确认。
