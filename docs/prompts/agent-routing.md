# Agent Routing

Future model-backed agents route through the Stage 9 provider abstraction.
Default execution remains `mock_dry_run`; real providers require explicit
configuration and environment variables.

| Agent | Preferred Profile | Input Focus | Output Focus |
| --- | --- | --- | --- |
| `story_semantic_parser` | `qwen_long` | novel text, story_map traces | semantic candidates |
| `adaptation_planner` | `kimi_creative` | story_map, quality report | outline candidates |
| `character_bible_agent` | `kimi_creative` | story_map, outline | character bible updates |
| `scene_writer_agent` | `kimi_creative` | outline, character bible, screenplay | scene draft suggestions |
| `dialogue_optimizer_agent` | `kimi_creative` | screenplay dialogue, character bible | dialogue suggestions |
| `beat_dramaturgy_agent` | `deepseek_reasoning` | screenplay beats, review report | beat analysis suggestions |
| `source_fidelity_reviewer` | `qwen_long` + `deepseek_reasoning` | source traces, screenplay | fidelity issues |
| `yaml_repair_agent` | `deepseek_reasoning` | schema errors, invalid YAML | schema repair suggestions |

Routing config example: `config/agent_routing.example.yaml`.

## Registry Safety

- Agents request an `agent_id`; they do not select raw API endpoints.
- Provider credentials come from environment variables only.
- Prompt outputs are advisory unless the target stage explicitly writes an
  artifact.
- Any patch affecting screenplay semantics requires human approval.
- Missing evidence must produce a structured error with `code`, `message`, and
  `required_artifacts`.
