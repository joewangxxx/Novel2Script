# GitHub 管理规范

## 分支策略

- `main` 保持可阅读、可演示和文档完整。
- 功能开发使用 `feature/<short-name>`。
- 修复使用 `fix/<short-name>`。
- 文档调整使用 `docs/<short-name>`。
- 大型实验使用 `experiment/<short-name>`，合并前必须整理为稳定实现。

## Commit 规范

建议使用简化 Conventional Commits：

- `chore:` 项目结构、工具、依赖和非业务变更。
- `docs:` 文档。
- `feat:` 新功能。
- `fix:` 修复。
- `test:` 测试。
- `refactor:` 不改变行为的结构调整。

初始提交建议：

```bash
git commit -m "chore: initialize Novel2Script project structure"
```

## Issue 类型

- `schema`：数据结构、字段和校验规则。
- `validator`：确定性校验器。
- `exporter`：Fountain 或其他格式导出。
- `agent`：Agent 职责、Prompt 和审校流程。
- `docs`：文档补充。
- `sample`：样例文本和样例输出。
- `privacy`：用户文本隐私和数据处理。

## PR 模板建议

PR 描述建议包含：

- 本次修改内容。
- 为什么需要修改。
- 影响范围。
- 验证方式。
- 是否涉及用户文本或隐私数据。
- 是否新增或修改样例。

## 安全与隐私

- 不提交 `.env`、API Key、访问令牌或本地凭据。
- 用户上传的小说文本默认属于隐私数据。
- 私有测试稿件应放在被 `.gitignore` 排除的目录。
- 公开样例文本必须自造、获得授权或确认可公开使用。
- 不在 issue、PR、commit message 中粘贴用户私密原文。

## 远程仓库

目标仓库：

```text
https://github.com/joewangxxx/Novel2Script.git
```

如果本地已经有 `origin`，先检查：

```bash
git remote -v
```

如果地址不正确，再更新：

```bash
git remote set-url origin https://github.com/joewangxxx/Novel2Script.git
```
