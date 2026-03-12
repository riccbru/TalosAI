from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserSignup


async def create_user(db: AsyncSession, user_in: UserSignup):
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


async def get_user_by_email(db: AsyncSession, email: str):
    query = select(User).where(User.email == email)

    result = await db.execute(query)

    return result.scalars().first()


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email=email)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
