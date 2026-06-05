from __future__ import annotations

import hashlib

from novel2script.llm.types import LLMRequest, LLMResponse, LLMRunRecord


def prompt_hash(prompt: str) -> str:
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def stable_run_id(request: LLMRequest, provider: str) -> str:
    seed = "|".join(
        [
            request.agent_id,
            request.task_type,
            request.trace_id,
            request.response_format,
            provider,
            prompt_hash(request.prompt),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"llm_run_{digest}"


def build_run_record(
    request: LLMRequest,
    response: LLMResponse,
    *,
    status: str,
    intended_profile: str | None = None,
    resolved_profile: str | None = None,
) -> LLMRunRecord:
    return {
        "run_id": response.run_id,
        "trace_id": request.trace_id,
        "agent_id": request.agent_id,
        "task_type": request.task_type,
        "provider": response.provider,
        "model": response.model,
        "status": status,
        "finish_reason": response.finish_reason,
        "prompt_hash": prompt_hash(request.prompt),
        "prompt_chars": len(request.prompt),
        "stored_prompt": False,
        "usage": dict(response.usage),
        "latency_ms": response.latency_ms,
        "intended_profile": intended_profile or response.provider,
        "resolved_profile": resolved_profile or response.provider,
    }
