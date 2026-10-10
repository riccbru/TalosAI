"""Mechanism tests for the v2 mission lifecycle.

Exercises the real endpoints, DB persistence, ownership scoping and the
resume/cancel state machine WITHOUT standing up Kali, Metasploitable or Gemini:
the background worker (`mission_runner.launch`) is patched to a no-op spy, so
every assertion is about the HTTP + DB mechanism the orchestrator relies on.
The orchestrator itself is already stubbed by conftest in this environment.

DB is the in-memory SQLite from conftest; the endpoints use the overridden
get_db, and the fixtures below seed rows through the same engine.
"""
import threading
import uuid

import pytest
from sqlalchemy import select

import app.api.endpoints.missions as missions_module
from app.core.security import create_access_token
from app.models.missions import Finding, Mission, MissionPort
from app.services import mission_runner

pytestmark = pytest.mark.anyio

BASE = "/talos/api/missions"


def _auth(user) -> dict:
    token = create_access_token(str(user.uuid), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def no_launch(monkeypatch):
    """Replace the background worker with a spy so endpoints don't spawn threads."""
    calls = []

    def _fake_launch(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(missions_module.mission_runner, "launch", _fake_launch)
    return calls


@pytest.fixture
def mission_factory(db_sessionmaker):
    async def _create(
        user,
        *,
        status: str = "completed",
        target: str = "scanme.nmap.org",
        ports: list | None = None,
        findings: list | None = None,
    ) -> Mission:
        async with db_sessionmaker() as s:
            mission = Mission(
                user_uid=user.uuid,
                target=target,
                target_ip=target,
                prompt="probe",
                orchestrator_version="v2",
                status=status,
            )
            s.add(mission)
            await s.flush()
            for p in ports or []:
                s.add(
                    MissionPort(
                        mission_uid=mission.uuid,
                        port=p["port"],
                        service_name=p.get("service_name"),
                        version=p.get("version"),
                        status=p.get("status", "completed"),
                        attempts=p.get("attempts", 1),
                        history=p.get("history", []),
                    )
                )
            for f in findings or []:
                s.add(
                    Finding(
                        mission_uid=mission.uuid,
                        port=f.get("port"),
                        service_name=f.get("service_name"),
                        action=f.get("action"),
                        command=f.get("command"),
                        output=f.get("output"),
                        reasoning=f.get("reasoning"),
                        confirmed=f.get("confirmed", False),
                    )
                )
            await s.commit()
            await s.refresh(mission)
            return mission

    return _create


# --- launch (202 + persistence + association) ---


async def test_launch_returns_202_and_persists_for_user(
    client, user_factory, no_launch, db
):
    user = await user_factory()
    resp = await client.post(
        f"{BASE}/v2/test/hybrid",
        json={"target": "scanme.nmap.org", "prompt": "enumerate"},
        headers=_auth(user),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    mission_uuid = uuid.UUID(body["mission_uuid"])  # valid uuid

    res = await db.execute(select(Mission).where(Mission.uuid == mission_uuid))
    mission = res.scalar_one()
    assert mission.user_uid == user.uuid
    assert mission.target == "scanme.nmap.org"
    assert mission.prompt == "enumerate"

    # exactly one background launch, as a fresh (non-resume) run
    assert len(no_launch) == 1
    assert no_launch[0]["resume"] is False
    assert str(no_launch[0]["mission_uuid"]) == body["mission_uuid"]


async def test_launch_requires_auth(client):
    resp = await client.post(f"{BASE}/v2/test/hybrid", json={"target": "x"})
    assert resp.status_code == 401


# --- list + detail (ownership scoped) ---


async def test_list_returns_only_callers_missions(
    client, user_factory, mission_factory
):
    alice = await user_factory(email="alice@example.com")
    bob = await user_factory(email="bob@example.com")
    await mission_factory(alice)
    await mission_factory(alice)
    await mission_factory(bob)

    resp = await client.get(BASE, headers=_auth(alice))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_detail_returns_ports_and_findings(
    client, user_factory, mission_factory
):
    user = await user_factory()
    mission = await mission_factory(
        user,
        status="completed",
        ports=[{"port": 80, "service_name": "http", "version": "2.2.8"}],
        findings=[
            {
                "port": 80,
                "service_name": "http",
                "action": "EXECUTE_ATTACK",
                "command": "nmap -sV 10.0.0.1",
                "output": "80/tcp open http",
                "reasoning": "probe",
            }
        ],
    )

    resp = await client.get(f"{BASE}/{mission.uuid}", headers=_auth(user))
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["mission"]["uuid"] == str(mission.uuid)
    assert detail["mission"]["status"] == "completed"
    assert len(detail["ports"]) == 1 and detail["ports"][0]["port"] == 80
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["command"] == "nmap -sV 10.0.0.1"


async def test_detail_of_other_users_mission_is_404(
    client, user_factory, mission_factory
):
    owner = await user_factory(email="owner@example.com")
    intruder = await user_factory(email="intruder@example.com")
    mission = await mission_factory(owner)

    resp = await client.get(f"{BASE}/{mission.uuid}", headers=_auth(intruder))
    assert resp.status_code == 404


async def test_detail_with_unknown_uuid_is_404(client, user_factory):
    user = await user_factory()
    resp = await client.get(f"{BASE}/{uuid.uuid4()}", headers=_auth(user))
    assert resp.status_code == 404


# --- resume (only failed/interrupted) ---


@pytest.mark.parametrize("status", ["completed", "running", "pending"])
async def test_resume_non_resumable_is_409(
    client, user_factory, mission_factory, no_launch, status
):
    user = await user_factory()
    mission = await mission_factory(user, status=status)
    resp = await client.post(f"{BASE}/{mission.uuid}/resume", headers=_auth(user))
    assert resp.status_code == 409
    assert no_launch == []  # nothing launched


@pytest.mark.parametrize("status", ["failed", "interrupted"])
async def test_resume_resumable_launches_with_resume_true(
    client, user_factory, mission_factory, no_launch, status
):
    user = await user_factory()
    mission = await mission_factory(user, status=status)
    resp = await client.post(f"{BASE}/{mission.uuid}/resume", headers=_auth(user))
    assert resp.status_code == 202
    assert resp.json()["status"] == "running"
    assert len(no_launch) == 1
    assert no_launch[0]["resume"] is True
    assert str(no_launch[0]["mission_uuid"]) == str(mission.uuid)


async def test_resume_of_other_users_mission_is_404(
    client, user_factory, mission_factory, no_launch
):
    owner = await user_factory(email="o2@example.com")
    intruder = await user_factory(email="i2@example.com")
    mission = await mission_factory(owner, status="failed")
    resp = await client.post(f"{BASE}/{mission.uuid}/resume", headers=_auth(intruder))
    assert resp.status_code == 404
    assert no_launch == []


# --- cancel (stop without delete) ---


@pytest.mark.parametrize("status", ["completed", "failed", "interrupted"])
async def test_cancel_terminal_is_409(client, user_factory, mission_factory, status):
    user = await user_factory()
    mission = await mission_factory(user, status=status)
    resp = await client.post(f"{BASE}/{mission.uuid}/cancel", headers=_auth(user))
    assert resp.status_code == 409


async def test_cancel_running_with_live_worker_returns_cancelling(
    client, user_factory, mission_factory, monkeypatch, db
):
    user = await user_factory()
    mission = await mission_factory(user, status="running")
    monkeypatch.setattr(
        missions_module.mission_runner, "request_cancel", lambda _uuid: True
    )
    resp = await client.post(f"{BASE}/{mission.uuid}/cancel", headers=_auth(user))
    assert resp.status_code == 202
    assert resp.json()["status"] == "cancelling"
    # the worker (not the endpoint) flips the DB status, so it stays 'running' here
    res = await db.execute(select(Mission).where(Mission.uuid == mission.uuid))
    assert res.scalar_one().status == "running"


async def test_cancel_running_without_worker_marks_interrupted(
    client, user_factory, mission_factory, monkeypatch, db
):
    user = await user_factory()
    mission = await mission_factory(user, status="running")
    # no live worker in this process (e.g. after a restart): endpoint updates DB
    monkeypatch.setattr(
        missions_module.mission_runner, "request_cancel", lambda _uuid: False
    )
    resp = await client.post(f"{BASE}/{mission.uuid}/cancel", headers=_auth(user))
    assert resp.status_code == 202
    assert resp.json()["status"] == "interrupted"
    res = await db.execute(select(Mission).where(Mission.uuid == mission.uuid))
    assert res.scalar_one().status == "interrupted"


async def test_cancelled_mission_is_then_resumable(
    client, user_factory, mission_factory, no_launch, monkeypatch
):
    """cancel -> interrupted -> resume is accepted (the round trip)."""
    user = await user_factory()
    mission = await mission_factory(user, status="running")
    monkeypatch.setattr(
        missions_module.mission_runner, "request_cancel", lambda _uuid: False
    )
    cancel = await client.post(f"{BASE}/{mission.uuid}/cancel", headers=_auth(user))
    assert cancel.json()["status"] == "interrupted"

    resume = await client.post(f"{BASE}/{mission.uuid}/resume", headers=_auth(user))
    assert resume.status_code == 202
    assert no_launch[-1]["resume"] is True


# --- live-event pub/sub + cancel registry (the streaming/stop plumbing) ---


async def test_pubsub_broadcast_and_unsubscribe():
    mid = f"mech-{uuid.uuid4()}"
    queue = mission_runner.subscribe(mid)
    try:
        mission_runner._broadcast(mid, {"type": "log", "message": "hello"})
        event = queue.get_nowait()
        assert event["type"] == "log" and event["message"] == "hello"
    finally:
        mission_runner.unsubscribe(mid, queue)
    assert mid not in mission_runner._subscribers


async def test_request_cancel_sets_flag_or_reports_absent():
    mid = f"cancel-{uuid.uuid4()}"
    event = threading.Event()
    mission_runner._cancel_events[mid] = event
    try:
        assert mission_runner.request_cancel(mid) is True
        assert event.is_set()
        assert mission_runner.request_cancel("does-not-exist") is False
    finally:
        mission_runner._cancel_events.pop(mid, None)


# --- GET /{uuid}/findings: filtri + paginazione ---


async def test_findings_endpoint_returns_all_with_metadata(
    client, user_factory, mission_factory
):
    user = await user_factory()
    mission = await mission_factory(
        user,
        findings=[
            {"port": 21, "command": "a", "confirmed": True},
            {"port": 22, "command": "b", "confirmed": False},
            {"port": 22, "command": "c", "confirmed": False},
        ],
    )
    resp = await client.get(f"{BASE}/{mission.uuid}/findings", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["count"] == 3
    assert body["limit"] == 50 and body["offset"] == 0
    assert len(body["findings"]) == 3


async def test_findings_filter_by_port(client, user_factory, mission_factory):
    user = await user_factory()
    mission = await mission_factory(
        user,
        findings=[
            {"port": 21, "command": "a"},
            {"port": 22, "command": "b"},
            {"port": 22, "command": "c"},
        ],
    )
    resp = await client.get(
        f"{BASE}/{mission.uuid}/findings?port=22", headers=_auth(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {f["port"] for f in body["findings"]} == {22}


async def test_findings_filter_by_confirmed(client, user_factory, mission_factory):
    user = await user_factory()
    mission = await mission_factory(
        user,
        findings=[
            {"port": 21, "command": "a", "confirmed": True},
            {"port": 22, "command": "b", "confirmed": False},
        ],
    )
    resp = await client.get(
        f"{BASE}/{mission.uuid}/findings?confirmed=true", headers=_auth(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["findings"][0]["confirmed"] is True


async def test_findings_pagination(client, user_factory, mission_factory):
    user = await user_factory()
    mission = await mission_factory(
        user,
        findings=[{"port": 80, "command": f"cmd-{i}"} for i in range(5)],
    )
    resp = await client.get(
        f"{BASE}/{mission.uuid}/findings?limit=2&offset=2", headers=_auth(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["count"] == 2
    assert body["limit"] == 2 and body["offset"] == 2
    assert body["findings"][0]["command"] == "cmd-2"  # chronological (id asc)


async def test_findings_of_other_users_mission_is_404(
    client, user_factory, mission_factory
):
    owner = await user_factory(email="fo@example.com")
    intruder = await user_factory(email="fi@example.com")
    mission = await mission_factory(owner, findings=[{"port": 21, "command": "a"}])
    resp = await client.get(f"{BASE}/{mission.uuid}/findings", headers=_auth(intruder))
    assert resp.status_code == 404


async def test_findings_invalid_limit_is_422(client, user_factory, mission_factory):
    user = await user_factory()
    mission = await mission_factory(user)
    too_big = await client.get(
        f"{BASE}/{mission.uuid}/findings?limit=999", headers=_auth(user)
    )
    assert too_big.status_code == 422
    zero = await client.get(
        f"{BASE}/{mission.uuid}/findings?limit=0", headers=_auth(user)
    )
    assert zero.status_code == 422
