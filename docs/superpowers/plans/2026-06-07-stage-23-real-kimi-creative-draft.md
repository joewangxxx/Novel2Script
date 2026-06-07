# Stage 23 Real Kimi Creative Draft Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run exactly one real Kimi creative drafter call, retain only schema-valid redacted candidates, apply them to a new enhanced screenplay, and complete the QA chain.

**Architecture:** The parent orchestrator owns gates, network execution, artifact validation, and blackboard updates. Existing `kimi_dialogue_scene_drafter` writes a redacted sidecar only after model output is accepted; `apply_creative_draft` creates a separate enhanced screenplay without mutating the source.

**Tech Stack:** Python CLI, PyYAML, jsonschema, Novel2Script LLM router/provider.

---

## Files

- Modify: `src/novel2script/agents/creative_draft.py`
- Modify: `tests/test_creative_draft_agent.py`
- Modify: `docs/qa/report.md`
- Modify: `docs/blackboard/state.yaml`
- Create: `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml` only if schema-valid
- Create: `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml` only with redacted metadata
- Create: enhanced screenplay and QA artifacts only after candidate gates pass

## Tasks

- [x] Read repository rules, stage contracts, schemas, code, and source artifacts.
- [x] Add and verify a TDD guard so incomplete real model candidates fail closed instead of being repaired.
- [ ] Run Stage 23 preflight gates: Stage 22 equivalent success, key present, `.env` ignored, author authorization, mock schema/targets, readiness hashes, and stale artifact absence.
- [ ] Run required focused tests before the network call.
- [ ] Execute exactly one real `kimi-dialogue-scene-drafter --allow-network` call with `max_attempts=1`.
- [ ] Stop on provider/runtime failure, `finish_reason=length`, schema invalidity, zero candidates, or failed safety scan.
- [ ] Validate accepted real candidates and target integrity.
- [ ] Apply candidates to `test1_sanguo_screenplay.enhanced.yaml`.
- [ ] Run enhanced screenplay validation, Fountain export, review, roundtrip, roundtrip validation, and quality evaluation.
- [ ] Run required focused tests and full pytest.
- [ ] Validate all requested schemas and run safety/hash/git hygiene scans.
- [ ] Update QA report and blackboard.

## Failure Policy

- No retry and no mock fallback.
- No raw prompt, raw response, provider body, API key, bearer token, Authorization header, or full novel text retention.
- Delete any noncompliant real artifact if safety scanning fails.
