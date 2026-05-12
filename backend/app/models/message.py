import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MessageHistory(Base):
    __tablename__ = "message_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    from_agent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    to_agent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="internal")
    role: Mapped[str] = mapped_column(String(50), default="assistant")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
