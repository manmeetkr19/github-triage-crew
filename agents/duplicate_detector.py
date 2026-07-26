"""
Duplicate Detector - a standalone A2A server.

Given an issue's (owner, repo, issue_number), re-fetches the issue itself
(never trusts the caller's copy of the content - see docs/ARCHITECTURE.md),
searches for semantically similar issues via GitHub's MCP server, and asks
the LLM for a duplicate verdict. Returns the verdict as an A2A data artifact.
"""

import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from a2a.helpers import get_data_parts, new_data_part, new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import add_a2a_routes_to_fastapi, create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients.github_mcp_client import GitHubMCPClient  # noqa: E402
from clients.llm_client import LLMClient  # noqa: E402

load_dotenv()

PORT = 8001

DUPLICATE_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_duplicate": {"type": "boolean"},
        "confidence": {"type": "number"},
        "candidate_issue_number": {"type": ["integer", "null"]},
        "reasoning": {"type": "string"},
    },
    "required": ["is_duplicate", "confidence", "candidate_issue_number", "reasoning"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are a duplicate-issue detector for a GitHub repository. Given a target "
    "issue and a list of candidate existing issues, decide whether the target is "
    "a duplicate of one of the candidates. Only report a duplicate if they "
    "describe the same underlying problem, not just a similar topic."
)


class DuplicateDetectorExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()

        [request] = get_data_parts(context.message.parts)
        owner, repo, issue_number = request["owner"], request["repo"], request["issue_number"]

        async with GitHubMCPClient(os.environ["GITHUB_TOKEN"]) as gh:
            issue = await gh.get_issue(owner, repo, issue_number)
            candidates = await gh.search_similar_issues(owner, repo, issue["title"])
            candidates = [c for c in candidates if c["number"] != issue_number][:5]

        if candidates:
            candidate_text = "\n\n".join(f"#{c['number']}: {c['title']}\n{c['body']}" for c in candidates)
        else:
            candidate_text = "No candidate issues found."

        user_prompt = f"Target issue #{issue_number}: {issue['title']}\n{issue['body']}\n\nCandidates:\n{candidate_text}"

        llm = LLMClient()
        verdict = await llm.structured_completion(
            SYSTEM_PROMPT, user_prompt, DUPLICATE_VERDICT_SCHEMA, "duplicate_verdict"
        )

        await updater.add_artifact([new_data_part(verdict)], name="duplicate_verdict")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Duplicate detection is a single quick step; cancellation isn't supported.")


def build_agent_card() -> AgentCard:
    return AgentCard(
        name="Duplicate Issue Detector",
        description="Checks whether a newly opened GitHub issue is a likely duplicate of an existing issue.",
        version="1.0.0",
        supported_interfaces=[AgentInterface(url=f"http://localhost:{PORT}/a2a", protocol_binding="JSONRPC")],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="detect_duplicate_issue",
                name="Detect duplicate issue",
                description="Given an issue number, searches existing issues and returns a duplicate verdict.",
                tags=["github", "triage", "duplicate-detection"],
            )
        ],
    )


def build_app() -> FastAPI:
    agent_card = build_agent_card()
    handler = DefaultRequestHandler(
        agent_executor=DuplicateDetectorExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/a2a"),
    )
    return app


if __name__ == "__main__":
    uvicorn.run(build_app(), host="0.0.0.0", port=PORT)
