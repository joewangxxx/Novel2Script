from copy import deepcopy

from novel2script.reviewers.character_consistency import review_character_consistency


def _trace():
    return {"chapter": 1, "paragraph_range": [1, 1], "note": "fixture trace"}


def _tags():
    return {"inferred": True, "confidence": "medium", "needs_human_review": True}


def _screenplay():
    return {
        "characters": [
            {"id": "char_001", "name": "Lin", "locked": True, "source_trace": _trace()},
        ],
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [],
                "elements": [
                    {
                        "type": "dialogue",
                        "character_id": "char_missing",
                        "text": "Hello",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
            }
        ],
    }


def _character_bible():
    return {
        "character_bible": {
            "characters": [
                {
                    "id": "char_001",
                    "name": "Lin Original",
                    "locked": True,
                    "source_trace": [
                        {"chapter_id": "ch_001", "paragraph_ids": ["p_001"]}
                    ],
                }
            ]
        }
    }


def test_reports_missing_dialogue_character_as_note_only_issue():
    result = review_character_consistency(_screenplay(), _character_bible())

    issue = next(
        item for item in result["issues"] if item["target"]["type"] == "element"
    )
    assert result["reviewer"] == "character_consistency"
    assert issue["reviewer"] == "character_consistency"
    assert issue["target"]["type"] == "element"
    assert issue["target"]["yaml_path"] == "scenes[0].elements[0]"
    assert issue["severity"] == "high"
    assert issue["confidence"] == "high"
    assert issue["suggested_patch"]["operation"] == "note_only"
    assert issue["requires_human_approval"] is True


def test_reports_locked_character_name_mismatch_without_changing_character():
    screenplay = _screenplay()
    screenplay["scenes"][0]["elements"] = []

    result = review_character_consistency(screenplay, _character_bible())

    issue = result["issues"][0]
    assert "locked" in issue["issue"].lower()
    assert issue["target_id"] == "char_001"
    assert issue["target"]["type"] == "character"
    assert issue["suggested_patch"]["operation"] == "note_only"


def test_reports_character_missing_source_trace():
    screenplay = deepcopy(_screenplay())
    screenplay["characters"][0].pop("source_trace")
    screenplay["scenes"][0]["elements"] = []
    bible = {"character_bible": {"characters": []}}

    result = review_character_consistency(screenplay, bible)

    assert any("source_trace" in issue["issue"] for issue in result["issues"])
