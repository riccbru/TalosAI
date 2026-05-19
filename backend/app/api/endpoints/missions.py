import docker
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.agents.hybrid_orchestrator_v1 import HybridOrchestratorV1
from app.agents.hybrid_orchestrator_v2 import HybridOrchestratorV2
from app.agents.local_orchestrator import LocalOrchestrator
from app.schemas.missions import MissionRequest


router = APIRouter()


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
        print(f"\033[1;45mRESULT\033[0m\n{result}")

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


@router.post("/v2/test/hybrid")
def hybrid_run_mission_v2(request: MissionRequest) -> dict:
    try:
        target = resolve_target_ip(request.target)
        orchestrator = HybridOrchestratorV2(
            target=target,
            user_prompt=request.prompt
        )
        result = orchestrator.run()
        print(f"\033[1;45mRESULT\033[0m\n{result}")

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
