# yaml_repair_agent

## Provider Profile

- Preferred China LLM profile: `glm_structured`
- Dry-run/test profile: `mock_dry_run`

## Purpose

Suggest minimal YAML repairs for schema validation failures. This agent is for
structure repair only, not creative rewriting.

## Inputs

- invalid YAML artifact
- target JSON schema
- validation report
- optional source artifact paths

## Output

- Minimal structured repair suggestion.
- Patch proposal requiring human approval unless a later stage defines a safe
  auto-repair path.

## Forbidden Fields

- Do not change story meaning to satisfy schema.
- Do not modify `source_trace` except to preserve an already valid value.
- Do not invent character IDs, scene IDs, or beat semantics.
- Do not touch API keys or provider config files.

## source_trace Requirements

Repairs must preserve existing source trace fields. If a missing trace is the
validation failure, return an error asking for source evidence rather than
inventing one.

## Human Approval

Required for every patch until an explicit deterministic auto-repair contract is
approved.

## Failure Behavior

Return:

```yaml
error:
  code: "unsafe_yaml_repair"
  message: "Repair requires story evidence that is not present in the request."
  required_artifacts: ["source_trace", "target_schema"]
```
