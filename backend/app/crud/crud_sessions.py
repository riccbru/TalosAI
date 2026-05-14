import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.sessions import UserSession


async def get_user_sessions(
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
    # result = await db.execute(query)
    return result.scalars().all()


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


async def revoke_session(db: AsyncSession, token: str) -> None:
    query = select(UserSession).where(UserSession.refresh_token == token)
    result = await db.execute(query)
    session = result.scalars().first()
    if session:
        session.is_revoked = True
        await db.commit()

async def get_session_by_uuid(db: AsyncSession, session_uuid: uuid_lib.UUID):
    query = select(UserSession).where(UserSession.uuid == session_uuid)
    result = await db.execute(query)
    return result.scalars().first()
