import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import MessageHistory


async def save_message(
    db: AsyncSession,
    content: str,
    *,
    workflow_run_id: Optional[uuid.UUID] = None,
    from_agent_id: Optional[uuid.UUID] = None,
    to_agent_id: Optional[uuid.UUID] = None,
    channel: str = "internal",
    role: str = "assistant",
    metadata: Optional[dict] = None,
) -> MessageHistory:
    msg = MessageHistory(
        workflow_run_id=workflow_run_id,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        content=content,
        channel=channel,
        role=role,
        metadata_=metadata or {},
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def get_messages(
    db: AsyncSession,
    *,
    workflow_run_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MessageHistory]:
    stmt = select(MessageHistory).order_by(MessageHistory.timestamp.desc())
    if workflow_run_id:
        stmt = stmt.where(MessageHistory.workflow_run_id == workflow_run_id)
    if agent_id:
        stmt = stmt.where(
            (MessageHistory.from_agent_id == agent_id) | (MessageHistory.to_agent_id == agent_id)
        )
    if channel:
        stmt = stmt.where(MessageHistory.channel == channel)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())
