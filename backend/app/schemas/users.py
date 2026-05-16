from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.users import UserRole


class UserSignin(BaseModel):
    email: EmailStr
    password: str


class UserSignup(BaseModel):
    email: EmailStr
    password: str


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    role: UserRole
    is_active: bool
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    user_uid: UUID = Field(validation_alias="uuid")


class UsersListOut(BaseModel):
    users: List[UserOut]


class AuthResponse(BaseModel):
    status: str
    access_token: str
    user: UserOut
