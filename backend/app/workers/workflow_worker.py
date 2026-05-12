import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

_local_thread_pool: ThreadPoolExecutor | None = None


def _get_local_thread_pool(size: int = 5) -> ThreadPoolExecutor:
    global _local_thread_pool
    if _local_thread_pool is None:
        _local_thread_pool = ThreadPoolExecutor(max_workers=size)
    return _local_thread_pool


def execute_workflow_in_pool(
    workflow_id: str,
    nodes: list[dict],
    edges: list[dict],
    agents: dict[str, dict],
    input_data: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    from app.runtime.engine import compile_workflow

    compiled_graph, tid = compile_workflow(
        workflow_id=uuid.UUID(workflow_id),
        nodes=nodes,
        edges=edges,
        agents=agents,
        thread_id=thread_id,
    )

    config = {"configurable": {"thread_id": tid}}

    query = input_data.get("query", input_data.get("message", "Hello"))
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "current_step": 0,
        "agent_outputs": {},
        "handoff_context": {},
        "metadata": input_data,
    }

    result = compiled_graph.invoke(initial_state, config=config)

    return _serialize_result(result)


def resume_workflow_in_pool(
    workflow_id: str,
    nodes: list[dict],
    edges: list[dict],
    agents: dict[str, dict],
    input_data: dict[str, Any],
    thread_id: str,
    checkpoint_id: str,
) -> dict[str, Any]:
    from app.runtime.engine import compile_workflow

    compiled_graph, tid = compile_workflow(
        workflow_id=uuid.UUID(workflow_id),
        nodes=nodes,
        edges=edges,
        agents=agents,
        thread_id=thread_id,
    )

    config = {
        "configurable": {
            "thread_id": tid,
            "checkpoint_id": checkpoint_id,
        }
    }

    query = input_data.get("query", input_data.get("message", "Continue"))
    state_update = {
        "messages": [HumanMessage(content=query)],
    }

    result = compiled_graph.invoke(state_update, config=config)
    return _serialize_result(result)


def _serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    messages = []
    for m in result.get("messages", []):
        if hasattr(m, "content"):
            messages.append({
                "role": getattr(m, "type", "ai"),
                "content": m.content,
            })
    return {
        "messages": messages,
        "agent_outputs": result.get("agent_outputs", {}),
        "current_step": result.get("current_step", 0),
    }
