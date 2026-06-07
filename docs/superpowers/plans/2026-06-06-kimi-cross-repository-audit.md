# Kimi Cross-Repository Audit And Repair Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive Novel2Script's Kimi K2.6 integration from the proven local K2.5 implementation, repair the verified incompatibility, and validate the creative-agent provider path safely.

**Architecture:** Treat `E:\health_ai_platform_2.0` as a read-only reference implementation. Reconstruct both call chains, compare configuration and wire payloads, then change only Novel2Script through TDD. Keep real validation separate from creative generation and retain redacted metadata only.

**Tech Stack:** Python 3.11, pytest, OpenAI-compatible chat completions, local dotenv configuration, YAML QA artifacts.

---

### Task 1: Audit The Successful Kimi K2.5 Integration

**Files:**
- Read only: `E:\health_ai_platform_2.0`
- Update findings: `findings.md`

- [ ] Locate environment/config files without printing secret values.
- [ ] Locate Kimi client construction and model selection.
- [ ] Trace startup, agent creation, prompt, memory, tools, streaming, and response handling.
- [ ] Record exact file/function/line references and a textual sequence diagram.

### Task 2: Audit Novel2Script Kimi K2.6

**Files:**
- Read: `src/novel2script/llm/openai_compatible_provider.py`
- Read: `src/novel2script/llm/router.py`
- Read: `src/novel2script/agents/creative_draft.py`
- Read: `src/novel2script/cli.py`
- Update findings: `findings.md`

- [ ] Trace configuration loading and router construction.
- [ ] Trace request payload creation and response parsing.
- [ ] Trace creative-agent prompt/context construction.
- [ ] Identify absent or unsupported streaming/tool-calling behavior.

### Task 3: Compare Against Current Official Kimi Behavior

**Files:**
- Update findings: `findings.md`

- [ ] Verify current official base URLs, model names, and SDK examples.
- [ ] Verify JSON mode, streaming, tool-calling, token, and retry expectations.
- [ ] Separate documented facts from source-based inference.

### Task 4: Write Failing Regression Tests

**Files:**
- Modify: `tests/test_openai_compatible_provider.py`
- Modify: `tests/test_llm_router.py`

- [ ] Write tests reproducing the reference project's successful request shape.
- [ ] Add tests for endpoint selection and optional unsupported parameters.
- [ ] Run focused tests and confirm the new tests fail for the intended reason.

### Task 5: Implement Minimal Repair

**Files:**
- Modify: `src/novel2script/llm/openai_compatible_provider.py`
- Modify: `src/novel2script/llm/router.py`
- Modify: `src/novel2script/cli.py` only if required

- [ ] Implement only the confirmed compatibility fix.
- [ ] Keep key normalization and redacted diagnostics intact.
- [ ] Run focused tests until green.

### Task 6: Offline Verification

**Files:**
- Update: `progress.md`

- [ ] Run provider/router tests.
- [ ] Run creative readiness tests.
- [ ] Run full pytest.
- [ ] Run secret/retention scans.

### Task 7: Minimal Real Validation

**Files:**
- Create a redacted probe report under `examples/output/` only if executed.

- [ ] Confirm explicit authorization remains applicable.
- [ ] Run one minimal request with no retry.
- [ ] Retain metadata only.
- [ ] Stop immediately on failure.

### Task 8: Documentation And Closeout

**Files:**
- Create: `docs/dev/PHASE_22_KIMI_CROSS_REPOSITORY_AUDIT.md`
- Modify: `docs/qa/report.md`
- Modify: `docs/blackboard/state.yaml`

- [ ] Document both call chains and ranked issue list.
- [ ] Document exact changes and verification evidence.
- [ ] State separately whether connectivity, conversation, tools, and streaming were verified.
