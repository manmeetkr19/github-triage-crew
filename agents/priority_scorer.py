"""
Priority Scorer - a standalone A2A server.

Given an issue, re-fetches it and asks the LLM to score it against our fixed
priority taxonomy (taxonomy.py) - priority:p0 (critical) through priority:p3
(low). Independent of the Labeler; the Coordinator reconciles the two later
(e.g. capping priority when the Labeler's type is "question").
"""

import os
import sys

from dotenv import load_dotenv

from a2a.helpers import get_data_parts, new_data_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._server import ensure_task, run  # noqa: E402
from clients.github_mcp_client import GitHubMCPClient  # noqa: E402
from clients.llm_client import LLMClient  # noqa: E402
from taxonomy import PRIORITY_LABELS  # noqa: E402

load_dotenv()

PORT = 8003

PRIORITY_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "priority_label": {"type": "string", "enum": list(PRIORITY_LABELS.keys())},
        "reasoning": {"type": "string"},
    },
    "required": ["priority_label", "reasoning"],
    "additionalProperties": False,
}

_TAXONOMY_TEXT = "\n".join(f"- {name}: {desc}" for name, desc in PRIORITY_LABELS.items())

SYSTEM_PROMPT = (
    "You are a priority scorer for a GitHub repository's issue tracker. Given an "
    f"issue, assign exactly one priority:\n{_TAXONOMY_TEXT}"
)


class PriorityScorerExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = await ensure_task(context, event_queue)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()

        [request] = get_data_parts(context.message.parts)
        owner, repo, issue_number = request["owner"], request["repo"], request["issue_number"]

        async with GitHubMCPClient(os.environ["GITHUB_TOKEN"]) as gh:
            issue = await gh.get_issue(owner, repo, issue_number)

        user_prompt = f"Issue #{issue_number}: {issue['title']}\n{issue['body']}"

        llm = LLMClient()
        verdict = await llm.structured_completion(
            SYSTEM_PROMPT, user_prompt, PRIORITY_VERDICT_SCHEMA, "priority_verdict"
        )

        await updater.add_artifact([new_data_part(verdict)], name="priority_verdict")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Priority scoring is a single quick step; cancellation isn't supported.")


def build_agent_card() -> AgentCard:
    return AgentCard(
        name="Priority Scorer",
        description="Scores a GitHub issue's priority (priority:p0 through priority:p3).",
        version="1.0.0",
        supported_interfaces=[AgentInterface(url=f"http://localhost:{PORT}/a2a", protocol_binding="JSONRPC")],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="score_priority",
                name="Score priority",
                description="Given an issue number, returns a priority label with reasoning.",
                tags=["github", "triage", "priority"],
            )
        ],
    )


if __name__ == "__main__":
    run(build_agent_card(), PriorityScorerExecutor(), PORT)
