import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud import crud_sessions, crud_users
from app.models.users import User
from app.schemas.sessions import SessionsListOut
from app.schemas.users import UserOut, UserPasswordUpdate, UsersListOut, UserUpdate


router = APIRouter()


@router.get("", response_model=UsersListOut)
async def get_users_list(
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_current_admin)
):
    users = await crud_users.get_all_users(db)
    return {"users": users}


@router.get("/profile", response_model=UserOut)
async def get_profile(
    current_user: User = Depends(deps.get_current_user)
):
    return current_user


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: UserPasswordUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    await crud_users.user_password_update(db, user=current_user, passwords=payload)
    return None


@router.get("/{user_uid}", response_model=UserOut)
async def get_user_by_admin(
    user_uid: uuid_lib.UUID,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_current_admin)
):
    return await crud_users.get_user_by_uuid(db, user_uuid=user_uid)


@router.patch("/{user_uid}", response_model=UserOut)
async def admin_update_user(
    user_uid: uuid_lib.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_current_admin)
):
    return await crud_users.user_update(
        db, user_uuid=user_uid, update_data=payload
    )


@router.get("/{user_uid}/sessions", response_model=SessionsListOut)
async def get_user_sessions_by_admin(
    user_uid: uuid_lib.UUID,
    revoked: Optional[bool] = None,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_current_admin)
):
    sessions = await crud_sessions.get_all_sessions(
        db,
        user_uuid=user_uid,
        revoked=revoked
    )
    return { "sessions": sessions }
