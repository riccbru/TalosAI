import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_refresh_token_hash
from app.models.sessions import UserSession


async def create_session(
    db: AsyncSession, user_uid: uuid_lib.UUID, refresh_token: str, expires_at: datetime,
    ip_address: str, user_agent: str, last_active: datetime
) -> UserSession:
    hashed_refresh_token = get_refresh_token_hash(refresh_token)
    session = UserSession(
        user_uid=user_uid, refresh_token=hashed_refresh_token, expires_at=expires_at,
        ip_address=ip_address, user_agent=user_agent, last_active=last_active
    )
    db.add(session)
    await db.commit()
    return session


async def rotate_session(
    db: AsyncSession,
    session: UserSession,
    new_refresh_token: str,
    expires_at: datetime,
    ip_address: str,
    user_agent: str,
    last_active: datetime,
) -> UserSession:
    session.refresh_token = get_refresh_token_hash(new_refresh_token)
    session.expires_at = expires_at
    session.last_active = last_active
    session.ip_address = ip_address
    session.user_agent = user_agent
    await db.commit()
    await db.refresh(session)
    return session


async def get_valid_session(db: AsyncSession, token: str) -> UserSession | None:
    hashed_refresh_token = get_refresh_token_hash(token)
    query = select(UserSession).where(
        UserSession.refresh_token == hashed_refresh_token,
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
        hashed_refresh_token = get_refresh_token_hash(token)
        query = query.where(UserSession.refresh_token == hashed_refresh_token)
    else:
        return None

    result = await db.execute(query)
    return result.scalars().first()


async def get_all_sessions(
        db: AsyncSession,
        user_uuid: uuid_lib.UUID,
        revoked: Optional[str] = None
    ):
    query = select(UserSession).where(
        UserSession.user_uid == user_uuid,
    ).order_by(UserSession.last_active.desc())
    if revoked in ['true', 'false']:
        query = query.where(UserSession.is_revoked == (revoked == 'true'))
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
    query = (
        update(UserSession)
        .where(UserSession.user_uid == user_uuid)
        .where(UserSession.is_revoked.is_(False))
        .values(
            is_revoked=True,
            expires_at=datetime.now(timezone.utc)
        )
    )
    await db.execute(query)
    await db.commit()

