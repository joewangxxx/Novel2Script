---
name: prd-writer
description: Write or update project PRDs, user stories, acceptance criteria, edge cases, and non-goals for Novel2Script.
---

# PRD Writer

Use this skill when the parent Orchestrator routes product definition work.

## Inputs

- User request or project goal.
- `docs/product/COMPLETE_PRODUCT_PLAN.md`.
- `docs/blackboard/state.yaml`.
- Existing `docs/prd/PRD.md`, if present.

## Instructions

- Define the problem, target users, scope, non-goals, user stories, acceptance criteria, and UAT notes.
- Keep PRD language testable and implementation-neutral.
- Do not choose API shapes, database schemas, or UI implementation details.
- Preserve existing PRD content and patch minimally.

## Outputs

- `docs/prd/PRD.md`.
- Related UAT updates in `docs/qa/UAT.md` when appropriate.
