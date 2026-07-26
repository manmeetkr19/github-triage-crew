"""
Seeds the sandbox repo with realistic test issues, including a deliberate
near-duplicate pair, so agents have something real to work against.

This starts small (Phase 1 needs just enough to test the Duplicate Detector).
It grows in Phase 7 into the larger seeded history the eval harness replays.
"""

import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

SEED_ISSUES = [
    {
        "title": "App crashes when uploading large CSV files",
        "body": (
            "When I try to upload a CSV file larger than 10MB, the app throws a "
            "500 Internal Server Error and the upload fails completely. Stack "
            "trace mentions a timeout in the file parser."
        ),
    },
    {
        "title": "500 error on big CSV upload",
        "body": (
            "Uploading a spreadsheet around 15MB in size results in a server "
            "error. Happens consistently with large files; smaller ones work fine."
        ),
    },
    {
        "title": "Add dark mode support",
        "body": (
            "It would be great to have a dark theme option in settings, "
            "especially for use at night."
        ),
    },
]


async def main() -> None:
    owner, repo = os.environ["GITHUB_REPO"].split("/")
    headers = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}

    async with streamablehttp_client("https://api.githubcopilot.com/mcp/", headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            for issue in SEED_ISSUES:
                result = await session.call_tool(
                    "issue_write",
                    {
                        "method": "create",
                        "owner": owner,
                        "repo": repo,
                        "title": issue["title"],
                        "body": issue["body"],
                    },
                )
                for c in result.content:
                    print(getattr(c, "text", c)[:200])


if __name__ == "__main__":
    asyncio.run(main())
