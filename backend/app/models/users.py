import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True
    )
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, native_enum=False), default=UserRole.user, nullable=False
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_users_email", "email"),
    )
