from __future__ import annotations

from dataclasses import dataclass

from novel2script.llm.mock_provider import MockLLMProvider
from novel2script.llm.openai_compatible_provider import (
    OpenAICompatibleProvider,
    provider_env_value,
)
from novel2script.llm.run_log import build_run_record
from novel2script.llm.types import LLMRequest, LLMResponse, LLMRunRecord


AGENT_PROVIDER_ROUTES = {
    "story_semantic_parser": "qwen_long",
    "adaptation_planner": "kimi_creative",
    "character_bible_agent": "kimi_creative",
    "scene_writer_agent": "kimi_creative",
    "dialogue_optimizer_agent": "kimi_creative",
    "beat_dramaturgy_agent": "deepseek_reasoning",
    "source_fidelity_reviewer": "qwen_long+deepseek_reasoning",
    "yaml_repair_agent": "deepseek_reasoning",
}


CHINESE_PROVIDER_PROFILES = {
    "qwen_long": {
        "provider_type": "qwen",
        "model": "qwen-long",
        "env_api_key": "N2S_QWEN_API_KEY",
        "env_base_url": "N2S_QWEN_BASE_URL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "kimi_creative": {
        "provider_type": "kimi",
        "model": "kimi-k2.6",
        "env_api_key": "N2S_KIMI_API_KEY",
        "env_base_url": "N2S_KIMI_BASE_URL",
        "default_base_url": "https://api.moonshot.ai/v1",
    },
    "deepseek_reasoning": {
        "provider_type": "deepseek",
        "model": "deepseek-v4-pro",
        "env_api_key": "N2S_DEEPSEEK_API_KEY",
        "env_base_url": "N2S_DEEPSEEK_BASE_URL",
        "default_base_url": "https://api.deepseek.com",
    },
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
    def __init__(
        self,
        *,
        providers: dict[str, object] | None = None,
        allow_network: bool = False,
    ) -> None:
        self.providers = providers or {"mock_dry_run": MockLLMProvider()}
        self.mock_provider = self.providers.get("mock_dry_run", MockLLMProvider())
        self.allow_network = allow_network

    @classmethod
    def default(cls) -> "LLMRouter":
        return cls()

    @classmethod
    def from_environment(cls, *, allow_network: bool = False) -> "LLMRouter":
        providers: dict[str, object] = {"mock_dry_run": MockLLMProvider()}
        if allow_network:
            for profile_id, config in CHINESE_PROVIDER_PROFILES.items():
                providers[profile_id] = OpenAICompatibleProvider(
                    profile_id=profile_id,
                    provider_type=config["provider_type"],
                    model=config["model"],
                    env_api_key=config["env_api_key"],
                    base_url=(
                        provider_env_value(config["env_base_url"])
                        or config["default_base_url"]
                    ),
                )
        return cls(providers=providers, allow_network=allow_network)

    def intended_profile_for(self, agent_id: str) -> str:
        try:
            return AGENT_PROVIDER_ROUTES[agent_id]
        except KeyError as exc:
            raise ProviderRoutingError(f"Unknown LLM agent_id: {agent_id}") from exc

    def dispatch(self, request: LLMRequest) -> RoutedLLMResult:
        intended_profile = self.intended_profile_for(request.agent_id)
        resolved_profile = self._resolve_profile(intended_profile)
        provider = self.providers.get(resolved_profile, self.mock_provider)
        response = provider.generate(request)  # type: ignore[attr-defined]
        run_record = build_run_record(
            request,
            response,
            status="completed" if self.allow_network else "dry_run",
            intended_profile=intended_profile,
            resolved_profile=resolved_profile,
        )
        return RoutedLLMResult(
            response=response,
            run_record=run_record,
            intended_profile=intended_profile,
            resolved_profile=resolved_profile,
        )

    def _resolve_profile(self, intended_profile: str) -> str:
        if not self.allow_network:
            return "mock_dry_run"
        for profile in intended_profile.split("+"):
            if profile in self.providers:
                return profile
        raise ProviderRoutingError(
            f"Provider profile {intended_profile} is not configured for network use."
        )
