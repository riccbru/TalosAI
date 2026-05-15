from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud import crud_sessions
from app.db.session import get_db
from app.models.users import User
from app.schemas.sessions import SessionSingleOut, SessionsListOut


router = APIRouter()


@router.get("", response_model=SessionsListOut)
async def get_all_sessions(
    revoked: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    sessions = await crud_sessions.get_all_sessions(
        db,
        user_uuid=current_user.uuid,
        revoked=revoked
    )
    return { "sessions": sessions }


@router.delete("", status_code=204)
async def delete_all_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    await crud_sessions.revoke_all_sessions(db, user_uuid=current_user.uuid)
    return None


@router.get("/{session_uid}", response_model=SessionSingleOut)
async def get_session_by_uuid(
    session_uid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    session = await crud_sessions.get_session(db, session_uuid=session_uid)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_uid != current_user.uuid:
        raise HTTPException(status_code=403, detail="Forbidden")

    return { "session": session }


@router.delete("/{session_uid}", response_model=SessionSingleOut)
async def delete_session_by_uuid(
    session_uid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    session = await crud_sessions.get_session(db, session_uuid=session_uid)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_uid != current_user.uuid:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: This is not your session"
        )

    updated_session = await crud_sessions.revoke_session(
        db, session_uuid=session_uid
    )

    return { "session": updated_session }
