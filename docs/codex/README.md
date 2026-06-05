# Codex Multi-Agent Setup

This repository is configured for a Codex workflow where the main parent thread acts as the Orchestrator and project-scoped specialists assist with bounded work.

## What This Setup Does

- Defines parent-thread orchestration rules in `AGENTS.md`.
- Defines seven project-scoped custom agents under `.codex/agents/`.
- Defines repository skills under `.agents/skills/`.
- Provides a single-writer blackboard at `docs/blackboard/state.yaml`.
- Defines artifact expectations for PRD, architecture, design, QA, and release work.

## What It Does Not Automate

- Codex does not automatically execute the state machine.
- Codex does not automatically read or write `docs/blackboard/state.yaml`.
- Subagents do not own the workflow.
- The parent thread must explicitly route work, wait for specialists, integrate results, enforce gates, and update the blackboard.

## Agents And Skills

Custom agents live in `.codex/agents/`:

- `pm`
- `architect`
- `designer`
- `fe`
- `be`
- `qa`
- `general`

Repository skills live in `.agents/skills/`:

- `prd-writer`
- `api-contract`
- `design-system`
- `qa-regression`
- `release-docs`

## Blackboard

`docs/blackboard/state.yaml` is the shared machine-readable state file.

Rules:

- The parent Orchestrator is the only writer.
- Specialists may read it.
- Specialists write their own artifacts.
- The parent summarizes specialist results and updates state.

## State Machine

Use these phases:

`intake -> prd -> architecture -> design -> implementation -> qa -> uat -> release`

Use `fast_path` only for small, scoped tasks where full PRD/architecture/design gates would add waste.

## Starting A New Task

1. The parent thread reads `AGENTS.md` and `docs/blackboard/state.yaml`.
2. The parent determines the current phase and needed specialists.
3. The parent routes narrowly scoped work to specialists.
4. Specialists produce artifacts and reports.
5. The parent reviews outputs, integrates results, updates the blackboard, and routes the next step.

## Worktrees For FE/BE Parallelism

Use git worktrees when frontend and backend implementation can proceed independently but may create conflicting changes:

```bash
git worktree add ../Novel2Script-fe feature/fe-task
git worktree add ../Novel2Script-be feature/be-task
```

Only use worktrees when the parent Orchestrator has defined disjoint write scopes.

## Retry Guard

Retry counts live in `docs/blackboard/state.yaml` under `retries` and `max_retries`.

If FE, BE, or QA exceeds its retry limit, stop and request human intervention instead of looping.

## Contract Change Requests

After contract freeze, FE/BE must not silently edit contracts.

Propose changes under:

`docs/architecture/change-requests/`

The Architect reviews the request, and the parent Orchestrator updates the blackboard if the contract state changes.

## Recovering From Context Loss

When context is lost:

1. Read `AGENTS.md`.
2. Read `docs/blackboard/state.yaml`.
3. Read the latest artifacts for the current phase.
4. Check `git status --short`.
5. Continue from repository state, not conversational memory.
