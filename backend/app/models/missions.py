import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


# JSONB on PostgreSQL (prod); generic JSON on other dialects (e.g. SQLite in
# tests). On the postgres dialect this is still JSONB, so migrations/DDL and
# alembic autogenerate are unaffected.
JSONType = JSONB().with_variant(JSON(), "sqlite")


class MissionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    interrupted = "interrupted"


class PortStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


# Statuses a mission can be resumed from.
RESUMABLE_STATUSES = (MissionStatus.failed.value, MissionStatus.interrupted.value)
TERMINAL_STATUSES = (
    MissionStatus.completed.value,
    MissionStatus.failed.value,
    MissionStatus.interrupted.value,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    user_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    target = Column(String, nullable=False)
    target_ip = Column(String, nullable=True)
    prompt = Column(Text, nullable=True)
    orchestrator_version = Column(String, nullable=False, default="v2")

    # Stored as plain strings; the *Status enums above are the source of truth.
    status = Column(
        String,
        default=MissionStatus.pending.value,
        nullable=False,
        index=True
    )
    discovered = Column(Boolean, default=False, nullable=False)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class MissionPort(Base):
    __tablename__ = "mission_ports"

    id = Column(Integer, primary_key=True, index=True)
    mission_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    port = Column(Integer, nullable=False)
    service_name = Column(String, nullable=True)
    version = Column(String, nullable=True)
    status = Column(String, default=PortStatus.pending.value, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    history = Column(JSONType, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        unique=True
    )
    mission_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    port = Column(Integer, nullable=True)
    service_name = Column(String, nullable=True)
    action = Column(String, nullable=True)
    command = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class MissionModelUsage(Base):
    """Per-agent LLM usage, accumulated over the whole mission.

    Provider-agnostic: `provider` records who served the call (ollama, gemini,
    openai, anthropic, ...) and token counts are normalized to the same three
    fields no matter the provider. One row per (mission, agent); counters are
    incremented on every call via `crud_missions.add_model_usage`.
    """

    __tablename__ = "mission_model_usage"
    __table_args__ = (
        UniqueConstraint("mission_uid", "agent", name="uq_mission_agent"),
    )

    id = Column(Integer, primary_key=True, index=True)
    mission_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent = Column(String, nullable=False)
    model = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    call_count = Column(Integer, default=0, nullable=False)
    total_latency_seconds = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
