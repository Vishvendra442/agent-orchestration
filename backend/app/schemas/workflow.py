import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowNodeCreate(BaseModel):
    id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    node_type: str = Field(default="agent", pattern="^(agent|condition|entry|exit)$")
    label: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeCreate(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    condition: Optional[dict[str, Any]] = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_template: bool = False
    nodes: list[WorkflowNodeCreate] = Field(default_factory=list)
    edges: list[WorkflowEdgeCreate] = Field(default_factory=list)


class WorkflowNodeResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    agent_id: Optional[uuid.UUID]
    node_type: str
    label: Optional[str]
    config: dict[str, Any]

    model_config = {"from_attributes": True}


class WorkflowEdgeResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    condition: Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    is_template: bool
    created_at: datetime
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]

    model_config = {"from_attributes": True}


class WorkflowExecuteRequest(BaseModel):
    input_data: dict[str, Any] = Field(default_factory=dict)


class CheckpointResumeRequest(BaseModel):
    checkpoint_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)
