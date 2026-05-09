from fastapi import Response

from app.core.config import settings


def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        value=token,
        secure=True,
        httponly=True,
        samesite="strict",
        key="refresh_token",
        path="/talos/api/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def delete_refresh_cookie(response: Response):
    response.delete_cookie(
        secure=True,
        httponly=True,
        samesite="strict",
        key="refresh_token",
        path="/talos/api/auth",
    )
