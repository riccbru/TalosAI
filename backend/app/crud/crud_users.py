import uuid as uuid_lib

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_password_hash, verify_password
from app.models.users import User
from app.schemas.users import UserSignup


async def create_user(db: AsyncSession, user_in: UserSignup):
    hashed_password = get_password_hash(user_in.password)

    db_user = User(email=user_in.email, hashed_password=hashed_password)
    db.add(db_user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    await db.refresh(db_user)
    return db_user


async def get_user_by_email(db: AsyncSession, email: str):
    query = select(User).where(User.email == email)

    result = await db.execute(query)

    return result.scalars().first()


async def get_user_by_uuid(db: AsyncSession, user_uuid: str):
    query = select(User).where(User.uuid == uuid_lib.UUID(user_uuid))
    result = await db.execute(query)
    return result.scalars().first()


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email=email)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
