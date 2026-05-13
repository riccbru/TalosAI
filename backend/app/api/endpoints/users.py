from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer


auth_scheme = HTTPBearer(bearerFormat="JWT")

router = APIRouter()

@router.get("/me", dependencies=[Depends(auth_scheme)])
async def get_me():
    return {}

@router.put("/me")
async def update_me():
    return {}

@router.patch("/me/password")
async def patch_me():
    return {}

@router.get("/me/sessions")
async def get_sessions():
    return {}

@router.delete("/me/sessions")
async def delete_all_sessions():
    return {}

@router.delete("/me/sessions/{uid}")
async def delete_session():
    return {}
