import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


async def create_agent(db: AsyncSession, payload: AgentCreate) -> Agent:
    agent = Agent(**payload.model_dump())
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Optional[Agent]:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def list_agents(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Agent]:
    result = await db.execute(
        select(Agent).order_by(Agent.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def update_agent(db: AsyncSession, agent_id: uuid.UUID, payload: AgentUpdate) -> Optional[Agent]:
    agent = await get_agent(db, agent_id)
    if not agent:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    await db.flush()
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, agent_id: uuid.UUID) -> bool:
    result = await db.execute(delete(Agent).where(Agent.id == agent_id))
    return result.rowcount > 0
