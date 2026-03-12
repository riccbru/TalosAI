from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr

class UserSignin(BaseModel):
    email: EmailStr
    password: str

class UserSignup(UserBase):
    password: str

class UserOut(UserBase):
    uuid: UUID
    class Config:
        from_attributes = True
