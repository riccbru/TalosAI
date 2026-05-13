from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.deps import auth_scheme
from app.crud import crud_session
from app.db.session import get_db
from app.schemas.user import AuthResponse, UserOut, UserSignin, UserSignup
from app.services.auth_service import auth_service
from app.utils.auth_utils import delete_refresh_cookie


router = APIRouter()


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def user_signup(user_in: UserSignup, db: AsyncSession = Depends(get_db)):
    return await auth_service.signup_user(db, user_in)


@router.post("/signin", response_model=AuthResponse)
async def user_signin(
    request: Request,
    response: Response,
    user_credentials: UserSignin,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.authenticate(db, user_credentials)
    ip_address = request.client.host
    user_agent = request.headers.get("User-Agent")
    return await auth_service.signin_user(
        db, response, user, ip_address=ip_address, user_agent=user_agent
    )


@router.post("/refresh", response_model=AuthResponse)
async def user_refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user=Depends(deps.get_current_active_user_from_refresh),
):
    old_token = request.cookies.get("refresh_token")
    await crud_session.revoke_session(db, old_token)
    ip_address = request.client.host
    user_agent = request.headers.get("User-Agent")
    return await auth_service.signin_user(
        db, response, user, ip_address=ip_address, user_agent=user_agent
    )


@router.post("/signout", status_code=204, dependencies=[Depends(auth_scheme)])
async def user_signout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if token:
        await crud_session.revoke_session(db, token)
    delete_refresh_cookie(response)
