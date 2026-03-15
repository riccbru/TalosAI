from fastapi import APIRouter, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.agents.orchestrator import Orchestrator
from app.schemas.mission import MissionRequest

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
        "details": {
            "type": error_type,
            "message": msg
        }
    }

@router.post("/run")
async def run_mission(request: MissionRequest):
    try:
        orchestrator = Orchestrator(target=request.target)
        result = orchestrator.run()

        clean_data = jsonable_encoder(result.pydantic) if result.pydantic else result.raw

        return {
            "status": "completed",
            "target": request.target,
            "data": clean_data
        }

    except Exception as e:
        error_body = get_mission_error(e, request.target)

        if "Connection" in type(e).__name__:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(
            status_code=status_code,
            content=error_body
        )
