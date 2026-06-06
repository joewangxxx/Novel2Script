from __future__ import annotations

import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from novel2script.llm.run_log import stable_run_id
from novel2script.llm.types import LLMRequest, LLMResponse


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderRuntimeError(RuntimeError):
    def __init__(
        self,
        *,
        category: str,
        status_code: int | None = None,
        retryable: bool = False,
        attempt: int = 0,
        max_attempts: int = 0,
        provider_profile: str = "",
        model: str = "",
        request_id: str = "",
    ) -> None:
        self.category = category
        self.status_code = status_code
        self.retryable = retryable
        self.attempt = attempt
        self.max_attempts = max_attempts
        self.provider_profile = provider_profile
        self.model = model
        self.request_id = request_id
        super().__init__(json.dumps(self.to_dict(), sort_keys=True))

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "provider_profile": self.provider_profile,
            "model": self.model,
            "request_id": self.request_id,
        }

    def with_context(
        self,
        *,
        attempt: int,
        max_attempts: int,
        provider_profile: str,
        model: str,
        fallback_request_id: str,
    ) -> "ProviderRuntimeError":
        return ProviderRuntimeError(
            category=self.category,
            status_code=self.status_code,
            retryable=self.retryable,
            attempt=attempt,
            max_attempts=max_attempts,
            provider_profile=provider_profile,
            model=model,
            request_id=_safe_request_id(self.request_id, fallback_request_id),
        )


JSONTransport = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    profile_id: str
    provider_type: str
    model: str
    env_api_key: str
    base_url: str
    timeout_seconds: int = 90
    transport: JSONTransport | None = None
    max_attempts: int = 3
    backoff_base_seconds: float = 0.5
    sleep: Callable[[float], None] = time.sleep

    def generate(self, request: LLMRequest) -> LLMResponse:
        api_key = provider_env_value(self.env_api_key)
        if not api_key:
            raise ProviderConfigurationError(
                f"Provider {self.profile_id} requires environment variable "
                f"{self.env_api_key}."
            )

        started = time.perf_counter()
        transport = self.transport or _urllib_json_transport
        raw: dict[str, Any] | None = None
        max_attempts = max(1, self.max_attempts)
        fallback_request_id = f"req_{request.trace_id}"
        final_attempt = 0
        for attempt in range(1, max_attempts + 1):
            final_attempt = attempt
            try:
                raw = transport(
                    url=_chat_completions_url(self.base_url),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    payload=_payload_for(request, self.model),
                    timeout_seconds=self.timeout_seconds,
                )
                break
            except ProviderRuntimeError as exc:
                error = exc.with_context(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    provider_profile=self.profile_id,
                    model=self.model,
                    fallback_request_id=fallback_request_id,
                )
                if not error.retryable or attempt >= max_attempts:
                    raise error from None
                self.sleep(self.backoff_base_seconds * (2 ** (attempt - 1)))
            except json.JSONDecodeError:
                raise self._runtime_error(
                    "invalid_provider_json",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    request_id=fallback_request_id,
                ) from None
            except Exception:
                raise self._runtime_error(
                    "transport_failure",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    request_id=fallback_request_id,
                ) from None
        if raw is None:
            raise self._runtime_error(
                "transport_failure",
                attempt=final_attempt,
                max_attempts=max_attempts,
                request_id=fallback_request_id,
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            text, finish_reason = _choice_text_and_reason(raw)
        except ProviderRuntimeError as exc:
            raise exc.with_context(
                attempt=final_attempt,
                max_attempts=max_attempts,
                provider_profile=self.profile_id,
                model=self.model,
                fallback_request_id=fallback_request_id,
            ) from None
        usage = _usage(raw.get("usage", {}))
        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.profile_id,
            usage=usage,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            run_id=stable_run_id(request, self.profile_id),
        )

    def _runtime_error(
        self,
        category: str,
        *,
        attempt: int,
        max_attempts: int,
        request_id: str,
    ) -> ProviderRuntimeError:
        return ProviderRuntimeError(
            category=category,
            retryable=False,
            attempt=attempt,
            max_attempts=max_attempts,
            provider_profile=self.profile_id,
            model=self.model,
            request_id=_safe_request_id("", request_id),
        )


def _payload_for(request: LLMRequest, model: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Novel2Script agent. Follow the requested "
                    "response format and do not invent source trace IDs."
                ),
            },
            {"role": "user", "content": request.prompt},
        ],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "stream": False,
    }
    if request.response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
    return payload


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _choice_text_and_reason(raw: dict[str, Any]) -> tuple[str, str]:
    choices = raw.get("choices", [])
    if not choices:
        raise ProviderRuntimeError(
            category="invalid_provider_response",
            retryable=False,
        )
    first = choices[0]
    message = first.get("message", {})
    content = str(message.get("content", ""))
    finish_reason = str(first.get("finish_reason") or "unknown")
    return content, finish_reason


def _usage(raw_usage: dict[str, Any]) -> dict[str, int]:
    input_tokens = int(
        raw_usage.get("prompt_tokens", raw_usage.get("input_tokens", 0)) or 0
    )
    output_tokens = int(
        raw_usage.get("completion_tokens", raw_usage.get("output_tokens", 0)) or 0
    )
    total_tokens = int(
        raw_usage.get("total_tokens", input_tokens + output_tokens) or 0
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _urllib_json_transport(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            try:
                return json.loads(response.read().decode("utf-8"))
            except json.JSONDecodeError:
                raise ProviderRuntimeError(
                    category="invalid_provider_json",
                    retryable=False,
                ) from None
    except urllib.error.HTTPError as exc:
        raise ProviderRuntimeError(
            category=_http_error_category(exc.code),
            status_code=exc.code,
            retryable=exc.code in {429, 500, 502, 503, 504},
            request_id=_request_id_from_headers(exc.headers),
        ) from exc
    except urllib.error.URLError as exc:
        category = _connection_error_category(exc.reason)
        raise ProviderRuntimeError(
            category=category,
            retryable=True,
        ) from exc
    except TimeoutError as exc:
        raise ProviderRuntimeError(category="timeout", retryable=True) from exc
    except ssl.SSLError as exc:
        raise ProviderRuntimeError(category="tls_error", retryable=True) from exc


def _http_error_category(status_code: int) -> str:
    return {
        400: "invalid_request",
        401: "authentication",
        403: "authorization",
        404: "endpoint_not_found",
        429: "rate_limited",
    }.get(status_code, "provider_server_error" if status_code >= 500 else "http_error")


def _connection_error_category(reason: object) -> str:
    if isinstance(reason, socket.gaierror):
        return "dns_error"
    if isinstance(reason, ssl.SSLError):
        return "tls_error"
    if isinstance(reason, TimeoutError):
        return "timeout"
    return "connection_error"


def _request_id_from_headers(headers: Any) -> str:
    if not headers:
        return ""
    for name in ("x-request-id", "request-id", "x-dashscope-request-id"):
        value = headers.get(name)
        if value:
            return _safe_request_id(str(value), "")
    return ""


def _safe_request_id(value: str, fallback: str) -> str:
    candidate = value if _is_safe_request_id(value) else fallback
    return candidate if _is_safe_request_id(candidate) else ""


def _is_safe_request_id(value: str) -> bool:
    return bool(value) and len(value) <= 128 and all(
        character.isalnum() or character in "._:-" for character in value
    )


def provider_env_value(name: str) -> str | None:
    return os.getenv(name) or _dotenv_value(name)


def _dotenv_value(name: str, path: str | Path = ".env") -> str | None:
    if os.getenv("N2S_DISABLE_DOTENV") == "1":
        return None
    env_path = Path(path)
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            return _unquote_env_value(value.strip())
    return None


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
