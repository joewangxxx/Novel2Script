from __future__ import annotations

import pytest

from novel2script.llm.openai_compatible_provider import (
    OpenAICompatibleProvider,
    ProviderConfigurationError,
)
from novel2script.llm.types import LLMRequest


class CapturingTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, *, url: str, headers: dict, payload: dict, timeout_seconds: int) -> dict:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "id": "chatcmpl_test_001",
            "choices": [
                {
                    "message": {"content": "structured semantic response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        }


def _request() -> LLMRequest:
    return LLMRequest(
        agent_id="story_semantic_parser",
        task_type="semantic_candidate_generation",
        prompt="Bounded excerpts only.",
        response_format="semantic_candidates.yaml",
        temperature=0.0,
        max_tokens=512,
        trace_id="trace_provider_001",
    )


def test_openai_compatible_provider_uses_env_key_without_storing_secret(monkeypatch):
    monkeypatch.setenv("N2S_TEST_API_KEY", "test-secret-value")
    transport = CapturingTransport()
    provider = OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        transport=transport,
    )

    response = provider.generate(_request())

    assert response.provider == "qwen_long"
    assert response.model == "qwen-long"
    assert response.text == "structured semantic response"
    assert response.finish_reason == "stop"
    assert response.usage == {
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
    }
    assert response.run_id.startswith("llm_run_")
    assert "test-secret-value" not in str(response)
    assert transport.calls[0]["url"] == (
        "https://example.test/compatible-mode/v1/chat/completions"
    )
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer test-secret-value"
    assert transport.calls[0]["payload"]["model"] == "qwen-long"
    assert transport.calls[0]["payload"]["temperature"] == 0.0
    assert transport.calls[0]["payload"]["max_tokens"] == 512
    assert transport.calls[0]["payload"]["messages"][1] == {
        "role": "user",
        "content": "Bounded excerpts only.",
    }


def test_openai_compatible_provider_requires_env_key(monkeypatch):
    monkeypatch.delenv("N2S_TEST_API_KEY", raising=False)
    monkeypatch.setenv("N2S_DISABLE_DOTENV", "1")
    provider = OpenAICompatibleProvider(
        profile_id="kimi_creative",
        provider_type="kimi",
        model="kimi-k2.6",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://api.moonshot.ai/v1",
        transport=CapturingTransport(),
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        provider.generate(_request())

    assert "N2S_TEST_API_KEY" in str(exc_info.value)
    assert "kimi_creative" in str(exc_info.value)


def test_openai_compatible_provider_loads_local_dotenv_without_overriding_env(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("N2S_TEST_API_KEY", raising=False)
    monkeypatch.delenv("N2S_DISABLE_DOTENV", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "N2S_TEST_API_KEY=dotenv-secret-value",
                "IGNORED_COMMENT_TEST=ok",
            ]
        ),
        encoding="utf-8",
    )
    transport = CapturingTransport()
    provider = OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        transport=transport,
    )

    response = provider.generate(_request())

    assert response.provider == "qwen_long"
    assert transport.calls[0]["headers"]["Authorization"] == (
        "Bearer dotenv-secret-value"
    )
