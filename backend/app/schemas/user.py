from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserInternal(UserBase):
    id: int

    class Config:
        from_attributes = True


class UserOut(UserBase):
    uuid: UUID

    class Config:
        from_attributes = True


class UserSignin(BaseModel):
    email: EmailStr
    password: str
