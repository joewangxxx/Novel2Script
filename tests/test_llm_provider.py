from novel2script.llm.mock_provider import MockLLMProvider
from novel2script.llm.run_log import build_run_record, prompt_hash
from novel2script.llm.types import LLMRequest


def test_mock_provider_returns_stable_response_and_usage():
    request = LLMRequest(
        agent_id="scene_writer_agent",
        task_type="scene_generation",
        prompt="Write a scene from source trace ch_001/p_001.",
        response_format="yaml",
        temperature=0.4,
        max_tokens=256,
        trace_id="trace_001",
    )
    provider = MockLLMProvider()

    first = provider.generate(request)
    second = provider.generate(request)

    assert first == second
    assert first.provider == "mock_dry_run"
    assert first.model == "mock-model"
    assert first.finish_reason == "dry_run"
    assert first.text == (
        "MOCK_RESPONSE agent=scene_writer_agent task=scene_generation "
        "format=yaml trace=trace_001"
    )
    assert first.usage["total_tokens"] == first.usage["input_tokens"] + first.usage["output_tokens"]
    assert first.run_id.startswith("llm_run_")


def test_run_record_redacts_prompt_and_keeps_hash_metadata():
    request = LLMRequest(
        agent_id="dialogue_optimizer_agent",
        task_type="dialogue_revision",
        prompt="Sensitive full prompt that must not be logged.",
        response_format="text",
        temperature=0.2,
        max_tokens=128,
        trace_id="trace_002",
    )
    response = MockLLMProvider().generate(request)

    record = build_run_record(request, response, status="dry_run")

    assert record["agent_id"] == "dialogue_optimizer_agent"
    assert record["provider"] == "mock_dry_run"
    assert record["model"] == "mock-model"
    assert record["prompt_hash"] == prompt_hash(request.prompt)
    assert "prompt" not in record
    assert "Sensitive full prompt" not in str(record)
    assert record["usage"] == response.usage
    assert record["status"] == "dry_run"
