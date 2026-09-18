"""Auth-boundary tests for /talos/api/status.

Request path exercised here:

    Request
      -> JWTMiddleware            (signature + expiry check only; no DB access)
      -> router dependency: auth_scheme       (HTTPBearer, syntax-only)
      -> router dependency: get_current_user  (real decode + DB user lookup +
                                                is_active check)
      -> endpoint handler

Missing/malformed/invalid/expired tokens are all rejected by JWTMiddleware
before the request ever reaches get_current_user (it never touches the DB).
Only a token that is cryptographically valid and unexpired reaches
get_current_user, which is the layer that actually confirms "this is a real,
active user" rather than just "this is a well-formed token".
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import jwt as jose_jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.users import User


pytestmark = pytest.mark.anyio

STATUS_URL = "/talos/api/status/backend"


async def test_no_token_is_rejected(client):
    resp = await client.get(STATUS_URL)
    assert resp.status_code == 401


async def test_malformed_authorization_header_is_rejected(client):
    resp = await client.get(STATUS_URL, headers={"Authorization": "Token abc123"})
    assert resp.status_code == 401


async def test_invalid_token_is_rejected(client):
    resp = await client.get(
        STATUS_URL, headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_expired_token_is_rejected(client, user_factory):
    user = await user_factory()
    expired_payload = {
        "role": user.role.value,
        "sub": str(user.uuid),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jose_jwt.encode(
        expired_payload, settings.ACCESS_TOKEN_SECRET, algorithm=settings.JWT_ALG
    )

    resp = await client.get(
        STATUS_URL, headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401


async def test_valid_token_for_active_user_authenticates(client, user_factory):
    user = await user_factory()
    token = create_access_token(str(user.uuid), role=user.role.value)

    resp = await client.get(STATUS_URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200


async def test_valid_token_for_deactivated_user_is_rejected(client, user_factory, db):
    user = await user_factory(email="status-deactivated@example.com")
    token = create_access_token(str(user.uuid), role=user.role.value)

    result = await db.execute(select(User).where(User.uuid == user.uuid))
    db_user = result.scalar_one()
    db_user.is_active = False
    await db.commit()

    resp = await client.get(STATUS_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_bearer_shaped_token_alone_is_not_sufficient(client):
    """Regression: JWTMiddleware only checks signature/expiry, never the DB.

    A token with a well-formed signature and a `sub` that matches no user at
    all is exactly the shape of token that used to reach missions/status
    handlers before this fix, because the middleware has no concept of
    "does this user exist". get_current_user must be the one to reject it.
    """
    nonexistent_user_uuid = str(uuid4())
    token = create_access_token(nonexistent_user_uuid, role="user")

    resp = await client.get(STATUS_URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
