from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.users import UserRole


class UserSignin(BaseModel):
    email: EmailStr
    password: str


class UserSignup(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    is_active: bool
    role: UserRole
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    user_uid: UUID = Field(validation_alias="uuid")


class AuthResponse(BaseModel):
    status: str
    access_token: str
    user: UserOut
