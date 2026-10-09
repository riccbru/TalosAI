import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

# JSONB on PostgreSQL (prod); generic JSON on other dialects (e.g. SQLite in
# tests). On the postgres dialect this is still JSONB, so migrations/DDL and
# alembic autogenerate are unaffected.
JSONType = JSONB().with_variant(JSON(), "sqlite")

from app.db.base import Base


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
    uuid = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False
    )
    user_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target = Column(String, nullable=False)  # original request, e.g. "metasploitable"
    target_ip = Column(String, nullable=True)  # resolved address actually scanned
    prompt = Column(Text, nullable=True)
    orchestrator_version = Column(String, nullable=False, default="v2")

    # Stored as plain strings; the *Status enums above are the source of truth.
    status = Column(
        String, default=MissionStatus.pending.value, nullable=False, index=True
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
        index=True,
    )
    port = Column(Integer, nullable=False)
    service_name = Column(String, nullable=True)
    version = Column(String, nullable=True)
    status = Column(String, default=PortStatus.pending.value, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    # [{"command_sent": ..., "terminal_output": ...}] — the manager's per-port memory,
    # persisted so an interrupted mission can be resumed with full context.
    history = Column(JSONType, default=list, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False
    )
    mission_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    port = Column(Integer, nullable=True)
    service_name = Column(String, nullable=True)
    action = Column(String, nullable=True)  # SEARCH_EXPLOIT / EXECUTE_ATTACK / ...
    command = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    confirmed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
