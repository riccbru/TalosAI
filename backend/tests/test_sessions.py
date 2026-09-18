import pytest
from sqlalchemy import select

from app.core.security import get_refresh_token_hash
from app.models.sessions import UserSession


pytestmark = pytest.mark.anyio


async def _login(client, email="erin@example.com", password="Password123!"):
    resp = await client.post(
        "/talos/api/auth/signin", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp


async def test_signout_revokes_the_session_and_clears_the_cookie(
    client, user_factory, db
):
    await user_factory(email="erin@example.com")
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    resp = await client.post(
        "/talos/api/auth/signout", cookies={"refresh_token": refresh_token}
    )
    assert resp.status_code == 204

    result = await db.execute(select(UserSession))
    session = result.scalars().one()
    assert session.is_revoked is True


async def test_revoked_session_cannot_refresh(client, user_factory):
    await user_factory(email="erin@example.com")
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    await client.post(
        "/talos/api/auth/signout", cookies={"refresh_token": refresh_token}
    )

    resp = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )
    assert resp.status_code == 401


async def test_session_listing_reflects_active_session(client, user_factory):
    await user_factory(email="erin@example.com")
    login_resp = await _login(client)
    access_token = login_resp.json()["access_token"]

    resp = await client.get(
        "/talos/api/sessions", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["is_revoked"] is False


async def test_revoking_one_session_does_not_affect_another(client, user_factory, db):
    await user_factory(email="erin@example.com")
    credentials = {"email": "erin@example.com", "password": "Password123!"}

    login_a = await client.post("/talos/api/auth/signin", json=credentials)
    login_b = await client.post("/talos/api/auth/signin", json=credentials)

    refresh_a = login_a.cookies.get("refresh_token")
    refresh_b = login_b.cookies.get("refresh_token")
    access_token = login_b.json()["access_token"]

    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token == get_refresh_token_hash(refresh_a)
        )
    )
    session_a = result.scalars().one()

    delete_resp = await client.delete(
        f"/talos/api/sessions/{session_a.uuid}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert delete_resp.status_code == 200

    refresh_a_after = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_a}
    )
    refresh_b_after = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_b}
    )

    assert refresh_a_after.status_code == 401
    assert refresh_b_after.status_code == 200
