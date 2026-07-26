"""
Phase 1 checkpoint: send one manual message/send call to the running
Duplicate Detector agent (start agents/duplicate_detector.py first) and
watch the Task go working -> completed with a real verdict artifact.
"""

import asyncio

import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message
from a2a.types import Role, SendMessageRequest

AGENT_URL = "http://localhost:8001"


async def main() -> None:
    # LLM calls (especially reasoning models) + multiple MCP round-trips can
    # easily exceed the client's short default timeout - this is a slow
    # pipeline, not a broken one, so we give it real headroom.
    long_timeout_client = httpx.AsyncClient(timeout=120.0)
    client = await create_client(AGENT_URL, client_config=ClientConfig(httpx_client=long_timeout_client))

    message = new_data_message(
        {"owner": "manmeetkr19", "repo": "github-triage-crew-sandbox", "issue_number": 2},
        role=Role.ROLE_USER,
    )
    request = SendMessageRequest(message=message)

    async for response in client.send_message(request):
        with open("debug_response.txt", "a", encoding="utf-8") as f:
            f.write(str(response) + "\n\n")
        print("response received, see debug_response.txt")


if __name__ == "__main__":
    asyncio.run(main())
