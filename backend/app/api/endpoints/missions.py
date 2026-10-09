import asyncio
import uuid as uuid_lib

import docker
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hybrid_orchestrator_v1 import HybridOrchestratorV1
from app.agents.local_orchestrator import LocalOrchestrator
from app.api.deps import get_current_user
from app.core.security import decode_access_token
from app.crud import crud_missions
from app.db.session import AsyncSessionLocal, get_db
from app.models.missions import RESUMABLE_STATUSES
from app.models.users import User
from app.schemas.missions import MissionRequest
from app.services import mission_runner


router = APIRouter()
ws_router = APIRouter()  # mounted WITHOUT the HTTP auth dependency (see main.py)


def get_mission_error(e: Exception, target: str) -> dict:
    error_type = type(e).__name__

    if "APIConnectionError" in error_type or "ConnectionError" in error_type:
        error_code = "PROVIDER_UNREACHABLE"
        msg = "Could not connect to the AI model provider (Ollama)"
    elif "ValidationError" in error_type:
        error_code = "CONFIG_ERROR"
        msg = "Invalid agent or task configuration."
    else:
        error_code = "ORCHESTRATION_FAILED"
        msg = str(e.args[-1]) if e.args else str(e)

    return {
        "status": "failed",
        "target": target,
        "error_code": error_code,
        "details": {"type": error_type, "message": msg},
    }


def resolve_target_ip(target: str) -> str:
    if (target.strip().lower() != 'metasploitable'):
        return target
    else:
        try:
            client = docker.from_env()
            container = client.containers.get('talos_metasploitable')

            networks = container.attrs['NetworkSettings']['Networks']
            for net_name, net_info in networks.items():
                ip = net_info['IPAddress']
                if ip:
                    return ip
        except Exception as e:
            print(
                f"\033[1;41m[DOCKER API ERROR]\033[0m] " \
                f"Impossible to inspect container {'talos_metasploitable'}: {e}"
            )
    return target


@router.post("/v1/test/local")
def local_run_mission(request: MissionRequest) -> dict:
    try:
        orchestrator = LocalOrchestrator(
            target=request.target, user_prompt=request.prompt
        )
        result = orchestrator.run()

        if "error" in result:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=get_mission_error(result["error"], request.target),
            )

        return {"status": "completed", "target": request.target, "data": result}

    except Exception as e:
        error_body = get_mission_error(e, request.target)

        if "Connection" in type(e).__name__:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(status_code=status_code, content=error_body)


@router.post("/v1/test/hybrid")
def hybrid_run_mission_v1(request: MissionRequest) -> dict:
    try:
        target = resolve_target_ip(request.target)
        orchestrator = HybridOrchestratorV1(
            target=target,
            user_prompt=request.prompt
        )
        result = orchestrator.run()

        if result.get("status") in ["failed", "error"]:

            if result.get("source") == "google":
                return JSONResponse(
                    content=result["details"],
                    status_code=result["code"]
                )

            return JSONResponse(
                content=result,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return result
    except Exception as e:
        error_body = get_mission_error(e, request.target)

        if "Connection" in type(e).__name__:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(status_code=status_code, content=error_body)


@router.post("/v2/test/hybrid", status_code=status.HTTP_202_ACCEPTED)
async def hybrid_run_mission_v2(
    request: MissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create the mission, return its uuid immediately, run it in the background."""
    target_ip = resolve_target_ip(request.target)

    mission = await crud_missions.create_mission(
        db,
        user_uid=current_user.uuid,
        target=request.target,
        target_ip=target_ip,
        prompt=request.prompt,
        version="v2",
    )
    await db.commit()

    mission_runner.launch(
        mission_uuid=mission.uuid,
        target=request.target,
        target_ip=target_ip,
        prompt=request.prompt,
        loop=asyncio.get_running_loop(),
        resume=False,
    )

    return {"mission_uuid": str(mission.uuid), "status": mission.status}


@router.get("")
async def list_missions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    missions = await crud_missions.list_missions(db, current_user.uuid)
    return [crud_missions.serialize_mission(m) for m in missions]


async def _require_owned_mission(
    db: AsyncSession, mission_uuid: str, user_uid
):
    try:
        mission = await crud_missions.get_mission(db, mission_uuid, user_uid=user_uid)
    except (ValueError, AttributeError):
        mission = None
    if mission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found"
        )
    return mission


@router.get("/{mission_uuid}")
async def get_mission_detail(
    mission_uuid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    mission = await _require_owned_mission(db, mission_uuid, current_user.uuid)
    ports = await crud_missions.get_ports(db, mission.uuid)
    findings = await crud_missions.get_findings(db, mission.uuid)
    return {
        "mission": crud_missions.serialize_mission(mission),
        "ports": [crud_missions.serialize_port(p) for p in ports],
        "findings": [crud_missions.serialize_finding(f) for f in findings],
    }


@router.post("/{mission_uuid}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_mission(
    mission_uuid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    mission = await _require_owned_mission(db, mission_uuid, current_user.uuid)

    if mission.status not in RESUMABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Mission is '{mission.status}'; only "
                f"{list(RESUMABLE_STATUSES)} missions can be resumed."
            ),
        )

    target_ip = mission.target_ip or resolve_target_ip(mission.target)

    mission_runner.launch(
        mission_uuid=mission.uuid,
        target=mission.target,
        target_ip=target_ip,
        prompt=mission.prompt,
        loop=asyncio.get_running_loop(),
        resume=True,
    )

    return {"mission_uuid": str(mission.uuid), "status": "running"}


@router.post("/{mission_uuid}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_mission(
    mission_uuid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stop a running mission without deleting it; it becomes 'interrupted'.

    Cancellation is cooperative: the worker stops at its next checkpoint, so an
    in-flight command finishes first. An 'interrupted' mission is resumable.
    """
    mission = await _require_owned_mission(db, mission_uuid, current_user.uuid)

    if mission.status not in ("running", "pending"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Mission is '{mission.status}'; only running or pending "
                "missions can be cancelled."
            ),
        )

    signalled = mission_runner.request_cancel(str(mission.uuid))
    if signalled:
        # A live worker will flip the mission to 'interrupted' at its checkpoint.
        return {"mission_uuid": str(mission.uuid), "status": "cancelling"}

    # No worker tracked in this process (e.g. a stale 'running' after a restart):
    # mark it interrupted directly so the record reflects reality.
    await crud_missions.update_mission_status(db, mission.uuid, "interrupted")
    await db.commit()
    return {"mission_uuid": str(mission.uuid), "status": "interrupted"}


@ws_router.websocket("/ws/{mission_uuid}")
async def mission_stream(
    websocket: WebSocket,
    mission_uuid: str,
    token: str = Query(..., description="A valid access JWT"),
):
    """Live stream of a mission's reasoning, actions and findings.

    Auth is via `?token=<access_jwt>` because browsers can't set the
    Authorization header on a WebSocket handshake. On connect the client gets a
    full snapshot, then incremental events until the mission reaches a terminal
    state. Dedupe findings by their `uuid` (a brief snapshot/stream overlap is
    possible by design).
    """
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=4401)  # unauthorized
        return
    user_uid = payload["sub"]

    try:
        mission_key = str(uuid_lib.UUID(str(mission_uuid)))
    except ValueError:
        await websocket.close(code=4404)
        return

    # Subscribe BEFORE reading the snapshot so no event is lost in between.
    queue = mission_runner.subscribe(mission_key)
    try:
        async with AsyncSessionLocal() as db:
            mission = await crud_missions.get_mission(
                db, mission_key, user_uid=user_uid
            )
            if mission is None:
                await websocket.close(code=4404)
                return
            ports = await crud_missions.get_ports(db, mission_key)
            findings = await crud_missions.get_findings(db, mission_key)
            snapshot = {
                "type": "snapshot",
                "mission": crud_missions.serialize_mission(mission),
                "ports": [crud_missions.serialize_port(p) for p in ports],
                "findings": [crud_missions.serialize_finding(f) for f in findings],
            }
            terminal = mission.status in (
                "completed",
                "failed",
                "interrupted",
            )

        await websocket.accept()
        await websocket.send_json(snapshot)

        if terminal:
            await websocket.send_json(
                {"type": "mission_status", "status": snapshot["mission"]["status"]}
            )
            return

        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") == "mission_status" and event.get("status") in (
                "completed",
                "failed",
                "interrupted",
            ):
                break
    except WebSocketDisconnect:
        pass
    finally:
        mission_runner.unsubscribe(mission_key, queue)
