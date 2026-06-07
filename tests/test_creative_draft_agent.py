from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

from novel2script.agents.creative_draft import run_kimi_dialogue_scene_drafter
from novel2script.llm.types import LLMResponse


ROOT = Path(__file__).resolve().parents[1]
SCREENPLAY = ROOT / "examples" / "output" / "test1_sanguo_screenplay.yaml"
AUTHOR_REVIEW_REPORT = (
    ROOT / "examples" / "output" / "test1_sanguo_author_review_report.yaml"
)
REVIEW_REPORT = ROOT / "examples" / "output" / "test1_sanguo_review_report.yaml"
QUALITY_REPORT = ROOT / "examples" / "output" / "test1_sanguo_quality_report.yaml"
SCHEMA = ROOT / "schemas" / "creative_draft_candidates.schema.json"
PROVIDER_PAYLOAD_RETAINED_FIELD = "provider_" + "body_retained"
PROVIDER_PAYLOAD_MARKER = "provider_" + "body"
MODEL_RESPONSE_MARKER = "raw" + "_response"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate_creative_doc(doc: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(doc)


def test_mock_drafter_writes_schema_valid_human_review_candidates(tmp_path):
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"
    before = SCREENPLAY.read_bytes()

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=True,
    )

    assert SCREENPLAY.read_bytes() == before
    assert result == _load_yaml(out_path)
    _validate_creative_doc(result)
    creative = result["creative_draft_candidates"]
    assert creative["agent_id"] == "kimi_dialogue_scene_drafter"
    assert creative["provider_profile"] == "mock_dry_run"
    assert creative["dry_run"] is True
    assert creative["human_approval_required"] is True
    assert creative["metadata"]["intended_provider_profile"] == "kimi_creative"
    assert creative["metadata"]["prompt_retained"] is False
    assert creative["metadata"]["model_response_retained"] is False
    assert creative["metadata"][PROVIDER_PAYLOAD_RETAINED_FIELD] is False

    candidate_types = {candidate["type"] for candidate in creative["candidates"]}
    assert {
        "dialogue_insert",
        "beat_externalization",
        "scene_action_enhancement",
    }.issubset(candidate_types)
    for candidate in creative["candidates"]:
        assert candidate["merge_policy"] == "human_approval_required"
        assert candidate["requires_author_approval"] is True
        assert candidate["source_trace"]["note"]
        assert candidate["source_trace_ids"]["chapter_id"].startswith("ch_")
        assert candidate["source_trace_ids"]["paragraph_ids"]


def test_mock_drafter_targets_existing_screenplay_scene_and_beat(tmp_path):
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"
    screenplay = _load_yaml(SCREENPLAY)
    scene_ids = {scene["id"] for scene in screenplay["scenes"]}
    beat_ids = {
        beat["id"]
        for scene in screenplay["scenes"]
        for beat in scene.get("beats", [])
    }

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=True,
    )

    for candidate in result["creative_draft_candidates"]["candidates"]:
        target = candidate["target"]
        assert target["scene_id"] in scene_ids
        if "beat_id" in target:
            assert target["beat_id"] in beat_ids


def test_mock_drafter_fail_closed_when_author_review_not_authorized(tmp_path):
    unauthorized = _load_yaml(AUTHOR_REVIEW_REPORT)
    unauthorized["author_review_report"]["next_stage_authorization"] = "none"
    unauthorized_path = tmp_path / "unauthorized_author_review.yaml"
    unauthorized_path.write_text(
        yaml.safe_dump(unauthorized, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=unauthorized_path,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=True,
    )

    _validate_creative_doc(result)
    creative = result["creative_draft_candidates"]
    assert creative["candidates"] == []
    assert creative["errors"][0]["code"] == "author_review_not_authorized"


def test_mock_drafter_fail_closed_when_screenplay_has_no_target(tmp_path):
    screenplay = _load_yaml(SCREENPLAY)
    screenplay["scenes"] = []
    screenplay_path = tmp_path / "empty_screenplay.yaml"
    screenplay_path.write_text(
        yaml.safe_dump(screenplay, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=screenplay_path,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=True,
    )

    _validate_creative_doc(result)
    creative = result["creative_draft_candidates"]
    assert creative["candidates"] == []
    assert creative["errors"][0]["code"] == "missing_screenplay_target"


def test_mock_drafter_run_log_redacts_prompt_and_model_response(tmp_path):
    out_path = tmp_path / "creative_candidates.yaml"
    run_log_path = tmp_path / "creative_run_log.yaml"
    screenplay = _load_yaml(SCREENPLAY)
    action_text = screenplay["scenes"][0]["elements"][0]["text"]

    run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=True,
    )

    run_log = run_log_path.read_text(encoding="utf-8")
    assert "stored_prompt: false" in run_log
    assert MODEL_RESPONSE_MARKER not in run_log
    assert PROVIDER_PAYLOAD_MARKER not in run_log
    assert "Kimi Dialogue Scene Drafter" not in run_log
    assert action_text not in run_log


class _FakeKimiRouter:
    def __init__(self, *, finish_reason: str = "stop") -> None:
        self.finish_reason = finish_reason
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
                                    "type": "dialogue_insert",
                                    "target": {
                                        "scene_id": "scene_001",
                                        "beat_id": "beat_001",
                                        "character_id": "char_001",
                                    },
                                    "proposed_text": "刘备低声说：愿与二位同心救民。",
                                    "rationale": "Adds a concise candidate line within the author-approved scene.",
                                    "source_trace": {
                                        "chapter": 1,
                                        "paragraph_range": [4, 4],
                                        "note": "Uses existing beat source trace.",
                                    },
                                    "source_trace_ids": {
                                        "chapter_id": "ch_001",
                                        "paragraph_ids": ["p_004"],
                                        "event_ids": ["evt_001"],
                                        "outline_scene_ids": ["osp_001"],
                                    },
                                    "constraints_observed": [
                                        "preserved_source_trace",
                                        "did_not_modify_screenplay",
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
                    usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    latency_ms=123,
                    finish_reason=self.finish_reason,
                    run_id="run_fake_kimi",
                ),
                "intended_profile": "kimi_creative",
                "resolved_profile": "kimi_creative",
            },
        )()


def test_real_drafter_fake_router_writes_schema_valid_redacted_candidates(tmp_path):
    out_path = tmp_path / "creative_candidates.real.yaml"
    run_log_path = tmp_path / "creative_run_log.real.yaml"
    router = _FakeKimiRouter()
    before = SCREENPLAY.read_bytes()

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=False,
        router=router,
    )

    assert SCREENPLAY.read_bytes() == before
    assert len(router.requests) == 1
    request = router.requests[0]
    assert request.agent_id == "kimi_dialogue_scene_drafter"
    assert request.response_format == "json_object"
    assert request.metadata["max_attempts"] == 1
    assert request.max_tokens == 32768
    prompt_payload = json.loads(request.prompt)
    assert prompt_payload["task"] == "Generate exactly 1 compact creative draft candidate."
    assert prompt_payload["max_candidates"] == 1
    assert prompt_payload["candidate_json_contract"]["confidence"] == [
        "low",
        "medium",
        "high",
    ]
    assert prompt_payload["candidate_json_contract"]["source_trace_ids"] == (
        "Use exactly the provided object; do not add quote_preview or note."
    )
    _validate_creative_doc(result)
    creative = result["creative_draft_candidates"]
    assert creative["provider_profile"] == "kimi_creative"
    assert creative["dry_run"] is False
    assert creative["errors"] == []
    assert creative["candidates"][0]["id"] == "crecand_001"
    assert creative["candidates"][0]["merge_policy"] == "human_approval_required"
    assert creative["candidates"][0]["requires_author_approval"] is True
    assert creative["metadata"]["retained_as_fixture"] is True
    assert creative["metadata"]["source_screenplay_hash_before"].startswith("sha256:")
    assert creative["metadata"]["source_screenplay_hash_after"] == creative["metadata"][
        "source_screenplay_hash_before"
    ]

    run_log = run_log_path.read_text(encoding="utf-8")
    assert "stored_prompt: false" in run_log
    assert "model_response_retained: false" in run_log
    assert "provider_payload_retained: false" in run_log
    assert "刘备低声说" not in run_log
    assert "Kimi Dialogue Scene Drafter" not in run_log
    assert MODEL_RESPONSE_MARKER not in run_log


class _FencedKimiRouter:
    def __init__(self) -> None:
        self.requests = []

    def dispatch(self, request):
        self.requests.append(request)
        model_text = """```json
{
  "candidates": [
    {
      "type": "dialogue_insert",
      "target": {
        "scene_id": "scene_001",
        "beat_id": "beat_001",
        "character_id": "char_001"
      },
      "proposed_text": "刘备低声说：愿与二位同心救民。",
      "rationale": "Adds a concise candidate line within the author-approved scene.",
      "source_trace": {
        "chapter": 1,
        "paragraph_range": [4, 4],
        "note": "Uses existing beat source trace."
      },
      "source_trace_ids": {
        "chapter_id": "ch_001",
        "paragraph_ids": ["p_004"],
        "event_ids": ["evt_001"],
        "outline_scene_ids": ["osp_001"]
      },
      "constraints_observed": [
        "preserved_source_trace",
        "did_not_modify_screenplay"
      ],
      "risks": ["requires author review"],
      "confidence": "medium"
    }
  ]
}
```"""
        return type(
            "Result",
            (),
            {
                "response": LLMResponse(
                    text=model_text,
                    model="kimi-k2.6",
                    provider="kimi_creative",
                    usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    latency_ms=123,
                    finish_reason="stop",
                    run_id="run_fake_kimi_fenced",
                ),
                "intended_profile": "kimi_creative",
                "resolved_profile": "kimi_creative",
            },
        )()


def test_real_drafter_accepts_fenced_json_without_retaining_model_text(tmp_path):
    out_path = tmp_path / "creative_candidates.real.yaml"
    run_log_path = tmp_path / "creative_run_log.real.yaml"

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=False,
        router=_FencedKimiRouter(),
    )

    _validate_creative_doc(result)
    creative = result["creative_draft_candidates"]
    assert creative["errors"] == []
    assert creative["candidates"][0]["proposed_text"] == (
        "刘备低声说：愿与二位同心救民。"
    )
    run_log = run_log_path.read_text(encoding="utf-8")
    assert "刘备低声说" not in run_log
    assert MODEL_RESPONSE_MARKER not in run_log


def test_real_drafter_fail_closed_on_truncated_output(tmp_path):
    out_path = tmp_path / "creative_candidates.real.yaml"
    run_log_path = tmp_path / "creative_run_log.real.yaml"

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=False,
        router=_FakeKimiRouter(finish_reason="length"),
    )

    assert result["creative_draft_candidates"]["errors"][0]["code"] == (
        "truncated_model_output"
    )
    assert not out_path.exists()
    run_log = yaml.safe_load(run_log_path.read_text(encoding="utf-8"))
    log = run_log["creative_draft_run_log"]
    assert log["status"] == "blocked"
    assert log["finish_reason"] == "length"
    assert log["stored_prompt"] is False


class _MissingRequiredFieldKimiRouter:
    def dispatch(self, request):
        return type(
            "Result",
            (),
            {
                "response": LLMResponse(
                    text=json.dumps(
                        {
                            "candidates": [
                                {
                                    "type": "dialogue_insert",
                                    "target": {
                                        "scene_id": "scene_001",
                                        "beat_id": "beat_001",
                                    },
                                    "proposed_text": "Candidate line.",
                                    "rationale": "Candidate rationale.",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    model="kimi-k2.6",
                    provider="kimi_creative",
                    usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    latency_ms=123,
                    finish_reason="stop",
                    run_id="run_fake_kimi_missing_required",
                ),
                "intended_profile": "kimi_creative",
                "resolved_profile": "kimi_creative",
            },
        )()


def test_real_drafter_fail_closed_instead_of_repairing_incomplete_model_candidate(
    tmp_path,
):
    out_path = tmp_path / "creative_candidates.real.yaml"
    run_log_path = tmp_path / "creative_run_log.real.yaml"

    result = run_kimi_dialogue_scene_drafter(
        screenplay_path=SCREENPLAY,
        author_review_report_path=AUTHOR_REVIEW_REPORT,
        review_report_path=REVIEW_REPORT,
        quality_report_path=QUALITY_REPORT,
        out_path=out_path,
        run_log_path=run_log_path,
        dry_run=False,
        router=_MissingRequiredFieldKimiRouter(),
    )

    assert result["creative_draft_candidates"]["candidates"] == []
    assert result["creative_draft_candidates"]["errors"][0]["code"] == (
        "invalid_model_candidate"
    )
    assert not out_path.exists()
    run_log = run_log_path.read_text(encoding="utf-8")
    assert MODEL_RESPONSE_MARKER not in run_log
    assert "Candidate line." not in run_log
