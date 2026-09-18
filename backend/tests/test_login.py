import pytest
from sqlalchemy import select

from app.models.sessions import UserSession


pytestmark = pytest.mark.anyio


async def test_login_succeeds(client, user_factory):
    await user_factory(email="alice@example.com", password="Password123!")

    resp = await client.post(
        "/talos/api/auth/signin",
        json={"email": "alice@example.com", "password": "Password123!"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert resp.cookies.get("refresh_token")


async def test_login_wrong_password_rejected(client, user_factory):
    await user_factory(email="alice@example.com", password="Password123!")

    resp = await client.post(
        "/talos/api/auth/signin",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert resp.status_code == 401


async def test_login_creates_exactly_one_session(client, user_factory, db):
    await user_factory(email="bob@example.com", password="Password123!")

    resp = await client.post(
        "/talos/api/auth/signin",
        json={"email": "bob@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 200

    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].is_revoked is False


async def test_second_login_creates_new_independent_session(client, user_factory, db):
    await user_factory(email="carol@example.com", password="Password123!")
    credentials = {"email": "carol@example.com", "password": "Password123!"}

    first = await client.post("/talos/api/auth/signin", json=credentials)
    second = await client.post("/talos/api/auth/signin", json=credentials)

    assert first.status_code == 200
    assert second.status_code == 200

    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()

    assert len(sessions) == 2
    session_ids = {s.uuid for s in sessions}
    assert len(session_ids) == 2
    assert all(not s.is_revoked for s in sessions)
