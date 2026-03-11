from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_user
from app.db.session import get_db
from app.schemas.user import UserCreate, UserOut

router = APIRouter()

@router.post("/signup", response_model=UserOut)
async def signup_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    return await crud_user.create_user(db=db, user_in=user_in)

