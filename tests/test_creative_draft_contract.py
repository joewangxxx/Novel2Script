from pathlib import Path
import json
import re

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_creative_draft_schema_accepts_minimal_fixture():
    schema = load_json("schemas/creative_draft_candidates.schema.json")
    fixture = {
        "creative_draft_candidates": {
            "schema_version": "0.1.0",
            "source_screenplay": "examples/output/test1_sanguo_screenplay.yaml",
            "source_author_review_report": "examples/output/test1_sanguo_author_review_report.yaml",
            "agent_id": "kimi_dialogue_scene_drafter",
            "provider_profile": "kimi_creative",
            "dry_run": False,
            "human_approval_required": True,
            "authorization": {
                "source": "author_review_report",
                "next_stage_authorization": "kimi_dialogue_draft",
                "scope": ["dialogue", "scene_action"],
            },
            "candidates": [
                {
                    "id": "crecand_001",
                    "type": "dialogue_insert",
                    "target": {
                        "scene_id": "scene_001",
                        "beat_id": "beat_001",
                        "character_id": "char_001",
                    },
                    "proposed_text": "A short candidate line.",
                    "rationale": "Adds dialogue where the author requested dialogue drafting.",
                    "source_trace": {
                        "chapter": 1,
                        "paragraph_range": [1, 1],
                        "note": "Inherited from target scene evidence.",
                    },
                    "source_trace_ids": {
                        "chapter_id": "ch_001",
                        "paragraph_ids": ["p_001"],
                    },
                    "constraints_observed": [
                        "did_not_modify_screenplay",
                        "preserved_source_trace",
                    ],
                    "risks": ["requires_author_review"],
                    "confidence": "medium",
                    "merge_policy": "human_approval_required",
                    "requires_author_approval": True,
                }
            ],
            "errors": [],
            "metadata": {
                "prompt_retained": False,
                "model_response_retained": False,
                "provider_body_retained": False,
                "full_source_text_retained": False,
            },
        }
    }
    Draft202012Validator(schema).validate(fixture)


def test_kimi_dialogue_scene_drafter_routing_is_human_approval_required():
    routing = load_yaml("config/agent_routing.example.yaml")
    agent = routing["agents"]["kimi_dialogue_scene_drafter"]
    assert agent["provider_profile"] == "kimi_creative"
    assert agent["fallback_profile"] == "mock_dry_run"
    assert agent["prompt_file"] == "docs/prompts/kimi_dialogue_scene_drafter.md"
    assert agent["output_policy"] == "human_approval_required"


def test_prompt_documents_candidate_only_boundaries_without_secrets():
    prompt_path = ROOT / "docs/prompts/kimi_dialogue_scene_drafter.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    required_phrases = [
        "only generate candidates",
        "do not modify screenplay",
        "author_review_report",
        "scene_id",
        "element_id",
        "source_trace",
        "reviewer_note",
        "Do not output Markdown",
        "Do not reveal chain-of-thought",
    ]
    for phrase in required_phrases:
        assert phrase in prompt
    forbidden_patterns = [
        r"sk-[A-Za-z0-9_-]{16,}",
        r"Bearer\s+[A-Za-z0-9._-]{20,}",
        r"Authorization\s*:\s*Bearer",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, prompt, re.IGNORECASE)


def test_stage17_contract_states_no_automatic_screenplay_mutation():
    doc = (ROOT / "docs/dev/PHASE_17_KIMI_DIALOGUE_SCENE_DRAFT_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    required_phrases = [
        "must not modify screenplay",
        "must not modify source_trace",
        "human approval",
        "does not call Kimi",
        "does not call any real LLM",
        "Stage 18",
    ]
    for phrase in required_phrases:
        assert phrase in doc
