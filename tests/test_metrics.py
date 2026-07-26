from eval.metrics import compute_metrics


def test_perfect_predictions():
    ground_truth = [
        {"issue_number": 1, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": None},
        {"issue_number": 2, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": 1},
    ]
    predictions = {
        1: {"label": {"type_label": "bug"}, "priority": {"priority_label": "priority:p1"}, "duplicate": {"is_duplicate": False}},
        2: {"label": {"type_label": "bug"}, "priority": {"priority_label": "priority:p1"}, "duplicate": {"is_duplicate": True}},
    }
    metrics = compute_metrics(predictions, ground_truth)
    assert metrics["type_accuracy"] == 1.0
    assert metrics["priority_accuracy"] == 1.0
    assert metrics["duplicate_detection"]["precision"] == 1.0
    assert metrics["duplicate_detection"]["recall"] == 1.0


def test_missing_specialist_excluded_not_penalized():
    ground_truth = [{"issue_number": 1, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": None}]
    predictions = {1: {"label": None, "priority": {"priority_label": "priority:p1"}, "duplicate": None}}
    metrics = compute_metrics(predictions, ground_truth)
    assert metrics["type_accuracy"] == 0.0  # no data at all -> defined as 0, not silently 100%
    assert metrics["priority_accuracy"] == 1.0


def test_false_positive_duplicate_lowers_precision():
    ground_truth = [
        {"issue_number": 1, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": None},
        {"issue_number": 2, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": None},
    ]
    predictions = {
        1: {"label": None, "priority": None, "duplicate": {"is_duplicate": True}},  # wrongly flagged
        2: {"label": None, "priority": None, "duplicate": {"is_duplicate": False}},
    }
    metrics = compute_metrics(predictions, ground_truth)
    dd = metrics["duplicate_detection"]
    assert dd["fp"] == 1
    assert dd["precision"] == 0.0


def test_false_negative_duplicate_lowers_recall():
    ground_truth = [{"issue_number": 2, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": 1}]
    predictions = {2: {"label": None, "priority": None, "duplicate": {"is_duplicate": False}}}
    metrics = compute_metrics(predictions, ground_truth)
    dd = metrics["duplicate_detection"]
    assert dd["fn"] == 1
    assert dd["recall"] == 0.0
