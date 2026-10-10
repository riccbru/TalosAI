import uuid as uuid_lib
from datetime import datetime, timezone
from typing import List, Optional, Union

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.missions import (
    Finding,
    Mission,
    MissionPort,
    TERMINAL_STATUSES,
)

UUIDLike = Union[str, uuid_lib.UUID]


def _as_uuid(value: UUIDLike) -> uuid_lib.UUID:
    return value if isinstance(value, uuid_lib.UUID) else uuid_lib.UUID(str(value))


async def create_mission(
    db: AsyncSession,
    *,
    user_uid: UUIDLike,
    target: str,
    target_ip: Optional[str],
    prompt: Optional[str],
    version: str = "v2",
) -> Mission:
    mission = Mission(
        user_uid=_as_uuid(user_uid),
        target=target,
        target_ip=target_ip,
        prompt=prompt,
        orchestrator_version=version,
    )
    db.add(mission)
    await db.flush()
    await db.refresh(mission)
    return mission


async def get_mission(
    db: AsyncSession, mission_uuid: UUIDLike, user_uid: Optional[UUIDLike] = None
) -> Optional[Mission]:
    stmt = select(Mission).where(Mission.uuid == _as_uuid(mission_uuid))
    if user_uid is not None:
        stmt = stmt.where(Mission.user_uid == _as_uuid(user_uid))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_missions(db: AsyncSession, user_uid: UUIDLike) -> List[Mission]:
    stmt = (
        select(Mission)
        .where(Mission.user_uid == _as_uuid(user_uid))
        .order_by(Mission.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_ports(db: AsyncSession, mission_uuid: UUIDLike) -> List[MissionPort]:
    stmt = (
        select(MissionPort)
        .where(MissionPort.mission_uid == _as_uuid(mission_uuid))
        .order_by(MissionPort.port.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_findings(db: AsyncSession, mission_uuid: UUIDLike) -> List[Finding]:
    stmt = (
        select(Finding)
        .where(Finding.mission_uid == _as_uuid(mission_uuid))
        .order_by(Finding.created_at.asc(), Finding.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_findings_filtered(
    db: AsyncSession,
    mission_uuid: UUIDLike,
    *,
    port: Optional[int] = None,
    confirmed: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[Finding], int]:
    """Return (page of findings, total matching count), chronological order."""
    filters = [Finding.mission_uid == _as_uuid(mission_uuid)]
    if port is not None:
        filters.append(Finding.port == port)
    if confirmed is not None:
        filters.append(Finding.confirmed == confirmed)

    total = await db.scalar(
        select(func.count()).select_from(Finding).where(*filters)
    )
    stmt = (
        select(Finding)
        .where(*filters)
        .order_by(Finding.created_at.asc(), Finding.id.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), int(total or 0)


async def set_discovered(
    db: AsyncSession, mission_uuid: UUIDLike, discovered: bool = True
) -> None:
    mission = await get_mission(db, mission_uuid)
    if mission:
        mission.discovered = discovered
        await db.flush()


async def replace_ports(
    db: AsyncSession, mission_uuid: UUIDLike, services: List[dict]
) -> None:
    mid = _as_uuid(mission_uuid)
    await db.execute(delete(MissionPort).where(MissionPort.mission_uid == mid))
    for svc in services:
        db.add(
            MissionPort(
                mission_uid=mid,
                port=svc["port"],
                service_name=svc.get("service_name"),
                version=svc.get("version"),
                status=svc.get("status", "pending"),
                attempts=svc.get("attempts", 0),
                history=svc.get("history") or [],
            )
        )
    await db.flush()


async def update_port(
    db: AsyncSession,
    mission_uuid: UUIDLike,
    port: int,
    status: str,
    attempts: int,
    history: List[dict],
) -> None:
    stmt = select(MissionPort).where(
        MissionPort.mission_uid == _as_uuid(mission_uuid),
        MissionPort.port == port,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.status = status
    row.attempts = attempts
    row.history = history
    await db.flush()


async def add_finding(
    db: AsyncSession, mission_uuid: UUIDLike, data: dict
) -> Finding:
    finding = Finding(
        mission_uid=_as_uuid(mission_uuid),
        port=data.get("port"),
        service_name=data.get("service_name"),
        action=data.get("action"),
        command=data.get("command"),
        output=data.get("output"),
        reasoning=data.get("reasoning"),
        confirmed=bool(data.get("confirmed", False)),
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


async def update_mission_status(
    db: AsyncSession,
    mission_uuid: UUIDLike,
    status: str,
    error: Optional[str] = None,
) -> None:
    mission = await get_mission(db, mission_uuid)
    if mission is None:
        return
    mission.status = status
    if error is not None:
        mission.error = error
    now = datetime.now(timezone.utc)
    if status == "running" and mission.started_at is None:
        mission.started_at = now
    if status in TERMINAL_STATUSES:
        mission.finished_at = now
    await db.flush()


# --- JSON-safe serializers (shared by HTTP responses and the WebSocket stream) ---


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def serialize_mission(mission: Mission) -> dict:
    return {
        "uuid": str(mission.uuid),
        "target": mission.target,
        "target_ip": mission.target_ip,
        "prompt": mission.prompt,
        "orchestrator_version": mission.orchestrator_version,
        "status": mission.status,
        "discovered": mission.discovered,
        "error": mission.error,
        "created_at": _iso(mission.created_at),
        "updated_at": _iso(mission.updated_at),
        "started_at": _iso(mission.started_at),
        "finished_at": _iso(mission.finished_at),
    }


def serialize_port(port: MissionPort) -> dict:
    return {
        "port": port.port,
        "service_name": port.service_name,
        "version": port.version,
        "status": port.status,
        "attempts": port.attempts,
    }


def serialize_finding(finding: Finding) -> dict:
    return {
        "uuid": str(finding.uuid),
        "port": finding.port,
        "service_name": finding.service_name,
        "action": finding.action,
        "command": finding.command,
        "output": finding.output,
        "reasoning": finding.reasoning,
        "confirmed": finding.confirmed,
        "created_at": _iso(finding.created_at),
    }
