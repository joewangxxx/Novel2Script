---
name: qa-regression
description: Run and document regression checks, failing commands, likely owners, and quality gate outcomes for Novel2Script.
---

# QA Regression

Use this skill when the parent Orchestrator routes QA verification.

## Inputs

- `docs/blackboard/state.yaml`.
- `docs/architecture/` artifacts.
- `pyproject.toml`, package files, or detected test configuration.
- Existing `docs/qa/report.md`, if present.

## Instructions

- Run the repository's actual lint, test, integration, and smoke commands.
- Record commands, outcomes, failures, tests not run, and reasons.
- For each defect, include owner, reproduction steps, failing command, likely files, and suggested next route.
- Do not update `docs/blackboard/state.yaml`.
- Do not implement fixes unless the parent explicitly routes a narrow fix.

## Outputs

- `docs/qa/report.md`.
