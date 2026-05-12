import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowExecuteRequest,
    CheckpointResumeRequest,
)
from app.schemas.execution import ExecutionResponse
from app.services import workflow_service

router = APIRouter()


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    wf = await workflow_service.create_workflow(db, payload)
    return wf


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(
    templates_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await workflow_service.list_workflows(db, templates_only=templates_only, limit=limit, offset=offset)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    wf = await workflow_service.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await workflow_service.delete_workflow(db, workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.execution_service import start_workflow_execution
    wf = await workflow_service.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution = await start_workflow_execution(db, wf, payload.input_data)
    return execution


@router.post("/{workflow_id}/resume", response_model=ExecutionResponse)
async def resume_workflow(
    workflow_id: uuid.UUID,
    payload: CheckpointResumeRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.execution_service import resume_workflow_execution
    wf = await workflow_service.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution = await resume_workflow_execution(db, wf, payload.checkpoint_id, payload.input_data)
    return execution


@router.get("/{workflow_id}/checkpoints")
async def list_checkpoints(workflow_id: uuid.UUID):
    from app.runtime.checkpointer import MongoDBCheckpointer
    cp = MongoDBCheckpointer()
    checkpoints = await cp.list_checkpoints(str(workflow_id))
    return checkpoints


@router.post("/templates/seed")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    from app.templates.research_report import get_template as get_research_template
    from app.templates.support_triage import get_template as get_triage_template
    from app.models.agent import Agent
    from app.models.workflow import Workflow, WorkflowNode, WorkflowEdge

    created = []
    for template_fn in [get_research_template, get_triage_template]:
        tmpl = template_fn()

        agent_id_map: dict[str, uuid.UUID] = {}
        for agent_data in tmpl["agents"]:
            old_id = agent_data.pop("id")
            agent_data.setdefault("interaction_rules", {})
            agent_data.setdefault("schedule", None)
            agent = Agent(**agent_data)
            db.add(agent)
            await db.flush()
            agent_id_map[old_id] = agent.id

        wf_data = tmpl["workflow"]
        workflow = Workflow(
            name=wf_data["name"],
            description=wf_data["description"],
            is_template=wf_data["is_template"],
        )
        db.add(workflow)
        await db.flush()

        node_id_map: dict[str, uuid.UUID] = {}
        for node_data in wf_data["nodes"]:
            old_node_id = node_data["id"]
            old_agent_id = node_data.get("agent_id")
            node = WorkflowNode(
                workflow_id=workflow.id,
                agent_id=agent_id_map.get(old_agent_id) if old_agent_id else None,
                node_type=node_data["node_type"],
                label=node_data["label"],
                config=node_data.get("config", {}),
            )
            db.add(node)
            await db.flush()
            node_id_map[old_node_id] = node.id

        for edge_data in wf_data["edges"]:
            src = node_id_map.get(edge_data["source_node_id"])
            tgt_raw = edge_data.get("target_node_id")
            tgt = node_id_map.get(tgt_raw) if tgt_raw else None

            condition = edge_data.get("condition")
            if condition:
                condition = dict(condition)
                if condition.get("true_target") in node_id_map:
                    condition["true_target"] = str(node_id_map[condition["true_target"]])
                if condition.get("false_target") in node_id_map:
                    condition["false_target"] = str(node_id_map[condition["false_target"]])

            if src:
                edge = WorkflowEdge(
                    workflow_id=workflow.id,
                    source_node_id=src,
                    target_node_id=tgt or src,
                    condition=condition,
                )
                db.add(edge)

        await db.flush()
        created.append({"name": wf_data["name"], "workflow_id": str(workflow.id)})

    return {"seeded": created}
