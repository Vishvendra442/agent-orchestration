import json
import logging
import time
import uuid
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from app.config import settings
from app.runtime.guardrails import apply_input_guardrails, apply_output_guardrails

logger = logging.getLogger(__name__)

MODEL_COST_PER_1K = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    costs = MODEL_COST_PER_1K.get(model, {"prompt": 0.001, "completion": 0.002})
    return (prompt_tokens / 1000 * costs["prompt"]) + (completion_tokens / 1000 * costs["completion"])


def create_agent_node(agent_config: dict[str, Any], execution_id: str | None = None):
    agent_id = agent_config["id"]
    agent_name = agent_config["name"]
    system_prompt = agent_config["system_prompt"]
    model_name = agent_config.get("model", settings.OPENAI_MODEL)
    tool_names = agent_config.get("tools", [])
    guardrail_config = agent_config.get("guardrails", {})
    max_tokens = agent_config.get("max_tokens", 4096)
    temperature = agent_config.get("temperature", 0.7)

    from app.runtime.tools.registry import get_tools
    tools = get_tools(tool_names) if tool_names else []

    llm = ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    tools_by_name = {t.name: t for t in tools}

    def agent_node(state: dict[str, Any]) -> dict[str, Any]:
        start_time = time.time()

        messages = list(state.get("messages", []))
        handoff_context = state.get("handoff_context")

        input_text = ""
        if messages:
            last = messages[-1]
            if hasattr(last, "content"):
                input_text = last.content

        try:
            input_text = apply_input_guardrails(input_text, guardrail_config)
        except Exception as exc:
            logger.warning("Input guardrail violation for agent %s: %s", agent_name, exc)
            return {
                "messages": messages + [AIMessage(content=f"[Guardrail blocked] {exc}")],
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    str(agent_id): {"error": str(exc)},
                },
            }

        sys_msg = SystemMessage(content=system_prompt)
        if handoff_context:
            context_str = (
                f"\n\nContext from previous agent ({handoff_context.get('from_agent_name', 'unknown')}):\n"
                f"{handoff_context.get('output', '')}"
            )
            sys_msg = SystemMessage(content=system_prompt + context_str)

        invocation_messages = [sys_msg] + messages

        response = llm_with_tools.invoke(invocation_messages)

        all_messages = messages + [response]

        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_results = []
            for tc in response.tool_calls:
                tool_fn = tools_by_name.get(tc["name"])
                if tool_fn:
                    try:
                        observation = tool_fn.invoke(tc["args"])
                    except Exception as exc:
                        observation = f"Tool error: {exc}"
                else:
                    observation = f"Unknown tool: {tc['name']}"
                tool_results.append(
                    ToolMessage(content=str(observation), tool_call_id=tc["id"])
                )
            all_messages.extend(tool_results)

            followup = llm.invoke([sys_msg] + all_messages)
            all_messages.append(followup)
            output_text = followup.content
        else:
            output_text = response.content

        try:
            output_text = apply_output_guardrails(output_text, guardrail_config)
        except Exception as exc:
            logger.warning("Output guardrail violation for agent %s: %s", agent_name, exc)
            output_text = f"[Guardrail blocked] {exc}"

        duration_ms = int((time.time() - start_time) * 1000)

        prompt_tokens = getattr(response, "usage_metadata", {}).get("input_tokens", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0
        completion_tokens = getattr(response, "usage_metadata", {}).get("output_tokens", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0
        cost = estimate_cost(model_name, prompt_tokens, completion_tokens)

        from app.runtime.handoff import build_handoff_context
        new_handoff = build_handoff_context(
            from_agent_id=uuid.UUID(str(agent_id)),
            from_agent_name=agent_name,
            output=output_text,
            accumulated_facts=state.get("handoff_context", {}).get("accumulated_facts", []) + [output_text[:200]],
        )

        agent_outputs = dict(state.get("agent_outputs", {}))
        agent_outputs[str(agent_id)] = {
            "output": output_text,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
            "cost": cost,
            "duration_ms": duration_ms,
        }

        return {
            "messages": all_messages,
            "agent_outputs": agent_outputs,
            "handoff_context": new_handoff,
            "current_step": state.get("current_step", 0) + 1,
        }

    agent_node.__name__ = f"agent_{agent_name.replace(' ', '_').lower()}"
    return agent_node
