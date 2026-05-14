from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionData(BaseModel):
    is_revoked: bool
    ip_address: str
    user_agent: str
    expires_at: datetime
    last_active: datetime
    created_at: datetime
    session_uid: UUID = Field(validation_alias="uuid")

    model_config = ConfigDict(from_attributes=True)


class SessionSingleOut(BaseModel):
    session: SessionData


class SessionsListOut(BaseModel):
    sessions: List[SessionData]
