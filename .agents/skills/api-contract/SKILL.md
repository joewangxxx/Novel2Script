---
name: api-contract
description: Create or update API contracts, data model notes, and contract change requests for Novel2Script.
---

# API Contract

Use this skill when the parent Orchestrator routes architecture or contract work.

## Inputs

- `docs/prd/PRD.md`.
- `schemas/screenplay.schema.json`.
- Existing `docs/architecture/` artifacts.

## Instructions

- Define the API contract in `docs/architecture/api.yaml` or a stack-appropriate equivalent.
- Document data model and schema decisions in `docs/architecture/schema.md`.
- Document folder and ownership implications in `docs/architecture/folder-plan.md`.
- If the contract is already frozen, propose changes under `docs/architecture/change-requests/`.
- Do not implement application code.

## Outputs

- API contract artifact.
- Schema/data model artifact.
- Folder/ownership plan.
- Optional contract change request.
