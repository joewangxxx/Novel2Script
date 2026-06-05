from novel2script.reviewers.pacing import review_pacing


def _trace():
    return {"chapter": 1, "paragraph_range": [1, 1], "note": "fixture trace"}


def _tags():
    return {"inferred": True, "confidence": "medium", "needs_human_review": True}


def test_reports_scene_without_beats_as_high_severity():
    screenplay = {
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [],
                "elements": [{"type": "action", "text": "A door opens.", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ]
    }

    result = review_pacing(screenplay)

    issue = result["issues"][0]
    assert result["reviewer"] == "pacing"
    assert issue["target_id"] == "scene_001"
    assert issue["target"]["type"] == "scene"
    assert issue["severity"] == "high"
    assert issue["suggested_patch"]["operation"] == "note_only"


def test_reports_empty_turn_and_stakes_on_beat():
    screenplay = {
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": [
                    {
                        "id": "beat_001",
                        "objective": "Find the signal.",
                        "tactic": "Open the door.",
                        "obstacle": "Fog blocks the way.",
                        "conflict": "The signal keeps changing.",
                        "stakes": "   ",
                        "turn": "",
                        "externalized_action": "She opens the door.",
                        "source_trace": _trace(),
                        "ai_tags": _tags(),
                    }
                ],
                "elements": [{"type": "action", "text": "She opens the door.", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ]
    }

    result = review_pacing(screenplay)

    issue = result["issues"][0]
    assert issue["target_id"] == "beat_001"
    assert issue["target"]["yaml_path"] == "scenes[0].beats[0]"
    assert issue["severity"] == "medium"
    assert "turn" in issue["evidence"]["description"]
    assert "stakes" in issue["evidence"]["description"]


def test_reports_excessive_beat_density_as_low_severity():
    beats = [
        {
            "id": f"beat_{index:03d}",
            "objective": "Objective",
            "tactic": "Tactic",
            "obstacle": "Obstacle",
            "conflict": "Conflict",
            "stakes": "Stakes",
            "turn": "Turn",
            "externalized_action": "Visible action.",
            "source_trace": _trace(),
            "ai_tags": _tags(),
        }
        for index in range(1, 8)
    ]
    screenplay = {
        "scenes": [
            {
                "id": "scene_001",
                "source_trace": _trace(),
                "beats": beats,
                "elements": [{"type": "action", "text": "Visible action.", "source_trace": _trace(), "ai_tags": _tags()}],
            }
        ]
    }

    result = review_pacing(screenplay)

    assert any(issue["severity"] == "low" for issue in result["issues"])
