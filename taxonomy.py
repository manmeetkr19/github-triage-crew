"""
Fixed label taxonomy for this crew, since GitHub's MCP toolset has no
"list all labels in this repo" tool - only get_label (one named label) and
issue_read(method=get_labels) (labels already on one issue). Rather than
add a raw REST fallback just to discover labels, we define our own small,
documented convention that the Labeler and Priority Scorer agents work
against, and that a maintainer could read and adjust directly.
"""

TYPE_LABELS = {
    "bug": "A defect - something that should work but doesn't.",
    "feature": "A request for new functionality that doesn't exist yet.",
    "question": "A question or request for clarification, not a defect or feature request.",
    "docs": "A documentation gap, error, or improvement.",
}

PRIORITY_LABELS = {
    "priority:p0": "Critical - blocks many users, security issue, or major data loss/corruption.",
    "priority:p1": "High - a significant bug affecting core functionality for a meaningful number of users.",
    "priority:p2": "Medium - a minor bug or a reasonable feature request.",
    "priority:p3": "Low - cosmetic, edge-case, or a question that isn't urgent.",
}
