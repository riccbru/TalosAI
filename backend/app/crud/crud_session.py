from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user_session import UserSession


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
