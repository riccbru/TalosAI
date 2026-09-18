"""Auth-boundary tests for /talos/api/missions.

Same request path and middleware/dependency division of labor as documented
in test_status_auth.py. The `get_current_user` dependency is attached at the
router level (see app.main / conftest.app), so it applies uniformly to every
mission endpoint; these tests exercise it once via `/v1/test/local` rather
than duplicating the same auth assertions across all three mission routes.

`LocalOrchestrator` is monkeypatched for the "authentication succeeds" case
only, purely to avoid triggering real agent/orchestration execution as a
side effect of an auth test — mission business logic itself is untouched.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import jwt as jose_jwt
from sqlalchemy import select

import app.api.endpoints.missions as missions_module
from app.core.config import settings
from app.core.security import create_access_token
from app.models.users import User


pytestmark = pytest.mark.anyio

MISSIONS_URL = "/talos/api/missions/v1/test/local"
VALID_BODY = {"target": "example.com"}


class _FakeOrchestrator:
    def __init__(self, *args, **kwargs):
        pass

    def run(self):
        return {"data": "stubbed"}


async def test_no_token_is_rejected(client):
    resp = await client.post(MISSIONS_URL, json=VALID_BODY)
    assert resp.status_code == 401


async def test_malformed_authorization_header_is_rejected(client):
    resp = await client.post(
        MISSIONS_URL, json=VALID_BODY, headers={"Authorization": "Token abc123"}
    )
    assert resp.status_code == 401


async def test_invalid_token_is_rejected(client):
    resp = await client.post(
        MISSIONS_URL,
        json=VALID_BODY,
        headers={"Authorization": "Bearer not-a-real-token"},
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

    resp = await client.post(
        MISSIONS_URL,
        json=VALID_BODY,
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


async def test_valid_token_for_active_user_authenticates(
    client, user_factory, monkeypatch
):
    monkeypatch.setattr(missions_module, "LocalOrchestrator", _FakeOrchestrator)

    user = await user_factory()
    token = create_access_token(str(user.uuid), role=user.role.value)

    resp = await client.post(
        MISSIONS_URL, json=VALID_BODY, headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code != 401
    assert resp.status_code == 200


async def test_valid_token_for_deactivated_user_is_rejected(client, user_factory, db):
    user = await user_factory(email="missions-deactivated@example.com")
    token = create_access_token(str(user.uuid), role=user.role.value)

    result = await db.execute(select(User).where(User.uuid == user.uuid))
    db_user = result.scalar_one()
    db_user.is_active = False
    await db.commit()

    resp = await client.post(
        MISSIONS_URL, json=VALID_BODY, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_bearer_shaped_token_alone_is_not_sufficient(client):
    """Regression: see test_status_auth.py for the full rationale. A
    well-formed, correctly signed, unexpired token for a `sub` that matches
    no user at all must still be rejected once it reaches get_current_user.
    """
    nonexistent_user_uuid = str(uuid4())
    token = create_access_token(nonexistent_user_uuid, role="user")

    resp = await client.post(
        MISSIONS_URL, json=VALID_BODY, headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 401
