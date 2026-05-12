import uuid
from typing import Any


def get_template() -> dict[str, Any]:
    researcher_id = str(uuid.uuid4())
    writer_id = str(uuid.uuid4())
    reviewer_id = str(uuid.uuid4())

    researcher_node_id = str(uuid.uuid4())
    writer_node_id = str(uuid.uuid4())
    reviewer_node_id = str(uuid.uuid4())

    agents = [
        {
            "id": researcher_id,
            "name": "Researcher",
            "role": "researcher",
            "system_prompt": (
                "You are a research assistant. Given a topic, search the web for "
                "relevant information and compile your findings into a structured "
                "list of key facts and sources. Be thorough and factual."
            ),
            "model": "gpt-4o-mini",
            "tools": ["web_search"],
            "channels": [],
            "memory_enabled": True,
            "memory_window": 10,
            "skills": ["research", "fact-finding"],
            "temperature": 0.3,
            "max_tokens": 4096,
            "guardrails": {"max_output_length": 8000},
        },
        {
            "id": writer_id,
            "name": "Writer",
            "role": "writer",
            "system_prompt": (
                "You are a professional writer. Take the research findings provided "
                "and write a well-structured, clear, and concise report. Include an "
                "introduction, main findings, and conclusion. If the reviewer asks "
                "for revisions, incorporate their feedback."
            ),
            "model": "gpt-4o-mini",
            "tools": ["summarizer"],
            "channels": [],
            "memory_enabled": True,
            "memory_window": 10,
            "skills": ["writing", "summarization"],
            "temperature": 0.7,
            "max_tokens": 4096,
            "guardrails": {},
        },
        {
            "id": reviewer_id,
            "name": "Reviewer",
            "role": "reviewer",
            "system_prompt": (
                "You are a quality reviewer. Evaluate the report provided for clarity, "
                "accuracy, completeness, and structure. Respond with EXACTLY one of:\n"
                "- 'APPROVED' if the report meets quality standards\n"
                "- 'REVISE: <specific feedback>' if improvements are needed\n"
                "Be constructive and specific in your feedback."
            ),
            "model": "gpt-4o-mini",
            "tools": [],
            "channels": [],
            "memory_enabled": True,
            "memory_window": 10,
            "skills": ["quality-assurance", "editing"],
            "temperature": 0.2,
            "max_tokens": 2048,
            "guardrails": {},
        },
    ]

    workflow = {
        "name": "Research and Report",
        "description": (
            "A 3-agent workflow: Researcher gathers information, Writer drafts a report, "
            "Reviewer evaluates quality. If the report needs revision, it loops back to "
            "the Writer (max 3 iterations)."
        ),
        "is_template": True,
        "nodes": [
            {
                "id": researcher_node_id,
                "agent_id": researcher_id,
                "node_type": "agent",
                "label": "Researcher",
                "config": {
                    "system_prompt": agents[0]["system_prompt"],
                    "model": "gpt-4o-mini",
                    "tools": ["web_search"],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
            },
            {
                "id": writer_node_id,
                "agent_id": writer_id,
                "node_type": "agent",
                "label": "Writer",
                "config": {
                    "system_prompt": agents[1]["system_prompt"],
                    "model": "gpt-4o-mini",
                    "tools": ["summarizer"],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            },
            {
                "id": reviewer_node_id,
                "agent_id": reviewer_id,
                "node_type": "agent",
                "label": "Reviewer",
                "config": {
                    "system_prompt": agents[2]["system_prompt"],
                    "model": "gpt-4o-mini",
                    "tools": [],
                    "temperature": 0.2,
                    "max_tokens": 2048,
                },
            },
        ],
        "edges": [
            {
                "source_node_id": researcher_node_id,
                "target_node_id": writer_node_id,
                "condition": None,
            },
            {
                "source_node_id": writer_node_id,
                "target_node_id": reviewer_node_id,
                "condition": None,
            },
            {
                "source_node_id": reviewer_node_id,
                "target_node_id": writer_node_id,
                "condition": {
                    "field": "",
                    "op": "contains",
                    "value": "REVISE",
                    "true_target": writer_node_id,
                    "false_target": "__end__",
                },
            },
        ],
    }

    return {"agents": agents, "workflow": workflow}
