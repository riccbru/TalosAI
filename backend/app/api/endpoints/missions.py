from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.agents.hybrid_orchestrator import HybridOrchestrator
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


@router.post("/hybrid")
async def hybrid_run_mission(request: MissionRequest) -> dict:
    orchestrator = HybridOrchestrator(target=request.target, user_prompt=request.prompt)
    result = orchestrator.run()
    print(result)

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


@router.post("/local")
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
