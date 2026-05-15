import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.sessions import UserSession


async def create_session(
    db: AsyncSession, user_uid: int, refresh_token: str, expires_at: datetime,
    ip_address: str, user_agent: str, last_active: datetime
) -> UserSession:
    session = UserSession(
        user_uid=user_uid, refresh_token=refresh_token, expires_at=expires_at,
        ip_address=ip_address, user_agent=user_agent, last_active=last_active
    )
    db.add(session)
    await db.commit()
    return session


async def get_valid_session(db: AsyncSession, token: str) -> UserSession | None:
    query = select(UserSession).where(
        UserSession.refresh_token == token,
        UserSession.is_revoked == False, # noqa: E712
        UserSession.expires_at > datetime.now(timezone.utc),
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_session(
    db: AsyncSession,
    session_uuid: Optional[uuid_lib.UUID] = None,
    token: Optional[str] = None
) -> Optional[UserSession]:
    query = select(UserSession)
    if session_uuid:
        query = query.where(UserSession.uuid == session_uuid)
    elif token:
        query = query.where(UserSession.refresh_token == token)
    else:
        return None

    result = await db.execute(query)
    return result.scalars().first()


async def get_all_sessions(
        db: AsyncSession,
        user_uuid: uuid_lib.UUID,
        revoked: Optional[bool] = None
    ):
    query = select(UserSession).where(
        UserSession.user_uid == user_uuid,
    ).order_by(UserSession.last_active.desc())
    if revoked is not None:
        query = query.where(UserSession.is_revoked == revoked)

    result = await db.execute(query.order_by(UserSession.last_active.desc()))
    return result.scalars().all()


async def revoke_session(
    db: AsyncSession,
    session_uuid: Optional[uuid_lib.UUID] = None,
    token: Optional[str] = None
) -> Optional[UserSession]:
    session = await get_session(db, session_uuid=session_uuid, token=token)

    if session and not session.is_revoked:
        session.is_revoked = True
        session.expires_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)

    return session


async def revoke_all_sessions(db: AsyncSession, user_uuid: uuid_lib.UUID) -> None:
    now = datetime.now(timezone.utc)

    stmt = (
        update(UserSession)
        .where(UserSession.user_uid == user_uuid)
        .where(UserSession.is_revoked.is_(False))
        .values(
            is_revoked=True,
            expires_at=now
        )
    )

    await db.execute(stmt)
    await db.commit()

