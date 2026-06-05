from __future__ import annotations

import json
import os
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
    pass


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

    def generate(self, request: LLMRequest) -> LLMResponse:
        api_key = os.getenv(self.env_api_key) or _dotenv_value(self.env_api_key)
        if not api_key:
            raise ProviderConfigurationError(
                f"Provider {self.profile_id} requires environment variable "
                f"{self.env_api_key}."
            )

        started = time.perf_counter()
        raw = (self.transport or _urllib_json_transport)(
            url=_chat_completions_url(self.base_url),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            payload=_payload_for(request, self.model),
            timeout_seconds=self.timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        text, finish_reason = _choice_text_and_reason(raw)
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


def _payload_for(request: LLMRequest, model: str) -> dict[str, Any]:
    return {
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


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _choice_text_and_reason(raw: dict[str, Any]) -> tuple[str, str]:
    choices = raw.get("choices", [])
    if not choices:
        raise ProviderRuntimeError("Provider response did not include choices.")
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
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderRuntimeError(
            f"Provider request failed with HTTP {exc.code}: {_short_error(body)}"
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderRuntimeError(f"Provider request failed: {exc}") from exc


def _short_error(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= 240:
        return compact
    return compact[:239] + "..."


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
