"""
Thin MCP client for our own audit_log_server.

Note: FastMCP wraps bare list/scalar tool returns in
structuredContent = {"result": [...]}, but content[0].text for a list
return only contains the FIRST item, not the whole list (confirmed live
against get_history) - so this client reads structuredContent, not
content[0].text, unlike github_mcp_client (whose tools all return objects,
where both forms agree).
"""

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

AUDIT_LOG_URL = "http://127.0.0.1:8010/mcp"


class AuditMCPClient:
    def __init__(self, url: str = AUDIT_LOG_URL):
        self._url = url
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "AuditMCPClient":
        read, write, _ = await self._stack.enter_async_context(streamablehttp_client(self._url))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._stack.aclose()

    async def _call(self, name: str, arguments: dict) -> Any:
        assert self._session is not None, "use 'async with AuditMCPClient()'"
        result = await self._session.call_tool(name, arguments)
        if result.structuredContent is not None:
            data = result.structuredContent
            if isinstance(data, dict) and set(data.keys()) == {"result"}:
                return data["result"]
            return data
        return json.loads(result.content[0].text)

    async def record_decision(
        self, repo: str, issue_number: int, labels: list[str], notes: list[str], raw_verdicts: dict
    ) -> dict:
        return await self._call(
            "record_decision",
            {"repo": repo, "issue_number": issue_number, "labels": labels, "notes": notes, "raw_verdicts": raw_verdicts},
        )

    async def get_history(self, repo: str, since: str | None = None) -> list[dict]:
        args: dict[str, Any] = {"repo": repo}
        if since is not None:
            args["since"] = since
        return await self._call("get_history", args)
