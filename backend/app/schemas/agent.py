import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=1)
    model: str = Field(default="gpt-4o-mini", max_length=100)
    tools: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    schedule: Optional[dict[str, Any]] = None
    memory_enabled: bool = True
    memory_window: int = Field(default=20, ge=1, le=100)
    skills: list[str] = Field(default_factory=list)
    interaction_rules: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[list[str]] = None
    channels: Optional[list[str]] = None
    schedule: Optional[dict[str, Any]] = None
    memory_enabled: Optional[bool] = None
    memory_window: Optional[int] = Field(None, ge=1, le=100)
    skills: Optional[list[str]] = None
    interaction_rules: Optional[dict[str, Any]] = None
    guardrails: Optional[dict[str, Any]] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    system_prompt: str
    model: str
    tools: list[str]
    channels: list[str]
    schedule: Optional[dict[str, Any]]
    memory_enabled: bool
    memory_window: int
    skills: list[str]
    interaction_rules: dict[str, Any]
    guardrails: dict[str, Any]
    max_tokens: int
    temperature: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
