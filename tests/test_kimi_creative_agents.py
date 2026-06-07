from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.kimi_creative_agents import (
    KIMI_CREATIVE_AGENT_IDS,
    run_kimi_creative_agent,
)
from novel2script.llm.types import LLMResponse


ROOT = Path(__file__).resolve().parents[1]
STORY_MAP = ROOT / "examples" / "output" / "test1_sanguo_story_map.merged.yaml"
OUTLINE = ROOT / "examples" / "output" / "test1_sanguo_outline.yaml"
CHARACTER_BIBLE = ROOT / "examples" / "output" / "test1_sanguo_character_bible.yaml"
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"
QUALITY_REPORT = ROOT / "examples" / "output" / "test1_sanguo_quality_report.yaml"


AGENT_INPUTS = {
    "adaptation_planner": {
        "story_map_path": STORY_MAP,
        "outline_path": OUTLINE,
        "quality_report_path": QUALITY_REPORT,
    },
    "character_bible_agent": {
        "story_map_path": STORY_MAP,
        "outline_path": OUTLINE,
        "character_bible_path": CHARACTER_BIBLE,
        "review_report_path": REVIEW_REPORT,
    },
    "scene_writer_agent": {
        "story_map_path": STORY_MAP,
        "outline_path": OUTLINE,
        "character_bible_path": CHARACTER_BIBLE,
        "screenplay_path": SCREENPLAY,
        "quality_report_path": QUALITY_REPORT,
    },
    "dialogue_optimizer_agent": {
        "screenplay_path": SCREENPLAY,
        "character_bible_path": CHARACTER_BIBLE,
        "review_report_path": REVIEW_REPORT,
        "quality_report_path": QUALITY_REPORT,
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


def test_mock_kimi_creative_agents_write_schema_valid_sidecars_and_run_logs(tmp_path):
    for agent_id in KIMI_CREATIVE_AGENT_IDS:
        out_path = tmp_path / f"{agent_id}.yaml"
        run_log_path = tmp_path / f"{agent_id}.run_log.yaml"

        result = run_kimi_creative_agent(
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
            assert candidate["source_trace"]
            assert candidate["source_trace_ids"]
            assert candidate["ai_tags"]["inferred"] is True
            assert candidate["ai_tags"]["needs_human_review"] is True
        run_log = _load_yaml(run_log_path)[f"{agent_id}_run_log"]
        assert run_log["stored_prompt"] is False
        assert run_log["model_response_retained"] is False
        assert run_log["provider_payload_retained"] is False
        assert run_log["candidate_count"] == len(sidecar["candidates"])


class _FakeKimiRouter:
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
                                    "target": {"path": "artifact[0]"},
                                    "proposed_text": "保留原结构，仅补充一条需人工确认的创意建议。",
                                    "rationale": "该建议遵守溯源与人工确认边界。",
                                    "source_trace": {
                                        "chapter_id": "ch_001",
                                        "paragraph_ids": ["p_004"],
                                    },
                                    "source_trace_ids": {
                                        "chapter_id": "ch_001",
                                        "paragraph_ids": ["p_004"],
                                    },
                                    "ai_tags": {
                                        "inferred": True,
                                        "confidence": "medium",
                                        "needs_human_review": True,
                                    },
                                    "constraints_observed": [
                                        "preserved_source_trace",
                                        "requires_author_approval",
                                    ],
                                    "risks": ["requires author review"],
                                    "confidence": "medium",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    model="kimi-k2.6",
                    provider="kimi_creative",
                    usage={"input_tokens": 11, "output_tokens": 22, "total_tokens": 33},
                    latency_ms=99,
                    finish_reason="stop",
                    run_id="run_fake_stage24",
                ),
                "intended_profile": "kimi_creative",
                "resolved_profile": "kimi_creative",
            },
        )()


def test_real_mode_fake_router_is_one_request_and_redacted(tmp_path):
    router = _FakeKimiRouter()
    out_path = tmp_path / "adaptation.real.yaml"
    run_log_path = tmp_path / "adaptation.real.run_log.yaml"

    result = run_kimi_creative_agent(
        agent_id="adaptation_planner",
        story_map_path=STORY_MAP,
        outline_path=OUTLINE,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=False,
        router=router,
    )

    assert len(router.requests) == 1
    request = router.requests[0]
    assert request.agent_id == "adaptation_planner"
    assert request.max_tokens == 32768
    assert request.metadata["max_attempts"] == 1
    Draft202012Validator(_schema_for("adaptation_planner")).validate(result)
    run_log_text = run_log_path.read_text(encoding="utf-8")
    assert "stored_prompt: false" in run_log_text
    assert "raw_response" not in run_log_text
    assert "provider_body" not in run_log_text
