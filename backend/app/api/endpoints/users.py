from fastapi import APIRouter, Depends

from app.api import deps
from app.models.users import User
from app.schemas.users import UserOut


router = APIRouter()


@router.get("/profile", response_model=UserOut)
async def get_profile(
    current_user: User = Depends(deps.get_current_user)
):
    return current_user


@router.put("/profile")
async def update_profile():
    return {}


@router.patch("/profile")
async def update_password():
    return {}
