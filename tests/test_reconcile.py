from coordinator.reconcile import reconcile


def test_normal_case_no_duplicate():
    result = reconcile(
        duplicate_verdict={"is_duplicate": False, "confidence": 0.1, "candidate_issue_number": None, "reasoning": "no match"},
        label_verdict={"type_label": "bug", "reasoning": "clearly a defect"},
        priority_verdict={"priority_label": "priority:p1", "reasoning": "affects core functionality"},
    )
    assert result.labels == ["bug", "priority:p1"]
    assert not result.notes
    assert "duplicate" not in result.comment_body.lower()


def test_high_confidence_duplicate_still_gets_labeled():
    result = reconcile(
        duplicate_verdict={"is_duplicate": True, "confidence": 0.95, "candidate_issue_number": 1, "reasoning": "same root cause"},
        label_verdict={"type_label": "bug", "reasoning": "defect"},
        priority_verdict={"priority_label": "priority:p0", "reasoning": "critical"},
    )
    assert result.labels == ["bug", "priority:p0"]  # still labeled despite being a likely duplicate
    assert "Likely duplicate of #1" in result.comment_body


def test_candidate_issue_number_formatted_as_int_not_float():
    # Numbers round-trip through the A2A artifact as protobuf doubles, so
    # a real specialist response has candidate_issue_number as 1.0, not 1.
    result = reconcile(
        duplicate_verdict={"is_duplicate": True, "confidence": 0.95, "candidate_issue_number": 1.0, "reasoning": "same bug"},
        label_verdict=None,
        priority_verdict=None,
    )
    assert "#1" in result.comment_body
    assert "#1.0" not in result.comment_body


def test_low_confidence_duplicate_is_phrased_as_possible():
    result = reconcile(
        duplicate_verdict={"is_duplicate": True, "confidence": 0.6, "candidate_issue_number": 7, "reasoning": "similar topic"},
        label_verdict=None,
        priority_verdict=None,
    )
    assert "Possible duplicate of #7" in result.comment_body


def test_very_low_confidence_duplicate_is_not_mentioned():
    result = reconcile(
        duplicate_verdict={"is_duplicate": True, "confidence": 0.3, "candidate_issue_number": 9, "reasoning": "weak match"},
        label_verdict=None,
        priority_verdict=None,
    )
    assert "duplicate" not in result.comment_body.lower()


def test_question_caps_priority():
    result = reconcile(
        duplicate_verdict=None,
        label_verdict={"type_label": "question", "reasoning": "just asking"},
        priority_verdict={"priority_label": "priority:p0", "reasoning": "scorer thought it urgent"},
    )
    assert result.labels == ["question", "priority:p2"]
    assert any("capped" in note for note in result.notes)


def test_question_does_not_raise_an_already_low_priority():
    result = reconcile(
        duplicate_verdict={"is_duplicate": False, "confidence": 0.0, "candidate_issue_number": None, "reasoning": ""},
        label_verdict={"type_label": "question", "reasoning": "just asking"},
        priority_verdict={"priority_label": "priority:p3", "reasoning": "not urgent"},
    )
    assert result.labels == ["question", "priority:p3"]
    assert not result.notes  # cap only fires when it would actually lower the priority


def test_missing_priority_scorer():
    result = reconcile(
        duplicate_verdict={"is_duplicate": False, "confidence": 0.0, "candidate_issue_number": None, "reasoning": ""},
        label_verdict={"type_label": "bug", "reasoning": "defect"},
        priority_verdict=None,
    )
    assert result.labels == ["bug"]
    assert "Priority scoring unavailable." in result.notes


def test_all_three_missing():
    result = reconcile(duplicate_verdict=None, label_verdict=None, priority_verdict=None)
    assert result.labels == []
    assert len(result.notes) == 3
    assert result.comment_body  # never empty, even with nothing to report


def test_two_specialists_missing_at_once():
    result = reconcile(
        duplicate_verdict=None,
        label_verdict=None,
        priority_verdict={"priority_label": "priority:p1", "reasoning": "seems significant"},
    )
    assert result.labels == ["priority:p1"]
    assert "Duplicate check unavailable." in result.notes
    assert "Labeling unavailable." in result.notes
