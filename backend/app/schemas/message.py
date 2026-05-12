import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: uuid.UUID
    workflow_run_id: Optional[uuid.UUID]
    from_agent_id: Optional[uuid.UUID]
    to_agent_id: Optional[uuid.UUID]
    content: str
    channel: str
    role: str
    metadata_: dict[str, Any]
    timestamp: datetime

    model_config = {"from_attributes": True}


class MessageQuery(BaseModel):
    workflow_run_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    channel: Optional[str] = None
    limit: int = 50
    offset: int = 0
