# Manual Codex App Steps

Some workflow setup cannot be fully completed by repository files alone.

## Required

- Trust this project in Codex so project-scoped config and agent files can load.
- Confirm that the active workspace is the intended repository path.
- Review `.codex/config.toml` before relying on project-scoped defaults.
- Review MCP access for `openaiDeveloperDocs`.

## Recommended

- Move the repository to an English-only path if path encoding problems appear in scripts or tooling.
- Review whether worktrees should be used for large FE/BE parallel implementation.
- Review internet allowlist and least-privilege browsing expectations.
- Optionally create recurring automations for periodic QA or release checks in the Codex App.

## Not Automated

- The state machine does not execute by itself.
- The blackboard is not automatically updated.
- Subagents are not autonomous workflow owners.
- The parent Orchestrator must explicitly route and integrate work.
