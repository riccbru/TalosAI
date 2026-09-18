"""Regression test for the originally reported bug:

    login -> session A
    refresh -> still session A (no new row)
    refresh again -> still session A (no new row)
    login again -> session B (a genuinely new, independent login)

Final DB state must be exactly {session A, session B}, not one row per
refresh cycle.
"""

import pytest
from sqlalchemy import select

from app.models.sessions import UserSession


pytestmark = pytest.mark.anyio


async def test_repeated_refresh_does_not_multiply_sessions(client, user_factory, db):
    await user_factory(email="frank@example.com", password="Password123!")
    credentials = {"email": "frank@example.com", "password": "Password123!"}

    login_1 = await client.post("/talos/api/auth/signin", json=credentials)
    assert login_1.status_code == 200
    refresh_token = login_1.cookies.get("refresh_token")

    result = await db.execute(select(UserSession))
    session_a_id = result.scalars().one().uuid

    refresh_1 = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )
    assert refresh_1.status_code == 200
    refresh_token = refresh_1.cookies.get("refresh_token")

    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].uuid == session_a_id

    refresh_2 = await client.post(
        "/talos/api/auth/refresh", cookies={"refresh_token": refresh_token}
    )
    assert refresh_2.status_code == 200

    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].uuid == session_a_id

    login_2 = await client.post("/talos/api/auth/signin", json=credentials)
    assert login_2.status_code == 200

    result = await db.execute(select(UserSession))
    sessions = result.scalars().all()

    assert len(sessions) == 2
    session_ids = {s.uuid for s in sessions}
    assert session_a_id in session_ids
    assert all(not s.is_revoked for s in sessions)
