import asyncio
import json
import logging
import uuid
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import WorkflowExecution, ExecutionLog
from app.models.workflow import Workflow
from app.redis_client import publish

logger = logging.getLogger(__name__)

WORKFLOW_EXECUTION_TIMEOUT_S = 300


async def _load_agent_configs_from_db(db: AsyncSession, workflow: Workflow) -> dict[str, dict[str, Any]]:
    from app.services.agent_service import get_agent

    configs: dict[str, dict[str, Any]] = {}
    for node in workflow.nodes:
        if node.agent_id:
            agent = await get_agent(db, node.agent_id)
            if agent:
                configs[str(agent.id)] = {
                    "id": str(agent.id),
                    "name": agent.name,
                    "role": agent.role,
                    "system_prompt": agent.system_prompt,
                    "model": agent.model,
                    "tools": agent.tools or [],
                    "guardrails": agent.guardrails or {},
                    "max_tokens": agent.max_tokens,
                    "temperature": agent.temperature,
                    "memory_enabled": agent.memory_enabled,
                    "memory_window": agent.memory_window,
                }
    return configs


def _run_workflow_sync(
    workflow_id: str,
    nodes: list[dict],
    edges: list[dict],
    agents: dict[str, dict],
    input_data: dict[str, Any],
    thread_id: str | None = None,
    checkpoint_id: str | None = None,
) -> dict[str, Any]:
    # Must be synchronous — runs inside ProcessPoolExecutor
    from app.runtime.engine import compile_workflow

    compiled_graph, tid = compile_workflow(
        workflow_id=uuid.UUID(workflow_id),
        nodes=nodes,
        edges=edges,
        agents=agents,
        thread_id=thread_id,
    )

    config = {"configurable": {"thread_id": tid}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id

    initial_state = {
        "messages": [HumanMessage(content=input_data.get("query", input_data.get("message", "Hello")))],
        "current_step": 0,
        "agent_outputs": {},
        "handoff_context": {},
        "metadata": input_data,
    }

    result = compiled_graph.invoke(initial_state, config=config)
    return {
        "messages": [
            {"role": getattr(m, "type", "ai"), "content": m.content}
            for m in result.get("messages", [])
            if hasattr(m, "content")
        ],
        "agent_outputs": result.get("agent_outputs", {}),
        "current_step": result.get("current_step", 0),
    }


async def _check_concurrent_execution(db: AsyncSession, workflow_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.status == "running",
        )
    )
    return result.scalar_one_or_none() is not None


def _serialize_workflow(workflow: Workflow) -> tuple[list[dict], list[dict]]:
    nodes = [
        {
            "id": str(n.id),
            "agent_id": str(n.agent_id) if n.agent_id else None,
            "node_type": n.node_type,
            "label": n.label,
            "config": n.config,
        }
        for n in workflow.nodes
    ]
    edges = [
        {
            "source_node_id": str(e.source_node_id),
            "target_node_id": str(e.target_node_id),
            "condition": e.condition,
        }
        for e in workflow.edges
    ]
    return nodes, edges


async def start_workflow_execution(
    db: AsyncSession,
    workflow: Workflow,
    input_data: dict[str, Any],
) -> WorkflowExecution:
    if await _check_concurrent_execution(db, workflow.id):
        raise ValueError(
            f"Workflow {workflow.id} already has a running execution. "
            "Wait for it to finish or cancel it first."
        )

    execution = WorkflowExecution(
        workflow_id=workflow.id,
        status="running",
        input_data=input_data,
        started_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    agents = await _load_agent_configs_from_db(db, workflow)
    nodes, edges = _serialize_workflow(workflow)

    await publish(
        f"execution:{execution.id}:logs",
        json.dumps({"type": "execution_started", "execution_id": str(execution.id)}),
    )

    loop = asyncio.get_running_loop()
    try:
        from app.workers.pool import get_process_pool
        pool = get_process_pool()

        future = loop.run_in_executor(
            pool,
            _run_workflow_sync,
            str(workflow.id),
            nodes,
            edges,
            agents,
            input_data,
            str(execution.id),
            None,
        )
        result = await asyncio.wait_for(future, timeout=WORKFLOW_EXECUTION_TIMEOUT_S)

        total_tokens = 0
        total_cost = 0.0
        step_idx = 0
        for agent_id, data in result.get("agent_outputs", {}).items():
            if isinstance(data, dict):
                tokens = data.get("tokens", {})
                t = tokens.get("prompt", 0) + tokens.get("completion", 0)
                c = data.get("cost", 0.0)
                total_tokens += t
                total_cost += c

                log_entry = ExecutionLog(
                    execution_id=execution.id,
                    agent_id=uuid.UUID(agent_id) if agent_id else None,
                    step_index=step_idx,
                    input_data={},
                    output_data=data,
                    tokens_used=t,
                    cost=c,
                    duration_ms=data.get("duration_ms", 0),
                )
                db.add(log_entry)
                step_idx += 1

        execution.status = "completed"
        execution.total_tokens = total_tokens
        execution.total_cost = total_cost
        execution.finished_at = datetime.now(timezone.utc)

    except asyncio.TimeoutError:
        logger.error("Workflow execution timed out after %ds: %s", WORKFLOW_EXECUTION_TIMEOUT_S, execution.id)
        execution.status = "failed"
        execution.error_message = f"Execution timed out after {WORKFLOW_EXECUTION_TIMEOUT_S}s"
        execution.finished_at = datetime.now(timezone.utc)

    except Exception as exc:
        logger.exception("Workflow execution failed: %s", exc)
        execution.status = "failed"
        execution.error_message = str(exc)[:2000]
        execution.finished_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(execution)

    await publish(
        f"execution:{execution.id}:logs",
        json.dumps({
            "type": "execution_finished",
            "execution_id": str(execution.id),
            "status": execution.status,
        }),
    )

    return execution


async def resume_workflow_execution(
    db: AsyncSession,
    workflow: Workflow,
    checkpoint_id: str,
    input_data: dict[str, Any],
) -> WorkflowExecution:
    execution = WorkflowExecution(
        workflow_id=workflow.id,
        status="running",
        input_data={"resumed_from": checkpoint_id, **input_data},
        started_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    agents = await _load_agent_configs_from_db(db, workflow)
    nodes, edges = _serialize_workflow(workflow)

    loop = asyncio.get_running_loop()
    try:
        from app.workers.pool import get_process_pool
        pool = get_process_pool()

        future = loop.run_in_executor(
            pool,
            _run_workflow_sync,
            str(workflow.id),
            nodes,
            edges,
            agents,
            input_data,
            str(execution.id),
            checkpoint_id,
        )
        result = await asyncio.wait_for(future, timeout=WORKFLOW_EXECUTION_TIMEOUT_S)

        execution.status = "completed"
        execution.finished_at = datetime.now(timezone.utc)

    except asyncio.TimeoutError:
        logger.error("Resumed execution timed out: %s", execution.id)
        execution.status = "failed"
        execution.error_message = f"Execution timed out after {WORKFLOW_EXECUTION_TIMEOUT_S}s"
        execution.finished_at = datetime.now(timezone.utc)

    except Exception as exc:
        logger.exception("Resumed workflow execution failed: %s", exc)
        execution.status = "failed"
        execution.error_message = str(exc)[:2000]
        execution.finished_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(execution)
    return execution
