"""
Phase 0 milestone: connect to GitHub's hosted MCP server and list its tools.

This is deliberately the very first thing we run: before writing any agent
or A2A code, see what an MCP "tool" actually is on the wire - a name, a
description, and a JSON Schema for its inputs. Every specialist agent we
build later is just: call session.list_tools() (or already know the name),
then session.call_tool(name, arguments).
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


async def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Set GITHUB_TOKEN in your .env file first (copy .env.example -> .env).", file=sys.stderr)
        raise SystemExit(1)

    headers = {"Authorization": f"Bearer {token}"}

    async with streamablehttp_client(GITHUB_MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            print(f"Connected to GitHub's MCP server. {len(result.tools)} tools available:\n")
            for tool in result.tools:
                print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
