"""Pure metric functions over (predictions, ground_truth) - no network, easy to test."""


def type_accuracy(predictions: dict[int, dict], ground_truth: list[dict]) -> float:
    total, correct = 0, 0
    for entry in ground_truth:
        pred = predictions.get(entry["issue_number"], {})
        label_verdict = pred.get("label")
        if label_verdict is None:
            continue  # specialist failure isn't a wrong prediction, it's a missing one - excluded, not penalized
        total += 1
        if label_verdict.get("type_label") == entry["expected_type"]:
            correct += 1
    return correct / total if total else 0.0


def priority_accuracy(predictions: dict[int, dict], ground_truth: list[dict]) -> float:
    total, correct = 0, 0
    for entry in ground_truth:
        pred = predictions.get(entry["issue_number"], {})
        priority_verdict = pred.get("priority")
        if priority_verdict is None:
            continue
        total += 1
        if priority_verdict.get("priority_label") == entry["expected_priority"]:
            correct += 1
    return correct / total if total else 0.0


def duplicate_precision_recall_f1(predictions: dict[int, dict], ground_truth: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    for entry in ground_truth:
        pred = predictions.get(entry["issue_number"], {})
        duplicate_verdict = pred.get("duplicate")
        if duplicate_verdict is None:
            continue
        predicted_positive = bool(duplicate_verdict.get("is_duplicate"))
        actual_positive = entry["expected_duplicate_of"] is not None
        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif not predicted_positive and actual_positive:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def compute_metrics(predictions: dict[int, dict], ground_truth: list[dict]) -> dict:
    return {
        "type_accuracy": type_accuracy(predictions, ground_truth),
        "priority_accuracy": priority_accuracy(predictions, ground_truth),
        "duplicate_detection": duplicate_precision_recall_f1(predictions, ground_truth),
        "n": len(ground_truth),
    }
