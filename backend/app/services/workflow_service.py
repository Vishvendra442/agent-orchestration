import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowNode, WorkflowEdge
from app.schemas.workflow import WorkflowCreate


async def create_workflow(db: AsyncSession, payload: WorkflowCreate) -> Workflow:
    workflow = Workflow(
        name=payload.name,
        description=payload.description,
        is_template=payload.is_template,
    )
    db.add(workflow)
    await db.flush()

    node_id_map: dict[uuid.UUID, uuid.UUID] = {}
    for node_data in payload.nodes:
        node = WorkflowNode(
            workflow_id=workflow.id,
            agent_id=node_data.agent_id,
            node_type=node_data.node_type,
            label=node_data.label,
            config=node_data.config,
        )
        if node_data.id:
            node_id_map[node_data.id] = node.id
        db.add(node)
        await db.flush()
        if node_data.id:
            node_id_map[node_data.id] = node.id

    for edge_data in payload.edges:
        src = node_id_map.get(edge_data.source_node_id, edge_data.source_node_id)
        tgt = node_id_map.get(edge_data.target_node_id, edge_data.target_node_id)
        edge = WorkflowEdge(
            workflow_id=workflow.id,
            source_node_id=src,
            target_node_id=tgt,
            condition=edge_data.condition,
        )
        db.add(edge)

    await db.flush()
    await db.refresh(workflow)
    return workflow


async def get_workflow(db: AsyncSession, workflow_id: uuid.UUID) -> Optional[Workflow]:
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    return result.scalar_one_or_none()


async def list_workflows(
    db: AsyncSession, templates_only: bool = False, limit: int = 100, offset: int = 0
) -> list[Workflow]:
    stmt = select(Workflow).order_by(Workflow.created_at.desc()).limit(limit).offset(offset)
    if templates_only:
        stmt = stmt.where(Workflow.is_template == True)  # noqa: E712
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_workflow(db: AsyncSession, workflow_id: uuid.UUID) -> bool:
    result = await db.execute(delete(Workflow).where(Workflow.id == workflow_id))
    return result.rowcount > 0
