"""Shared boilerplate for manually testing a single specialist agent."""

import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import new_data_message
from a2a.types import Role, SendMessageRequest


async def send_and_log(port: int, payload: dict, out_path: str) -> None:
    # LLM calls (especially reasoning models) + multiple MCP round-trips can
    # exceed the client's short default timeout - this is a slow pipeline,
    # not a broken one, so we give it real headroom.
    long_timeout_client = httpx.AsyncClient(timeout=120.0)
    client = await create_client(f"http://localhost:{port}", client_config=ClientConfig(httpx_client=long_timeout_client))

    message = new_data_message(payload, role=Role.ROLE_USER)
    request = SendMessageRequest(message=message)

    async for response in client.send_message(request):
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(str(response) + "\n\n")
        print(f"response received, see {out_path}")
