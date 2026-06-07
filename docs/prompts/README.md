# Agent Prompt Registry

This registry defines the bounded prompt contracts for future model-backed
Novel2Script agents. It does not call models, replace deterministic Stage 3-8
modules, or authorize schema changes.

Each agent prompt file documents:

- preferred China LLM provider profile
- allowed input artifacts
- expected output artifact or schema
- forbidden fields
- source trace requirements
- human approval requirements
- structured error behavior

Agents must use the Stage 9 provider abstraction in
`docs/architecture/llm-provider.md`. They must not call provider APIs directly
or read API keys from files.

## Registry Files

- `agent-routing.md`: routing overview and profile table.
- `story_semantic_parser.md`
- `adaptation_planner.md`
- `character_bible_agent.md`
- `scene_writer_agent.md`
- `dialogue_optimizer_agent.md`
- `beat_dramaturgy_agent.md`
- `source_fidelity_reviewer.md`
- `yaml_repair_agent.md`

## Shared Rules

- Preserve existing deterministic artifacts unless a later approved stage
  explicitly allows writing a new artifact.
- Do not silently change frozen or draft schemas to satisfy model output.
- Keep full novel text out of run logs.
- Use bounded source excerpts and artifact references.
- Return structured errors instead of guessing when required evidence is
  missing.
- Suggested changes that alter creative or semantic fields require human
  approval.
