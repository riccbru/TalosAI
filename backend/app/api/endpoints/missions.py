import docker
import xmltodict
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.agents.hybrid_orechstrator import HybridOrchestrator
from app.agents.local_orchestrator import LocalOrchestrator
from app.schemas.missions import MissionRequest


router = APIRouter()


def get_mission_error(e: Exception, target: str) -> dict:
    error_type = type(e).__name__

    if "APIConnectionError" in error_type or "ConnectionError" in error_type:
        error_code = "PROVIDER_UNREACHABLE"
        msg = "Could not connect to the AI model provider (Ollama)."
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


@router.post("/run/hybrid")
async def hybrid_run_mission(request: MissionRequest) -> dict:
    orchestrator = HybridOrchestrator(target=request.target, user_prompt=request.prompt)
    result = orchestrator.run()

    if result["status"] == "failed":
        return JSONResponse(
            content=result,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return result


@router.post("/run/local")
async def local_run_mission(request: MissionRequest) -> dict:
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


@router.get("/test/metasploitable/local")
async def run_test() -> dict:
    try:
        client = docker.from_env()
        kali = client.containers.get("talos_kali")
        target_container = client.containers.get("talos_metasploitable")
        target_ip = target_container.attrs["NetworkSettings"]["Networks"][
            "talos_network"
        ]["IPAddress"]  # noqa: E501
        cmd = f"nmap -oX - -n -Pn --top-ports 20 -sV -T4 {target_ip}"
        exec_result = kali.exec_run(cmd)
        data = xmltodict.parse(exec_result.output.decode())
        return {"result": data}
    except Exception as e:
        return JSONResponse(status_code=500, content=e)
