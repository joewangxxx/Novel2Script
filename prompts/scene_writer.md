# Scene Writer Prompt Template

## 职责

根据改编计划和角色圣经生成结构化 YAML 场景初稿。

## 输入

- 场景规划。
- 角色圣经。
- 原文片段。
- YAML Schema 约束。

## 输出

- Scene。
- Beat。
- Element。
- `source_trace`。
- `ai_tags`。

## 限制

- 不调用真实模型接口。
- 不生成无法追溯的关键剧情。
- 心理描写必须尽量外化为可拍摄行动。
- 低置信推断必须标记 `needs_human_review`。
