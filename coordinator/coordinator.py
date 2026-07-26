"""
Coordinator - the A2A client + final decision-maker.

Fans a new issue out to the three specialists in parallel (genuine
concurrency via asyncio.gather, not sequential LLM calls in one process),
gives each a timeout so one slow/dead specialist can't block the whole
pipeline, reconciles their verdicts deterministically (reconcile.py), and
performs the final GitHub write (labels + one triage comment) itself.
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message
from a2a.types import Role, SendMessageRequest, TaskState

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients.github_mcp_client import GitHubMCPClient  # noqa: E402
from coordinator.reconcile import reconcile  # noqa: E402

load_dotenv()

SPECIALIST_URLS = {
    "duplicate": "http://localhost:8001",
    "label": "http://localhost:8002",
    "priority": "http://localhost:8003",
}

PER_SPECIALIST_TIMEOUT = 60.0


async def _call_specialist(name: str, url: str, payload: dict) -> dict | None:
    """Returns the specialist's verdict dict, or None if it failed/timed out.

    A missing result is a first-class outcome here, not an exception to
    propagate - one dead specialist should not sink the whole triage.
    """
    try:
        http_client = httpx.AsyncClient(timeout=PER_SPECIALIST_TIMEOUT)
        client = await create_client(url, client_config=ClientConfig(httpx_client=http_client))
        message = new_data_message(payload, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        async for response in client.send_message(request):
            task = response.task
            if task.status.state != TaskState.TASK_STATE_COMPLETED:
                return None
            if not task.artifacts:
                return None
            [verdict] = get_data_parts(task.artifacts[0].parts)
            return verdict
        return None
    except Exception:
        return None


async def triage_issue(owner: str, repo: str, issue_number: int) -> dict:
    payload = {"owner": owner, "repo": repo, "issue_number": issue_number}

    duplicate_verdict, label_verdict, priority_verdict = await asyncio.gather(
        _call_specialist("duplicate", SPECIALIST_URLS["duplicate"], payload),
        _call_specialist("label", SPECIALIST_URLS["label"], payload),
        _call_specialist("priority", SPECIALIST_URLS["priority"], payload),
    )

    result = reconcile(duplicate_verdict, label_verdict, priority_verdict)

    async with GitHubMCPClient(os.environ["GITHUB_TOKEN"]) as gh:
        if result.labels:
            await gh.update_issue(owner, repo, issue_number, labels=result.labels)
        await gh.add_comment(owner, repo, issue_number, result.comment_body)

    return {
        "issue_number": issue_number,
        "labels": result.labels,
        "notes": result.notes,
        "raw_verdicts": {
            "duplicate": duplicate_verdict,
            "label": label_verdict,
            "priority": priority_verdict,
        },
    }
