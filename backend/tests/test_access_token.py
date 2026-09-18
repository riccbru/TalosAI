from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.users import User


pytestmark = pytest.mark.anyio


async def test_valid_access_token_authenticates_protected_endpoint(
    client, user_factory
):
    user = await user_factory()
    token = create_access_token(str(user.uuid), role=user.role.value)

    resp = await client.get(
        "/talos/api/sessions", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200


async def test_missing_authorization_header_is_rejected(client):
    resp = await client.get("/talos/api/sessions")
    assert resp.status_code == 401


async def test_invalid_access_token_is_rejected(client):
    resp = await client.get(
        "/talos/api/sessions", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_expired_access_token_is_rejected(client, user_factory):
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
        "/talos/api/sessions", headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert resp.status_code == 401


async def test_deactivated_user_is_rejected_even_with_a_still_valid_token(
    client, user_factory, db
):
    user = await user_factory(email="deactivated@example.com")
    token = create_access_token(str(user.uuid), role=user.role.value)

    still_active = await client.get(
        "/talos/api/sessions", headers={"Authorization": f"Bearer {token}"}
    )
    assert still_active.status_code == 200

    result = await db.execute(select(User).where(User.uuid == user.uuid))
    db_user = result.scalar_one()
    db_user.is_active = False
    await db.commit()

    after_deactivation = await client.get(
        "/talos/api/sessions", headers={"Authorization": f"Bearer {token}"}
    )
    assert after_deactivation.status_code == 401
