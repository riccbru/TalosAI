from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings


ph = PasswordHasher()


def get_password_hash(password: str) -> str:
    hash = ph.hash(password)
    return hash


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(user_data: dict) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {
        "user": dict(user_data),
        "exp": expires,
        "sub": str(user_data.get("uid")),
    }
    return jwt.encode(
        to_encode, settings.ACCESS_TOKEN_SECRET, algorithm=settings.JWT_ALG
    )


def create_refresh_token(user_uid: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"type": "refresh", "exp": expires, "sub": str(user_uid)}
    return jwt.encode(
        to_encode, settings.REFRESH_TOKEN_SECRET, algorithm=settings.JWT_ALG
    )


def create_tokens(user_data: dict) -> tuple[str, str]:
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(str(user_data.get("uid")))
    return access_token, refresh_token


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.ACCESS_TOKEN_SECRET, algorithms=[settings.JWT_ALG]
        )
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.REFRESH_TOKEN_SECRET, algorithms=[settings.JWT_ALG]
        )
    except JWTError:
        return None
    if payload.get("type") != "refresh":
        return None
    return payload
