import uuid as uuid_lib
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.crud import crud_sessions
from app.models.users import User
from app.schemas.users import UserPasswordUpdate, UserSignup, UserUpdate


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


async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.asc()))
    return list(result.scalars().all())


async def get_user_by_email(db: AsyncSession, email: str):
    query = select(User).where(User.email == email)

    result = await db.execute(query)

    return result.scalars().first()


async def get_user_by_uuid(db: AsyncSession, user_uuid: str):
    query = select(User).where(User.uuid == user_uuid)
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email=email)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def user_password_update(
        db: AsyncSession, user: User, passwords: UserPasswordUpdate
    ) -> None:
    if not verify_password(passwords.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )

    user.hashed_password = get_password_hash(passwords.new_password)
    await db.commit()

    await crud_sessions.revoke_all_sessions(db, user_uuid=user.uuid)


async def user_update(
        db: AsyncSession, user_uuid: uuid_lib.UUID, update_data: UserUpdate
    ) -> User:
    user = await get_user_by_uuid(db, user_uuid=user_uuid)

    update_dict = update_data.model_dump(exclude_unset=True)

    if not update_dict:
        return user

    for field, value in update_dict.items():
        setattr(user, field, value)

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    if update_dict.get("is_active") is False:
        await crud_sessions.revoke_all_sessions(db, user_uuid=user_uuid)

    return user
