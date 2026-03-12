from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_user
from app.db.session import get_db
from app.schemas.user import UserOut, UserSignin, UserSignup

router = APIRouter()

@router.post("/signup", response_model=UserOut, status_code=201)
async def user_signup(user: UserSignup, db: AsyncSession = Depends(get_db)):
    return await crud_user.create_user(db=db, user_in=user)

@router.post("/signin", response_model=UserOut, status_code=200)
async def user_signin(user: UserSignin, db: AsyncSession = Depends(get_db)):
    user = await crud_user.authenticate_user(
        db, email=user.email, password=user.password
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
