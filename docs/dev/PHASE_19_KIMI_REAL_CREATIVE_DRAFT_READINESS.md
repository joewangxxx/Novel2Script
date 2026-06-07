# Phase 19: Kimi Real Creative Draft Readiness

## Goal

Stage 19A defines the readiness contract for a future real Kimi dialogue and
scene creative draft run. It does not call real Kimi, does not call any real
LLM, does not modify screenplay, and does not apply creative candidates.

The purpose is to decide when Stage 20 may make exactly one real request and
how any accepted output can be retained as a human-review-only candidate
sidecar.

## Background

Stage 18 completed a mock-first `kimi_dialogue_scene_drafter` runner and sample
fixture:

- `examples/output/test1_sanguo_creative_draft_candidates.mock.yaml`
- `examples/output/test1_sanguo_creative_draft_run_log.mock.yaml`

The mock fixture validates against
`schemas/creative_draft_candidates.schema.json`, targets real screenplay scene
and beat IDs, keeps source traces, and marks every candidate as requiring human
approval.

## Stage 19A Non-Goals

- No real Kimi call.
- No real LLM call.
- No screenplay mutation.
- No source trace mutation.
- No creative candidate application.
- No merged screenplay generation.
- No Stage 15, Stage 16, or Stage 18 artifact mutation.
- No commit.

## Stage 20 Real Call Hard Gates

Stage 20 may make a real Kimi call only when every gate below is satisfied:

1. `author_review_report` exists.
2. `author_review_report.next_stage_authorization` is `kimi_dialogue_draft`.
3. The Stage 18 mock fixture is schema-valid.
4. `schemas/creative_draft_candidates.schema.json` passes contract tests.
5. `config/agent_routing.example.yaml` maps `kimi_dialogue_scene_drafter` to
   `kimi_creative`.
6. Local environment contains the Kimi API key required by the provider profile,
   but the key is never printed, persisted, or copied into artifacts.
7. The user gives explicit network authorization for the real run.
8. The request uses `max_attempts=1`.
9. Stage 20 allows at most one real Kimi call.
10. If the provider or runtime fails, stop without retry.
11. If the model output is schema-invalid, stop without retry.
12. If `finish_reason=length`, stop without retry and do not parse partial
    output.
13. If `candidate_count > 0` is not true, stop without retry.
14. Save only a schema-valid `creative_draft_candidates` sidecar.
15. Save only redacted run-log metadata.
16. do not save prompt.
17. do not save model response.
18. do not save provider request payload.
19. Do not save API keys, bearer values, Authorization values, or `.env`
    content.
20. do not auto-apply candidates.

## Real Output Names

Recommended Stage 20 real-run outputs:

- `examples/output/test1_sanguo_creative_draft_candidates.real_kimi.yaml`
- `examples/output/test1_sanguo_creative_draft_run_log.real_kimi.yaml`

The files must be written only after the model output validates against
`schemas/creative_draft_candidates.schema.json`.

## Real Sidecar Required Fields

The real sidecar keeps the Stage 17/18 contract and adds retention/audit
metadata through the existing `metadata` object:

```yaml
creative_draft_candidates:
  provider_profile: "kimi_creative"
  dry_run: false
  human_approval_required: true
  candidates:
    - merge_policy: "human_approval_required"
      requires_author_approval: true
  metadata:
    retained_as_fixture: true
    prompt_retained: false
    model_response_retained: false
    provider_body_retained: false
    full_source_text_retained: false
    source_screenplay_hash_before: "sha256:..."
    source_screenplay_hash_after: "sha256:..."
    author_review_authorization:
      source: "examples/output/test1_sanguo_author_review_report.yaml"
      next_stage_authorization: "kimi_dialogue_draft"
```

`model_response_retained: false` is the Stage 18 draft-schema equivalent of
"raw model response not retained." The field avoids storing the
raw model response marker inside generated sidecars while preserving the safety
meaning.

## Run Log Boundary

The real Kimi run log may contain only:

- run ID;
- agent ID;
- provider profile;
- model name;
- latency;
- token usage;
- status;
- finish reason;
- prompt hash;
- source artifact paths;
- redacted structured error category when blocked.

The run log must not contain the prompt text, model response text, provider
request payload, API key material, authorization header values, full screenplay
text, or full novel text.

## Screenplay Protection

Real creative draft candidates are sidecars only. Stage 20 must not:

- modify `examples/output/test1_sanguo_screenplay.yaml`;
- modify source traces;
- modify author-approved structure;
- modify characters or event order;
- export Fountain;
- write a merged screenplay;
- apply candidates automatically.

Every candidate must keep:

- `merge_policy: human_approval_required`;
- `requires_author_approval: true`;
- `source_trace`;
- `source_trace_ids`;
- target IDs resolvable against the source screenplay.

## Failure Report Policy

If Stage 20 fails before a schema-valid sidecar exists:

- do not write a partial candidate sidecar;
- write only a redacted diagnostic report if needed;
- record the failure category in QA;
- stop without retry;
- request human intervention for the next attempt.

Blocked categories include:

- missing author authorization;
- missing Kimi credential;
- missing user network authorization;
- provider runtime failure;
- schema-invalid output;
- `finish_reason=length`;
- zero candidates;
- target IDs that do not resolve;
- missing source trace.

## QA Gates For Stage 20

Before any real run:

```bash
python -m pytest tests/test_creative_draft_agent.py tests/test_creative_draft_cli.py
python -m pytest tests/test_creative_draft_contract.py tests/test_creative_draft_real_readiness.py
python -m pytest
```

After a real run, Stage 20 must verify:

- real sidecar schema validity;
- `provider_profile: kimi_creative`;
- `dry_run: false`;
- `human_approval_required: true`;
- `candidate_count > 0`;
- all targets resolve against screenplay;
- all candidates have source traces;
- source screenplay hash before and after are identical;
- author review report hash before and after are identical;
- run log has no retained prompt or model response text;
- artifact security scan passes.

## Stage 19A Gate

Stage 19A passes when:

- this document exists;
- the mock fixture is schema-valid;
- routing points to `kimi_creative`;
- all real-call gates are documented;
- no real Kimi call is made;
- QA report and blackboard are updated.

## Stage 19B Offline Readiness Gate

Stage 19B implements a local-only readiness check. It confirms whether the
repository is ready for a future explicitly authorized Stage 20 real Kimi run,
but it never calls Kimi and never enables network access.

Recommended command:

```bash
python -m novel2script.cli check-real-creative-draft-readiness \
  --screenplay examples/output/test1_sanguo_screenplay.yaml \
  --author-review-report examples/output/test1_sanguo_author_review_report.yaml \
  --mock-candidates examples/output/test1_sanguo_creative_draft_candidates.mock.yaml \
  --out examples/output/test1_sanguo_kimi_real_readiness_report.yaml
```

The report root is `creative_draft_readiness_report`. It records:

- author review authorization;
- mock candidate schema validity;
- candidate target resolution against the screenplay;
- agent routing to `kimi_creative`;
- Kimi key presence as `kimi_key_present: true | false` only;
- real call policy with `max_attempts: 1`, `allow_network: false`, and
  `real_run_authorized: false`;
- retention policy with prompt, model response, provider request payload, and auto-apply
  all disabled.

Status values:

- `ready_pending_network_authorization`: all offline prerequisites are
  satisfied, but the required explicit Stage 20 network authorization is absent.
- `blocked`: at least one hard prerequisite failed.
- `warn`: reserved for future advisory-only checks.
- `ready`: reserved for a future stage that separately records explicit network
  authorization while still preserving the one-call/no-retry policy.

Missing Kimi credentials are `blocked`, because Stage 20 must not discover
credential problems by making a real request.

## Stage 20 Readiness

Stage 20 may be planned next, but real execution still requires explicit user
authorization in that future stage. That authorization must be separate from
this Stage 19A contract.
