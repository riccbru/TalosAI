from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate


async def create_user(db: AsyncSession, user_in: UserCreate):
    email = user_in.email
    password = user_in.password
    hashed_password = get_password_hash(password)

    db_user = User(
        email=email,
        hashed_password=hashed_password,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
