import uuid
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import MessageHistory


async def load_agent_memory(
    db: AsyncSession,
    agent_id: uuid.UUID,
    window: int = 20,
    workflow_run_id: Optional[uuid.UUID] = None,
) -> list[BaseMessage]:
    stmt = (
        select(MessageHistory)
        .where(
            (MessageHistory.from_agent_id == agent_id) | (MessageHistory.to_agent_id == agent_id)
        )
        .order_by(MessageHistory.timestamp.desc())
        .limit(window)
    )
    if workflow_run_id:
        stmt = stmt.where(MessageHistory.workflow_run_id == workflow_run_id)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()

    messages: list[BaseMessage] = []
    for row in rows:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        else:
            messages.append(AIMessage(content=row.content))
    return messages


async def clear_agent_memory(
    db: AsyncSession,
    agent_id: uuid.UUID,
    workflow_run_id: Optional[uuid.UUID] = None,
):
    from sqlalchemy import delete

    stmt = delete(MessageHistory).where(
        (MessageHistory.from_agent_id == agent_id) | (MessageHistory.to_agent_id == agent_id)
    )
    if workflow_run_id:
        stmt = stmt.where(MessageHistory.workflow_run_id == workflow_run_id)
    await db.execute(stmt)
