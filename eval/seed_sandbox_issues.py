"""
Builds the eval ground-truth set. Since this is a sandbox repo with no real
maintainer history, "ground truth" can't be scraped - it has to be a test
set we construct ourselves with known-correct answers per issue.

Issues #1-4 already exist from earlier phases; their expected answers are
recorded here from what we already manually confirmed was correct during
Phases 1-3. This script creates 6 more (two new duplicate pairs, a
question, and a feature request) and writes eval/ground_truth.json with
all 10 entries once real issue numbers are known.
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"

EXISTING_ISSUES = [
    {"issue_number": 1, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": None},
    {"issue_number": 2, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": 1},
    {"issue_number": 3, "expected_type": "feature", "expected_priority": "priority:p3", "expected_duplicate_of": None},
    {"issue_number": 4, "expected_type": "bug", "expected_priority": "priority:p1", "expected_duplicate_of": None},
]

NEW_ISSUES = [
    {
        "title": "Login fails with SSO right after a password reset",
        "body": "Right after resetting my password, trying to sign in via SSO just spins and then errors out. Regular password login works fine, only SSO is affected post-reset.",
        "expected_type": "bug",
        "expected_priority": "priority:p0",
        "expected_duplicate_of": None,
    },
    {
        "title": "Cannot sign in via SSO after changing password",
        "body": "After I change my password, SSO login stops working - it just hangs and eventually fails. Have to use password login instead, which does work.",
        "expected_type": "bug",
        "expected_priority": "priority:p0",
        "expected_duplicate_of": "prev",  # duplicate of the previous entry in this list
    },
    {
        "title": "Export button does nothing on Safari",
        "body": "Clicking the 'Export' button on the reports page has no effect in Safari. Works fine in Chrome and Firefox.",
        "expected_type": "bug",
        "expected_priority": "priority:p2",
        "expected_duplicate_of": None,
    },
    {
        "title": "Safari: export button is unresponsive",
        "body": "The export button on reports doesn't do anything when I click it in Safari. No error, nothing happens. Other browsers seem okay.",
        "expected_type": "bug",
        "expected_priority": "priority:p2",
        "expected_duplicate_of": "prev",
    },
    {
        "title": "How do I change my account email address?",
        "body": "I can't find a setting to update the email address on my account. Is this possible, and if so where?",
        "expected_type": "question",
        "expected_priority": "priority:p3",
        "expected_duplicate_of": None,
    },
    {
        "title": "Add CSV export option for reports",
        "body": "Right now reports can only be viewed on-screen. It would help a lot to be able to export them as CSV for further analysis.",
        "expected_type": "feature",
        "expected_priority": "priority:p2",
        "expected_duplicate_of": None,
    },
]


async def main() -> None:
    owner, repo = os.environ["GITHUB_REPO"].split("/")
    headers = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}

    created_numbers: list[int] = []

    async with streamablehttp_client("https://api.githubcopilot.com/mcp/", headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            for issue in NEW_ISSUES:
                result = await session.call_tool(
                    "issue_write",
                    {"method": "create", "owner": owner, "repo": repo, "title": issue["title"], "body": issue["body"]},
                )
                data = json.loads(result.content[0].text)
                issue_number = int(data["url"].rsplit("/", 1)[-1])
                created_numbers.append(issue_number)
                print(f"created #{issue_number}: {issue['title']}")

    ground_truth = list(EXISTING_ISSUES)
    for issue, issue_number in zip(NEW_ISSUES, created_numbers):
        expected_dup = issue["expected_duplicate_of"]
        if expected_dup == "prev":
            expected_dup = created_numbers[created_numbers.index(issue_number) - 1]
        ground_truth.append(
            {
                "issue_number": issue_number,
                "expected_type": issue["expected_type"],
                "expected_priority": issue["expected_priority"],
                "expected_duplicate_of": expected_dup,
            }
        )

    GROUND_TRUTH_PATH.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print(f"wrote {len(ground_truth)} entries to {GROUND_TRUTH_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
