import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ExecutionLogResponse(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    agent_id: Optional[uuid.UUID]
    node_id: Optional[uuid.UUID]
    step_index: int
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    tokens_used: int
    cost: float
    duration_ms: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    input_data: dict[str, Any]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_tokens: int
    total_cost: float
    error_message: Optional[str]
    logs: list[ExecutionLogResponse]

    model_config = {"from_attributes": True}
