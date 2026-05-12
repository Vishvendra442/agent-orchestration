import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.execution import WorkflowExecution, ExecutionLog
from app.schemas.execution import ExecutionResponse, ExecutionLogResponse

router = APIRouter()


@router.get("/executions", response_model=list[ExecutionResponse])
async def list_executions(
    workflow_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WorkflowExecution).order_by(WorkflowExecution.started_at.desc())
    if workflow_id:
        stmt = stmt.where(WorkflowExecution.workflow_id == workflow_id)
    if status:
        stmt = stmt.where(WorkflowExecution.status == status)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    ex = result.scalar_one_or_none()
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ex


@router.get("/executions/{execution_id}/logs", response_model=list[ExecutionLogResponse])
async def get_execution_logs(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.execution_id == execution_id)
        .order_by(ExecutionLog.step_index)
    )
    return list(result.scalars().all())
