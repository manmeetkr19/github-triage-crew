"""
Thin wrapper around GitHub's hosted MCP server, exposing only the
operations this crew actually needs. Each agent process opens its own
session (kept simple deliberately - a production system would pool
connections, but request volume here is low).
"""

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


class GitHubMCPClient:
    def __init__(self, token: str):
        self._headers = {"Authorization": f"Bearer {token}"}
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "GitHubMCPClient":
        read, write, _ = await self._stack.enter_async_context(
            streamablehttp_client(GITHUB_MCP_URL, headers=self._headers)
        )
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._stack.aclose()

    async def _call(self, name: str, arguments: dict) -> Any:
        assert self._session is not None, "use 'async with GitHubMCPClient(...)'"
        result = await self._session.call_tool(name, arguments)
        return json.loads(result.content[0].text)

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        return await self._call(
            "issue_read",
            {"method": "get", "owner": owner, "repo": repo, "issue_number": issue_number},
        )

    async def search_similar_issues(self, owner: str, repo: str, query: str) -> list[dict]:
        result = await self._call("search_issues", {"query": query, "owner": owner, "repo": repo})
        return result.get("items", [])

    async def update_issue(
        self, owner: str, repo: str, issue_number: int, *, labels: list[str] | None = None
    ) -> dict:
        args: dict[str, Any] = {"method": "update", "owner": owner, "repo": repo, "issue_number": issue_number}
        if labels is not None:
            args["labels"] = labels
        return await self._call("issue_write", args)

    async def add_comment(self, owner: str, repo: str, issue_number: int, body: str) -> dict:
        return await self._call(
            "add_issue_comment", {"owner": owner, "repo": repo, "issue_number": issue_number, "body": body}
        )
