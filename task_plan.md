# Kimi Cross-Repository Audit And Repair Plan

## Goal

Audit the working Kimi K2.5 integration in `E:\health_ai_platform_2.0`,
compare it with Novel2Script's Kimi K2.6 creative-agent path, identify the
root cause of the current failure, implement the smallest tested repair, and
verify connectivity without retaining secrets or raw provider content.

## Constraints

- Follow `AGENTS.md`; the parent orchestrator owns integration and blackboard.
- Never print, copy, or persist API key values or Authorization headers.
- Do not modify the successful reference project.
- Subagents are read-only and have disjoint investigation scopes.
- Use TDD before production-code changes.
- Do not run the full creative drafter until a minimal provider probe passes.
- Do not retain prompts, raw model responses, or provider request/response bodies.
- Do not commit automatically.

## Phases

- [complete] Phase 1: Inventory both repositories and dispatch read-only audits.
- [complete] Phase 2: Reconstruct the successful Kimi K2.5 call chain.
- [complete] Phase 3: Reconstruct the Novel2Script Kimi K2.6 call chain.
- [complete] Phase 4: Compare code, dependencies, configuration, and official API behavior.
- [complete] Phase 5: Establish root cause and write failing regression tests.
- [complete] Phase 6: Implement the minimal provider/configuration repair.
- [complete] Phase 7: Run offline tests and one minimal authorized Kimi validation.
- [complete] Phase 8: Verify agent conversation, tool calling, and streaming capabilities where implemented.
- [complete] Phase 9: Produce final audit report and update QA/blackboard.

## Expected Files

- Modify as needed:
  - `src/novel2script/llm/openai_compatible_provider.py`
  - `src/novel2script/llm/router.py`
  - `src/novel2script/cli.py`
  - `tests/test_openai_compatible_provider.py`
  - `tests/test_llm_router.py`
  - `docs/qa/report.md`
  - `docs/blackboard/state.yaml`
- Create:
  - `docs/dev/PHASE_22_KIMI_CROSS_REPOSITORY_AUDIT.md`
  - a redacted probe report only if a real validation is executed

## Verification

- Focused provider/router tests.
- Creative readiness tests.
- Full pytest.
- YAML parsing checks.
- Secret and retention scans.
- `.env` ignore and git-status hygiene.
- Minimal real Kimi probe only after offline gates pass.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| `rg.exe` returned access denied when searching `E:\health_ai_platform_2.0` and dependency files | 1 | Switched to native PowerShell `Get-ChildItem` plus `Select-String`; do not repeat the same `rg` action |

# Stage 23 Real Kimi Creative Draft Plan

## Goal

Execute one authorized real Kimi creative drafter call, retain only schema-valid
redacted candidates, apply them to a new enhanced screenplay artifact, and run
the full QA chain.

## Phases

- [complete] Phase 1: Re-read repository rules, stage contracts, schemas, code,
  and source artifacts.
- [complete] Phase 2: Add TDD guard against repairing incomplete real model
  candidates.
- [complete] Phase 3: Run preflight gates and focused tests before the
  single real Kimi call.
- [complete] Phase 4: Execute exactly one real Kimi creative drafter call.
- [complete] Phase 5: Validate real candidates, target integrity, retention, and
  safety scan.
- [blocked] Phase 6: Apply accepted candidates to a new enhanced screenplay.
- [blocked] Phase 7: Run enhanced QA chain, schema validation, focused/full
  tests, security scan, and hash checks.
- [complete] Phase 8: Update QA report and blackboard.

## Stage 23 Result

- One real Kimi creative drafter call was executed.
- The call failed with provider/runtime `tls_error` at attempt 1 of 1.
- No retry, mock fallback, real sidecar, run log, enhanced screenplay, apply
  report, or enhanced QA artifact was retained.

# Stage 23R TLS Diagnostic And One-Shot Retry Plan

## Goal

Use the user's new authorization to diagnose the `tls_error` and execute one
additional real Kimi creative drafter attempt without retry or artifact leakage.

## Phases

- [complete] Phase 1: Re-read repository rules, current QA state, blackboard,
  and provider TLS error path.
- [complete] Phase 2: Run non-model DNS, TCP, TLS, urllib, Windows WebRequest,
  curl, and proxy diagnostics.
- [complete] Phase 3: Run preflight gates and confirm no stale real/enhanced
  artifacts.
- [complete] Phase 4: Execute exactly one real Kimi creative drafter attempt.
- [complete] Phase 5: Stop on repeated `tls_error`, confirm no artifacts, and
  run safety/hash checks.
- [complete] Phase 6: Update QA report, blackboard, and progress.

## Stage 23R Result

- TCP 443 to `api.moonshot.cn` succeeded.
- DNS resolved `api.moonshot.cn` to an Aliyun DDoS CNAME and IP `8.147.223.37`.
- Python OpenSSL handshake timed out.
- Python urllib failed with `UNEXPECTED_EOF_WHILE_READING`.
- Windows WebRequest and curl also failed before receiving HTTP headers.
- The one authorized real creative drafter retry failed with `tls_error` at
  attempt 1 of 1.
- No real sidecar, run log, enhanced screenplay, or apply report was retained.

# Stage 23V VPN Restored One-Shot Plan

## Goal

After the user enabled VPN access to `api.moonshot.cn`, verify terminal network
connectivity and execute one authorized real Kimi creative drafter attempt.

## Phases

- [complete] Phase 1: Verify Python/Windows/TCP HTTPS access to
  `api.moonshot.cn`.
- [complete] Phase 2: Run preflight gates and confirm no stale real/enhanced
  artifacts.
- [complete] Phase 3: Execute exactly one real Kimi creative drafter call.
- [complete] Phase 4: Stop on `finish_reason=length` and inspect only redacted
  run-log metadata.
- [blocked] Phase 5: Candidate validation, apply, enhanced QA, and Stage 24
  readiness.
- [complete] Phase 6: Update QA, blackboard, and safety evidence.

## Stage 23V Result

- Terminal HTTPS to `api.moonshot.cn` is restored.
- The one authorized real Kimi call reached the model.
- The model returned `finish_reason=length` after 1600 output tokens.
- Candidate count remained 0 because truncated output is rejected without parse
  or repair.
- No real candidates, enhanced screenplay, or apply report was generated.

# Stage 23W Kimi Prompt/Budget Repair Plan

## Goal

Repair the single-shot real Kimi creative drafter path so it can avoid
truncation and move toward schema-valid candidate output.

## Phases

- [complete] Phase 1: Add red tests for Kimi `thinking` extra body, router
  wiring, and 32768-token real creative budget.
- [complete] Phase 2: Implement provider `extra_body`, Kimi router
  `thinking: disabled`, and the larger real creative budget.
- [complete] Phase 3: Run focused and full tests.
- [complete] Phase 4: Clear stale Stage 23 outputs and run preflight.
- [complete] Phase 5: Execute exactly one real Kimi creative drafter call.
- [blocked] Phase 6: Candidate schema validation, apply, enhanced QA, and
  Stage 24 readiness.
- [complete] Phase 7: Tighten next-attempt prompt constraints offline and
  update QA/blackboard.

## Stage 23W Result

- The real call reached Kimi and returned `finish_reason=stop`.
- The previous truncation blocker was removed.
- The model output was rejected as `invalid_creative_draft_schema`.
- No real candidate sidecar, enhanced screenplay, or apply report was generated.
- A stricter exact-one-candidate prompt contract is now covered by tests for a
  future authorized attempt.

# Stage 23X Exact-One Real Kimi Candidate Plan

## Goal

Use the already tightened exact-one-candidate prompt for one more
human-authorized real Kimi creative drafter attempt and stop after candidate
generation validation.

## Phases

- [complete] Phase 1: Verify prompt/code/tests and clear stale Stage 23 outputs.
- [complete] Phase 2: Run HTTPS/preflight gates before the authorized one-shot.
- [complete] Phase 3: Execute exactly one real Kimi creative drafter call.
- [complete] Phase 4: Validate candidate schema, target integrity, run-log
  redaction, and output safety scan.
- [complete] Phase 5: Run full pytest and update QA/blackboard/progress.
- [pending] Phase 6: Apply to an enhanced screenplay only after separate human
  authorization.

## Stage 23X Result

- The real call reached Kimi and returned `finish_reason=stop`.
- The retained real Kimi sidecar contains exactly one schema-valid candidate.
- Target integrity checks passed with zero unresolved references.
- Output safety scan passed and retained run metadata is redacted.
- Full pytest passed at `165 passed`.
- Apply and enhanced QA were not run in this turn.

# Stage 23Y Real Kimi Apply And Enhanced QA Plan

## Goal

Apply the retained schema-valid real Kimi candidate to a new enhanced screenplay
artifact and run the full enhanced QA chain.

## Phases

- [complete] Phase 1: Apply the retained real Kimi candidate to
  `test1_sanguo_screenplay.enhanced.yaml`.
- [complete] Phase 2: Validate enhanced screenplay schema.
- [complete] Phase 3: Export enhanced Fountain and map.
- [complete] Phase 4: Generate enhanced review report.
- [complete] Phase 5: Import enhanced Fountain roundtrip and validate the
  roundtrip screenplay.
- [complete] Phase 6: Generate enhanced quality report and dashboard.
- [complete] Phase 7: Run required focused tests and full pytest.
- [complete] Phase 8: Run hash, metadata, and safety checks.
- [complete] Phase 9: Update QA, blackboard, and progress.

## Stage 23Y Result

- Apply succeeded with `applied_count=1`, `skipped_count=0`, and
  `blocked_count=0`.
- The original screenplay hash was preserved.
- Enhanced screenplay schema validation passed.
- Fountain export and roundtrip passed.
- Enhanced review report has no blocking issues.
- Enhanced quality readiness is `pass` with score 100 and decision
  `ready_for_author_review`.
- Focused and full tests passed.
- Safety scan passed.

# Stage 24A-D Four Kimi Creative Agents Plan

## Goal

Implement and execute four Kimi K2.6 creative Agents with prompt, schema,
sidecar, run log, CLI, tests, and AI/human-review markers.

## Phases

- [complete] Phase 1: Read repo rules, existing Kimi provider routing, and
  `kimi_dialogue_scene_drafter` implementation.
- [complete] Phase 2: Add failing tests for shared four-Agent sidecars,
  redacted run logs, CLI, and fake real-router behavior.
- [complete] Phase 3: Implement shared `kimi_creative_agents` runner and four
  schemas.
- [complete] Phase 4: Wire CLI commands for `adaptation-planner`,
  `character-bible-agent`, `scene-writer-agent`, and
  `dialogue-optimizer-agent`.
- [complete] Phase 5: Update the four prompt documents with implemented JSON
  contracts and retention policy.
- [complete] Phase 6: Run focused and full pytest.
- [complete] Phase 7: Execute one real Kimi K2.6 call per Agent.
- [complete] Phase 8: Validate schemas, run-log redaction, candidate policy,
  and safety scan.
- [complete] Phase 9: Update QA report, blackboard, and progress.

## Stage 24A-D Result

- All four Agents are implemented.
- All four real Kimi runs returned `finish_reason=stop`.
- Each Agent retained one schema-valid candidate.
- Every candidate is marked as AI-generated/inferred and requiring human
  approval.
- All run logs are redacted.
- Stage 24 output safety scan passed.
- Full pytest passed at `169 passed`.

# Stage 25 Stage 24 Candidate Review Plan

## Goal

Prepare human review and protected selective apply for Stage 24 real Kimi
candidate sidecars.

## Phases

- [complete] Phase 1: Inspect Stage 24 candidate artifacts and schema constraints.
- [complete] Phase 2: Add failing tests for review packet generation, pending
  decisions, and selective apply behavior.
- [complete] Phase 3: Implement `stage24_candidate_review` module.
- [complete] Phase 4: Add CLI commands for preparing review and applying
  decisions.
- [complete] Phase 5: Generate Stage 25 review packet and pending decisions
  template.
- [complete] Phase 6: Run protected selective apply with no accepted decisions.
- [complete] Phase 7: Run focused/full tests and safety scan.
- [complete] Phase 8: Update QA, blackboard, progress, and task plan.

## Stage 25 Result

- Author review packet generated.
- Decisions template generated with 4 pending decisions.
- Protected selective apply generated a selected-candidates sidecar with zero
  selected candidates.
- Apply report status is `blocked_pending_author_review`.
- No source artifact was modified.
- Full pytest passed at `173 passed`.
- Safety scan passed.

## Stage 25 Accepted Selection Result

- User instructed the system to proceed to the next operation.
- All 4 Stage 24 candidate decisions were marked `accept`.
- `reviewed_by` was set to `human_author_via_user_instruction`.
- Selective apply was rerun.
- Selected candidates sidecar now contains 4 accepted candidates.
- Apply report status is `success`.
- No source artifact was modified.
- Full pytest passed at `173 passed`.
- Safety scan passed.

# Stage 26 Apply Selected Candidates Plan

## Goal

Apply the four selected Stage 24 Kimi candidates to new downstream artifacts
without mutating the original outline, character bible, or screenplay.

## Phases

- [complete] Phase 1: Inspect selected candidates and target schema-safe apply
  points.
- [complete] Phase 2: Add failing tests for Stage 26 apply.
- [complete] Phase 3: Implement Stage 26 apply module and CLI.
- [complete] Phase 4: Generate new Stage 26 outline, character bible, and
  screenplay artifacts.
- [complete] Phase 5: Validate schemas, safety scan, focused tests, and full
  pytest.
- [complete] Phase 6: Update QA, blackboard, progress, and task plan.

## Stage 26 Result

- Applied 4 selected candidates.
- Generated schema-valid Stage 26 outline, character bible, and screenplay.
- Generated Stage 26 apply report with status `success`.
- Preserved original artifacts.
- Full pytest passed at `174 passed`.
- Safety scan passed.

# Stage 27 Stage 26 QA And Author Review Package Plan

## Goal

Run the full QA loop on the Stage 26 screenplay artifacts and package the
result for the next human author-review decision step.

## Phases

- [complete] Phase 1: Validate the Stage 26 screenplay schema.
- [complete] Phase 2: Export the Stage 26 screenplay to Fountain and map.
- [complete] Phase 3: Generate the Stage 26 review report.
- [complete] Phase 4: Import Fountain roundtrip and validate the roundtrip
  screenplay.
- [complete] Phase 5: Generate the Stage 26 quality report and dashboard.
- [complete] Phase 6: Generate the Stage 26 author-review packet and decisions
  template.
- [complete] Phase 7: Validate schemas, run focused/full tests, safety scan,
  and update QA/blackboard/progress.

## Stage 27 Result

- Stage 26 screenplay validation passed.
- Fountain export and roundtrip passed.
- Stage 26 review, quality report, and quality dashboard were generated.
- Stage 26 author-review packet and decisions template were generated.
- Quality readiness is `pass` with score 98 and decision
  `ready_for_author_review`.
- Focused tests passed at `11 passed`.
- Full pytest passed at `174 passed`.
- Stage 27 safety scan passed.

# Stage 28 Author Review Decision Entry Plan

## Goal

Record the human author-review decision entry for the Stage 26 package and
produce a schema-valid author review report for the next stage boundary.

## Phases

- [complete] Phase 1: Inspect Stage 27 author-review packet and decisions
  template.
- [complete] Phase 2: Record the user's proceed instruction as the Stage 26
  author-review decision entry.
- [complete] Phase 3: Generate a schema-valid Stage 26 author review report.
- [complete] Phase 4: Validate author-review schemas, run safety checks, and
  update QA/blackboard/progress.

## Stage 28 Result

- Stage 26 package author-review decisions were recorded under
  `human_author_via_user_instruction`.
- Stage 26 author review report was generated.
- Structure, character, beat, and quality decisions are approved.
- Dialogue drafting is requested.
- Future Kimi dialogue draft planning is authorized, but no LLM call was made.

# Stage 29 Kimi Dialogue Draft Planning Plan

## Goal

Prepare the Stage 26 package for a future one-shot real Kimi dialogue draft run
without making a network call.

## Phases

- [complete] Phase 1: Inspect Stage 28 author review authorization and the
  existing Kimi dialogue drafter contract.
- [complete] Phase 2: Run the Kimi dialogue scene drafter dry-run against the
  Stage 26 package.
- [complete] Phase 3: Validate mock candidate schema, target integrity, and
  run-log retention flags.
- [complete] Phase 4: Write the Stage 29 plan and planning report.
- [complete] Phase 5: Update QA, blackboard, progress, run safety checks, and
  verify tests.

## Stage 29 Result

- Generated Stage 26 mock creative draft candidates and a redacted dry-run log.
- Mock candidates are schema-valid and target-valid.
- No real LLM provider call was made.
- Future Stage 30 real Kimi run policy is documented and requires explicit
  network authorization.

# Stage 30 One-Shot Real Kimi Dialogue Draft Plan

## Goal

Execute one authorized real Kimi dialogue drafter call for the Stage 26 package
and retain only schema-valid candidates plus a redacted run log.

## Phases

- [complete] Phase 1: Run Stage 30 preflight gates.
- [complete] Phase 2: Execute exactly one real Kimi dialogue drafter call.
- [complete] Phase 3: Validate candidate schema, target integrity, run-log
  redaction, and safety.
- [complete] Phase 4: Update QA, blackboard, progress, and run focused/full
  verification.

## Stage 30 Result

- One real Kimi call was executed.
- Kimi returned `finish_reason=stop`.
- One schema-valid and target-valid candidate was retained.
- The run log is redacted.
- No retry, fallback, source mutation, or apply step occurred.

# Stage 31 Human Review Real Kimi Dialogue Candidate Plan

## Goal

Record the human review decision for the one retained Stage 30 real Kimi
dialogue candidate without applying it.

## Phases

- [complete] Phase 1: Inspect Stage 30 candidate reviewability.
- [complete] Phase 2: Generate Stage 31 review packet, decisions, and report.
- [complete] Phase 3: Update QA, blackboard, progress, and run verification.

## Stage 31 Result

- One Stage 30 real Kimi candidate was accepted by
  `human_author_via_user_instruction`.
- The candidate remains in its original sidecar.
- No screenplay was modified.
- No apply step occurred.
- Stage 32 is ready to plan a protected apply into a new screenplay artifact.
