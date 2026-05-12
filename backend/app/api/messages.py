import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.message import MessageResponse
from app.services import message_service

router = APIRouter()


@router.get("/", response_model=list[MessageResponse])
async def list_messages(
    workflow_run_id: Optional[uuid.UUID] = Query(None),
    agent_id: Optional[uuid.UUID] = Query(None),
    channel: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await message_service.get_messages(
        db,
        workflow_run_id=workflow_run_id,
        agent_id=agent_id,
        channel=channel,
        limit=limit,
        offset=offset,
    )
