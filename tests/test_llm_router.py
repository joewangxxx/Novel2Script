import pytest

from novel2script.llm.router import LLMRouter, ProviderRoutingError
from novel2script.llm.types import LLMRequest


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
    assert router.intended_profile_for("dialogue_optimizer_agent") == "doubao_dialogue"
    assert router.intended_profile_for("beat_dramaturgy_agent") == "deepseek_reasoning"
    assert router.intended_profile_for("source_fidelity_reviewer") == "qwen_long+deepseek_reasoning"
    assert router.intended_profile_for("yaml_repair_agent") == "glm_structured"


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
