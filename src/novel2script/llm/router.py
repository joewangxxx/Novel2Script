from __future__ import annotations

from dataclasses import dataclass

from novel2script.llm.mock_provider import MockLLMProvider
from novel2script.llm.run_log import build_run_record
from novel2script.llm.types import LLMRequest, LLMResponse, LLMRunRecord


AGENT_PROVIDER_ROUTES = {
    "story_semantic_parser": "qwen_long",
    "adaptation_planner": "kimi_creative",
    "character_bible_agent": "kimi_creative",
    "scene_writer_agent": "kimi_creative",
    "dialogue_optimizer_agent": "doubao_dialogue",
    "beat_dramaturgy_agent": "deepseek_reasoning",
    "source_fidelity_reviewer": "qwen_long+deepseek_reasoning",
    "yaml_repair_agent": "glm_structured",
}


class ProviderRoutingError(ValueError):
    pass


@dataclass(frozen=True)
class RoutedLLMResult:
    response: LLMResponse
    run_record: LLMRunRecord
    intended_profile: str
    resolved_profile: str


class LLMRouter:
    def __init__(self, *, providers: dict[str, object] | None = None) -> None:
        self.providers = providers or {"mock_dry_run": MockLLMProvider()}

    @classmethod
    def default(cls) -> "LLMRouter":
        return cls()

    def intended_profile_for(self, agent_id: str) -> str:
        try:
            return AGENT_PROVIDER_ROUTES[agent_id]
        except KeyError as exc:
            raise ProviderRoutingError(f"Unknown LLM agent_id: {agent_id}") from exc

    def dispatch(self, request: LLMRequest) -> RoutedLLMResult:
        intended_profile = self.intended_profile_for(request.agent_id)
        resolved_profile = "mock_dry_run"
        provider = self.providers[resolved_profile]
        response = provider.generate(request)  # type: ignore[attr-defined]
        run_record = build_run_record(
            request,
            response,
            status="dry_run",
            intended_profile=intended_profile,
            resolved_profile=resolved_profile,
        )
        return RoutedLLMResult(
            response=response,
            run_record=run_record,
            intended_profile=intended_profile,
            resolved_profile=resolved_profile,
        )
