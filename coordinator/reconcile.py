"""
Deterministic reconciliation policy for the three specialists' verdicts.

Deliberately NOT a fourth "judge" LLM call: these rules are boring, but
boring is auditable - you can unit-test them, and you can report exactly
how often each rule fires (e.g. "the question->priority cap fired on 8%
of issues") as a real metric, which a judge model's improvised reasoning
would not give you.
"""

from dataclasses import dataclass, field

DUPLICATE_HIGH_CONFIDENCE = 0.8
DUPLICATE_LOW_CONFIDENCE = 0.5

PRIORITY_ORDER = ["priority:p0", "priority:p1", "priority:p2", "priority:p3"]
QUESTION_PRIORITY_CAP = "priority:p2"


@dataclass
class ReconciliationResult:
    labels: list[str]
    comment_body: str
    notes: list[str] = field(default_factory=list)


def _cap_priority(priority_label: str, cap: str) -> str:
    """Return whichever of the two is lower priority (larger index)."""
    return max([priority_label, cap], key=PRIORITY_ORDER.index)


def reconcile(
    duplicate_verdict: dict | None,
    label_verdict: dict | None,
    priority_verdict: dict | None,
) -> ReconciliationResult:
    notes: list[str] = []
    labels: list[str] = []
    comment_parts: list[str] = []

    # --- duplicate framing ---
    if duplicate_verdict is None:
        notes.append("Duplicate check unavailable.")
        comment_parts.append("_Duplicate check unavailable._")
    elif duplicate_verdict.get("is_duplicate"):
        confidence = duplicate_verdict.get("confidence", 0.0)
        candidate_raw = duplicate_verdict.get("candidate_issue_number")
        # Numbers round-trip through the A2A artifact as protobuf Struct
        # doubles, so an issue number like 1 comes back as 1.0.
        candidate = int(candidate_raw) if candidate_raw is not None else None
        reasoning = duplicate_verdict.get("reasoning", "")
        if confidence >= DUPLICATE_HIGH_CONFIDENCE:
            comment_parts.append(f"**Likely duplicate of #{candidate}** (confidence {confidence:.2f}): {reasoning}")
        elif confidence >= DUPLICATE_LOW_CONFIDENCE:
            comment_parts.append(f"**Possible duplicate of #{candidate}**, worth a look (confidence {confidence:.2f}): {reasoning}")
        # below DUPLICATE_LOW_CONFIDENCE: too weak a signal to even mention

    # --- type label ---
    type_label: str | None = None
    if label_verdict is None:
        notes.append("Labeling unavailable.")
    else:
        type_label = label_verdict.get("type_label")
        if type_label:
            labels.append(type_label)

    # --- priority label, with the question->cap rule ---
    if priority_verdict is None:
        notes.append("Priority scoring unavailable.")
    else:
        priority_label = priority_verdict.get("priority_label")
        if priority_label:
            if type_label == "question" and priority_label != _cap_priority(priority_label, QUESTION_PRIORITY_CAP):
                notes.append(
                    f"Priority capped from {priority_label} to {QUESTION_PRIORITY_CAP} (type=question)."
                )
                priority_label = QUESTION_PRIORITY_CAP
            labels.append(priority_label)

    # --- assemble comment ---
    if labels:
        comment_parts.append(f"Applied labels: {', '.join(labels)}.")
    if label_verdict and label_verdict.get("reasoning"):
        comment_parts.append(f"<details><summary>Labeling reasoning</summary>\n\n{label_verdict['reasoning']}\n</details>")
    if priority_verdict and priority_verdict.get("reasoning"):
        comment_parts.append(f"<details><summary>Priority reasoning</summary>\n\n{priority_verdict['reasoning']}\n</details>")
    for note in notes:
        comment_parts.append(f"_Note: {note}_")

    comment_body = "\n\n".join(comment_parts) if comment_parts else "Triage complete; no labels applied."

    return ReconciliationResult(labels=labels, comment_body=comment_body, notes=notes)
