import uuid
from typing import Any


def get_template() -> dict[str, Any]:
    classifier_id = str(uuid.uuid4())
    tech_support_id = str(uuid.uuid4())
    sales_agent_id = str(uuid.uuid4())

    classifier_node_id = str(uuid.uuid4())
    tech_node_id = str(uuid.uuid4())
    sales_node_id = str(uuid.uuid4())

    agents = [
        {
            "id": classifier_id,
            "name": "Classifier",
            "role": "classifier",
            "system_prompt": (
                "You are a message classifier for a customer support system. "
                "Analyze the incoming message and classify it into EXACTLY one category:\n"
                "- 'TECHNICAL' for technical issues, bugs, or how-to questions\n"
                "- 'SALES' for pricing, plans, purchasing, or upgrade questions\n"
                "- 'GENERAL' if the message is unclear or doesn't fit the above\n\n"
                "Respond with ONLY the category name (TECHNICAL, SALES, or GENERAL) "
                "followed by a brief reason."
            ),
            "model": "gpt-4o-mini",
            "tools": [],
            "channels": ["telegram"],
            "memory_enabled": True,
            "memory_window": 5,
            "skills": ["classification", "intent-detection"],
            "temperature": 0.1,
            "max_tokens": 256,
            "guardrails": {"max_output_length": 500},
        },
        {
            "id": tech_support_id,
            "name": "Technical Support",
            "role": "technical_support",
            "system_prompt": (
                "You are a technical support agent. Help the user resolve their "
                "technical issue. Be patient, clear, and provide step-by-step "
                "instructions when appropriate. If you need to run code to demonstrate "
                "a solution, use the code_executor tool."
            ),
            "model": "gpt-4o-mini",
            "tools": ["code_executor", "web_search"],
            "channels": [],
            "memory_enabled": True,
            "memory_window": 20,
            "skills": ["troubleshooting", "technical-writing"],
            "temperature": 0.5,
            "max_tokens": 4096,
            "guardrails": {"block_pii": True},
        },
        {
            "id": sales_agent_id,
            "name": "Sales Agent",
            "role": "sales",
            "system_prompt": (
                "You are a sales representative. Help the user understand pricing, "
                "plans, and features. Be friendly, informative, and helpful. "
                "Answer questions about the product and guide them toward the best "
                "plan for their needs."
            ),
            "model": "gpt-4o-mini",
            "tools": ["calculator"],
            "channels": [],
            "memory_enabled": True,
            "memory_window": 20,
            "skills": ["sales", "product-knowledge"],
            "temperature": 0.7,
            "max_tokens": 4096,
            "guardrails": {},
        },
    ]

    workflow = {
        "name": "Customer Support Triage",
        "description": (
            "A 3-agent support workflow: Classifier categorizes incoming messages, "
            "then routes to Technical Support or Sales Agent based on the classification. "
            "If unclear, loops back to Classifier for clarification."
        ),
        "is_template": True,
        "nodes": [
            {
                "id": classifier_node_id,
                "agent_id": classifier_id,
                "node_type": "agent",
                "label": "Classifier",
                "config": {
                    "system_prompt": agents[0]["system_prompt"],
                    "model": "gpt-4o-mini",
                    "tools": [],
                    "temperature": 0.1,
                    "max_tokens": 256,
                },
            },
            {
                "id": tech_node_id,
                "agent_id": tech_support_id,
                "node_type": "agent",
                "label": "TechSupport",
                "config": {
                    "system_prompt": agents[1]["system_prompt"],
                    "model": "gpt-4o-mini",
                    "tools": ["code_executor", "web_search"],
                    "temperature": 0.5,
                    "max_tokens": 4096,
                },
            },
            {
                "id": sales_node_id,
                "agent_id": sales_agent_id,
                "node_type": "agent",
                "label": "SalesAgent",
                "config": {
                    "system_prompt": agents[2]["system_prompt"],
                    "model": "gpt-4o-mini",
                    "tools": ["calculator"],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            },
        ],
        "edges": [
            {
                "source_node_id": classifier_node_id,
                "target_node_id": tech_node_id,
                "condition": {
                    "field": "",
                    "op": "contains",
                    "value": "TECHNICAL",
                    "true_target": tech_node_id,
                    "false_target": sales_node_id,
                },
            },
            {
                "source_node_id": tech_node_id,
                "target_node_id": None,
                "condition": None,
            },
            {
                "source_node_id": sales_node_id,
                "target_node_id": None,
                "condition": None,
            },
        ],
    }

    return {"agents": agents, "workflow": workflow}
