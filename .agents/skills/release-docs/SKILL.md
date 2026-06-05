---
name: release-docs
description: Prepare release notes, deployment notes, environment gotchas, and handoff documentation for Novel2Script.
---

# Release Docs

Use this skill when the parent Orchestrator routes release or deployment documentation work.

## Inputs

- `docs/qa/report.md`.
- `docs/architecture/` artifacts.
- README and existing `docs/release/` artifacts.
- Git history or change summary supplied by the parent.

## Instructions

- Create or update release notes and deployment notes under `docs/release/`.
- Document environment variables, setup caveats, deployment assumptions, and rollback notes.
- Keep docs clear for a maintainer who did not participate in implementation.
- Do not ship product changes or update the blackboard directly.

## Outputs

- Release README or release notes.
- Deployment notes.
- Environment gotchas.
