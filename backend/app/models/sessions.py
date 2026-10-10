import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    user_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_revoked = Column(Boolean, default=False)
    refresh_token = Column(Text, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_address = Column(String(45), index=True)
    user_agent = Column(Text)
    last_active = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_user_sessions_uuid", "uuid"),
    )
