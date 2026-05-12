import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def build_handoff_context(
    from_agent_id: uuid.UUID,
    from_agent_name: str,
    output: str,
    accumulated_facts: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "from_agent_id": str(from_agent_id),
        "from_agent_name": from_agent_name,
        "output": output,
        "accumulated_facts": accumulated_facts or [],
        "metadata": metadata or {},
        "handed_off_at": datetime.now(timezone.utc).isoformat(),
    }


async def publish_handoff_event(
    from_agent_id: uuid.UUID,
    to_agent_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    handoff_context: dict[str, Any],
):
    from app.redis_client import publish

    event = {
        "type": "agent_handoff",
        "from_agent_id": str(from_agent_id),
        "to_agent_id": str(to_agent_id),
        "workflow_run_id": str(workflow_run_id),
        "context": handoff_context,
    }
    channel = f"execution:{workflow_run_id}:logs"
    await publish(channel, json.dumps(event))
    logger.info(
        "Handoff published: %s → %s (run=%s)",
        from_agent_id, to_agent_id, workflow_run_id,
    )
