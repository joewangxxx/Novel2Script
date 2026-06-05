from novel2script.reviewers.dialogue_naturalness import review_dialogue_naturalness


def _trace():
    return {"chapter": 1, "paragraph_range": [1, 1], "note": "fixture trace"}


def _tags(confidence="medium"):
    return {"inferred": True, "confidence": confidence, "needs_human_review": True}


def test_no_dialogue_is_skipped_without_issues():
    screenplay = {
        "characters": [{"id": "char_001", "name": "Lin"}],
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [],
                "elements": [{"type": "action", "text": "She waits.", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ],
    }

    result = review_dialogue_naturalness(screenplay)

    assert result["reviewer"] == "dialogue_naturalness"
    assert result["status"] == "skipped"
    assert result["issues"] == []


def test_reports_missing_dialogue_character_id():
    screenplay = {
        "characters": [{"id": "char_001", "name": "Lin"}],
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [],
                "elements": [
                    {
                        "type": "dialogue",
                        "text": "I saw the light.",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
            }
        ],
    }

    result = review_dialogue_naturalness(screenplay)

    issue = result["issues"][0]
    assert issue["target"]["type"] == "element"
    assert issue["severity"] == "high"
    assert "character_id" in issue["issue"]


def test_reports_expository_dialogue_and_long_parenthetical():
    long_dialogue = "因为所以我其实你知道吗我要告诉你" * 8
    screenplay = {
        "characters": [{"id": "char_001", "name": "Lin"}],
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [],
                "elements": [
                    {
                        "type": "dialogue",
                        "character_id": "char_001",
                        "text": long_dialogue,
                        "source_trace": _trace(),
                        "ai_tags": _tags("low"),
                    },
                    {
                        "type": "parenthetical",
                        "text": "speaking with a very long explanatory emotional instruction",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    },
                ],
            }
        ],
    }

    result = review_dialogue_naturalness(screenplay)

    assert len(result["issues"]) >= 2
    assert all(issue["suggested_patch"]["operation"] == "note_only" for issue in result["issues"])
    assert all(issue["requires_human_approval"] is True for issue in result["issues"])
