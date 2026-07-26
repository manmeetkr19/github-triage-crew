"""
Labeler - a standalone A2A server.

Given an issue, re-fetches it and asks the LLM to classify it against our
fixed type taxonomy (taxonomy.py) - bug/feature/question/docs. Only decides
type; priority is a separate agent's job (Priority Scorer).
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
from taxonomy import TYPE_LABELS  # noqa: E402

load_dotenv()

PORT = 8002

LABEL_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "type_label": {"type": "string", "enum": list(TYPE_LABELS.keys())},
        "reasoning": {"type": "string"},
    },
    "required": ["type_label", "reasoning"],
    "additionalProperties": False,
}

_TAXONOMY_TEXT = "\n".join(f"- {name}: {desc}" for name, desc in TYPE_LABELS.items())

SYSTEM_PROMPT = (
    "You are an issue labeler for a GitHub repository. Given an issue, classify "
    f"it into exactly one of these types:\n{_TAXONOMY_TEXT}"
)


class LabelerExecutor(AgentExecutor):
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
        verdict = await llm.structured_completion(SYSTEM_PROMPT, user_prompt, LABEL_VERDICT_SCHEMA, "label_verdict")

        await updater.add_artifact([new_data_part(verdict)], name="label_verdict")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Labeling is a single quick step; cancellation isn't supported.")


def build_agent_card() -> AgentCard:
    return AgentCard(
        name="Issue Labeler",
        description="Classifies a GitHub issue's type (bug/feature/question/docs).",
        version="1.0.0",
        supported_interfaces=[AgentInterface(url=f"http://localhost:{PORT}/a2a", protocol_binding="JSONRPC")],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="label_issue",
                name="Label issue",
                description="Given an issue number, returns a type label with reasoning.",
                tags=["github", "triage", "labeling"],
            )
        ],
    )


if __name__ == "__main__":
    run(build_agent_card(), LabelerExecutor(), PORT)
