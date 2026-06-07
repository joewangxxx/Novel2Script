# Phase 31: Human Review Real Kimi Dialogue Candidate

## Goal

Stage 31 records the human review decision for the retained Stage 30 real Kimi
dialogue candidate. It does not call an LLM and does not apply the candidate to
the screenplay.

## Source Candidate

- Candidate sidecar:
  `examples/output/test1_sanguo_creative_draft_candidates.stage26.real_kimi.yaml`
- Candidate ID: `crecand_001`
- Candidate type: `beat_externalization`
- Target scene: `scene_001`
- Target beat: `beat_001`
- Provider profile: `kimi_creative`
- Model: `kimi-k2.6`

## Review Boundary

- The candidate remains a sidecar proposal.
- The source screenplay is not modified.
- The candidate text is not copied into the review packet.
- The original sidecar remains the source of truth for candidate text.
- Any apply step must occur in a later stage and produce a new screenplay
  artifact.

## Decision

The user's instruction to proceed was recorded as author acceptance of the one
retained real Kimi candidate:

- Decision: `accept`
- Reviewed by: `human_author_via_user_instruction`
- Human approval required: true
- Auto apply allowed: false

## Generated Artifacts

- Review packet:
  `examples/output/test1_sanguo_stage31_real_kimi_candidate_review_packet.md`
- Decisions:
  `examples/output/test1_sanguo_stage31_real_kimi_candidate_decisions.yaml`
- Review report:
  `examples/output/test1_sanguo_stage31_real_kimi_candidate_review_report.yaml`

## Next Stage

Stage 32 may plan and execute a protected apply of the accepted Stage 30
candidate into a new Stage 32 screenplay artifact. It must not mutate the Stage
26 screenplay in place.
