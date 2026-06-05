import pytest

from novel2script.llm.router import LLMRouter, ProviderRoutingError
from novel2script.llm.types import LLMRequest, LLMResponse


def test_router_defaults_to_mock_provider_for_registered_agent():
    request = LLMRequest(
        agent_id="story_semantic_parser",
        task_type="semantic_parse",
        prompt="Parse source trace references only.",
        response_format="yaml",
        temperature=0.0,
        max_tokens=512,
        trace_id="trace_router_001",
    )
    router = LLMRouter.default()

    result = router.dispatch(request)

    assert result.response.provider == "mock_dry_run"
    assert result.response.model == "mock-model"
    assert result.resolved_profile == "mock_dry_run"
    assert result.intended_profile == "qwen_long"
    assert result.run_record["agent_id"] == "story_semantic_parser"
    assert result.run_record["prompt_hash"].startswith("sha256:")
    assert "Parse source trace" not in str(result.run_record)


def test_router_uses_contract_routing_table_for_all_stage9_agents():
    router = LLMRouter.default()

    assert router.intended_profile_for("story_semantic_parser") == "qwen_long"
    assert router.intended_profile_for("adaptation_planner") == "kimi_creative"
    assert router.intended_profile_for("character_bible_agent") == "kimi_creative"
    assert router.intended_profile_for("scene_writer_agent") == "kimi_creative"
    assert router.intended_profile_for("dialogue_optimizer_agent") == "kimi_creative"
    assert router.intended_profile_for("beat_dramaturgy_agent") == "deepseek_reasoning"
    assert router.intended_profile_for("source_fidelity_reviewer") == "qwen_long+deepseek_reasoning"
    assert router.intended_profile_for("yaml_repair_agent") == "deepseek_reasoning"


def test_router_blocks_unknown_agent_without_network_or_key_lookup():
    router = LLMRouter.default()
    request = LLMRequest(
        agent_id="unknown_agent",
        task_type="unknown",
        prompt="No route.",
        response_format="text",
        temperature=0.0,
        max_tokens=10,
        trace_id="trace_router_002",
    )

    with pytest.raises(ProviderRoutingError):
        router.dispatch(request)


class CapturingProvider:
    profile_id = "qwen_long"
    model = "qwen-long"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            text="real provider response",
            model=self.model,
            provider=self.profile_id,
            usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            latency_ms=12,
            finish_reason="stop",
            run_id="llm_run_real_001",
        )


def test_router_uses_real_provider_only_when_network_is_allowed():
    request = LLMRequest(
        agent_id="story_semantic_parser",
        task_type="semantic_parse",
        prompt="Parse source trace references only.",
        response_format="yaml",
        temperature=0.0,
        max_tokens=512,
        trace_id="trace_router_003",
    )
    real_provider = CapturingProvider()
    router = LLMRouter(
        providers={"qwen_long": real_provider},
        allow_network=True,
    )

    result = router.dispatch(request)

    assert real_provider.requests == [request]
    assert result.response.provider == "qwen_long"
    assert result.resolved_profile == "qwen_long"
    assert result.run_record["status"] == "completed"
    assert "Parse source trace" not in str(result.run_record)


def test_router_from_environment_registers_selected_chinese_model_profiles(monkeypatch):
    monkeypatch.setenv("N2S_QWEN_API_KEY", "test-qwen-key")
    monkeypatch.setenv("N2S_KIMI_API_KEY", "test-kimi-key")
    monkeypatch.setenv("N2S_DEEPSEEK_API_KEY", "test-deepseek-key")

    router = LLMRouter.from_environment(allow_network=True)

    assert router.providers["qwen_long"].model == "qwen-long"  # type: ignore[attr-defined]
    assert router.providers["kimi_creative"].model == "kimi-k2.6"  # type: ignore[attr-defined]
    assert router.providers["deepseek_reasoning"].model == "deepseek-v4-pro"  # type: ignore[attr-defined]
