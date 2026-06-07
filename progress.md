# Kimi Cross-Repository Audit Progress

## 2026-06-06

- Started parent-orchestrated cross-repository audit.
- Loaded repository multi-agent rules and process skills.
- Created persistent task plan and findings log.
- No API calls have been made as part of this new audit yet.
- Spawned three read-only explorer agents for the successful project,
  Novel2Script, and dependency/compatibility comparison.
- `rg.exe` was blocked by Windows access control in the E-drive project;
  switched to native PowerShell search.
- After context transition, earlier explorer agent handles were unavailable;
  continuing the audit locally from the discovered file references.

## Test Results

- `python -m pytest tests/test_openai_compatible_provider.py::test_kimi_provider_omits_json_mode_for_moonshot_compatibility tests/test_llm_router.py::test_router_from_environment_registers_selected_chinese_model_profiles -q`
  failed before implementation, then passed at `2 passed`.
- `python -m pytest tests/test_openai_compatible_provider.py tests/test_llm_router.py tests/test_creative_draft_real_readiness.py -q`
  passed at `39 passed`.
- One minimal real Kimi probe using `.cn` and no provider JSON mode returned
  HTTP 400 `invalid_request`; no retry or raw artifact retention.
- One minimal real Kimi probe using `.cn`, no provider JSON mode, and no
  temperature reached the provider and received a model response. The probe did
  not retain raw text and failed only at strict JSON acceptance.
- `python -m pytest` passed at `163 passed`.

## Files Modified

- `task_plan.md`
- `findings.md`
- `progress.md`
- `src/novel2script/llm/openai_compatible_provider.py`
- `src/novel2script/llm/router.py`
- `tests/test_openai_compatible_provider.py`
- `tests/test_llm_router.py`
- `tests/test_creative_draft_agent.py`
- `docs/dev/PHASE_22_KIMI_CROSS_REPOSITORY_AUDIT.md`
- `examples/output/test1_sanguo_kimi_probe_cn_compat_payload_report.yaml`

## 2026-06-07 Stage 23

- Re-read Stage 17/18/19 contracts, schemas, creative draft/apply/readiness code,
  router/provider code, CLI, and source artifacts.
- Added a TDD guard so incomplete real Kimi model candidates fail closed instead
  of being repaired into schema-valid candidates.
- Preflight gates passed: Stage 22D equivalent provider response, key present,
  `.env` ignored, `.cn` base URL, author authorization, mock schema/targets,
  readiness, source hashes, and no stale Stage 23 artifacts.
- Focused tests passed before the real call: `27 passed`.
- Full pytest passed before the real call: `164 passed`.
- Executed exactly one real `kimi-dialogue-scene-drafter --allow-network` call.
- The call failed with provider/runtime `tls_error` at attempt 1 of 1.
- No retry, mock fallback, real candidates, run log, enhanced screenplay, apply
  report, or enhanced QA artifacts were generated or retained.
- Post-failure security scan passed and source hashes remained unchanged.

## 2026-06-07 Stage 23R

- Re-read current blackboard and QA state plus provider TLS classification code.
- Ran non-model diagnostics against `api.moonshot.cn`:
  - DNS resolved to `rp68jmko8a6qpuee.aliyunddos1022.com` / `8.147.223.37`.
  - TCP 443 succeeded.
  - Python OpenSSL handshake timed out.
  - Python urllib failed with TLS unexpected EOF.
  - Windows WebRequest timed out.
  - curl did not receive headers before timeout.
  - no proxy environment variable was present.
- Preflight gates passed without printing or storing the Kimi key.
- Executed exactly one user-authorized real Kimi creative drafter retry.
- Retry failed with `tls_error` at attempt 1 of 1.
- No retry, mock fallback, real sidecar, run log, enhanced screenplay, or apply
  report was retained.
- Post-failure hash and security checks passed.

## 2026-06-07 Stage 23V

- User enabled VPN access to `api.moonshot.cn` and authorized one more real Kimi
  creative drafter attempt.
- Verified terminal-level connectivity:
  - Python urllib root endpoint returned HTTP 200.
  - Python urllib `/v1/models` returned HTTP 401 without an API key.
  - Windows WebRequest root endpoint returned HTTP 200.
  - TCP 443 succeeded.
- Preflight gates passed and no stale real/enhanced artifacts existed.
- Executed exactly one real `kimi-dialogue-scene-drafter --allow-network` call.
- The call reached Kimi and failed closed with `finish_reason=length`,
  `output_tokens=1600`, `candidate_count=0`, and `truncated_model_output`.
- No retry, mock fallback, real candidate sidecar, enhanced screenplay, or apply
  report was generated.
- Retained only the redacted run log metadata allowed by Stage 23.

## 2026-06-07 Stage 23W

- Added failing tests for:
  - Kimi provider `extra_body` merge with `thinking: disabled`.
  - Router wiring of Kimi `extra_body`.
  - Real creative drafter max token budget of 32768.
- Implemented the provider/router/creative budget repair.
- Focused Stage 23W suite passed at `58 passed`.
- Full pytest passed at `165 passed`.
- Verified terminal HTTPS to `api.moonshot.cn` and cleared stale Stage 23
  outputs before the real call.
- Executed exactly one real Kimi creative drafter call.
- The call reached `finish_reason=stop` with usage 319 input, 838 output, 1157
  total tokens, but failed closed with `invalid_creative_draft_schema`.
- No retry, mock fallback, real candidate sidecar, enhanced screenplay, or apply
  report was generated.
- Added an offline prompt tightening test and implementation for a future
  exact-one-candidate authorized attempt.

## 2026-06-07 Stage 23X

- User authorized one more one-shot real Kimi creative drafter attempt using the
  tightened exact-one-candidate prompt.
- Cleared stale Stage 23 real/enhanced outputs before the call.
- Preflight passed:
  - terminal HTTPS root endpoint returned HTTP 200.
  - `/v1/models` without a key returned HTTP 401 as expected.
  - Kimi key present without printing or retaining the key.
  - `.env` remained Git ignored.
  - focused provider/router/creative tests passed at `40 passed`.
- Executed exactly one real `kimi-dialogue-scene-drafter --allow-network` call.
- The call exited 0 with `finish_reason=stop`, usage 491 input tokens, 178
  output tokens, and 669 total tokens.
- Retained one real Kimi candidate sidecar and one redacted run log.
- Creative candidate schema validation passed with 0 schema errors.
- Candidate target integrity passed with 0 unresolved target errors.
- Output artifact safety scan passed; no API key, bearer token value,
  Authorization header value, raw response value, provider body value, prompt
  retention, or `.env` key assignment was found.
- Full pytest passed at `165 passed`.
- Apply and enhanced QA were not run because this turn only authorized the
  one-shot generation attempt.

## 2026-06-07 Stage 23Y

- User authorized applying the retained real Kimi candidate to a new enhanced
  screenplay and running the full enhanced QA chain.
- Applied `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`
  to `examples/output/test1_sanguo_screenplay.enhanced.yaml`.
- Apply report passed integrity checks:
  - `applied_count=1`.
  - `skipped_count=0`.
  - `blocked_count=0`.
  - `preserved_original_screenplay=true`.
  - source screenplay hash unchanged.
  - enhanced screenplay hash recorded.
- The applied creative element includes source trace, trace IDs, AI tags,
  candidate ID, author approval requirement, and `provider_profile:
  kimi_creative`.
- Ran enhanced validation, Fountain export, enhanced review, Fountain import
  roundtrip, roundtrip validation, and quality evaluation.
- Schema validation passed for real candidates, enhanced screenplay, enhanced
  roundtrip screenplay, enhanced review report, enhanced roundtrip report, and
  enhanced quality report.
- Enhanced quality readiness is `pass`, score 100, decision
  `ready_for_author_review`, with no hard gate failures.
- Focused tests passed:
  - creative draft agent/CLI: `12 passed`.
  - creative draft apply: `5 passed`.
  - real readiness: `10 passed`.
- Full pytest passed at `165 passed`.
- Stage 23 output safety scan passed with no API key, bearer token value,
  Authorization header value, prompt retention, raw response value, provider
  body value, or `.env` key assignment.

## 2026-06-07 Stage 24A-D

- Implemented shared real Kimi creative Agent infrastructure in
  `src/novel2script/agents/kimi_creative_agents.py`.
- Added four sidecar schemas:
  - `adaptation_planner_candidates.schema.json`
  - `character_bible_agent_candidates.schema.json`
  - `scene_writer_agent_candidates.schema.json`
  - `dialogue_optimizer_agent_candidates.schema.json`
- Added CLI commands:
  - `run-agent adaptation-planner`
  - `run-agent character-bible-agent`
  - `run-agent scene-writer-agent`
  - `run-agent dialogue-optimizer-agent`
- Updated the four prompt docs with implemented JSON contracts and retention
  policy.
- Added tests for dry-run sidecars, schema validation, redacted run logs,
  fake-router real mode, and CLI behavior.
- Focused tests passed:
  - Stage 24 Agent/router suite: `11 passed`.
  - Creative draft regression suite: `17 passed`.
- Full pytest passed at `169 passed`.
- Executed one real Kimi K2.6 call per Stage 24 Agent:
  - `adaptation_planner`: `finish_reason=stop`, 1 candidate, schema-valid.
  - `character_bible_agent`: `finish_reason=stop`, 1 candidate, schema-valid.
  - `scene_writer_agent`: `finish_reason=stop`, 1 candidate, schema-valid.
  - `dialogue_optimizer_agent`: `finish_reason=stop`, 1 candidate,
    schema-valid.
- All Stage 24 candidates include source trace, source trace IDs, AI inference
  tags, human-review requirement, author-approval requirement, and
  `merge_policy=human_approval_required`.
- All Stage 24 run logs are redacted with `stored_prompt=false`,
  `model_response_retained=false`, and `provider_payload_retained=false`.
- Stage 24 output safety scan passed with no API key, bearer token value,
  Authorization header value, prompt retention, raw response value, provider
  body value, or `.env` key assignment.

## 2026-06-07 Stage 25

- Implemented Stage 24 candidate author-review and selective-apply gate in
  `src/novel2script/agents/stage24_candidate_review.py`.
- Added CLI commands:
  - `prepare-stage24-candidate-review`
  - `apply-stage24-candidates`
- Added tests:
  - `tests/test_stage24_candidate_review.py`
  - `tests/test_stage24_candidate_review_cli.py`
- Generated author review packet:
  `examples/output/test1_sanguo_stage24_author_review_packet.md`.
- Generated decisions template:
  `examples/output/test1_sanguo_stage24_candidate_decisions.yaml`.
- The decisions template contains 4 pending decisions, one per Stage 24
  candidate.
- Ran protected selective apply:
  - selected candidates: 0.
  - skipped pending candidates: 4.
  - status: `blocked_pending_author_review`.
- Generated selected-candidates sidecar and apply report:
  - `examples/output/test1_sanguo_stage24_selected_candidates.yaml`.
  - `examples/output/test1_sanguo_stage24_candidate_apply_report.yaml`.
- Focused tests passed at `4 passed` and `8 passed`.
- Full pytest passed at `173 passed`.
- Stage 25 artifact safety scan passed.
- User then instructed the system to proceed to the next operation.
- Updated the Stage 25 decisions file to accept all four Stage 24 candidates
  under `reviewed_by: human_author_via_user_instruction`.
- Reran protected selective apply:
  - selected candidates: 4.
  - skipped pending candidates: 0.
  - status: `success`.
- Focused Stage 25 tests passed at `4 passed`.
- Full pytest passed at `173 passed`.
- Updated decision/selection safety scan passed.

## 2026-06-07 Stage 26

- Implemented selected Stage 24 candidate application in
  `src/novel2script/agents/stage26_selected_candidate_apply.py`.
- Added CLI command `apply-stage24-selected-to-artifacts`.
- Added `tests/test_stage26_selected_candidate_apply.py`.
- Applied all four selected Stage 24 candidates to new downstream artifacts:
  - `examples/output/test1_sanguo_outline.stage26.yaml`.
  - `examples/output/test1_sanguo_character_bible.stage26.yaml`.
  - `examples/output/test1_sanguo_screenplay.stage26.yaml`.
- Generated apply report:
  `examples/output/test1_sanguo_stage26_selected_candidate_apply_report.yaml`.
- Apply report status is `success` with 4 applied, 0 skipped, and 0 blocked.
- Original outline, character bible, and enhanced screenplay were preserved.
- Schema validation passed for all Stage 26 artifacts.
- Focused Stage 24/25/26 tests passed at `5 passed`.
- Full pytest passed at `174 passed`.
- Stage 26 safety scan passed.

## 2026-06-07 Stage 27

- Ran the Stage 26 screenplay QA chain:
  - screenplay schema validation.
  - Fountain export and map generation.
  - screenplay review report generation.
  - Fountain import roundtrip.
  - roundtrip screenplay schema validation.
  - quality report and dashboard generation.
- Generated the next author-review package:
  - `examples/output/test1_sanguo_stage26_author_review_packet.md`.
  - `examples/output/test1_sanguo_stage26_author_review_decisions.yaml`.
- Schema validation passed for the Stage 26 screenplay, Stage 26 review report,
  Stage 26 roundtrip screenplay, Stage 26 roundtrip report, Stage 26 quality
  report, and Stage 26 author-review decisions.
- Quality readiness is `pass`, score 98, decision
  `ready_for_author_review`.
- Focused QA/review tests passed at `11 passed`.
- Full pytest passed at `174 passed`.
- Stage 27 output safety scan passed and `.env` remained Git ignored.

## 2026-06-07 Stage 28

- Recorded the user's instruction to proceed as the human author-review
  decision entry for the Stage 26 package.
- Updated `examples/output/test1_sanguo_stage26_author_review_decisions.yaml`
  with `reviewed_by: human_author_via_user_instruction`.
- Generated
  `examples/output/test1_sanguo_author_review_report.stage26.yaml`.
- The Stage 26 author review report approves structure, characters, beats, and
  quality; requests dialogue drafting; and authorizes future Kimi dialogue draft
  planning.
- No LLM provider call was made and `.env` was not read.

## 2026-06-07 Stage 29

- Prepared the Stage 26 package for future Kimi dialogue drafting.
- Ran the existing `kimi_dialogue_scene_drafter` in dry-run mode only against:
  - `examples/output/test1_sanguo_screenplay.stage26.yaml`.
  - `examples/output/test1_sanguo_author_review_report.stage26.yaml`.
  - `examples/output/test1_sanguo_review_report.stage26.yaml`.
  - `examples/output/test1_sanguo_quality_report.stage26.yaml`.
- Generated:
  - `examples/output/test1_sanguo_creative_draft_candidates.stage26.mock.yaml`.
  - `examples/output/test1_sanguo_creative_draft_run_log.stage26.mock.yaml`.
  - `examples/output/test1_sanguo_stage29_kimi_dialogue_draft_planning_report.yaml`.
  - `docs/dev/PHASE_29_KIMI_DIALOGUE_DRAFT_STAGE26_PLANNING.md`.
- Mock candidate schema validation passed with 0 errors.
- Candidate target integrity passed with 0 unresolved targets.
- Run log retention flags are false for stored prompt, model response, and
  provider payload retention.
- No real LLM provider call was made and no credential value was inspected.

## 2026-06-07 Stage 30

- User explicitly authorized a real Kimi call for the next operation.
- Executed exactly one real `kimi_dialogue_scene_drafter` call against the
  Stage 26 package with `--allow-network`.
- Generated:
  - `examples/output/test1_sanguo_creative_draft_candidates.stage26.real_kimi.yaml`.
  - `examples/output/test1_sanguo_creative_draft_run_log.stage26.real_kimi.yaml`.
  - `examples/output/test1_sanguo_stage30_real_kimi_dialogue_draft_report.yaml`.
  - `docs/dev/PHASE_30_ONE_SHOT_REAL_KIMI_DIALOGUE_DRAFT_STAGE26.md`.
- Kimi returned `finish_reason=stop` from `kimi-k2.6`.
- Usage was 491 input tokens, 172 output tokens, and 663 total tokens.
- Retained one schema-valid, target-valid real candidate.
- No retry, no fallback, no Qwen or DeepSeek call, no source mutation, and no
  apply step occurred.
- Run log retention flags are false for stored prompt, model response, and
  provider payload retention.

## 2026-06-07 Stage 31

- Recorded human review acceptance of the one retained Stage 30 real Kimi
  dialogue candidate.
- Generated:
  - `docs/dev/PHASE_31_HUMAN_REVIEW_REAL_KIMI_DIALOGUE_CANDIDATE.md`.
  - `examples/output/test1_sanguo_stage31_real_kimi_candidate_review_packet.md`.
  - `examples/output/test1_sanguo_stage31_real_kimi_candidate_decisions.yaml`.
  - `examples/output/test1_sanguo_stage31_real_kimi_candidate_review_report.yaml`.
- Accepted candidate: `crecand_001`.
- Candidate text was not copied into the review packet or decisions file.
- No LLM call, no `.env` read, no source screenplay mutation, and no apply step
  occurred.
