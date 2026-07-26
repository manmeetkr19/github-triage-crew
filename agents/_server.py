"""
Shared A2A server plumbing - identical across every specialist agent.
Domain logic (MCP calls, prompts, schemas) stays in each agent's own file;
only the wiring that's genuinely the same gets extracted here.
"""

import uvicorn
from fastapi import FastAPI

from a2a.helpers import new_task_from_user_message
from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import add_a2a_routes_to_fastapi, create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCard, Task


async def ensure_task(context: RequestContext, event_queue: EventQueue) -> Task:
    """Every execute() needs this: enqueue the initial Task before any status
    update, or the framework rejects the first TaskStatusUpdateEvent."""
    task = context.current_task
    if task is None:
        task = new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)
    return task


def build_app(agent_card: AgentCard, executor) -> FastAPI:
    handler = DefaultRequestHandler(
        agent_executor=executor,
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


def run(agent_card: AgentCard, executor, port: int) -> None:
    uvicorn.run(build_app(agent_card, executor), host="0.0.0.0", port=port)
