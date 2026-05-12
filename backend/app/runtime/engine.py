import logging
import operator
import uuid
from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.runtime.agent_node import create_agent_node

logger = logging.getLogger(__name__)

MAX_LOOP_ITERATIONS = 10


def _merge_handoff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if not old:
        return new
    if not new:
        return old
    merged = dict(new)
    old_facts = old.get("accumulated_facts", [])
    new_facts = new.get("accumulated_facts", [])
    seen = set()
    combined = []
    for fact in old_facts + new_facts:
        if fact not in seen:
            seen.add(fact)
            combined.append(fact)
    merged["accumulated_facts"] = combined
    return merged


def _merge_dict(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(old)
    merged.update(new)
    return merged


class WorkflowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_step: int
    agent_outputs: Annotated[dict[str, Any], _merge_dict]
    handoff_context: Annotated[dict[str, Any], _merge_handoff]
    metadata: dict[str, Any]


def _build_condition_func(condition_config: dict[str, Any], max_iterations: int = MAX_LOOP_ITERATIONS):
    field = condition_config.get("field", "")
    op = condition_config.get("op", "eq")
    value = condition_config.get("value", "")
    true_target = condition_config.get("true_target")
    false_target = condition_config.get("false_target", END)

    loop_count = {"n": 0}

    def condition_fn(state: WorkflowState) -> str:
        loop_count["n"] += 1
        if loop_count["n"] > max_iterations:
            logger.warning(
                "Loop guard triggered after %d iterations, forcing END",
                max_iterations,
            )
            return END

        last_output = ""
        for agent_id, data in state.get("agent_outputs", {}).items():
            if isinstance(data, dict):
                last_output = data.get("output", "")

        if field and field in state.get("agent_outputs", {}):
            data = state["agent_outputs"][field]
            last_output = data.get("output", "") if isinstance(data, dict) else str(data)

        if op == "eq":
            match = last_output.strip().lower() == str(value).lower()
        elif op == "contains":
            match = str(value).lower() in last_output.lower()
        elif op == "ne":
            match = last_output.strip().lower() != str(value).lower()
        else:
            match = False

        return true_target if match else false_target

    return condition_fn


def compile_workflow(
    workflow_id: uuid.UUID,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    agents: dict[str, dict[str, Any]],
    thread_id: str | None = None,
):
    graph = StateGraph(WorkflowState)

    node_name_map: dict[str, str] = {}
    entry_node_name: str | None = None

    for node in nodes:
        node_id = str(node["id"])
        node_type = node.get("node_type", "agent")
        label = node.get("label") or f"node_{node_id[:8]}"
        node_name = label.replace(" ", "_").lower()
        node_name_map[node_id] = node_name

        if node_type == "entry":
            entry_node_name = node_name
            continue
        if node_type == "exit":
            continue

        agent_id = str(node.get("agent_id", ""))
        agent_config = agents.get(agent_id)
        if not agent_config:
            logger.warning("No agent config for node %s (agent_id=%s), skipping", node_id, agent_id)
            continue

        agent_fn = create_agent_node(agent_config, execution_id=str(workflow_id))
        graph.add_node(node_name, agent_fn)

    if not entry_node_name:
        first_agent_nodes = [
            node_name_map[str(n["id"])]
            for n in nodes
            if n.get("node_type", "agent") == "agent" and str(n["id"]) in node_name_map
        ]
        if first_agent_nodes:
            entry_node_name = first_agent_nodes[0]

    if entry_node_name:
        graph.add_edge(START, entry_node_name)

    for edge in edges:
        src_id = str(edge["source_node_id"])
        tgt_id = str(edge["target_node_id"])
        src_name = node_name_map.get(src_id)
        tgt_name = node_name_map.get(tgt_id, END)
        condition = edge.get("condition")

        if not src_name:
            continue

        exit_nodes = [str(n["id"]) for n in nodes if n.get("node_type") == "exit"]
        if tgt_id in exit_nodes:
            tgt_name = END

        if condition:
            resolved_condition = dict(condition)
            true_target = resolved_condition.get("true_target")
            false_target = resolved_condition.get("false_target", END)
            if true_target and true_target in node_name_map:
                resolved_condition["true_target"] = node_name_map[true_target]
            elif true_target:
                resolved_condition["true_target"] = true_target
            if false_target and false_target in node_name_map:
                resolved_condition["false_target"] = node_name_map[false_target]
            elif false_target != END:
                resolved_condition["false_target"] = false_target

            cond_fn = _build_condition_func(resolved_condition)
            targets = {
                resolved_condition.get("true_target", tgt_name): resolved_condition.get("true_target", tgt_name),
                resolved_condition.get("false_target", END): resolved_condition.get("false_target", END),
            }
            graph.add_conditional_edges(src_name, cond_fn, list(targets.values()))
        else:
            graph.add_edge(src_name, tgt_name)

    from app.runtime.checkpointer import get_sync_checkpointer
    checkpointer = get_sync_checkpointer()
    compiled = graph.compile(checkpointer=checkpointer)

    return compiled, thread_id or str(workflow_id)
