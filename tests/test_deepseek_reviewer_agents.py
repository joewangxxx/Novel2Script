from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.deepseek_reviewer_agents import (
    DEEPSEEK_REVIEWER_AGENT_IDS,
    run_deepseek_reviewer_agent,
)
from novel2script.llm.types import LLMResponse


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "test1_sanguo_story_map.merged.yaml"
OUTLINE = ROOT / "examples" / "output" / "test1_sanguo_outline.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "test1_sanguo_character_bible.yaml"
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"


AGENT_INPUTS = {
    "beat_dramaturgy_agent": {
        "screenplay_path": SCREENPLAY,
    },
    "source_fidelity_reviewer": {
        "story_map_path": STORY_MAP,
        "outline_path": OUTLINE,
        "screenplay_path": SCREENPLAY,
    },
    "yaml_repair_agent": {
        "screenplay_path": SCREENPLAY,
    },
}


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _schema_for(agent_id: str) -> dict:
    return json.loads(
        (ROOT / "schemas" / f"{agent_id}_candidates.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_mock_deepseek_reviewer_agents_write_schema_valid_sidecars_and_run_logs(tmp_path):
    for agent_id in DEEPSEEK_REVIEWER_AGENT_IDS:
        out_path = tmp_path / f"{agent_id}.yaml"
        run_log_path = tmp_path / f"{agent_id}.run_log.yaml"

        result = run_deepseek_reviewer_agent(
            agent_id=agent_id,
            out_path=out_path,
            run_log_path=run_log_path,
            dry_run=True,
            **AGENT_INPUTS[agent_id],
        )

        root_key = f"{agent_id}_candidates"
        Draft202012Validator(_schema_for(agent_id)).validate(result)
        assert result == _load_yaml(out_path)
        sidecar = result[root_key]
        assert sidecar["agent_id"] == agent_id
        assert sidecar["provider_profile"] == "mock_dry_run"
        assert sidecar["dry_run"] is True
        assert sidecar["human_approval_required"] is True
        assert sidecar["candidates"]
        assert sidecar["errors"] == []
        for candidate in sidecar["candidates"]:
            assert candidate["merge_policy"] == "human_approval_required"
            assert candidate["requires_author_approval"] is True
            assert candidate["ai_tags"]["inferred"] is True
            assert candidate["ai_tags"]["needs_human_review"] is True
        run_log = _load_yaml(run_log_path)[f"{agent_id}_run_log"]
        assert run_log["stored_prompt"] is False
        assert run_log["model_response_retained"] is False
        assert run_log["provider_payload_retained"] is False
        assert run_log["candidate_count"] == len(sidecar["candidates"])


class _FakeDeepSeekRouter:
    def __init__(self) -> None:
        self.requests = []

    def dispatch(self, request):
        self.requests.append(request)
        return type(
            "Result",
            (),
            {
                "response": LLMResponse(
                    text=json.dumps(
                        {
                            "candidates": [
                                {
                                    "type": "reviewer_note",
                                    "target": {"path": "scenes[0]"},
                                    "proposed_text": "建议针对该段落补充一条推理备忘，优化整体结构。",
                                    "rationale": "DeepSeek 审校推理发现该片段有细微缺陷。",
                                    "source_trace": {
                                        "chapter_id": "ch_001",
                                        "paragraph_ids": ["p_001"],
                                    },
                                    "source_trace_ids": {
                                        "chapter_id": "ch_001",
                                        "paragraph_ids": ["p_001"],
                                    },
                                    "ai_tags": {
                                        "inferred": True,
                                        "confidence": "high",
                                        "needs_human_review": True,
                                    },
                                    "constraints_observed": [
                                        "requires_author_approval",
                                    ],
                                    "risks": ["needs review"],
                                    "confidence": "high",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    model="deepseek-v4-pro",
                    provider="deepseek_reasoning",
                    usage={"input_tokens": 15, "output_tokens": 25, "total_tokens": 40},
                    latency_ms=120,
                    finish_reason="stop",
                    run_id="run_fake_deepseek_reviewer",
                ),
                "intended_profile": "deepseek_reasoning",
                "resolved_profile": "deepseek_reasoning",
            },
        )()


def test_real_mode_fake_router_is_one_request_and_redacted_deepseek(tmp_path):
    router = _FakeDeepSeekRouter()
    out_path = tmp_path / "fidelity.real.yaml"
    run_log_path = tmp_path / "fidelity.real.run_log.yaml"

    result = run_deepseek_reviewer_agent(
        agent_id="source_fidelity_reviewer",
        story_map_path=STORY_MAP,
        outline_path=OUTLINE,
        screenplay_path=SCREENPLAY,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=False,
        router=router,
    )

    assert len(router.requests) == 1
    request = router.requests[0]
    assert request.agent_id == "source_fidelity_reviewer"
    assert request.max_tokens == 4096
    assert request.metadata["max_attempts"] == 1
    Draft202012Validator(_schema_for("source_fidelity_reviewer")).validate(result)
    run_log_text = run_log_path.read_text(encoding="utf-8")
    assert "stored_prompt: false" in run_log_text
    assert "raw_response" not in run_log_text
    assert "provider_body" not in run_log_text
