from novel2script.reviewers.shootability import review_shootability


def _trace():
    return {"chapter": 1, "paragraph_range": [1, 1], "note": "fixture trace"}


def _tags():
    return {"inferred": True, "confidence": "medium", "needs_human_review": True}


def test_reports_short_externalized_action():
    screenplay = {
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [
                    {
                        "id": "beat_001",
                        "externalized_action": "想",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
                "elements": [{"type": "action", "text": "She looks up.", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ]
    }

    result = review_shootability(screenplay)

    issue = result["issues"][0]
    assert result["reviewer"] == "shootability"
    assert issue["target_id"] == "beat_001"
    assert issue["severity"] in {"medium", "high"}
    assert issue["suggested_patch"]["operation"] == "note_only"


def test_reports_scene_with_only_note_elements():
    screenplay = {
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [
                    {
                        "id": "beat_001",
                        "externalized_action": "She closes the envelope.",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
                "elements": [{"type": "note", "text": "Review later.", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ]
    }

    result = review_shootability(screenplay)

    assert any(issue["target"]["type"] == "scene" for issue in result["issues"])
    assert any("action" in issue["issue"].lower() for issue in result["issues"])


def test_reports_internal_action_wording_without_visible_behavior():
    screenplay = {
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [
                    {
                        "id": "beat_001",
                        "externalized_action": "她意识到自己心里害怕。",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
                "elements": [{"type": "action", "text": "她心里觉得害怕。", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ]
    }

    result = review_shootability(screenplay)

    assert any(issue["confidence"] == "medium" for issue in result["issues"])
    assert all(issue["requires_human_approval"] is True for issue in result["issues"])
