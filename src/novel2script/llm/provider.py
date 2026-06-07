from __future__ import annotations

from typing import Protocol

from novel2script.llm.types import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    profile_id: str
    model: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return a provider response for a request."""
