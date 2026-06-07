from __future__ import annotations

import io
import json
import socket
import ssl
import urllib.error

import pytest

from novel2script.llm.openai_compatible_provider import (
    OpenAICompatibleProvider,
    ProviderConfigurationError,
    ProviderRuntimeError,
)
from novel2script.llm.types import LLMRequest


AUTH_PREFIX = "Bearer" + " "


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


def _request(*, response_format: str = "semantic_candidates.yaml") -> LLMRequest:
    return LLMRequest(
        agent_id="story_semantic_parser",
        task_type="semantic_candidate_generation",
        prompt="Return one JSON object from bounded excerpts only.",
        response_format=response_format,
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
    assert transport.calls[0]["headers"]["Authorization"] == (
        AUTH_PREFIX + "test-secret-value"
    )
    assert transport.calls[0]["payload"]["model"] == "qwen-long"
    assert transport.calls[0]["payload"]["temperature"] == 0.0
    assert transport.calls[0]["payload"]["max_tokens"] == 512
    assert transport.calls[0]["payload"]["messages"][1] == {
        "role": "user",
        "content": "Return one JSON object from bounded excerpts only.",
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
        AUTH_PREFIX + "dotenv-secret-value"
    )


def test_openai_compatible_provider_normalizes_bearer_prefixed_env_key(monkeypatch):
    monkeypatch.setenv("N2S_TEST_API_KEY", AUTH_PREFIX + "prefixed-secret-value")
    transport = CapturingTransport()
    provider = OpenAICompatibleProvider(
        profile_id="kimi_creative",
        provider_type="kimi",
        model="kimi-k2.6",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://api.moonshot.ai/v1",
        transport=transport,
    )

    provider.generate(_request(response_format="json_object"))

    assert transport.calls[0]["headers"]["Authorization"] == (
        AUTH_PREFIX + "prefixed-secret-value"
    )


def test_openai_compatible_provider_enables_optional_json_mode(monkeypatch):
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

    provider.generate(_request(response_format="json_object"))

    assert transport.calls[0]["payload"]["response_format"] == {
        "type": "json_object"
    }


def test_kimi_provider_omits_json_mode_for_moonshot_compatibility(monkeypatch):
    monkeypatch.setenv("N2S_TEST_API_KEY", "test-secret-value")
    transport = CapturingTransport()
    provider = OpenAICompatibleProvider(
        profile_id="kimi_creative",
        provider_type="kimi",
        model="kimi-k2.6",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://api.moonshot.cn/v1",
        transport=transport,
        supports_response_format=False,
    )

    provider.generate(_request(response_format="json_object"))

    assert "response_format" not in transport.calls[0]["payload"]


def test_kimi_provider_omits_temperature_for_moonshot_compatibility(monkeypatch):
    monkeypatch.setenv("N2S_TEST_API_KEY", "test-secret-value")
    transport = CapturingTransport()
    provider = OpenAICompatibleProvider(
        profile_id="kimi_creative",
        provider_type="kimi",
        model="kimi-k2.6",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://api.moonshot.cn/v1",
        transport=transport,
        supports_temperature=False,
    )

    provider.generate(_request(response_format="json_object"))

    assert "temperature" not in transport.calls[0]["payload"]


def test_kimi_provider_merges_profile_extra_body_for_thinking_disabled(monkeypatch):
    monkeypatch.setenv("N2S_TEST_API_KEY", "test-secret-value")
    transport = CapturingTransport()
    provider = OpenAICompatibleProvider(
        profile_id="kimi_creative",
        provider_type="kimi",
        model="kimi-k2.6",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://api.moonshot.cn/v1",
        transport=transport,
        supports_response_format=False,
        supports_temperature=False,
        extra_body={"thinking": {"type": "disabled"}},
    )

    provider.generate(_request(response_format="json_object"))

    payload = transport.calls[0]["payload"]
    assert payload["thinking"] == {"type": "disabled"}
    assert "response_format" not in payload
    assert "temperature" not in payload


class RetryTransport:
    def __init__(self, failures: list[ProviderRuntimeError]) -> None:
        self.failures = list(failures)
        self.calls = 0

    def __call__(self, **_: object) -> dict:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return {
            "choices": [
                {
                    "message": {"content": '{"candidates": []}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
        }


def test_openai_compatible_provider_retries_retryable_failures_with_backoff(
    monkeypatch,
):
    monkeypatch.setenv("N2S_TEST_API_KEY", "test-secret-value")
    transport = RetryTransport(
        [
            ProviderRuntimeError(category="tls_error", retryable=True),
            ProviderRuntimeError(
                category="provider_server_error",
                status_code=503,
                retryable=True,
            ),
        ]
    )
    delays: list[float] = []
    provider = OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        transport=transport,
        max_attempts=3,
        backoff_base_seconds=0.5,
        sleep=delays.append,
    )

    response = provider.generate(_request(response_format="json_object"))

    assert response.text == '{"candidates": []}'
    assert transport.calls == 3
    assert delays == [0.5, 1.0]


def test_openai_compatible_provider_does_not_retry_non_retryable_failure(
    monkeypatch,
):
    monkeypatch.setenv("N2S_TEST_API_KEY", "test-secret-value")
    transport = RetryTransport(
        [
            ProviderRuntimeError(
                category="invalid_request",
                status_code=400,
                retryable=False,
            )
        ]
    )
    provider = OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        transport=transport,
        max_attempts=3,
        sleep=lambda _: None,
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        provider.generate(_request(response_format="json_object"))

    assert transport.calls == 1
    assert exc_info.value.to_dict() == {
        "category": "invalid_request",
        "status_code": 400,
        "retryable": False,
        "attempt": 1,
        "max_attempts": 3,
        "provider_profile": "qwen_long",
        "model": "qwen-long",
        "request_id": "req_trace_provider_001",
    }


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _network_provider(*, max_attempts: int = 1) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        max_attempts=max_attempts,
        sleep=lambda _: None,
    )


@pytest.mark.parametrize(
    ("status_code", "category", "retryable"),
    [
        (400, "invalid_request", False),
        (401, "authentication", False),
        (403, "authorization", False),
        (404, "endpoint_not_found", False),
        (429, "rate_limited", True),
        (500, "provider_server_error", True),
        (503, "provider_server_error", True),
    ],
)
def test_provider_classifies_http_errors_without_leaking_response(
    monkeypatch,
    status_code: int,
    category: str,
    retryable: bool,
) -> None:
    secret = "SENSITIVE_HTTP_BODY_API_KEY_PROMPT_NOVEL"
    monkeypatch.setenv("N2S_TEST_API_KEY", "secret-api-key")
    error = urllib.error.HTTPError(
        url="https://example.test",
        code=status_code,
        msg="unsafe status message",
        hdrs={"x-request-id": "safe-request-123"},
        fp=io.BytesIO(secret.encode("utf-8")),
    )
    monkeypatch.setattr(
        "novel2script.llm.openai_compatible_provider.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        _network_provider().generate(_request())

    detail = exc_info.value.to_dict()
    assert detail == {
        "category": category,
        "status_code": status_code,
        "retryable": retryable,
        "attempt": 1,
        "max_attempts": 1,
        "provider_profile": "qwen_long",
        "model": "qwen-long",
        "request_id": "safe-request-123",
    }
    serialized = str(exc_info.value)
    assert json.loads(serialized) == detail
    for forbidden in (
        secret,
        "secret-api-key",
        "Authorization",
        _request().prompt,
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("reason", "category"),
    [
        (socket.gaierror("SENSITIVE_DNS_HOST"), "dns_error"),
        (ssl.SSLError("SENSITIVE_TLS_CERT"), "tls_error"),
        (TimeoutError("SENSITIVE_TIMEOUT"), "timeout"),
    ],
)
def test_provider_classifies_connection_errors_without_leaking_reason(
    monkeypatch,
    reason: BaseException,
    category: str,
) -> None:
    monkeypatch.setenv("N2S_TEST_API_KEY", "secret-api-key")
    error = urllib.error.URLError(reason)
    monkeypatch.setattr(
        "novel2script.llm.openai_compatible_provider.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        _network_provider().generate(_request())

    detail = exc_info.value.to_dict()
    assert detail["category"] == category
    assert detail["status_code"] is None
    assert detail["retryable"] is True
    assert str(reason) not in str(exc_info.value)


def test_provider_classifies_direct_timeout(monkeypatch) -> None:
    monkeypatch.setenv("N2S_TEST_API_KEY", "secret-api-key")
    monkeypatch.setattr(
        "novel2script.llm.openai_compatible_provider.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TimeoutError("SENSITIVE_DIRECT_TIMEOUT")
        ),
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        _network_provider().generate(_request())

    assert exc_info.value.to_dict()["category"] == "timeout"
    assert "SENSITIVE_DIRECT_TIMEOUT" not in str(exc_info.value)


def test_provider_classifies_invalid_provider_json_without_leaking_body(
    monkeypatch,
) -> None:
    marker = "SENSITIVE_INVALID_PROVIDER_JSON"
    monkeypatch.setenv("N2S_TEST_API_KEY", "secret-api-key")
    monkeypatch.setattr(
        "novel2script.llm.openai_compatible_provider.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response(
            f'{{"invalid":"{marker}"'.encode("utf-8")
        ),
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        _network_provider().generate(_request())

    detail = exc_info.value.to_dict()
    assert detail["category"] == "invalid_provider_json"
    assert detail["retryable"] is False
    assert marker not in str(exc_info.value)


def test_provider_classifies_unknown_transport_failure_without_leaking_exception(
    monkeypatch,
) -> None:
    marker = "SENSITIVE_UNKNOWN_TRANSPORT_FAILURE"
    monkeypatch.setenv("N2S_TEST_API_KEY", "secret-api-key")

    def fail_transport(**_: object) -> dict:
        raise RuntimeError(marker)

    provider = OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        transport=fail_transport,
        max_attempts=1,
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        provider.generate(_request())

    detail = exc_info.value.to_dict()
    assert detail["category"] == "transport_failure"
    assert detail["retryable"] is False
    assert marker not in str(exc_info.value)


def test_provider_rejects_response_without_choices_as_structured_error(
    monkeypatch,
) -> None:
    monkeypatch.setenv("N2S_TEST_API_KEY", "secret-api-key")
    provider = OpenAICompatibleProvider(
        profile_id="qwen_long",
        provider_type="qwen",
        model="qwen-long",
        env_api_key="N2S_TEST_API_KEY",
        base_url="https://example.test/compatible-mode/v1",
        transport=lambda **_: {},
        max_attempts=1,
    )

    with pytest.raises(ProviderRuntimeError) as exc_info:
        provider.generate(_request())

    assert exc_info.value.to_dict()["category"] == "invalid_provider_response"
