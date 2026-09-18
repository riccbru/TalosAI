import pytest
from sqlalchemy import select

from app.models.sessions import UserSession


pytestmark = pytest.mark.anyio


async def _login(client, email="user@example.com", password="Password123!"):
    resp = await client.post(
        "/talos/api/auth/signin", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp


async def _get_only_session(db) -> UserSession:
    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    return sessions[0]


async def test_refresh_succeeds(client, user_factory):
    await user_factory()
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    resp = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["access_token"]
    assert resp.cookies.get("refresh_token")


async def test_refresh_does_not_create_a_second_session_row(client, user_factory, db):
    await user_factory()
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )

    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1


async def test_refresh_keeps_same_session_id(client, user_factory, db):
    await user_factory()
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    session_before = await _get_only_session(db)
    session_id_before = session_before.uuid

    await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )

    session_after = await _get_only_session(db)
    assert session_after.uuid == session_id_before


async def test_refresh_rotates_the_refresh_token(client, user_factory):
    await user_factory()
    login_resp = await _login(client)
    old_refresh_token = login_resp.cookies.get("refresh_token")

    refresh_resp = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": old_refresh_token}
    )
    new_refresh_token = refresh_resp.cookies.get("refresh_token")

    assert new_refresh_token
    assert new_refresh_token != old_refresh_token


async def test_old_refresh_token_cannot_be_reused_after_rotation(client, user_factory):
    await user_factory()
    login_resp = await _login(client)
    old_refresh_token = login_resp.cookies.get("refresh_token")

    first_refresh = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": old_refresh_token}
    )
    assert first_refresh.status_code == 200

    replay = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": old_refresh_token}
    )
    assert replay.status_code == 401


async def test_new_refresh_token_works(client, user_factory):
    await user_factory()
    login_resp = await _login(client)
    old_refresh_token = login_resp.cookies.get("refresh_token")

    first_refresh = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": old_refresh_token}
    )
    new_refresh_token = first_refresh.cookies.get("refresh_token")

    second_refresh = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": new_refresh_token}
    )
    assert second_refresh.status_code == 200


async def test_refresh_extends_expiration(client, user_factory, db):
    await user_factory()
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    session_before = await _get_only_session(db)
    expires_before = session_before.expires_at

    await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )

    session_after = await _get_only_session(db)
    assert session_after.expires_at >= expires_before


async def test_refresh_updates_last_active(client, user_factory, db):
    await user_factory()
    login_resp = await _login(client)
    refresh_token = login_resp.cookies.get("refresh_token")

    session_before = await _get_only_session(db)
    last_active_before = session_before.last_active

    await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )

    session_after = await _get_only_session(db)
    assert session_after.last_active >= last_active_before


async def test_refresh_without_cookie_is_rejected(client, user_factory):
    await user_factory()
    await _login(client)

    resp = await client.post("/talos/api/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_with_garbage_token_is_rejected(client, user_factory):
    await user_factory()
    await _login(client)

    resp = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": "not-a-real-token"}
    )
    assert resp.status_code == 401
