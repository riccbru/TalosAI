from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.crud import crud_sessions, crud_users
from app.schemas.users import AuthResponse, UserOut
from app.utils.auth_utils import delete_refresh_cookie, set_refresh_cookie


class AuthService:
    async def authenticate(self, db: AsyncSession, user_in) -> any:
        user = await crud_users.authenticate_user(
            db, email=user_in.email, password=user_in.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User is not active"
            )
        return user

    async def signin_user(
        self, db: AsyncSession, response: Response, db_user, ip_address, user_agent
    ) -> AuthResponse:
        user_data = UserOut.model_validate(db_user)

        token_payload = user_data.model_dump(mode="json")

        access_token, refresh_token = security.create_tokens(token_payload)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        last_active = datetime.now(timezone.utc)

        await crud_sessions.create_session(
            db, db_user.uuid, refresh_token, expires_at,
            ip_address, user_agent, last_active
        )

        set_refresh_cookie(response, refresh_token)

        return AuthResponse(status="success", access_token=access_token, user=user_data)

    async def signup_user(self, db: AsyncSession, user_in) -> UserOut:
        return await crud_users.create_user(db=db, user_in=user_in)

    def signout_user(self, response: Response):
        delete_refresh_cookie(response)


auth_service = AuthService()
