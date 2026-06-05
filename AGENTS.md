# Codex Multi-Agent Workflow

This repository is configured for a parent-thread-orchestrated Codex workflow.

## Main Thread Role

The main Codex parent thread is the Orchestrator. It routes work, enforces gates, waits for specialists, integrates results, and is the only writer of `docs/blackboard/state.yaml`.

The parent should avoid direct application code edits unless the user explicitly switches to single-agent mode or an emergency fix requires it.

Do not create or use a separate orchestrator custom agent.

## State Machine

Use these phases:

- `intake`
- `prd`
- `architecture`
- `design`
- `implementation`
- `qa`
- `uat`
- `release`
- `fast_path` for small scoped tasks

## Routing Rules

- PM owns PRD, stories, acceptance criteria, UAT, and final business acceptance.
- Architect owns API contract, data design, integration notes, technical blueprint, contract freeze, and change request review.
- Designer owns UI prompt, design tokens, component states, and interaction notes.
- FE owns frontend implementation and frontend-relevant tests.
- BE owns backend implementation, migrations, and backend-relevant tests.
- QA owns lint, unit/integration verification, defect reports, and regression checks.
- General owns docs, deployment notes, CI/CD notes, environment gotchas, and targeted research.

## Hard Gates

- FE/BE cannot start full implementation until contract artifacts exist or the parent explicitly chooses prototype/mock mode.
- After contract freeze, FE/BE must not silently edit the contract.
- Contract changes after freeze must be proposed under `docs/architecture/change-requests/`.
- QA cannot start until implementation artifacts exist.
- UAT cannot start until QA passes.
- If FE/BE/QA exceed retry limits, stop and request human intervention.

## Parallelism Rules

- Spawn subagents only when the user explicitly asks for agent, delegation, or parallel work, or when repository rules require it.
- Parallel agents must have disjoint write scopes.
- FE/BE parallel work should use worktrees when a change is large or likely to conflict.
- The parent thread must wait for relevant agents, review outputs, then integrate.

## Artifact Expectations

Use stack-appropriate names, but maintain human-readable artifacts for:

- PRD: `docs/prd/PRD.md`
- UAT: `docs/qa/UAT.md`
- API contract: `docs/architecture/api.yaml` or stack-equivalent
- Schema/data model: `docs/architecture/schema.md`
- Design notes/tokens when UI is involved: `docs/design/`
- QA report: `docs/qa/report.md`
- Release/deployment notes: `docs/release/`

## Operational Rules

- Only the parent thread writes `docs/blackboard/state.yaml`.
- Specialists may read the blackboard and write their own artifacts.
- Specialists keep changes minimal and avoid unrelated files.
- Prefer repo files and artifacts over long conversational memory.
- Use OpenAI developer documentation MCP first for OpenAI API, ChatGPT, Codex, Apps SDK, or MCP questions.
- Keep internet usage least-privilege and document assumptions.
- Close or stop using subagents once their task is done.
