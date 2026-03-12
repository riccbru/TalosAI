from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_user
from app.db.session import get_db
from app.schemas.user import UserCreate, UserOut, UserSignin

router = APIRouter()


@router.post("/signup", response_model=UserOut, status_code=201)
async def signup_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud_user.create_user(db=db, user_in=user_in)


@router.post("/signin", response_model=UserOut, status_code=200)
async def signin(user_in: UserSignin, db: AsyncSession = Depends(get_db)):
    user = await crud_user.authenticate_user(
        db, email=user_in.email, password=user_in.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user
