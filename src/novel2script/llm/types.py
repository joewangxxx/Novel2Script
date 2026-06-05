from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    agent_id: str
    task_type: str
    prompt: str
    response_format: str
    temperature: float
    max_tokens: int
    trace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: dict[str, int]
    latency_ms: int
    finish_reason: str
    run_id: str


LLMRunRecord = dict[str, Any]
