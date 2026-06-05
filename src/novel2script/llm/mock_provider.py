from __future__ import annotations

from novel2script.llm.run_log import stable_run_id
from novel2script.llm.types import LLMRequest, LLMResponse


class MockLLMProvider:
    profile_id = "mock_dry_run"
    model = "mock-model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        text = (
            f"MOCK_RESPONSE agent={request.agent_id} task={request.task_type} "
            f"format={request.response_format} trace={request.trace_id}"
        )
        input_tokens = _token_estimate(request.prompt)
        output_tokens = _token_estimate(text)
        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.profile_id,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            latency_ms=0,
            finish_reason="dry_run",
            run_id=stable_run_id(request, self.profile_id),
        )


def _token_estimate(text: str) -> int:
    return max(1, (len(text) + 3) // 4)
